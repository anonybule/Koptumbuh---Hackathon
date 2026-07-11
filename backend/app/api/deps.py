from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from app.database import get_db
from app.config import settings
from app.models.koptumbuh import PenggunaKoptumbuh

security = HTTPBearer()

ROLE_ANGGOTA = "ANGGOTA"
ROLE_OPERATOR = "OPERATOR"
ROLE_ADMIN = {"ADMIN", "PEMBINA", "KETUA", "BENDAHARA"}
ROLE_OPERATOR_PLUS = ROLE_ADMIN | {ROLE_OPERATOR}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate JWT, load user from DB, reject inactive accounts."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        pengguna_id: str = payload.get("sub")
        if pengguna_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        uid = UUID(pengguna_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(PenggunaKoptumbuh).where(PenggunaKoptumbuh.pengguna_id == uid))
    user = result.scalar_one_or_none()
    if not user or not user.status_aktif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    return {
        "pengguna_id": str(user.pengguna_id),
        "role": user.role,
        "koperasi_ref": user.koperasi_ref,
        "nama": user.nama,
        "nomor_whatsapp": user.nomor_whatsapp,
        "anggota_ref": None,
    }


def require_roles(*roles: str):
    """Dependency factory: allow only listed roles (case-sensitive as stored)."""
    allowed = set(roles)

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker


# Common role bundles
require_operator = require_roles("OPERATOR", "ADMIN", "PEMBINA", "KETUA", "BENDAHARA")
require_admin = require_roles("ADMIN", "PEMBINA", "KETUA", "BENDAHARA")
require_any_auth = get_current_user
