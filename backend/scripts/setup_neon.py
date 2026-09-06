"""
setup_neon.py — One-shot Neon database initialisation.

Usage:
    DATABASE_URL="postgresql://..." python backend/scripts/setup_neon.py

What it does:
  1. Runs migrations/schema.sql  (creates all tables, enums, views, indexes)
  2. Creates default users        (admin / state / district officers)
  3. Prints credentials summary
"""

import sys
import os

# So we can import app.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# If DATABASE_URL is passed as env var it overrides the default in config
from app.db.database import engine, SessionLocal
from app.db.models import Base, User, UserRole
from app.core.security import hash_password
from sqlalchemy import text as sa_text

SCHEMA_FILE = os.path.join(
    os.path.dirname(__file__), "..", "migrations", "schema.sql"
)

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


def run_schema():
    print("─── Step 1: Running schema.sql ───────────────────────────────")
    if not os.path.exists(SCHEMA_FILE):
        print(f"  ERROR: schema file not found at {SCHEMA_FILE}")
        sys.exit(1)

    with open(SCHEMA_FILE, "r") as f:
        sql = f.read()

    # Split on semicolons but skip empty statements
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    with engine.connect() as conn:
        for stmt in statements:
            try:
                conn.execute(sa_text(stmt))
            except Exception as e:
                # Ignore "already exists" errors — schema is idempotent
                msg = str(e).lower()
                if "already exists" in msg or "duplicate" in msg:
                    continue
                print(f"  WARN: {e}")
        conn.commit()
    print("  Schema applied successfully.")


def create_users():
    print("─── Step 2: Creating default users ──────────────────────────")
    # Also ensure ORM tables exist (for any tables not in schema.sql)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
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
            print(f"  Created: {u['username']:20s} ({u['role'].value})")
        db.commit()
    finally:
        db.close()


def main():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("WARNING: DATABASE_URL env var not set — using value from .env / config.py")
    else:
        print(f"Using DATABASE_URL: {db_url[:40]}...")

    run_schema()
    create_users()

    print()
    print("═══════════════════════════════════════════════════════════")
    print("  Neon DB setup complete!")
    print()
    print("  Login credentials:")
    for u in DEFAULT_USERS:
        print(f"    {u['username']:20s}  /  {u['password']:15s}  ({u['role'].value})")
    print()
    print("  Next steps:")
    print("    1. Deploy backend to Vercel (set env vars below)")
    print("    2. After deploy, call: POST /api/projects/import-csv")
    print("       with admin Bearer token to load project data")
    print("═══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    main()
