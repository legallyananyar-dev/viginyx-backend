"""
Seed script to populate the database with initial data.
Run: ENVIRONMENT=dev .venv/bin/python seed.py
"""
import os
os.environ.setdefault("ENVIRONMENT", "dev")

from sqlmodel import Session, select
from api.core.database import write_engine
from api.core.security import get_password_hash
from api.models.user import User, Organization, UserRole, UserType
from uuid import uuid4
from datetime import datetime, timezone


def seed():
    with Session(write_engine) as session:
        # --- Seed Organization ---
        org = session.exec(
            select(Organization).where(Organization.name == "Viginyx Health")
        ).first()

        if not org:
            org = Organization(
                id=uuid4(),
                name="Viginyx Health",
                description="Primary healthcare organization",
                license_no="VGX-2026-001",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(org)
            session.commit()
            session.refresh(org)
            print(f"✅ Organization created: {org.name} (id={org.id})")
        else:
            print(f"⏭️  Organization already exists: {org.name}")

        # --- Seed Superuser ---
        user = session.exec(
            select(User).where(User.email == "vaibhav1262002@gmail.com")
        ).first()

        if not user:
            user = User(
                id=uuid4(),
                email="vaibhav1262002@gmail.com",
                hashed_password=get_password_hash("Vaibhav@123"),
                is_active=True,
                role=UserRole.SUPER_ADMIN,
                user_type=UserType.DOCTOR,
                first_name="Vaibhav",
                last_name="Ugale",
                phone_number="+919876543210",
                organization_id=org.id,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✅ Superuser created: {user.email} (id={user.id})")
        else:
            print(f"⏭️  Superuser already exists: {user.email}")

    print("\n🌱 Seeding complete!")


if __name__ == "__main__":
    seed()
