from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User, UserCreate, UserRead
from app.main import limiter

# ==========================
#  Configuración de seguridad
# ==========================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra el hash almacenado."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash bcrypt de la contraseña."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()

    if expires_delta is None:
        expires_delta = timedelta(hours=24)

    expire = now + expires_delta

    # claims mínimos que el enunciado pide: sub, user_id, exp, iat
    to_encode.update(
        {
            "exp": expire,
            "iat": now,
        }
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


# ============
#  Schemas
# ============

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ===============================
#  Endpoints de autenticación
# ===============================

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    request: Request,
    user: UserCreate,
    session: Session = Depends(get_session),
):
    # Comprobar que username o email no existan ya
    existing = session.exec(
        select(User).where(
            (User.username == user.username) | (User.email == user.email)
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario o email ya registrados",
        )

    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    session: Session = Depends(get_session),
):
    user = get_user_by_username(session, credentials.username)

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
        }
    )

    return TokenResponse(access_token=token)


async def get_current_user(
    credentials=Depends(security),
    session: Session = Depends(get_session),
) -> User:
    """Dependencia para obtener el usuario autenticado a partir del JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(session, username)
    if user is None:
        raise credentials_exception

    return user
