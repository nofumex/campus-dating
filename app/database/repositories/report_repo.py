"""Репозиторий для работы с жалобами."""
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database.models import Report


class ReportRepository:
    """Репозиторий для работы с жалобами."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        from_user_id: int,
        to_user_id: int,
        reason: str,
        comment: Optional[str] = None
    ) -> Report:
        """Создать жалобу."""
        report = Report(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            reason=reason,
            comment=comment
        )
        session.add(report)
        await session.flush()
        await session.refresh(report)
        return report
    
    @staticmethod
    async def get_pending(
        session: AsyncSession
    ) -> List[Report]:
        """Получить все необработанные жалобы."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.from_user),
                selectinload(Report.to_user)
            )
            .where(Report.status == "pending")
            .order_by(Report.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        report_id: int
    ) -> Optional[Report]:
        """Получить жалобу по ID."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.from_user),
                selectinload(Report.to_user)
            )
            .where(Report.id == report_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_status(
        session: AsyncSession,
        report_id: int,
        status: str,
        admin_comment: Optional[str] = None
    ) -> Optional[Report]:
        """Обновить статус жалобы."""
        report = await ReportRepository.get_by_id(session, report_id)
        if report:
            report.status = status
            report.admin_comment = admin_comment
            report.reviewed_at = datetime.utcnow()
            await session.flush()
            await session.refresh(report)
        return report



