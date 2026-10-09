from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.database.models.patient import Patient
from app.models.patient import PatientCreate, PatientUpdate
from app.repositories.patient_repository import PatientRepository


class PatientService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = PatientRepository(db)

    def create_patient(
        self,
        data: PatientCreate,
    ) -> Patient:
        patient = self.repository.create(
            full_name=data.full_name,
            age=data.age,
            gender=data.gender.value,
        )

        self.db.commit()
        self.db.refresh(patient)

        return patient

    def get_patient(
        self,
        patient_id: UUID,
    ) -> Patient:
        patient = self.repository.get_by_id(
            patient_id
        )

        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found.",
            )

        return patient

    def list_patients(
        self,
        offset: int,
        limit: int,
        search: str | None,
    ):
        return self.repository.list_patients(
            offset=offset,
            limit=limit,
            search=search,
        )

    def update_patient(
        self,
        patient_id: UUID,
        data: PatientUpdate,
    ) -> Patient:
        patient = self.get_patient(patient_id)

        changes = data.model_dump(
            exclude_unset=True,
            mode="json",
        )

        patient = self.repository.update(
            patient,
            changes,
        )

        self.db.commit()
        self.db.refresh(patient)

        return patient

    def delete_patient(
        self,
        patient_id: UUID,
    ):
        patient = self.get_patient(patient_id)

        self.repository.delete(patient)
        self.db.commit()