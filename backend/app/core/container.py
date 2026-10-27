"""Ponto único de composição das dependências da aplicação."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.core.config import Settings, get_settings
from backend.app.modules.classes.application.use_cases import (
    ChangeClassActivation,
    ChangeModalityActivation,
    CreateClass,
    CreateModality,
    GetClass,
    GetModality,
    ListClasses,
    ListModalities,
    UpdateClass,
    UpdateModality,
)
from backend.app.modules.classes.infrastructure.repositories import InMemoryClassRepository
from backend.app.modules.classes.infrastructure.supabase_repository import (
    SupabaseClassRepository,
)
from backend.app.modules.enrollments.application.use_cases import (
    ChangeEnrollmentStatus,
    CreateEnrollment,
    GetEnrollment,
    ListEnrollments,
)
from backend.app.modules.enrollments.domain.repositories import EnrollmentRepository
from backend.app.modules.enrollments.infrastructure.repositories import InMemoryEnrollmentRepository
from backend.app.modules.enrollments.infrastructure.supabase_repository import (
    SupabaseEnrollmentRepository,
)
from backend.app.modules.identity.application.use_cases import (
    ChangeProfileActivation,
    ChangeProfileRole,
    GetMyProfile,
    ListProfiles,
    UpdateMyProfile,
)
from backend.app.modules.identity.infrastructure.repositories import InMemoryProfileRepository
from backend.app.modules.identity.infrastructure.supabase_profiles import SupabaseProfileRepository
from backend.app.modules.operations.application.health import (
    LocalReadinessProbe,
    ReadinessProbe,
)
from backend.app.modules.operations.infrastructure.supabase_health import (
    SupabaseReadinessProbe,
)
from backend.app.modules.students.application.listeners import (
    StudentRegisteredAuditListener,
)
from backend.app.modules.students.application.use_cases import (
    AddStudentGuardian,
    ChangeStudentStatus,
    GetStudent,
    GetStudentGuardian,
    ListStudentGuardians,
    ListStudents,
    RegisterStudent,
    SetPrimaryGuardian,
    UnlinkStudentGuardian,
    UpdateStudent,
    UpdateStudentGuardian,
)
from backend.app.modules.students.domain.entities import StudentStatus
from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.modules.students.infrastructure.supabase_repository import (
    SupabaseStudentRepository,
)
from backend.app.shared.application.event_bus import EventBus
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import SupabaseRPCGateway


@dataclass(frozen=True, slots=True)
class IdentityServices:
    """Casos de uso de perfil vinculados à identidade atual."""

    get_my_profile: GetMyProfile
    update_my_profile: UpdateMyProfile
    list_profiles: ListProfiles
    change_profile_role: ChangeProfileRole
    activate_profile: ChangeProfileActivation
    deactivate_profile: ChangeProfileActivation


@dataclass(frozen=True, slots=True)
class StudentServices:
    """Casos de uso vinculados ao armazenamento e à identidade da requisição."""

    register_student: RegisterStudent
    get_student: GetStudent
    update_student: UpdateStudent
    activate_student: ChangeStudentStatus
    deactivate_student: ChangeStudentStatus
    list_students: ListStudents
    list_guardians: ListStudentGuardians
    get_guardian: GetStudentGuardian
    add_guardian: AddStudentGuardian
    update_guardian: UpdateStudentGuardian
    set_primary_guardian: SetPrimaryGuardian
    unlink_guardian: UnlinkStudentGuardian


@dataclass(frozen=True, slots=True)
class ClassServices:
    """Casos de uso do catálogo vinculados ao perfil da requisição."""

    list_modalities: ListModalities
    get_modality: GetModality
    create_modality: CreateModality
    update_modality: UpdateModality
    activate_modality: ChangeModalityActivation
    deactivate_modality: ChangeModalityActivation
    list_classes: ListClasses
    get_class: GetClass
    create_class: CreateClass
    update_class: UpdateClass
    activate_class: ChangeClassActivation
    deactivate_class: ChangeClassActivation


@dataclass(frozen=True, slots=True)
class EnrollmentServices:
    create: CreateEnrollment
    get: GetEnrollment
    cancel: ChangeEnrollmentStatus
    reactivate: ChangeEnrollmentStatus
    list: ListEnrollments


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Mantém recursos globais e cria serviços seguros por requisição."""

    event_bus: EventBus
    readiness_probe: ReadinessProbe
    in_memory_profile_store: InMemoryProfileRepository | None
    in_memory_student_store: InMemoryStudentRepository | None
    supabase_gateway: SupabaseRPCGateway | None
    in_memory_class_store: InMemoryClassRepository | None = None
    in_memory_enrollment_store: InMemoryEnrollmentRepository | None = None

    def identity_for(self, context: RequestContext) -> IdentityServices:
        if self.supabase_gateway is not None:
            store = SupabaseProfileRepository(self.supabase_gateway, context)
            return self._identity_services(store, context)
        if self.in_memory_profile_store is None:
            raise RuntimeError("O container não possui armazenamento de perfis.")
        return self._identity_services(self.in_memory_profile_store, context)

    def _identity_services(
        self,
        store: InMemoryProfileRepository | SupabaseProfileRepository,
        context: RequestContext,
    ) -> IdentityServices:
        actor_id = context.user.user_id
        return IdentityServices(
            get_my_profile=GetMyProfile(store, actor_id),
            update_my_profile=UpdateMyProfile(store, self.event_bus, actor_id),
            list_profiles=ListProfiles(store, store, actor_id),
            change_profile_role=ChangeProfileRole(store, self.event_bus, actor_id),
            activate_profile=ChangeProfileActivation(store, self.event_bus, actor_id, True),
            deactivate_profile=ChangeProfileActivation(store, self.event_bus, actor_id, False),
        )

    def students_for(self, context: RequestContext) -> StudentServices:
        if self.supabase_gateway is not None:
            # O adaptador é barato e nasce por requisição para manter o JWT
            # efêmero isolado; o gateway HTTP compartilhado preserva conexões.
            store = SupabaseStudentRepository(self.supabase_gateway, context)
            return self._student_services(store)

        if self.in_memory_student_store is None:
            raise RuntimeError("O container não possui armazenamento de alunos.")

        # O modo em memória serve apenas ao desenvolvimento/testes. Ainda exige
        # autenticação na camada HTTP para não criar dois contratos de segurança.
        return self._student_services(self.in_memory_student_store)

    def _student_services(
        self,
        store: InMemoryStudentRepository | SupabaseStudentRepository,
    ) -> StudentServices:
        return StudentServices(
            register_student=RegisterStudent(store, self.event_bus),
            get_student=GetStudent(store),
            update_student=UpdateStudent(store, self.event_bus),
            activate_student=ChangeStudentStatus(
                store,
                self.event_bus,
                StudentStatus.ACTIVE,
            ),
            deactivate_student=ChangeStudentStatus(
                store,
                self.event_bus,
                StudentStatus.INACTIVE,
            ),
            list_students=ListStudents(store),
            list_guardians=ListStudentGuardians(store),
            get_guardian=GetStudentGuardian(store),
            add_guardian=AddStudentGuardian(store, self.event_bus),
            update_guardian=UpdateStudentGuardian(store, self.event_bus),
            set_primary_guardian=SetPrimaryGuardian(store, self.event_bus),
            unlink_guardian=UnlinkStudentGuardian(store, self.event_bus),
        )

    def classes_for(self, context: RequestContext) -> ClassServices:
        actor_id = context.user.user_id
        if self.supabase_gateway is not None:
            catalog = SupabaseClassRepository(self.supabase_gateway, context)
            profiles = SupabaseProfileRepository(self.supabase_gateway, context)
            return self._class_services(catalog, profiles, actor_id)
        if self.in_memory_class_store is None or self.in_memory_profile_store is None:
            raise RuntimeError("O container não possui armazenamento de turmas.")
        return self._class_services(
            self.in_memory_class_store,
            self.in_memory_profile_store,
            actor_id,
        )

    def enrollments_for(self, context: RequestContext) -> EnrollmentServices:
        store: EnrollmentRepository
        if self.supabase_gateway is not None:
            store = SupabaseEnrollmentRepository(self.supabase_gateway, context)
        elif self.in_memory_enrollment_store is not None:
            store = self.in_memory_enrollment_store
        else:
            raise RuntimeError("O container não possui armazenamento de matrículas.")
        return EnrollmentServices(
            create=CreateEnrollment(store),
            get=GetEnrollment(store),
            cancel=ChangeEnrollmentStatus(store, False),
            reactivate=ChangeEnrollmentStatus(store, True),
            list=ListEnrollments(store),
        )

    def _class_services(
        self,
        catalog: InMemoryClassRepository | SupabaseClassRepository,
        profiles: InMemoryProfileRepository | SupabaseProfileRepository,
        actor_id: UUID,
    ) -> ClassServices:
        return ClassServices(
            list_modalities=ListModalities(catalog, profiles, actor_id),
            get_modality=GetModality(catalog, profiles, actor_id),
            create_modality=CreateModality(catalog, profiles, self.event_bus, actor_id),
            update_modality=UpdateModality(catalog, profiles, self.event_bus, actor_id),
            activate_modality=ChangeModalityActivation(
                catalog, profiles, self.event_bus, actor_id, True
            ),
            deactivate_modality=ChangeModalityActivation(
                catalog, profiles, self.event_bus, actor_id, False
            ),
            list_classes=ListClasses(catalog, profiles, actor_id),
            get_class=GetClass(catalog, profiles, actor_id),
            create_class=CreateClass(catalog, catalog, profiles, self.event_bus, actor_id),
            update_class=UpdateClass(catalog, catalog, profiles, self.event_bus, actor_id),
            activate_class=ChangeClassActivation(
                catalog, catalog, profiles, self.event_bus, actor_id, True
            ),
            deactivate_class=ChangeClassActivation(
                catalog, catalog, profiles, self.event_bus, actor_id, False
            ),
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
        gateway = SupabaseRPCGateway(
            current_settings.supabase_url,
            current_settings.supabase_publishable_key,
        )
        return ApplicationContainer(
            event_bus=event_bus,
            readiness_probe=SupabaseReadinessProbe(gateway),
            in_memory_profile_store=None,
            in_memory_student_store=None,
            supabase_gateway=gateway,
            in_memory_class_store=None,
        )

    if current_settings.environment not in {"development", "test"}:
        # Em produção/staging, memória seria perda silenciosa no primeiro cold
        # start. A aplicação recusa inicializar até a persistência estar completa.
        raise ValueError("Supabase é obrigatório fora de development e test.")

    return ApplicationContainer(
        event_bus=event_bus,
        readiness_probe=LocalReadinessProbe(),
        in_memory_profile_store=InMemoryProfileRepository(),
        in_memory_student_store=InMemoryStudentRepository(),
        supabase_gateway=None,
        in_memory_class_store=InMemoryClassRepository(),
        in_memory_enrollment_store=InMemoryEnrollmentRepository(),
    )
