"""Casos de uso autorizados para modalidades e turmas."""

from dataclasses import dataclass
from uuid import UUID

from backend.app.modules.classes.application.dtos import (
    ChangeCatalogActivationInput,
    ClassOutput,
    ClassPageOutput,
    CreateClassInput,
    CreateModalityInput,
    ModalityOutput,
    ModalityPageOutput,
    UpdateClassInput,
    UpdateModalityInput,
)
from backend.app.modules.classes.application.mappers import CatalogMapper
from backend.app.modules.classes.application.queries import (
    ClassQueryService,
    ClassSearchCriteria,
    ModalityQueryService,
    ModalitySearchCriteria,
)
from backend.app.modules.classes.domain.entities import ClassGroup, ClassInstructor, Modality
from backend.app.modules.classes.domain.exceptions import (
    ClassNotFoundError,
    ClassVersionConflictError,
    InvalidInstructorAssignmentError,
    ModalityNotFoundError,
    ModalityVersionConflictError,
)
from backend.app.modules.classes.domain.repositories import ClassRepository, ModalityRepository
from backend.app.modules.classes.domain.value_objects import ClassChangeReason
from backend.app.modules.identity.domain.entities import Capability, UserProfile, UserRole
from backend.app.modules.identity.domain.repositories import ProfileRepository
from backend.app.shared.application.event_bus import EventPublisher
from backend.app.shared.application.exceptions import PermissionDeniedError


async def _require_capability(
    profiles: ProfileRepository,
    actor_id: UUID,
    capability: Capability,
) -> UserProfile:
    profile = await profiles.get_current(actor_id)
    if profile is None or capability not in profile.capabilities:
        # A mesma resposta cobre perfil ausente, inativo ou sem papel suficiente;
        # não revelamos qual estado interno causou a recusa.
        raise PermissionDeniedError
    return profile


async def _resolve_instructors(
    profiles: ProfileRepository,
    instructor_ids: list[UUID],
) -> tuple[ClassInstructor, ...]:
    if len(set(instructor_ids)) != len(instructor_ids):
        raise InvalidInstructorAssignmentError

    instructors: list[ClassInstructor] = []
    for instructor_id in instructor_ids:
        profile = await profiles.get_by_id(instructor_id)
        if profile is None or not profile.active or profile.role is not UserRole.INSTRUCTOR:
            raise InvalidInstructorAssignmentError
        instructors.append(ClassInstructor(id=profile.id, full_name=profile.full_name))
    return tuple(instructors)


def _publish_events(entity: Modality | ClassGroup, publisher: EventPublisher) -> None:
    # Eventos só saem após a persistência aceitar versão, autorização e constraints.
    for event in entity.pull_events():
        publisher.publish(event)


@dataclass(slots=True)
class ListModalities:
    queries: ModalityQueryService
    profiles: ProfileRepository
    actor_id: UUID

    async def execute(
        self,
        *,
        active: bool | None,
        query: str | None,
        page: int,
        page_size: int,
    ) -> ModalityPageOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_LIST)
        result = await self.queries.search_modalities(
            ModalitySearchCriteria(
                active=active,
                query=query,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        )
        total_pages = (result.total + page_size - 1) // page_size if result.total else 0
        return ModalityPageOutput(
            items=[CatalogMapper.modality_to_output(item) for item in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
        )


@dataclass(slots=True)
class GetModality:
    repository: ModalityRepository
    profiles: ProfileRepository
    actor_id: UUID

    async def execute(self, modality_id: UUID) -> ModalityOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_READ)
        modality = await self.repository.get_modality(modality_id)
        if modality is None:
            raise ModalityNotFoundError
        return CatalogMapper.modality_to_output(modality)


@dataclass(slots=True)
class CreateModality:
    repository: ModalityRepository
    profiles: ProfileRepository
    publisher: EventPublisher
    actor_id: UUID

    async def execute(self, dto: CreateModalityInput) -> ModalityOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_MANAGE)
        modality = Modality.create(name=dto.name, description=dto.description)
        version = await self.repository.add_modality(modality)
        modality.mark_created(version.created_at, version.updated_at)
        _publish_events(modality, self.publisher)
        return CatalogMapper.modality_to_output(modality)


@dataclass(slots=True)
class UpdateModality:
    repository: ModalityRepository
    profiles: ProfileRepository
    publisher: EventPublisher
    actor_id: UUID

    async def execute(self, modality_id: UUID, dto: UpdateModalityInput) -> ModalityOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_MANAGE)
        modality = await self.repository.get_modality(modality_id)
        if modality is None:
            raise ModalityNotFoundError
        if modality.updated_at != dto.expected_updated_at:
            raise ModalityVersionConflictError
        changed = modality.update(name=dto.name, description=dto.description)
        if changed:
            updated_at = await self.repository.update_modality(
                modality,
                expected_updated_at=dto.expected_updated_at,
            )
            modality.mark_persisted(updated_at)
            _publish_events(modality, self.publisher)
        return CatalogMapper.modality_to_output(modality)


@dataclass(slots=True)
class ChangeModalityActivation:
    repository: ModalityRepository
    profiles: ProfileRepository
    publisher: EventPublisher
    actor_id: UUID
    active: bool

    async def execute(
        self,
        modality_id: UUID,
        dto: ChangeCatalogActivationInput,
    ) -> ModalityOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_MANAGE)
        modality = await self.repository.get_modality(modality_id)
        if modality is None:
            raise ModalityNotFoundError
        if modality.updated_at != dto.expected_updated_at:
            raise ModalityVersionConflictError
        reason = ClassChangeReason(dto.reason)
        if modality.change_activation(self.active, reason):
            updated_at = await self.repository.change_modality_activation(
                modality,
                reason=reason,
                expected_updated_at=dto.expected_updated_at,
            )
            modality.mark_persisted(updated_at)
            _publish_events(modality, self.publisher)
        return CatalogMapper.modality_to_output(modality)


