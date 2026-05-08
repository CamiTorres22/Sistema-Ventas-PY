"""
auth.py — Autenticación JWT simple

Endpoints:
  POST /auth/login   → devuelve access_token
  GET  /auth/me      → datos del usuario autenticado
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import LoginLog, Usuario
from backend.app.schemas import LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# ── Configuración JWT ──────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("SECRET_KEY", "dev_secret_key_cambia_en_produccion_abc123xyz")
ALGORITHM   = os.getenv("ALGORITHM", "HS256")
EXPIRE_MIN  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MIN)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(Usuario).where(Usuario.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.activo:
        raise credentials_exception
    return user


async def require_admin(user: Usuario = Depends(get_current_user)) -> Usuario:
    if user.rol != "admin":
        raise HTTPException(status_code=403, detail="Acceso exclusivo para administradores.")
    return user


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(form: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Autentica al usuario y devuelve un JWT."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:200]

    result = await db.execute(select(Usuario).where(Usuario.email == form.email))
    user = result.scalar_one_or_none()

    # ── Credenciales inválidas ────────────────────────────────────────────────
    if user is None or not verify_password(form.password, user.hashed_password):
        db.add(LoginLog(
            email        = form.email,
            usuario_id   = user.id if user else None,
            nombre       = user.nombre if user else None,
            rol          = user.rol if user else None,
            exitoso      = False,
            motivo_fallo = "Contraseña incorrecta" if user else "Usuario no encontrado",
            ip_address   = ip,
            user_agent   = ua,
        ))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    if not user.activo:
        db.add(LoginLog(
            email=form.email, usuario_id=user.id, nombre=user.nombre,
            rol=user.rol, exitoso=False, motivo_fallo="Usuario inactivo",
            ip_address=ip, user_agent=ua,
        ))
        await db.commit()
        raise HTTPException(status_code=403, detail="Usuario inactivo.")

    # ── Login exitoso ─────────────────────────────────────────────────────────
    db.add(LoginLog(
        email=form.email, usuario_id=user.id, nombre=user.nombre,
        rol=user.rol, exitoso=True, motivo_fallo=None,
        ip_address=ip, user_agent=ua,
    ))
    await db.commit()

    token = create_access_token({"sub": str(user.id), "rol": user.rol})
    return TokenResponse(
        access_token=token,
        rol=user.rol,
        nombre=user.nombre,
        vendedor_id=user.id,
    )


@router.get("/me", response_model=UsuarioOut)
async def me(current_user: Usuario = Depends(get_current_user)):
    """Devuelve los datos del usuario autenticado."""
    return current_user
