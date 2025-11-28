"""Скрипт для автоматической настройки базы данных."""
import asyncio
import sys
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import Config

async def setup_database():
    """Настройка базы данных."""
    print("🔍 Проверка и настройка базы данных...\n")
    
    # Парсим DATABASE_URL
    db_url = Config.DATABASE_URL
    if not db_url.startswith("postgresql+asyncpg://"):
        print("❌ Неверный формат DATABASE_URL")
        return False
    
    # Получаем базовый URL без имени БД
    base_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    # Извлекаем имя БД из URL
    if "/" in base_url:
        parts = base_url.rsplit("/", 1)
        base_connection = parts[0]
        db_name = parts[1].split("?")[0] if "?" in parts[1] else parts[1]
    else:
        print("❌ Не удалось извлечь имя БД из URL")
        return False
    
    print(f"📊 База данных: {db_name}")
    print(f"🔗 Подключение: {base_connection}\n")
    
    # Подключаемся к PostgreSQL (к базе postgres по умолчанию)
    try:
        # Используем синхронный движок для создания БД
        sync_engine = create_engine(
            f"{base_connection}/postgres",
            isolation_level="AUTOCOMMIT"
        )
        
        with sync_engine.connect() as conn:
            # Проверяем, существует ли БД
            result = conn.execute(text(
                f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
            ))
            exists = result.fetchone() is not None
            
            if not exists:
                print(f"📦 База данных '{db_name}' не найдена. Создаю...")
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print(f"✅ База данных '{db_name}' создана!")
            else:
                print(f"✅ База данных '{db_name}' уже существует")
        
        sync_engine.dispose()
        
    except Exception as e:
        print(f"❌ Ошибка при работе с БД: {e}")
        print("\nВозможные причины:")
        print("1. PostgreSQL не запущен")
        print("2. Неверные учетные данные в DATABASE_URL")
        print("3. Нет прав на создание БД")
        return False
    
    # Теперь проверяем подключение к нашей БД
    print(f"\n🔌 Проверка подключения к '{db_name}'...")
    try:
        async_engine = create_async_engine(db_url, echo=False)
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Подключение успешно!")
            print(f"   PostgreSQL версия: {version.split(',')[0]}")
        
        await async_engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

async def apply_migrations():
    """Применение миграций."""
    print("\n📋 Применение миграций...")
    try:
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Миграции применены!")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ Ошибка применения миграций:")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут при применении миграций")
        return False
    except Exception as e:
        print(f"❌ Ошибка применения миграций: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    if await setup_database():
        if await apply_migrations():
            print("\n✅ База данных настроена и готова к работе!")
            print("\n🚀 Теперь можно запустить бота: python bot.py")
            return True
    
    print("\n❌ Не удалось настроить базу данных")
    return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

