"""Репозиторий для работы с университетами."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import University


class UniversityRepository:
    """Репозиторий для работы с университетами."""
    
    @staticmethod
    async def get_all_active(session: AsyncSession) -> List[University]:
        """Получить все активные университеты."""
        stmt = select(University).where(University.is_active == True)
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        university_id: int
    ) -> Optional[University]:
        """Получить университет по ID."""
        stmt = select(University).where(University.id == university_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(
        session: AsyncSession,
        name: str,
        short_name: str,
        city: str
    ) -> University:
        """Создать новый университет."""
        university = University(
            name=name,
            short_name=short_name,
            city=city
        )
        session.add(university)
        await session.flush()
        await session.refresh(university)
        return university
    
    @staticmethod
    async def update(
        session: AsyncSession,
        university_id: int,
        data: dict
    ) -> Optional[University]:
        """Обновить информацию об университете."""
        university = await UniversityRepository.get_by_id(session, university_id)
        if not university:
            return None
        
        for key, value in data.items():
            if hasattr(university, key):
                setattr(university, key, value)
        
        await session.flush()
        await session.refresh(university)
        return university
    
    @staticmethod
    async def delete(
        session: AsyncSession,
        university_id: int
    ) -> bool:
        """Удалить университет (деактивировать)."""
        university = await UniversityRepository.get_by_id(session, university_id)
        if not university:
            return False
        
        university.is_active = False
        await session.flush()
        return True
    
    @staticmethod
    async def get_by_short_name(
        session: AsyncSession,
        short_name: str
    ) -> Optional[University]:
        """Получить университет по аббревиатуре."""
        stmt = select(University).where(
            University.short_name == short_name,
            University.is_active == True
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()





