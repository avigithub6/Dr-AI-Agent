from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.services.patient_service import PatientService


router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)


def get_patient_service(
    db: Annotated[Session, Depends(get_db)],
) -> PatientService:
    return PatientService(db)


ServiceDependency = Annotated[
    PatientService,
    Depends(get_patient_service),
]


@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_patient(
    data: PatientCreate,
    service: ServiceDependency,
):
    return service.create_patient(data)


@router.get(
    "/",
    response_model=PatientListResponse,
)
def list_patients(
    service: ServiceDependency,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
):
    patients, total = service.list_patients(
        offset=offset,
        limit=limit,
        search=search,
    )

    return {
        "items": patients,
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
)
def get_patient(
    patient_id: UUID,
    service: ServiceDependency,
):
    return service.get_patient(patient_id)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
)
def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    service: ServiceDependency,
):
    return service.update_patient(
        patient_id,
        data,
    )


@router.delete(
    "/{patient_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_patient(
    patient_id: UUID,
    service: ServiceDependency,
):
    service.delete_patient(patient_id)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )