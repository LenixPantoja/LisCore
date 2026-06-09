"""
Script: create_superadmin.py

Creates a SuperAdmin role with all system permissions and an admin user assigned to it.
Idempotent: skips creation if the role or user already exists.

Usage:
    python utils/create_superadmin.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text
from app.core.database import async_session
from app.core.security import get_password_hash

# ── Configuration ─────────────────────────────────────────────────────────────
SUPERADMIN_ROLE_NAME = "SuperAdmin"
SUPERADMIN_ROLE_DESCRIPTION = "Rol con acceso total al sistema"

ADMIN_USER = {
    "usr_login": "admin",
    "usr_password": "1313",   # Change after first login
    "usr_first_name": "Administrador",
    "usr_last_name": "Sistema",
    "usr_document_number": "000000000",
    "usr_mail": "admin@laboratorio.com",
    "usr_is_active": True,
    "usr_is_Locked": False,
}
# ─────────────────────────────────────────────────────────────────────────────


async def create_superadmin():
    async with async_session() as db:
        # 1. Create or get SuperAdmin role
        result = await db.execute(
            text('SELECT r_id FROM "Rols" WHERE r_name = :name'),
            {"name": SUPERADMIN_ROLE_NAME},
        )
        role_row = result.fetchone()

        if role_row:
            role_id = role_row[0]
            print(f"✓ Role '{SUPERADMIN_ROLE_NAME}' already exists (id={role_id}). Skipping creation.")
        else:
            result = await db.execute(
                text(
                    'INSERT INTO "Rols" (r_name, r_description) VALUES (:name, :desc) RETURNING r_id'
                ),
                {"name": SUPERADMIN_ROLE_NAME, "desc": SUPERADMIN_ROLE_DESCRIPTION},
            )
            role_id = result.fetchone()[0]
            await db.commit()
            print(f"✓ Created role '{SUPERADMIN_ROLE_NAME}' (id={role_id}).")

        # 2. Fetch all permissions
        result = await db.execute(text('SELECT p_id, p_name FROM "Permissions"'))
        all_permissions = result.fetchall()

        if not all_permissions:
            print("⚠ No permissions found in the database. Run seed_permissions.py first.")
            return

        # 3. Fetch already linked permissions for this role
        result = await db.execute(
            text('SELECT rp_permission_id FROM "RolPermissions" WHERE rp_rol_id = :role_id'),
            {"role_id": role_id},
        )
        existing_perm_ids = {row[0] for row in result.fetchall()}

        new_count = 0
        for perm_id, perm_name in all_permissions:
            if perm_id not in existing_perm_ids:
                await db.execute(
                    text(
                        'INSERT INTO "RolPermissions" (rp_rol_id, rp_permission_id, rp_active) '
                        "VALUES (:rol_id, :perm_id, TRUE)"
                    ),
                    {"rol_id": role_id, "perm_id": perm_id},
                )
                new_count += 1

        if new_count:
            await db.commit()
            print(f"✓ Linked {new_count} new permissions to '{SUPERADMIN_ROLE_NAME}'.")
        else:
            print(f"✓ All permissions already linked to '{SUPERADMIN_ROLE_NAME}'.")

        # 4. Create admin user
        result = await db.execute(
            text('SELECT usr_id FROM "AppUsers" WHERE usr_login = :login'),
            {"login": ADMIN_USER["usr_login"]},
        )
        user_row = result.fetchone()

        if user_row:
            print(f"✓ User '{ADMIN_USER['usr_login']}' already exists (id={user_row[0]}). Skipping creation.")
        else:
            hashed_password = get_password_hash(ADMIN_USER["usr_password"])
            result = await db.execute(
                text(
                    'INSERT INTO "AppUsers" '
                    '(usr_login, usr_password, usr_first_name, usr_last_name, '
                    'usr_document_number, usr_mail, usr_is_active, "usr_is_Locked", usr_rol_id) '
                    "VALUES (:login, :password, :first_name, :last_name, "
                    ":document_number, :mail, :is_active, :is_locked, :rol_id) RETURNING usr_id"
                ),
                {
                    "login": ADMIN_USER["usr_login"],
                    "password": hashed_password,
                    "first_name": ADMIN_USER["usr_first_name"],
                    "last_name": ADMIN_USER["usr_last_name"],
                    "document_number": ADMIN_USER["usr_document_number"],
                    "mail": ADMIN_USER["usr_mail"],
                    "is_active": ADMIN_USER["usr_is_active"],
                    "is_locked": ADMIN_USER["usr_is_Locked"],
                    "rol_id": role_id,
                },
            )
            user_id = result.fetchone()[0]
            await db.commit()
            print(f"✓ Created admin user '{ADMIN_USER['usr_login']}' (id={user_id}) with role '{SUPERADMIN_ROLE_NAME}'.")
            print(f"  Login:    {ADMIN_USER['usr_login']}")
            print(f"  Password: {ADMIN_USER['usr_password']}  ← Change this after first login!")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(create_superadmin())
