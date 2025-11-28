"""Репозиторий для работы с мэтчами."""
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Match, User


class MatchRepository:
    """Репозиторий для работы с мэтчами."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user1_id: int,
        user2_id: int
    ) -> Match:
        """Создать мэтч (упорядочивает ID для избежания дубликатов)."""
        first_id, second_id = sorted([user1_id, user2_id])
        
        match = Match(user1_id=first_id, user2_id=second_id)
        session.add(match)
        await session.flush()
        await session.refresh(match)
        return match
    
    @staticmethod
    async def get_user_matches(
        session: AsyncSession,
        user_id: int
    ) -> List[Match]:
        """Получить все мэтчи пользователя."""
        from sqlalchemy import and_
        stmt = (
            select(Match)
            .where(
                and_(
                    or_(
                        Match.user1_id == user_id,
                        Match.user2_id == user_id
                    ),
                    Match.is_active == True
                )
            )
            .options(
                selectinload(Match.user1),
                selectinload(Match.user2)
            )
            .order_by(Match.created_at.desc())
        )
        result = await session.execute(stmt)
        matches = list(result.scalars().all())
        
        # Возвращаем пользователя-партнера для каждого мэтча
        return matches
    
    @staticmethod
    async def get_match_partner(
        match: Match,
        user_id: int
    ) -> Optional[User]:
        """Получить партнера по мэтчу."""
        if match.user1_id == user_id:
            return match.user1
        return match.user2
    
    @staticmethod
    async def check_match_exists(
        session: AsyncSession,
        user1_id: int,
        user2_id: int
    ) -> bool:
        """Проверить, существует ли мэтч."""
        first_id, second_id = sorted([user1_id, user2_id])
        stmt = select(Match).where(
            Match.user1_id == first_id,
            Match.user2_id == second_id,
            Match.is_active == True
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

