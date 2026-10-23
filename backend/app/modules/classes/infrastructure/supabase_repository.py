"""Catálogo de modalidades e turmas persistido por RPCs Supabase."""

from datetime import datetime, time
from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from backend.app.modules.classes.application.queries import (
    ClassSearchCriteria,
    ClassSearchResult,
    ModalitySearchCriteria,
    ModalitySearchResult,
)
from backend.app.modules.classes.domain.entities import (
    ClassGroup,
    ClassInstructor,
    ClassSchedule,
    Modality,
    Weekday,
)
from backend.app.modules.classes.domain.exceptions import (
    ActiveClassesExistError,
    ClassDomainError,
    ClassNotFoundError,
    ClassVersionConflictError,
    DuplicateClassError,
    DuplicateModalityError,
    InvalidInstructorAssignmentError,
    InvalidScheduleError,
    ModalityNotFoundError,
    ModalityVersionConflictError,
)
from backend.app.modules.classes.domain.repositories import PersistedCatalogVersion
from backend.app.modules.classes.domain.value_objects import ClassChangeReason
from backend.app.modules.identity.application.authentication import InvalidAccessTokenError
from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceRejectedError,
    PersistenceUnavailableError,
)
from backend.app.shared.application.request_context import RequestContext
from backend.app.shared.infrastructure.supabase_rpc import (
    SupabaseRPCError,
    SupabaseRPCGateway,
    SupabaseTransportError,
)


class _DatabaseWeekday(StrEnum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


_TO_DATABASE_WEEKDAY = {
    Weekday.MONDAY: _DatabaseWeekday.MONDAY,
    Weekday.TUESDAY: _DatabaseWeekday.TUESDAY,
    Weekday.WEDNESDAY: _DatabaseWeekday.WEDNESDAY,
    Weekday.THURSDAY: _DatabaseWeekday.THURSDAY,
    Weekday.FRIDAY: _DatabaseWeekday.FRIDAY,
    Weekday.SATURDAY: _DatabaseWeekday.SATURDAY,
    Weekday.SUNDAY: _DatabaseWeekday.SUNDAY,
}
_TO_DOMAIN_WEEKDAY = {value: key for key, value in _TO_DATABASE_WEEKDAY.items()}


class _ModalityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str = Field(min_length=3, max_length=80)
    description: str | None
    active: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class _ModalitySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_ModalityRow]
    total: int = Field(ge=0)


class _ScheduleRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday: _DatabaseWeekday
    starts_at: time
    ends_at: time


class _InstructorRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    full_name: str = Field(min_length=3, max_length=120)


class _ClassRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    modality_id: UUID
    name: str = Field(min_length=3, max_length=120)
    capacity: int = Field(ge=1, le=500)
    location: str = Field(min_length=2, max_length=120)
    minimum_age: int | None = Field(default=None, ge=0, le=120)
    maximum_age: int | None = Field(default=None, ge=0, le=120)
    schedules: list[_ScheduleRow] = Field(min_length=1, max_length=14)
    instructors: list[_InstructorRow] = Field(min_length=1, max_length=20)
    active: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime


class _ClassSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[_ClassRow]
    total: int = Field(ge=0)


class _MutationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated_at: AwareDatetime


_MODALITY = TypeAdapter(_ModalityRow)
_MODALITY_SEARCH = TypeAdapter(_ModalitySearchResponse)
_CLASS = TypeAdapter(_ClassRow)
_CLASS_SEARCH = TypeAdapter(_ClassSearchResponse)
_MUTATION = TypeAdapter(_MutationResponse)