@dataclass(slots=True)
class ListClasses:
    queries: ClassQueryService
    profiles: ProfileRepository
    actor_id: UUID

    async def execute(
        self,
        *,
        active: bool | None,
        modality_id: UUID | None,
        query: str | None,
        page: int,
        page_size: int,
    ) -> ClassPageOutput:
        profile = await _require_capability(
            self.profiles,
            self.actor_id,
            Capability.CLASSES_LIST,
        )
        result = await self.queries.search_classes(
            ClassSearchCriteria(
                active=active,
                modality_id=modality_id,
                query=query,
                offset=(page - 1) * page_size,
                limit=page_size,
                viewer_instructor_id=(
                    self.actor_id if profile.role is UserRole.INSTRUCTOR else None
                ),
            )
        )
        total_pages = (result.total + page_size - 1) // page_size if result.total else 0
        return ClassPageOutput(
            items=[CatalogMapper.class_to_output(item) for item in result.items],
            page=page,
            page_size=page_size,
            total=result.total,
            total_pages=total_pages,
            has_previous=page > 1,
            has_next=page < total_pages,
        )


@dataclass(slots=True)
class GetClass:
    repository: ClassRepository
    profiles: ProfileRepository
    actor_id: UUID

    async def execute(self, class_id: UUID) -> ClassOutput:
        profile = await _require_capability(
            self.profiles,
            self.actor_id,
            Capability.CLASSES_READ,
        )
        group = await self.repository.get_class(class_id)
        if group is None:
            raise ClassNotFoundError
        if profile.role is UserRole.INSTRUCTOR and all(
            instructor.id != self.actor_id for instructor in group.instructors
        ):
            # Não distinguimos turma inexistente de turma alheia na RPC; a camada
            # local usa a mesma recusa genérica para evitar enumeração por instrutor.
            raise PermissionDeniedError
        return CatalogMapper.class_to_output(group)


@dataclass(slots=True)
class CreateClass:
    repository: ClassRepository
    modalities: ModalityRepository
    profiles: ProfileRepository
    publisher: EventPublisher
    actor_id: UUID

    async def execute(self, dto: CreateClassInput) -> ClassOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_MANAGE)
        modality = await self.modalities.get_modality(dto.modality_id)
        if modality is None or not modality.active:
            raise ModalityNotFoundError
        instructors = await _resolve_instructors(self.profiles, dto.instructor_ids)
        group = CatalogMapper.class_to_domain(dto, instructors)
        version = await self.repository.add_class(group)
        group.mark_created(version.created_at, version.updated_at)
        _publish_events(group, self.publisher)
        return CatalogMapper.class_to_output(group)


@dataclass(slots=True)
class UpdateClass:
    repository: ClassRepository
    modalities: ModalityRepository
    profiles: ProfileRepository
    publisher: EventPublisher
    actor_id: UUID

    async def execute(self, class_id: UUID, dto: UpdateClassInput) -> ClassOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_MANAGE)
        group = await self.repository.get_class(class_id)
        if group is None:
            raise ClassNotFoundError
        if group.updated_at != dto.expected_updated_at:
            raise ClassVersionConflictError
        modality = await self.modalities.get_modality(dto.modality_id)
        if modality is None or not modality.active:
            raise ModalityNotFoundError
        instructors = await _resolve_instructors(self.profiles, dto.instructor_ids)
        schedules = tuple(CatalogMapper.schedule_to_domain(item) for item in dto.schedules)
        changed = group.update(
            modality_id=dto.modality_id,
            name=dto.name,
            capacity=dto.capacity,
            location=dto.location,
            minimum_age=dto.minimum_age,
            maximum_age=dto.maximum_age,
            schedules=schedules,
            instructors=instructors,
        )
        if changed:
            updated_at = await self.repository.update_class(
                group,
                expected_updated_at=dto.expected_updated_at,
            )
            group.mark_persisted(updated_at)
            _publish_events(group, self.publisher)
        return CatalogMapper.class_to_output(group)


@dataclass(slots=True)
class ChangeClassActivation:
    repository: ClassRepository
    modalities: ModalityRepository
    profiles: ProfileRepository
    publisher: EventPublisher
    actor_id: UUID
    active: bool

    async def execute(
        self,
        class_id: UUID,
        dto: ChangeCatalogActivationInput,
    ) -> ClassOutput:
        await _require_capability(self.profiles, self.actor_id, Capability.CLASSES_MANAGE)
        group = await self.repository.get_class(class_id)
        if group is None:
            raise ClassNotFoundError
        if group.updated_at != dto.expected_updated_at:
            raise ClassVersionConflictError
        if self.active:
            modality = await self.modalities.get_modality(group.modality_id)
            if modality is None or not modality.active:
                raise ModalityNotFoundError
        reason = ClassChangeReason(dto.reason)
        if group.change_activation(self.active, reason):
            updated_at = await self.repository.change_class_activation(
                group,
                reason=reason,
                expected_updated_at=dto.expected_updated_at,
            )
            group.mark_persisted(updated_at)
            _publish_events(group, self.publisher)
        return CatalogMapper.class_to_output(group)
