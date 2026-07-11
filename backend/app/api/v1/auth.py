from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
from datetime import datetime, timedelta
from app.database import get_db
from app.config import settings
from app.models.koptumbuh import PenggunaKoptumbuh
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from app.schemas.common import ApiResponse
import bcrypt

router = APIRouter(prefix="/auth", tags=["auth"])

# Demo password hash (bcrypt.hashpw(b"kop123", bcrypt.gensalt()))
DEMO_PASSWORD_HASH = b"$2b$12$l2WMB/RfJ1Fy3ZQLO9ZhuONE600pM5d2AMLG5xpCIWEUlmFlo/ZIi"


def create_token(data: dict, expires_delta: timedelta = None) -> str:
    if not settings.JWT_SECRET_KEY:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY not configured")
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post("/login", response_model=ApiResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with phone + password (bcrypt)."""
    result = await db.execute(
        select(PenggunaKoptumbuh).where(
            PenggunaKoptumbuh.nomor_whatsapp == body.phone,
            PenggunaKoptumbuh.status_aktif == True,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Verify password (demo: all users use "kop123")
    if not bcrypt.checkpw(body.password.encode(), DEMO_PASSWORD_HASH):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_token({
        "sub": str(user.pengguna_id),
        "role": user.role,
        "koperasi_ref": user.koperasi_ref,
    })
    refresh_token = create_token({
        "sub": str(user.pengguna_id), "type": "refresh",
        "role": user.role, "koperasi_ref": user.koperasi_ref,
    }, timedelta(days=7))

    return ApiResponse(data={
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "pengguna_id": str(user.pengguna_id),
            "nama": user.nama,
            "role": user.role,
            "koperasi_ref": user.koperasi_ref,
            "nomor_whatsapp": user.nomor_whatsapp,
        }
    })


@router.post("/refresh", response_model=ApiResponse)
async def refresh(body: RefreshRequest):
    """Refresh access token."""
    try:
        payload = jwt.decode(body.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        # Preserve all claims from original refresh token
        access_token = create_token({
            "sub": payload["sub"],
            "role": payload.get("role", "OPERATOR"),
            "koperasi_ref": payload.get("koperasi_ref", ""),
        })
        return ApiResponse(data={"access_token": access_token})
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
