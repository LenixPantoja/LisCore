from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from app.domains.users.infrastructure.repository import PermissionRepository


async def execute(db: AsyncSession) -> list[dict]:
    permissions = await PermissionRepository.get_all(db)

    tree: dict[str, list] = defaultdict(list)
    for perm in permissions:
        module = perm.p_module or "Sin módulo"
        tree[module].append(perm)

    return [
        {"module": module, "permissions": perms}
        for module, perms in sorted(tree.items())
    ]
