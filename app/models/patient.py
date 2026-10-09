from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class PatientCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    full_name: str = Field(
        min_length=2,
        max_length=100,
        strict=True,
    )

    age: int = Field(
        ge=0,
        le=130,
        strict=True,
    )

    gender: Gender


class PatientUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        strict=True,
    )

    age: int | None = Field(
        default=None,
        ge=0,
        le=130,
        strict=True,
    )

    gender: Gender | None = None

    @field_validator(
        "full_name",
        "age",
        "gender",
        mode="before",
    )
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError(
                "Provided fields cannot be null"
            )

        return value

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one field to update"
            )

        return self


class PatientResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    full_name: str
    age: int
    gender: Gender
    created_at: datetime
    updated_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientResponse]
    total: int
    offset: int
    limit: int