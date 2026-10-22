"""Ponto único de composição das dependências da aplicação."""

from dataclasses import dataclass

from backend.app.core.config import Settings, get_settings
from backend.app.modules.students.application.listeners import (
    StudentRegisteredAuditListener,
)
from backend.app.modules.students.application.use_cases import ListStudents, RegisterStudent
from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.modules.students.infrastructure.supabase_repository import (
    SupabaseStudentRepository,
)
from backend.app.shared.application.event_bus import EventBus
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


@dataclass(frozen=True, slots=True)
class StudentServices:
    """Casos de uso vinculados ao armazenamento e à identidade da requisição."""

    register_student: RegisterStudent
    list_students: ListStudents


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Mantém recursos globais e cria serviços seguros por requisição."""

    event_bus: EventBus
    in_memory_student_store: InMemoryStudentRepository | None
    supabase_gateway: SupabaseRPCGateway | None

    def students_for(self, context: RequestContext) -> StudentServices:
        if self.supabase_gateway is not None:
            # O adaptador é barato e nasce por requisição para manter o JWT
            # efêmero isolado; o gateway HTTP compartilhado preserva conexões.
            store = SupabaseStudentRepository(self.supabase_gateway, context)
            return StudentServices(
                register_student=RegisterStudent(store, self.event_bus),
                list_students=ListStudents(store),
            )

        if self.in_memory_student_store is None:
            raise RuntimeError("O container não possui armazenamento de alunos.")

        # O modo em memória serve apenas ao desenvolvimento/testes. Ainda exige
        # autenticação na camada HTTP para não criar dois contratos de segurança.
        return StudentServices(
            register_student=RegisterStudent(self.in_memory_student_store, self.event_bus),
            list_students=ListStudents(self.in_memory_student_store),
        )

    async def close(self) -> None:
        """Encerra pools criados pela aplicação sem tocar em clientes injetados."""

        if self.supabase_gateway is not None:
            await self.supabase_gateway.close()


def build_container(settings: Settings | None = None) -> ApplicationContainer:
    current_settings = settings or get_settings()
    event_bus = EventBus()
    event_bus.subscribe(StudentRegistered, StudentRegisteredAuditListener())

    has_url = current_settings.supabase_url is not None
    has_key = current_settings.supabase_publishable_key is not None
    if has_url != has_key:
        # Configuração parcial nunca recua silenciosamente para memória; isso
        # poderia fazer uma implantação aceitar dados e perdê-los no reinício.
        raise ValueError("Configure SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY em conjunto.")

    if current_settings.supabase_url and current_settings.supabase_publishable_key:
        return ApplicationContainer(
            event_bus=event_bus,
            in_memory_student_store=None,
            supabase_gateway=SupabaseRPCGateway(
                current_settings.supabase_url,
                current_settings.supabase_publishable_key,
            ),
        )

    if current_settings.environment not in {"development", "test"}:
        # Em produção/staging, memória seria perda silenciosa no primeiro cold
        # start. A aplicação recusa inicializar até a persistência estar completa.
        raise ValueError("Supabase é obrigatório fora de development e test.")

    return ApplicationContainer(
        event_bus=event_bus,
        in_memory_student_store=InMemoryStudentRepository(),
        supabase_gateway=None,
    )
