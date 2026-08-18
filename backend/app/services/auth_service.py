from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import settings
from app.models import User
from app.schemas import Token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(data: dict):
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode = {**data, "exp": expire, "type": "refresh"}
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @classmethod
    async def authenticate(cls, db: AsyncSession, email: str, password: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not cls.verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        access_token = cls.create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role})
        refresh_token = cls.create_refresh_token({"sub": str(user.id)})
        return Token(access_token=access_token, refresh_token=refresh_token)

    @classmethod
    async def refresh_token(cls, db: AsyncSession, refresh_token: str):
        try:
            payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")
            user_id = payload.get("sub")
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise ValueError("User not found")

            access_token = cls.create_access_token({"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role})
            new_refresh = cls.create_refresh_token({"sub": str(user.id)})
            return Token(access_token=access_token, refresh_token=new_refresh)
        except JWTError:
            raise ValueError("Invalid refresh token")

    @classmethod
    async def register_user(cls, db: AsyncSession, user_data):
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        hashed = cls.get_password_hash(user_data.password)
        user = User(email=user_data.email, hashed_password=hashed, name=user_data.name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {"id": str(user.id), "email": user.email}

    @classmethod
    async def create_invite(cls, db: AsyncSession, tenant_id, email, role):
        return {"tenant_id": str(tenant_id), "email": email, "role": role, "status": "pending"}
