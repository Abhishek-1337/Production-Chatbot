"""Make a user admin by email."""
import asyncio, os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from sqlalchemy import select
from database import SessionLocal
from models.user import User

async def main(email: str):
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {email}")
            return
        user.is_admin = True
        await db.commit()
        print(f"Made admin: {email} ({user.id})")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python scripts/make_admin.py <email>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
