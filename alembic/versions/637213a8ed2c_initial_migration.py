"""Initial migration

Revision ID: 637213a8ed2c
Revises: 
Create Date: 2025-11-28 20:10:24.505366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '637213a8ed2c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание таблицы universities
    op.create_table(
        'universities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('short_name', sa.String(length=50), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Создание таблицы users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=False),
        sa.Column('looking_for', sa.String(length=10), nullable=False),
        sa.Column('bio', sa.Text(), nullable=False),
        sa.Column('photo_1', sa.String(length=255), nullable=False),
        sa.Column('photo_2', sa.String(length=255), nullable=True),
        sa.Column('photo_3', sa.String(length=255), nullable=True),
        sa.Column('university_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_registered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('show_in_search', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_active', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=False)
    
    # Создание таблицы likes
    op.create_table(
        'likes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=False),
        sa.Column('to_user_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('is_like', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_user_id', 'to_user_id', name='unique_like')
    )
    op.create_index(op.f('ix_likes_from_user_id'), 'likes', ['from_user_id'], unique=False)
    op.create_index(op.f('ix_likes_to_user_id'), 'likes', ['to_user_id'], unique=False)
    
    # Создание таблицы matches
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user1_id', sa.Integer(), nullable=False),
        sa.Column('user2_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user1_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user2_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matches_user1_id'), 'matches', ['user1_id'], unique=False)
    op.create_index(op.f('ix_matches_user2_id'), 'matches', ['user2_id'], unique=False)
    
    # Создание таблицы reports
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_user_id', sa.Integer(), nullable=False),
        sa.Column('to_user_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=50), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('admin_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['to_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание таблицы viewed_profiles
    op.create_table(
        'viewed_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('viewer_id', sa.Integer(), nullable=False),
        sa.Column('viewed_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['viewed_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['viewer_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('viewer_id', 'viewed_id', name='unique_view')
    )
    op.create_index(op.f('ix_viewed_profiles_viewer_id'), 'viewed_profiles', ['viewer_id'], unique=False)
    op.create_index(op.f('ix_viewed_profiles_viewed_id'), 'viewed_profiles', ['viewed_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_viewed_profiles_viewed_id'), table_name='viewed_profiles')
    op.drop_index(op.f('ix_viewed_profiles_viewer_id'), table_name='viewed_profiles')
    op.drop_table('viewed_profiles')
    op.drop_table('reports')
    op.drop_index(op.f('ix_matches_user2_id'), table_name='matches')
    op.drop_index(op.f('ix_matches_user1_id'), table_name='matches')
    op.drop_table('matches')
    op.drop_index(op.f('ix_likes_to_user_id'), table_name='likes')
    op.drop_index(op.f('ix_likes_from_user_id'), table_name='likes')
    op.drop_table('likes')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_table('users')
    op.drop_table('universities')