class SupabaseClassRepository:
    """Implementa catálogo via PostgREST usando o JWT efêmero da requisição."""

    def __init__(self, gateway: SupabaseRPCGateway, context: RequestContext) -> None:
        self._gateway = gateway
        self._context = context

    async def add_modality(self, modality: Modality) -> PersistedCatalogVersion:
        result = await self._call(
            "create_modality",
            {
                "p_modality_id": str(modality.id),
                "p_request_id": str(self._context.request_id),
                "p_name": modality.name,
                "p_description": modality.description,
            },
        )
        row = self._parse_modality(result)
        if row.id != modality.id:
            raise PersistenceUnavailableError
        return PersistedCatalogVersion(row.created_at, row.updated_at)

    async def get_modality(self, modality_id: UUID) -> Modality | None:
        try:
            result = await self._call("get_modality", {"p_modality_id": str(modality_id)})
        except ModalityNotFoundError:
            return None
        return self._to_modality(self._parse_modality(result))

    async def update_modality(
        self,
        modality: Modality,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "update_modality",
            {
                "p_modality_id": str(modality.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_name": modality.name,
                "p_description": modality.description,
            },
        )
        return self._mutation_timestamp(result)

    async def change_modality_activation(
        self,
        modality: Modality,
        *,
        reason: ClassChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "change_modality_activation",
            {
                "p_modality_id": str(modality.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_active": modality.active,
                "p_reason": reason.value,
            },
        )
        return self._mutation_timestamp(result)

    async def search_modalities(
        self,
        criteria: ModalitySearchCriteria,
    ) -> ModalitySearchResult:
        result = await self._call(
            "list_modalities",
            {
                "p_active": criteria.active,
                "p_query": criteria.query,
                "p_limit": criteria.limit,
                "p_offset": criteria.offset,
            },
        )
        try:
            response = _MODALITY_SEARCH.validate_python(result)
            return ModalitySearchResult(
                items=tuple(self._to_modality(item) for item in response.items),
                total=response.total,
            )
        except (ValidationError, ClassDomainError) as error:
            raise PersistenceUnavailableError from error

    async def add_class(self, group: ClassGroup) -> PersistedCatalogVersion:
        result = await self._call(
            "create_class",
            self._class_payload(group)
            | {
                "p_class_id": str(group.id),
                "p_request_id": str(self._context.request_id),
            },
        )
        row = self._parse_class(result)
        if row.id != group.id:
            raise PersistenceUnavailableError
        return PersistedCatalogVersion(row.created_at, row.updated_at)

    async def get_class(self, class_id: UUID) -> ClassGroup | None:
        try:
            result = await self._call("get_class", {"p_class_id": str(class_id)})
        except ClassNotFoundError:
            return None
        return self._to_class(self._parse_class(result))

    async def update_class(
        self,
        group: ClassGroup,
        *,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "update_class",
            self._class_payload(group)
            | {
                "p_class_id": str(group.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
            },
        )
        return self._mutation_timestamp(result)

    async def change_class_activation(
        self,
        group: ClassGroup,
        *,
        reason: ClassChangeReason,
        expected_updated_at: datetime,
    ) -> datetime:
        result = await self._call(
            "change_class_activation",
            {
                "p_class_id": str(group.id),
                "p_request_id": str(self._context.request_id),
                "p_expected_updated_at": expected_updated_at.isoformat(),
                "p_active": group.active,
                "p_reason": reason.value,
            },
        )
        return self._mutation_timestamp(result)

    async def search_classes(self, criteria: ClassSearchCriteria) -> ClassSearchResult:
        # viewer_instructor_id nunca atravessa a rede. A função SQL consulta
        # auth.uid() e impede que um instrutor escolha a identidade de outro.
        result = await self._call(
            "list_classes",
            {
                "p_active": criteria.active,
                "p_modality_id": (
                    str(criteria.modality_id) if criteria.modality_id is not None else None
                ),
                "p_query": criteria.query,
                "p_limit": criteria.limit,
                "p_offset": criteria.offset,
            },
        )
        try:
            response = _CLASS_SEARCH.validate_python(result)
            return ClassSearchResult(
                items=tuple(self._to_class(item) for item in response.items),
                total=response.total,
            )
        except (ValidationError, ClassDomainError) as error:
            raise PersistenceUnavailableError from error

    def _class_payload(self, group: ClassGroup) -> dict[str, object]:
        return {
            "p_modality_id": str(group.modality_id),
            "p_name": group.name,
            "p_capacity": group.capacity,
            "p_location": group.location,
            "p_minimum_age": group.minimum_age,
            "p_maximum_age": group.maximum_age,
            "p_schedules": [
                {
                    "weekday": _TO_DATABASE_WEEKDAY[item.weekday].value,
                    "starts_at": item.starts_at.isoformat(),
                    "ends_at": item.ends_at.isoformat(),
                }
                for item in group.schedules
            ],
            "p_instructor_ids": [str(item.id) for item in group.instructors],
        }

    async def _call(self, function_name: str, payload: dict[str, object]) -> object:
        try:
            return await self._gateway.call(function_name, payload, self._context)
        except SupabaseTransportError as error:
            raise PersistenceUnavailableError from error
        except SupabaseRPCError as error:
            if error.status_code == 401:
                raise InvalidAccessTokenError from error
            if (
                error.status_code == 403
                or error.database_code == "42501"
                or error.message_code == "forbidden"
            ):
                raise PermissionDeniedError from error
            error_mapping: dict[str, type[ClassDomainError]] = {
                "duplicate_modality": DuplicateModalityError,
                "duplicate_class": DuplicateClassError,
                "modality_not_found": ModalityNotFoundError,
                "class_not_found": ClassNotFoundError,
                "modality_version_conflict": ModalityVersionConflictError,
                "class_version_conflict": ClassVersionConflictError,
                "invalid_instructor_assignment": InvalidInstructorAssignmentError,
                "schedule_overlap": InvalidScheduleError,
                "active_classes_exist": ActiveClassesExistError,
            }
            mapped_error = (
                error_mapping.get(error.message_code) if error.message_code is not None else None
            )
            if mapped_error is not None:
                raise mapped_error from error
            if error.status_code == 404 or error.status_code >= 500:
                raise PersistenceUnavailableError from error
            raise PersistenceRejectedError from error

    @staticmethod
    def _parse_modality(result: object) -> _ModalityRow:
        try:
            return _MODALITY.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    @staticmethod
    def _parse_class(result: object) -> _ClassRow:
        try:
            return _CLASS.validate_python(result)
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    @staticmethod
    def _mutation_timestamp(result: object) -> datetime:
        try:
            return _MUTATION.validate_python(result).updated_at
        except ValidationError as error:
            raise PersistenceUnavailableError from error

    @staticmethod
    def _to_modality(row: _ModalityRow) -> Modality:
        return Modality(
            id=row.id,
            name=row.name,
            description=row.description,
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _to_class(row: _ClassRow) -> ClassGroup:
        return ClassGroup(
            id=row.id,
            modality_id=row.modality_id,
            name=row.name,
            capacity=row.capacity,
            location=row.location,
            minimum_age=row.minimum_age,
            maximum_age=row.maximum_age,
            schedules=tuple(
                ClassSchedule(
                    weekday=_TO_DOMAIN_WEEKDAY[item.weekday],
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                )
                for item in row.schedules
            ),
            instructors=tuple(
                ClassInstructor(id=item.id, full_name=item.full_name) for item in row.instructors
            ),
            active=row.active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
