import os
import psycopg2
from contextlib import contextmanager

# Получаем строку подключения к PostgreSQL из переменных окружения Render
DATABASE_URL = os.getenv("DATABASE_URL")

@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасного подключения к базе данных"""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Инициализация базы данных и создание таблиц"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    xp INTEGER DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    daily_score INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    premium_until TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Таблица рефералов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id BIGINT,
                    referred_id BIGINT PRIMARY KEY,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Таблица логов администратора
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT,
                    action TEXT,
                    target_id BIGINT,
                    amount INTEGER,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

def get_or_create_user(user_id: int, username: str):
    """Получает пользователя из БД или создает нового, если его нет"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
            user = cursor.fetchone()
            if not user:
                cursor.execute(
                    "INSERT INTO users (user_id, username, xp, score, daily_score, level) VALUES (%s, %s, 0, 0, 0, 1);",
                    (user_id, username)
                )
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE user_id = %s;", (user_id,))
                user = cursor.fetchone()
            return user
      
