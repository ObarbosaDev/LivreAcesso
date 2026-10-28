"""Ponto único de composição das dependências da aplicação."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from backend.app.core.config import Settings, get_settings
from backend.app.modules.alerts.application.dtos import AlertInput, AlertOutput
from backend.app.modules.alerts.infrastructure.supabase_repository import SupabaseAlertRepository
from backend.app.modules.attendance.application.dtos import (
    AttendanceMarkInput,
    AttendanceSessionOutput,
    OpenAttendanceInput,
)
from backend.app.modules.attendance.application.use_cases import (
    CloseAttendance,
    OpenAttendance,
    RecordAttendance,
)
from backend.app.modules.attendance.domain.repositories import AttendanceRepository
from backend.app.modules.attendance.infrastructure.repositories import (
    InMemoryAttendanceRepository,
)
from backend.app.modules.attendance.infrastructure.supabase_repository import (
    SupabaseAttendanceRepository,
)
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
    GetEnrollmentOccupancy,
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
    InviteProfile,
    ListProfiles,
    UpdateMyProfile,
)
from backend.app.modules.identity.infrastructure.repositories import InMemoryProfileRepository
from backend.app.modules.identity.infrastructure.supabase_invitations import (
    SupabaseInvitationService,
)
from backend.app.modules.identity.infrastructure.supabase_profiles import SupabaseProfileRepository
from backend.app.modules.operations.application.agenda import (
    AgendaEventInput,
    AgendaEventOutput,
    AgendaRepository,
)
from backend.app.modules.operations.application.health import (
    LocalReadinessProbe,
    ReadinessProbe,
)
from backend.app.modules.operations.infrastructure.agenda_repository import SupabaseAgendaRepository
from backend.app.modules.operations.infrastructure.supabase_health import (
    SupabaseReadinessProbe,
)
from backend.app.modules.students.application.evaluation_use_cases import (
    CreateStudentEvaluation,
    ListStudentEvaluations,
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
from backend.app.modules.students.domain.evaluation_repositories import StudentEvaluationRepository
from backend.app.modules.students.domain.events import StudentRegistered
from backend.app.modules.students.infrastructure.evaluation_repository import (
    SupabaseStudentEvaluationRepository,
)
from backend.app.modules.students.infrastructure.in_memory_evaluation_repository import (
    InMemoryStudentEvaluationRepository,
)
from backend.app.modules.students.infrastructure.repositories import InMemoryStudentRepository
from backend.app.modules.students.infrastructure.supabase_repository import (
    SupabaseStudentRepository,
)
from backend.app.modules.waiting_list.application.dtos import WaitingListInput, WaitingListOutput
from backend.app.modules.waiting_list.application.use_cases import (
    AcceptWaitingListEntry,
    JoinWaitingList,
    ListWaitingList,
    OfferWaitingListEntry,
    WithdrawWaitingListEntry,
)
from backend.app.modules.waiting_list.infrastructure.repositories import (
    InMemoryWaitingListRepository,
)
from backend.app.modules.waiting_list.infrastructure.supabase_repository import (
    SupabaseWaitingListRepository,
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
    invite_profile: InviteProfile | None
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
    occupancy: GetEnrollmentOccupancy


@dataclass(frozen=True, slots=True)
class EvaluationServices:
    create: CreateStudentEvaluation
    list: ListStudentEvaluations


@dataclass(frozen=True, slots=True)
class AttendanceServices:
    """Casos de uso da chamada ligados ao armazenamento escolhido."""

    open_case: OpenAttendance | None = None
    record_case: RecordAttendance | None = None
    close_case: CloseAttendance | None = None
    remote: SupabaseAttendanceRepository | None = None

    async def open(self, payload: OpenAttendanceInput) -> AttendanceSessionOutput:
        if self.remote is not None:
            return await self.remote.open(payload)
        if self.open_case is None:
            raise RuntimeError("O serviço de abertura de chamada não está configurado.")
        return await self.open_case.execute(payload)

    async def record(
        self, session_id: UUID, marks: tuple[AttendanceMarkInput, ...]
    ) -> AttendanceSessionOutput:
        if self.remote is not None:
            return await self.remote.record(session_id, marks)
        if self.record_case is None:
            raise RuntimeError("O serviço de registro de chamada não está configurado.")
        return await self.record_case.execute(session_id, marks)

    async def close(self, session_id: UUID) -> AttendanceSessionOutput:
        if self.remote is not None:
            return await self.remote.close(session_id)
        if self.close_case is None:
            raise RuntimeError("O serviço de fechamento de chamada não está configurado.")
        return await self.close_case.execute(session_id)


@dataclass(frozen=True, slots=True)
class WaitingListServices:
    join_case: JoinWaitingList | None = None
    offer_case: OfferWaitingListEntry | None = None
    accept_case: AcceptWaitingListEntry | None = None
    remote: SupabaseWaitingListRepository | None = None
    withdraw_case: WithdrawWaitingListEntry | None = None
    list_case: ListWaitingList | None = None

    async def join(self, payload: WaitingListInput) -> WaitingListOutput:
        if self.remote is not None:
            return await self.remote.join(payload)
        if self.join_case is None:
            raise RuntimeError("O serviço de entrada na fila não está configurado.")
        return await self.join_case.execute(payload)

    async def offer(self, entry_id: UUID) -> WaitingListOutput:
        if self.remote is not None:
            return await self.remote.offer(entry_id)
        if self.offer_case is None:
            raise RuntimeError("O serviço de oferta da fila não está configurado.")
        return await self.offer_case.execute(entry_id)

    async def accept(self, entry_id: UUID) -> WaitingListOutput:
        if self.remote is not None:
            return await self.remote.accept(entry_id)
        if self.accept_case is None:
            raise RuntimeError("O serviço de aceitação da fila não está configurado.")
        return await self.accept_case.execute(entry_id)

    async def withdraw(self, entry_id: UUID) -> WaitingListOutput:
        if self.remote is not None:
            return await self.remote.withdraw(entry_id)
        if self.withdraw_case is None:
            raise RuntimeError("O serviço de retirada da fila não está configurado.")
        return await self.withdraw_case.execute(entry_id)

    async def list(self, class_id: UUID) -> tuple[WaitingListOutput, ...]:
        if self.remote is not None:
            return await self.remote.list(class_id)
        if self.list_case is None:
            raise RuntimeError("O serviço de listagem da fila não está configurado.")
        return await self.list_case.execute(class_id)


@dataclass(frozen=True, slots=True)
class AlertServices:
    repository: SupabaseAlertRepository

    async def list_open(self) -> tuple[AlertOutput, ...]:
        return await self.repository.list_open()

    async def upsert(self, payload: AlertInput) -> AlertOutput:
        return await self.repository.upsert(payload)

    async def resolve(self, alert_id: UUID) -> AlertOutput:
        return await self.repository.resolve(alert_id)


@dataclass(frozen=True, slots=True)
class AgendaServices:
    repository: AgendaRepository

    async def list(
        self,
        starts_at: datetime,
        ends_at: datetime,
        event_type: str | None,
        assigned_to: UUID | None,
        context: RequestContext,
    ) -> list[AgendaEventOutput]:
        return await self.repository.list(starts_at, ends_at, event_type, assigned_to, context)

    async def create(self, payload: AgendaEventInput, context: RequestContext) -> AgendaEventOutput:
        return await self.repository.create(payload, context)

    async def update(
        self,
        event_id: UUID,
        expected_updated_at: datetime,
        payload: AgendaEventInput,
        context: RequestContext,
    ) -> AgendaEventOutput:
        return await self.repository.update(event_id, expected_updated_at, payload, context)

    async def cancel(
        self, event_id: UUID, expected_updated_at: datetime, reason: str, context: RequestContext
    ) -> AgendaEventOutput:
        return await self.repository.cancel(event_id, expected_updated_at, reason, context)


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Mantém recursos globais e cria serviços seguros por requisição."""

    event_bus: EventBus
    readiness_probe: ReadinessProbe
    in_memory_profile_store: InMemoryProfileRepository | None
    in_memory_student_store: InMemoryStudentRepository | None
    supabase_gateway: SupabaseRPCGateway | None
    invitation_service: SupabaseInvitationService | None = None
    in_memory_class_store: InMemoryClassRepository | None = None
    in_memory_enrollment_store: InMemoryEnrollmentRepository | None = None
    in_memory_evaluation_store: InMemoryStudentEvaluationRepository | None = None
    in_memory_attendance_store: InMemoryAttendanceRepository | None = None
    in_memory_waiting_list_store: InMemoryWaitingListRepository | None = None

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
            invite_profile=(
                InviteProfile(store, self.invitation_service, actor_id)
                if self.invitation_service is not None
                else None
            ),
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
            occupancy=GetEnrollmentOccupancy(store),
        )

    def evaluations_for(self, context: RequestContext) -> EvaluationServices:
        store: StudentEvaluationRepository
        if self.supabase_gateway is not None:
            store = SupabaseStudentEvaluationRepository(self.supabase_gateway)
        elif self.in_memory_evaluation_store is not None:
            store = self.in_memory_evaluation_store
        else:
            raise RuntimeError("O container não possui armazenamento de avaliações.")
        return EvaluationServices(
            create=CreateStudentEvaluation(store),
            list=ListStudentEvaluations(store),
        )

    def attendance_for(self, context: RequestContext) -> AttendanceServices:
        if self.supabase_gateway is not None:
            return AttendanceServices(
                remote=SupabaseAttendanceRepository(self.supabase_gateway, context)
            )
        if self.in_memory_attendance_store is None:
            raise RuntimeError("O container não possui armazenamento de frequência.")
        store: AttendanceRepository = self.in_memory_attendance_store
        return AttendanceServices(
            open_case=OpenAttendance(store),
            record_case=RecordAttendance(store),
            close_case=CloseAttendance(store),
        )

    def waiting_list_for(self, context: RequestContext) -> WaitingListServices:
        if self.supabase_gateway is not None:
            return WaitingListServices(
                remote=SupabaseWaitingListRepository(self.supabase_gateway, context)
            )
        if self.in_memory_waiting_list_store is None:
            raise RuntimeError("O container não possui armazenamento da fila.")
        store = self.in_memory_waiting_list_store
        return WaitingListServices(
            join_case=JoinWaitingList(store),
            offer_case=OfferWaitingListEntry(store),
            accept_case=AcceptWaitingListEntry(store),
            withdraw_case=WithdrawWaitingListEntry(store),
            list_case=ListWaitingList(store),
        )

    def alerts_for(self, context: RequestContext) -> AlertServices:
        if self.supabase_gateway is None:
            raise RuntimeError("Alertas exigem persistência Supabase configurada.")
        return AlertServices(SupabaseAlertRepository(self.supabase_gateway, context))

    def agenda_for(self, context: RequestContext) -> AgendaServices:
        if self.supabase_gateway is None:
            raise RuntimeError("A agenda exige persistência Supabase configurada.")
        return AgendaServices(SupabaseAgendaRepository(self.supabase_gateway))

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
        if self.invitation_service is not None:
            await self.invitation_service.close()


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
            service_role_key=current_settings.supabase_service_role_key,
        )
        return ApplicationContainer(
            event_bus=event_bus,
            readiness_probe=SupabaseReadinessProbe(gateway),
            in_memory_profile_store=None,
            in_memory_student_store=None,
            supabase_gateway=gateway,
            invitation_service=(
                SupabaseInvitationService(
                    current_settings.supabase_url,
                    current_settings.supabase_service_role_key,
                )
                if current_settings.supabase_service_role_key
                else None
            ),
            in_memory_class_store=None,
            in_memory_evaluation_store=None,
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
        invitation_service=None,
        in_memory_class_store=InMemoryClassRepository(),
        in_memory_enrollment_store=InMemoryEnrollmentRepository(),
        in_memory_evaluation_store=InMemoryStudentEvaluationRepository(),
        in_memory_attendance_store=InMemoryAttendanceRepository(),
        in_memory_waiting_list_store=InMemoryWaitingListRepository(),
    )
