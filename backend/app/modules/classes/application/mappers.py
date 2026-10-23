"""Conversões explícitas entre DTOs e entidades do catálogo."""

from backend.app.modules.classes.application.dtos import (
    ClassOutput,
    CreateClassInput,
    InstructorOutput,
    ModalityOutput,
    ScheduleInput,
    ScheduleOutput,
)
from backend.app.modules.classes.domain.entities import (
    ClassGroup,
    ClassInstructor,
    ClassSchedule,
    Modality,
)


class CatalogMapper:
    @staticmethod
    def modality_to_output(modality: Modality) -> ModalityOutput:
        return ModalityOutput(
            id=modality.id,
            name=modality.name,
            description=modality.description,
            active=modality.active,
            created_at=modality.created_at,
            updated_at=modality.updated_at,
        )

    @staticmethod
    def schedule_to_domain(schedule: ScheduleInput) -> ClassSchedule:
        return ClassSchedule(
            weekday=schedule.weekday,
            starts_at=schedule.starts_at,
            ends_at=schedule.ends_at,
        )

    @staticmethod
    def class_to_domain(
        dto: CreateClassInput,
        instructors: tuple[ClassInstructor, ...],
    ) -> ClassGroup:
        return ClassGroup.create(
            modality_id=dto.modality_id,
            name=dto.name,
            capacity=dto.capacity,
            location=dto.location,
            minimum_age=dto.minimum_age,
            maximum_age=dto.maximum_age,
            schedules=tuple(CatalogMapper.schedule_to_domain(item) for item in dto.schedules),
            instructors=instructors,
        )

    @staticmethod
    def class_to_output(group: ClassGroup) -> ClassOutput:
        return ClassOutput(
            id=group.id,
            modality_id=group.modality_id,
            name=group.name,
            capacity=group.capacity,
            location=group.location,
            minimum_age=group.minimum_age,
            maximum_age=group.maximum_age,
            schedules=[
                ScheduleOutput(
                    weekday=item.weekday,
                    starts_at=item.starts_at,
                    ends_at=item.ends_at,
                )
                for item in group.schedules
            ],
            instructors=[
                InstructorOutput(id=item.id, full_name=item.full_name) for item in group.instructors
            ],
            active=group.active,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
