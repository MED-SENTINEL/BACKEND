"""
Seed the database with a demo user and profile for development.
Runs automatically on server startup if the database is empty.
"""

from datetime import date
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.profile import PatientProfile
from app.core.security import hash_password


def seed_database(db: Session):
    """Insert a demo user with profile if the users table is empty."""

    existing = db.query(User).count()
    if existing > 0:
        print(f"[SEED] Database already has {existing} users. Skipping seed.")
        return

    print("[SEED] Seeding database with demo user...")

    # ─── Create Demo User (pre-verified, pre-onboarded) ───
    demo_user = User(
        id="demo-user-001",
        email="demo@sentinel.dev",
        password_hash=hash_password("sentinel123"),
        full_name="Arjun Mehta",
        is_verified=True,
        is_onboarded=True,
    )
    db.add(demo_user)
    db.commit()

    print("[SEED] Created demo user (demo@sentinel.dev / sentinel123)")

    # ─── Create Demo Profile ───
    demo_profile = PatientProfile(
        id="profile-001",
        user_id="demo-user-001",
        gender="male",
        date_of_birth=date(1990, 5, 14),
        blood_type="B+",
        height_cm=175.0,
        weight_kg=72.0,
        phone="+91-9876543210",
        emergency_contact_name="Priya Mehta",
        emergency_contact_phone="+91-9876543211",
        emergency_contact_relation="spouse",
        allergies="Penicillin",
        chronic_conditions="None",
        current_medications="None",
        past_surgeries="Appendectomy (2015)",
    )
    db.add(demo_profile)
    db.commit()

    print("[SEED] Created demo patient profile")

