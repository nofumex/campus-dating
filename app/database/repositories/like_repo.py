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
        """Создать лайк/дизлайк.
        
        ВАЖНО: каждый новый лайк создаётся отдельной записью, даже если между
        этими же пользователями уже были лайки/дизлайки. Это позволяет
        одному и тому же пользователю лайкать другого много раз, а анкете
        появляться несколько раз во входящих лайках и мэтчах.
        """
        # Всегда создаём новую запись лайка
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
        # Теперь между пользователями может быть несколько лайков,
        # поэтому просто проверяем, что нашлась ХОТЯ БЫ одна строка,
        # не используя scalar_one_or_none (оно кидает MultipleResultsFound).
        return result.first() is not None

    @staticmethod
    async def delete_between_users(
        session: AsyncSession,
        user1_id: int,
        user2_id: int
    ) -> None:
        """Удалить все лайки между двумя пользователями (в обе стороны)."""
        from sqlalchemy import or_

        stmt = select(Like).where(
            or_(
                and_(Like.from_user_id == user1_id, Like.to_user_id == user2_id),
                and_(Like.from_user_id == user2_id, Like.to_user_id == user1_id),
            )
        )
        result = await session.execute(stmt)
        likes = list(result.scalars().all())
        for like in likes:
            await session.delete(like)
        await session.flush()
    
    @staticmethod
    async def get_incoming_likes(
        session: AsyncSession,
        user_id: int
    ) -> List[Like]:
        """Получить ВСЕ входящие лайки пользователя.
        
        Не фильтруем по существующим мэтчам и не исключаем повторные лайки:
        если кто-то лайкает пользователя несколько раз, все такие лайки
        попадают в список (последние будут сверху).
        """
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

