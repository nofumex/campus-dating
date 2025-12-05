"""Скрипт для проверки подключения и запуска бота."""
import asyncio
import sys
from app.config import Config
from app.database.engine import engine

async def check_db():
    """Проверка подключения к БД."""
    try:
        Config.validate()
        print("✅ Конфигурация валидна")
        print(f"   BOT_TOKEN: {'установлен' if Config.BOT_TOKEN else 'НЕ установлен'}")
        print(f"   ADMIN_ID: {Config.ADMIN_ID}")
        print(f"   DATABASE_URL: {Config.DATABASE_URL[:30]}...")
        
        # Проверка подключения к БД
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        print("✅ Подключение к БД успешно")
        return True
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print("   Убедитесь, что PostgreSQL запущен и база данных создана")
        return False

if __name__ == "__main__":
    if asyncio.run(check_db()):
        print("\n🚀 Запуск бота...")
        from bot import main
        asyncio.run(main())
    else:
        print("\n❌ Не удалось запустить бота. Исправьте ошибки выше.")
        sys.exit(1)






