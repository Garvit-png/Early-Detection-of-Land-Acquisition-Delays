"""
One-time DB seed script.
Creates tables, creates default users, imports all projects from CSV.
Run: python backend/scripts/seed_db.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import engine, SessionLocal
from app.db.models import Base, User, UserRole
from app.core.security import hash_password

DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@dolr.gov.in",
        "password": "Admin@123",
        "full_name": "Central Admin",
        "role": UserRole.CENTRAL,
        "state": None,
        "district": None,
    },
    {
        "username": "up_officer",
        "email": "up@dolr.gov.in",
        "password": "State@123",
        "full_name": "UP State Officer",
        "role": UserRole.STATE,
        "state": "Uttar Pradesh",
        "district": None,
    },
    {
        "username": "lucknow_officer",
        "email": "lucknow@dolr.gov.in",
        "password": "District@123",
        "full_name": "Lucknow District Officer",
        "role": UserRole.DISTRICT,
        "state": "Uttar Pradesh",
        "district": "Lucknow",
    },
    {
        "username": "mh_officer",
        "email": "mh@dolr.gov.in",
        "password": "State@123",
        "full_name": "Maharashtra State Officer",
        "role": UserRole.STATE,
        "state": "Maharashtra",
        "district": None,
    },
]


def seed():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        # Create default users
        for u in DEFAULT_USERS:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if existing:
                print(f"  User '{u['username']}' already exists — skipped")
                continue
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                state=u["state"],
                district=u["district"],
            )
            db.add(user)
            print(f"  Created user: {u['username']} ({u['role'].value})")
        db.commit()
        print("\nDefault users created.")
        print("\nCredentials:")
        for u in DEFAULT_USERS:
            print(f"  {u['username']:20s} / {u['password']:15s} ({u['role'].value})")

    finally:
        db.close()

    print("\nSeed complete. Now start the backend and call POST /api/projects/import-csv with the admin token to load project data.")


if __name__ == "__main__":
    seed()
