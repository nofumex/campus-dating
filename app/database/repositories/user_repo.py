"""Репозиторий для работы с пользователями."""
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database.models import User, University


class UserRepository:
    """Репозиторий для работы с пользователями."""
    
    @staticmethod
    async def get_by_telegram_id(
        session: AsyncSession,
        telegram_id: int
    ) -> Optional[User]:
        """Получить пользователя по Telegram ID."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(session: AsyncSession, user_data: dict) -> User:
        """Создать нового пользователя."""
        user = User(**user_data)
        session.add(user)
        await session.flush()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def update(
        session: AsyncSession,
        user_id: int,
        update_data: dict
    ) -> Optional[User]:
        """Обновить данные пользователя."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**update_data, updated_at=datetime.utcnow())
            .returning(User)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_last_active(
        session: AsyncSession,
        user_id: int
    ) -> None:
        """Обновить время последней активности."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_active=datetime.utcnow())
        )
        await session.execute(stmt)
        await session.flush()
    
    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        user_id: int
    ) -> Optional[User]:
        """Получить пользователя по ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_with_university(
        session: AsyncSession,
        user_id: int
    ) -> Optional[User]:
        """Получить пользователя с загруженным университетом."""
        stmt = (
            select(User)
            .options(selectinload(User.university))
            .where(User.id == user_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

