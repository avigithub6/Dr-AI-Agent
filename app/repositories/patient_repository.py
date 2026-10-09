from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models.patient import Patient


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        full_name: str,
        age: int,
        gender: str,
    ) -> Patient:
        patient = Patient(
            full_name=full_name,
            age=age,
            gender=gender,
        )

        self.db.add(patient)
        self.db.flush()

        return patient

    def get_by_id(
        self,
        patient_id: UUID,
    ) -> Patient | None:
        return self.db.get(
            Patient,
            patient_id,
        )

    def list_patients(
        self,
        offset: int,
        limit: int,
        search: str | None = None,
    ) -> tuple[list[Patient], int]:
        query = select(Patient)
        count_query = select(func.count()).select_from(Patient)

        if search and search.strip():
            term = search.strip()

            term = (
                term.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )

            condition = Patient.full_name.ilike(
                f"%{term}%",
                escape="\\",
            )

            query = query.where(condition)
            count_query = count_query.where(condition)

        query = (
            query
            .order_by(
                Patient.created_at.desc(),
                Patient.id,
            )
            .offset(offset)
            .limit(limit)
        )

        patients = list(
            self.db.scalars(query).all()
        )

        total = self.db.scalar(count_query) or 0

        return patients, total

    def update(
        self,
        patient: Patient,
        changes: dict,
    ) -> Patient:
        for field, value in changes.items():
            setattr(patient, field, value)

        self.db.flush()

        return patient

    def delete(self, patient: Patient):
        self.db.delete(patient)
        self.db.flush()