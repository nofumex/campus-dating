"""Модели базы данных."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    BigInteger, Boolean, ForeignKey, Integer, String, Text, 
    UniqueConstraint, func
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class University(Base):
    """Модель университета."""
    __tablename__ = "universities"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    short_name: Mapped[str] = mapped_column(String(50))
    city: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    users: Mapped[List["User"]] = relationship("User", back_populates="university")


class User(Base):
    """Модель пользователя/анкеты."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Данные анкеты
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(10))  # "male" / "female"
    looking_for: Mapped[str] = mapped_column(String(10))  # "male" / "female" / "any"
    bio: Mapped[str] = mapped_column(Text)
    
    # Медиа (до 3 фото)
    photo_1: Mapped[str] = mapped_column(String(255))
    photo_2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    photo_3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Привязка к университету
    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"))
    university: Mapped["University"] = relationship("University", back_populates="users")
    
    # Статусы
    is_active: Mapped[bool] = mapped_column(default=True)
    is_banned: Mapped[bool] = mapped_column(default=False)
    is_registered: Mapped[bool] = mapped_column(default=False)
    
    # Настройки
    show_in_search: Mapped[bool] = mapped_column(default=True)
    is_fake: Mapped[bool] = mapped_column(default=False)
    is_super_favorite: Mapped[bool] = mapped_column(default=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    last_active: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    # Связи
    sent_likes: Mapped[List["Like"]] = relationship(
        "Like",
        foreign_keys="Like.from_user_id",
        back_populates="from_user"
    )
    received_likes: Mapped[List["Like"]] = relationship(
        "Like",
        foreign_keys="Like.to_user_id",
        back_populates="to_user"
    )
    reports_sent: Mapped[List["Report"]] = relationship(
        "Report",
        foreign_keys="Report.from_user_id"
    )
    reports_received: Mapped[List["Report"]] = relationship(
        "Report",
        foreign_keys="Report.to_user_id"
    )


class Like(Base):
    """Модель лайка."""
    __tablename__ = "likes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_like: Mapped[bool] = mapped_column(Boolean)  # True = лайк, False = дизлайк
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    from_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[from_user_id],
        back_populates="sent_likes"
    )
    to_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[to_user_id],
        back_populates="received_likes"
    )


class Match(Base):
    """Модель взаимной симпатии."""
    __tablename__ = "matches"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user1_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user2_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id])
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id])


class Report(Base):
    """Модель жалобы."""
    __tablename__ = "reports"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    reason: Mapped[str] = mapped_column(String(50))
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/reviewed/rejected
    admin_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Связи
    from_user: Mapped["User"] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id])


class ViewedProfile(Base):
    """Модель просмотренной анкеты."""
    __tablename__ = "viewed_profiles"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    viewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    viewed_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('viewer_id', 'viewed_id', name='unique_view'),
    )

