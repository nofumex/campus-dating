"""Сервис для подбора анкет."""
from typing import Optional, List
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import User, ViewedProfile


class MatchingService:
    """Сервис для подбора анкет."""
    
    @staticmethod
    async def get_viewed_profile_ids(
        session: AsyncSession,
        user_id: int
    ) -> List[int]:
        """Получить ID просмотренных анкет."""
        stmt = select(ViewedProfile.viewed_id).where(
            ViewedProfile.viewer_id == user_id
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_next_profile(
        session: AsyncSession,
        user: User
    ) -> Optional[User]:
        """Получить следующую анкету для просмотра."""
        # Получить ID уже просмотренных
        viewed_ids = await MatchingService.get_viewed_profile_ids(session, user.id)
        
        # Определить искомый пол
        if user.looking_for == "any":
            gender_filter = ["male", "female"]
        else:
            gender_filter = [user.looking_for]
        
        # Запрос
        conditions = [
            User.university_id == user.university_id,  # Тот же университет
            User.id != user.id,  # Не сам себе
            User.is_active == True,
            User.is_banned == False,
            User.is_registered == True,
            User.show_in_search == True,
            User.gender.in_(gender_filter),
            # Взаимный интерес по полу
            or_(
                User.looking_for == "any",
                User.looking_for == user.gender
            )
        ]
        
        if viewed_ids:
            conditions.append(User.id.not_in(viewed_ids))
        
        query = select(User).where(
            *conditions
        ).options(
            selectinload(User.university)
        ).order_by(
            User.last_active.desc()  # Сначала активные
        ).limit(1)
        
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def mark_as_viewed(
        session: AsyncSession,
        viewer_id: int,
        viewed_id: int
    ) -> None:
        """Пометить анкету как просмотренную."""
        viewed = ViewedProfile(
            viewer_id=viewer_id,
            viewed_id=viewed_id
        )
        session.add(viewed)
        await session.flush()
    
    @staticmethod
    async def reset_views(
        session: AsyncSession,
        user_id: int
    ) -> None:
        """Сбросить просмотренные анкеты."""
        stmt = select(ViewedProfile).where(ViewedProfile.viewer_id == user_id)
        result = await session.execute(stmt)
        viewed_profiles = result.scalars().all()
        
        for viewed in viewed_profiles:
            await session.delete(viewed)
        
        await session.flush()

    @staticmethod
    async def reset_views_between_users(
        session: AsyncSession,
        user1_id: int,
        user2_id: int
    ) -> None:
        """Удалить пометки просмотра анкет между двумя пользователями (в обе стороны)."""
        stmt = select(ViewedProfile).where(
            or_(
                and_(ViewedProfile.viewer_id == user1_id, ViewedProfile.viewed_id == user2_id),
                and_(ViewedProfile.viewer_id == user2_id, ViewedProfile.viewed_id == user1_id),
            )
        )
        result = await session.execute(stmt)
        viewed_profiles = result.scalars().all()
        for vp in viewed_profiles:
            await session.delete(vp)
        await session.flush()

