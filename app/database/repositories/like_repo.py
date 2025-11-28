"""Репозиторий для работы с лайками."""
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Like, User


class LikeRepository:
    """Репозиторий для работы с лайками."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        from_user_id: int,
        to_user_id: int,
        is_like: bool,
        message: Optional[str] = None
    ) -> Like:
        """Создать лайк/дизлайк. Если уже существует, обновляет существующий."""
        # Проверяем, существует ли уже лайк
        existing_like = await LikeRepository.get_by_ids(session, from_user_id, to_user_id)
        
        if existing_like:
            # Обновляем существующий лайк
            existing_like.is_like = is_like
            if message is not None:
                existing_like.message = message
            await session.flush()
            await session.refresh(existing_like)
            return existing_like
        
        # Создаем новый лайк
        like = Like(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            is_like=is_like,
            message=message
        )
        session.add(like)
        await session.flush()
        await session.refresh(like)
        return like
    
    @staticmethod
    async def check_mutual_like(
        session: AsyncSession,
        user1_id: int,
        user2_id: int
    ) -> bool:
        """Проверить, есть ли взаимный лайк."""
        stmt = select(Like).where(
            and_(
                Like.from_user_id == user2_id,
                Like.to_user_id == user1_id,
                Like.is_like == True
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def get_incoming_likes(
        session: AsyncSession,
        user_id: int
    ) -> List[Like]:
        """Получить входящие лайки пользователя (исключая только тех, с кем уже есть мэтч)."""
        from app.database.repositories.match_repo import MatchRepository
        
        # Получаем все входящие лайки
        stmt = (
            select(Like)
            .options(selectinload(Like.from_user))
            .where(
                and_(
                    Like.to_user_id == user_id,
                    Like.is_like == True
                )
            )
            .order_by(Like.created_at.desc())
        )
        result = await session.execute(stmt)
        incoming_likes = list(result.scalars().all())
        
        # Исключаем только тех, с кем уже есть мэтч
        if incoming_likes:
            filtered_likes = []
            for like in incoming_likes:
                # Проверяем, есть ли мэтч с этим пользователем
                has_match = await MatchRepository.check_match_exists(
                    session,
                    user_id,
                    like.from_user_id
                )
                if not has_match:
                    filtered_likes.append(like)
            return filtered_likes
        
        return incoming_likes
    
    @staticmethod
    async def get_by_ids(
        session: AsyncSession,
        from_user_id: int,
        to_user_id: int
    ) -> Optional[Like]:
        """Получить лайк по ID пользователей."""
        stmt = select(Like).where(
            and_(
                Like.from_user_id == from_user_id,
                Like.to_user_id == to_user_id
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

