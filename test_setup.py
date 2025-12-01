"""Тестовый скрипт для проверки настройки."""
import asyncio
import sys
from sqlalchemy import text

async def test_setup():
    """Проверка всех компонентов."""
    print("🔍 Проверка настройки бота...\n")
    
    # 1. Проверка конфигурации
    try:
        from app.config import Config
        Config.validate()
        print("✅ Конфигурация (.env) - OK")
        print(f"   BOT_TOKEN: {'✓ установлен' if Config.BOT_TOKEN else '✗ НЕ установлен'}")
        print(f"   ADMIN_ID: {Config.ADMIN_ID if Config.ADMIN_ID else '✗ НЕ установлен'}")
    except ValueError as e:
        print(f"❌ Конфигурация - ОШИБКА: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False
    
    # 2. Проверка подключения к БД
    try:
        from app.database.engine import engine
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        print("✅ Подключение к БД - OK")
    except Exception as e:
        print(f"❌ Подключение к БД - ОШИБКА: {e}")
        print("   Убедитесь, что:")
        print("   1. PostgreSQL запущен")
        print("   2. База данных 'dating_bot' создана")
        print("   3. DATABASE_URL в .env правильный")
        return False
    
    # 3. Проверка таблиц
    try:
        from app.database.engine import engine
        from sqlalchemy import inspect
        async with engine.begin() as conn:
            # Проверяем наличие таблиц
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result.fetchall()]
            
            required_tables = ['universities', 'users', 'likes', 'matches', 'reports', 'viewed_profiles']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"⚠️  Таблицы не созданы: {', '.join(missing_tables)}")
                print("   Выполните: alembic upgrade head")
                return False
            else:
                print("✅ Таблицы БД - OK")
    except Exception as e:
        print(f"⚠️  Не удалось проверить таблицы: {e}")
        print("   Возможно, нужно выполнить: alembic upgrade head")
    
    # 4. Проверка импортов
    try:
        from app.handlers import start, registration, profile, viewing, likes, matches, messages, reports, admin
        print("✅ Импорты handlers - OK")
    except Exception as e:
        print(f"❌ Ошибка импорта handlers: {e}")
        return False
    
    print("\n✅ Все проверки пройдены! Бот готов к запуску.")
    print("\n🚀 Запуск бота...\n")
    return True

if __name__ == "__main__":
    try:
        if asyncio.run(test_setup()):
            from bot import main
            asyncio.run(main())
        else:
            print("\n❌ Исправьте ошибки перед запуском бота.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



