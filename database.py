"""
StudyGo — Database module
PostgreSQL via psycopg2
"""

import os
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values


DATABASE_URL = os.getenv("DATABASE_URL")


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        yield conn
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def init_db():
    """Create all tables if they do not exist."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id         BIGINT PRIMARY KEY,
                    username        TEXT,
                    first_name      TEXT,
                    last_name       TEXT,
                    xp              INTEGER NOT NULL DEFAULT 0,
                    score           INTEGER NOT NULL DEFAULT 0,
                    daily_score     INTEGER NOT NULL DEFAULT 0,
                    level           INTEGER NOT NULL DEFAULT 1,
                    premium_until   TIMESTAMP WITH TIME ZONE,
                    streak           INTEGER NOT NULL DEFAULT 0,
                    last_daily_date DATE,
                    last_weekly_date DATE,
                    solved_tasks    INTEGER NOT NULL DEFAULT 0,
                    is_blocked      BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referred_id     BIGINT PRIMARY KEY,
                    referrer_id     BIGINT NOT NULL,
                    is_confirmed    BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    confirmed_at    TIMESTAMP WITH TIME ZONE,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id),
                    FOREIGN KEY (referred_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_referrals_referrer
                ON referrals(referrer_id);
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id              SERIAL PRIMARY KEY,
                    admin_id        BIGINT NOT NULL,
                    action          TEXT NOT NULL,
                    target_id       BIGINT,
                    amount          INTEGER,
                    details         TEXT,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS xp_transactions (
                    id              SERIAL PRIMARY KEY,
                    user_id         BIGINT NOT NULL,
                    amount          INTEGER NOT NULL,
                    type            TEXT NOT NULL,
                    reason          TEXT,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_xp_transactions_user
                ON xp_transactions(user_id);
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS stars_purchases (
                    id              SERIAL PRIMARY KEY,
                    user_id         BIGINT NOT NULL,
                    stars_amount    INTEGER NOT NULL,
                    product_type    TEXT NOT NULL,
                    product_value   INTEGER,
                    telegram_payment_charge_id TEXT,
                    provider_payment_charge_id TEXT,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_tasks (
                    id              SERIAL PRIMARY KEY,
                    user_id         BIGINT NOT NULL,
                    task_date       DATE NOT NULL,
                    completed       BOOLEAN NOT NULL DEFAULT FALSE,
                    reward_claimed  BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, task_date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS weekly_tasks (
                    id              SERIAL PRIMARY KEY,
                    user_id         BIGINT NOT NULL,
                    week_start      DATE NOT NULL,
                    completed       BOOLEAN NOT NULL DEFAULT FALSE,
                    reward_claimed  BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, week_start),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_rank_history (
                    id              SERIAL PRIMARY KEY,
                    rank_date       DATE NOT NULL,
                    user_id         BIGINT NOT NULL,
                    place           INTEGER NOT NULL,
                    daily_score     INTEGER NOT NULL,
                    reward_xp       INTEGER NOT NULL DEFAULT 0,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    UNIQUE(rank_date, user_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_rank_history_date
                ON daily_rank_history(rank_date);
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS achievements (
                    id              SERIAL PRIMARY KEY,
                    code            TEXT UNIQUE NOT NULL,
                    title           TEXT NOT NULL,
                    description     TEXT,
                    xp_reward       INTEGER NOT NULL DEFAULT 0,
                    score_reward    INTEGER NOT NULL DEFAULT 0,
                    icon            TEXT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id         BIGINT NOT NULL,
                    achievement_id  INTEGER NOT NULL,
                    earned_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (user_id, achievement_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (achievement_id) REFERENCES achievements(id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_usage (
                    id              SERIAL PRIMARY KEY,
                    user_id         BIGINT NOT NULL,
                    request_type    TEXT NOT NULL,
                    xp_spent        INTEGER NOT NULL DEFAULT 0,
                    is_premium      BOOLEAN NOT NULL DEFAULT FALSE,
                    success         BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_usage_user
                ON ai_usage(user_id);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_usage_created
                ON ai_usage(created_at);
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS economy_settings (
                    key             TEXT PRIMARY KEY,
                    value           TEXT NOT NULL,
                    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_by      BIGINT
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscription_checks (
                    user_id         BIGINT PRIMARY KEY,
                    is_subscribed   BOOLEAN NOT NULL DEFAULT FALSE,
                    checked_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
            """)

            _seed_achievements(cur)
            _seed_economy_settings(cur)


def _seed_achievements(cur):
    """Insert default achievements if table is empty."""
    cur.execute("SELECT COUNT(*) AS cnt FROM achievements")

    if cur.fetchone()["cnt"] > 0:
        return

    defaults = [
        (
            "first_task",
            "Первое задание",
            "Решил первое задание",
            20,
            10,
            "🟢",
        ),
        (
            "streak_7",
            "7 дней активности",
            "Активность 7 дней подряд",
            100,
            50,
            "🔥",
        ),
        (
            "solved_100",
            "100 решённых заданий",
            "Решил 100 заданий",
            200,
            100,
            "📚",
        ),
        (
            "referrals_10",
            "10 успешных рефералов",
            "Пригласил 10 друзей",
            150,
            80,
            "👥",
        ),
        (
            "referrals_50",
            "50 успешных рефералов",
            "Пригласил 50 друзей",
            500,
            250,
            "🚀",
        ),
        (
            "top10",
            "TOP-10",
            "Попал в TOP-10 Daily Rank",
            100,
            50,
            "🏆",
        ),
        (
            "first_premium",
            "Первая покупка Premium",
            "Купил Premium впервые",
            50,
            30,
            "💎",
        ),
    ]

    for code, title, desc, xp, score, icon in defaults:
        cur.execute(
            """
            INSERT INTO achievements
                (code, title, description, xp_reward, score_reward, icon)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
            """,
            (code, title, desc, xp, score, icon),
        )


def _seed_economy_settings(cur):
    """Insert default economy values if missing."""
    defaults = {
        "star_to_xp_rate": "10",
        "cost_check_answer": "10",
        "cost_simple_task": "10",
        "cost_explain_topic": "20",
        "cost_normal_task": "20",
        "cost_hard_task": "30",
        "cost_photo_task": "30",
        "cost_create_test": "30",
        "cost_big_analysis": "40",
        "cost_very_hard": "50",
        "premium_1_day": "50",
        "premium_7_days": "200",
        "premium_30_days": "750",
        "daily_task_reward": "30",
        "daily_streak_3": "50",
        "daily_streak_7": "100",
        "daily_streak_30": "500",
        "weekly_task_reward": "200",
        "weekly_streak_3": "300",
        "weekly_streak_4": "500",
        "referral_referrer_xp": "100",
        "referral_referred_xp": "20",
        "daily_rank_1": "100",
        "daily_rank_2": "70",
        "daily_rank_3": "50",
        "ds_solve_task": "5",
        "ds_explain": "5",
        "ds_photo": "7",
        "ds_create_test": "7",
        "ds_daily_task": "20",
        "ds_special": "25",
        "score_solve_task": "5",
        "score_daily_task": "30",
        "score_weekly_task": "200",
    }

    for key, value in defaults.items():
        cur.execute(
            """
            INSERT INTO economy_settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO NOTHING
            """,
            (key, value),
            )
        def create_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a user or update basic profile information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    user_id,
                    username,
                    first_name,
                    last_name
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    updated_at = NOW()
                RETURNING *
                """,
                (user_id, username, first_name, last_name),
            )
            return cur.fetchone()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by Telegram ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )
            return cur.fetchone()


def user_exists(user_id: int) -> bool:
    """Check whether user exists."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM users
                    WHERE user_id = %s
                ) AS exists
                """,
                (user_id,),
            )
            return bool(cur.fetchone()["exists"])


def is_user_blocked(user_id: int) -> bool:
    """Check whether user is blocked."""
    user = get_user(user_id)
    return bool(user and user["is_blocked"])


def set_user_blocked(user_id: int, blocked: bool) -> bool:
    """Block or unblock a user."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET is_blocked = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING user_id
                """,
                (blocked, user_id),
            )
            return cur.fetchone() is not None


def update_user_profile(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update user's Telegram profile."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    username = %s,
                    first_name = %s,
                    last_name = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING *
                """,
                (
                    username,
                    first_name,
                    last_name,
                    user_id,
                ),
            )
            return cur.fetchone()


def get_setting(
    key: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """Get economy setting."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT value
                FROM economy_settings
                WHERE key = %s
                """,
                (key,),
            )

            row = cur.fetchone()

            if row is None:
                return default

            return row["value"]


def get_setting_int(
    key: str,
    default: int = 0,
) -> int:
    """Get economy setting as integer."""
    value = get_setting(key)

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def set_setting(
    key: str,
    value: Any,
    updated_by: Optional[int] = None,
) -> bool:
    """Create or update economy setting."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO economy_settings (
                    key,
                    value,
                    updated_at,
                    updated_by
                )
                VALUES (%s, %s, NOW(), %s)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                """,
                (key, str(value), updated_by),
            )

            return True


def add_xp(
    user_id: int,
    amount: int,
    reason: Optional[str] = None,
    transaction_type: str = "manual",
) -> Tuple[int, int]:
    """
    Add XP to user.

    Returns:
        (new_xp, new_level)
    """
    if amount == 0:
        user = get_user(user_id)
        if not user:
            raise ValueError("User does not exist")

        return user["xp"], user["level"]

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    xp = GREATEST(0, xp + %s),
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING xp
                """,
                (amount, user_id),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError("User does not exist")

            new_xp = row["xp"]

            cur.execute(
                """
                INSERT INTO xp_transactions (
                    user_id,
                    amount,
                    type,
                    reason
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    amount,
                    transaction_type,
                    reason,
                ),
            )

            new_level = calculate_level(new_xp)

            cur.execute(
                """
                UPDATE users
                SET level = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (new_level, user_id),
            )

            return new_xp, new_level


def calculate_level(xp: int) -> int:
    """Calculate level from XP."""
    if xp < 0:
        xp = 0

    level = 1
    required = 100

    while xp >= required:
        xp -= required
        level += 1
        required = 100 + (level - 1) * 50

    return level


def get_xp_history(
    user_id: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get XP transaction history."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM xp_transactions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return cur.fetchall()


def add_score(
    user_id: int,
    amount: int,
) -> Tuple[int, int]:
    """
    Add score and return:
        (new_score, new_level)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    score = GREATEST(0, score + %s),
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING score, level
                """,
                (amount, user_id),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError("User does not exist")

            new_score = row["score"]
            new_level = calculate_level(new_score)

            cur.execute(
                """
                UPDATE users
                SET level = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (new_level, user_id),
            )

            return new_score, new_level


def add_daily_score(
    user_id: int,
    amount: int,
) -> int:
    """Add points to daily score."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    daily_score = GREATEST(0, daily_score + %s),
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING daily_score
                """,
                (amount, user_id),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError("User does not exist")

            return row["daily_score"]


def increment_solved_tasks(user_id: int) -> int:
    """Increment solved tasks counter."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    solved_tasks = solved_tasks + 1,
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING solved_tasks
                """,
                (user_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError("User does not exist")

            return row["solved_tasks"]


def reset_daily_scores() -> int:
    """Reset all daily scores."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET
                    daily_score = 0,
                    updated_at = NOW()
                WHERE daily_score <> 0
                """
            )

            return cur.rowcount


def get_top_users(
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get global leaderboard."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    user_id,
                    username,
                    first_name,
                    xp,
                    score,
                    level,
                    solved_tasks
                FROM users
                WHERE is_blocked = FALSE
                ORDER BY score DESC, xp DESC, solved_tasks DESC
                LIMIT %s
                """,
                (limit,),
            )

            return cur.fetchall()


def get_daily_top_users(
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get daily leaderboard."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    user_id,
                    username,
                    first_name,
                    daily_score,
                    score,
                    level
                FROM users
                WHERE is_blocked = FALSE
                ORDER BY daily_score DESC, score DESC
                LIMIT %s
                """,
                (limit,),
            )

            return cur.fetchall()
            def create_referral(
    referred_id: int,
    referrer_id: int,
) -> bool:
    """
    Create referral relationship.

    The referral is initially unconfirmed.
    """
    if referred_id == referrer_id:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM referrals
                WHERE referred_id = %s
                """,
                (referred_id,),
            )

            if cur.fetchone():
                return False

            cur.execute(
                """
                SELECT 1
                FROM users
                WHERE user_id = %s
                """,
                (referrer_id,),
            )

            if cur.fetchone() is None:
                return False

            cur.execute(
                """
                SELECT 1
                FROM users
                WHERE user_id = %s
                """,
                (referred_id,),
            )

            if cur.fetchone() is None:
                return False

            cur.execute(
                """
                INSERT INTO referrals (
                    referred_id,
                    referrer_id
                )
                VALUES (%s, %s)
                ON CONFLICT (referred_id) DO NOTHING
                """,
                (referred_id, referrer_id),
            )

            return cur.rowcount > 0


def get_referral(
    referred_id: int,
) -> Optional[Dict[str, Any]]:
    """Get referral information."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM referrals
                WHERE referred_id = %s
                """,
                (referred_id,),
            )

            return cur.fetchone()


def get_referrer(
    referred_id: int,
) -> Optional[int]:
    """Get referrer ID."""
    referral = get_referral(referred_id)

    if not referral:
        return None

    return referral["referrer_id"]


def confirm_referral(
    referred_id: int,
) -> bool:
    """
    Confirm referral and reward both users.

    Returns True only when confirmation happened now.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    referred_id,
                    referrer_id,
                    is_confirmed
                FROM referrals
                WHERE referred_id = %s
                FOR UPDATE
                """,
                (referred_id,),
            )

            referral = cur.fetchone()

            if referral is None:
                return False

            if referral["is_confirmed"]:
                return False

            referrer_id = referral["referrer_id"]

            cur.execute(
                """
                UPDATE referrals
                SET
                    is_confirmed = TRUE,
                    confirmed_at = NOW()
                WHERE referred_id = %s
                """,
                (referred_id,),
            )

            referrer_xp = get_setting_int(
                "referral_referrer_xp",
                100,
            )

            referred_xp = get_setting_int(
                "referral_referred_xp",
                20,
            )

            cur.execute(
                """
                UPDATE users
                SET xp = xp + %s,
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (referrer_xp, referrer_id),
            )

            cur.execute(
                """
                UPDATE users
                SET xp = xp + %s,
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (referred_xp, referred_id),
            )

            cur.execute(
                """
                INSERT INTO xp_transactions (
                    user_id,
                    amount,
                    type,
                    reason
                )
                VALUES
                    (%s, %s, 'referral', 'Реферальная награда'),
                    (%s, %s, 'referral', 'Бонус за регистрацию по приглашению')
                """,
                (
                    referrer_id,
                    referrer_xp,
                    referred_id,
                    referred_xp,
                ),
            )

            return True


def get_referral_count(
    user_id: int,
    confirmed_only: bool = True,
) -> int:
    """Get number of referrals."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if confirmed_only:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM referrals
                    WHERE referrer_id = %s
                      AND is_confirmed = TRUE
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM referrals
                    WHERE referrer_id = %s
                    """,
                    (user_id,),
                )

            return int(cur.fetchone()["cnt"])


def get_referrals(
    user_id: int,
    confirmed_only: bool = False,
) -> List[Dict[str, Any]]:
    """Get user's referrals."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if confirmed_only:
                cur.execute(
                    """
                    SELECT
                        r.*,
                        u.username,
                        u.first_name,
                        u.last_name
                    FROM referrals r
                    JOIN users u
                        ON u.user_id = r.referred_id
                    WHERE r.referrer_id = %s
                      AND r.is_confirmed = TRUE
                    ORDER BY r.created_at DESC
                    """,
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        r.*,
                        u.username,
                        u.first_name,
                        u.last_name
                    FROM referrals r
                    JOIN users u
                        ON u.user_id = r.referred_id
                    WHERE r.referrer_id = %s
                    ORDER BY r.created_at DESC
                    """,
                    (user_id,),
                )

            return cur.fetchall()


def get_referral_leaderboard(
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get users with the most confirmed referrals."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    u.user_id,
                    u.username,
                    u.first_name,
                    COUNT(r.referred_id) AS referrals
                FROM users u
                LEFT JOIN referrals r
                    ON r.referrer_id = u.user_id
                   AND r.is_confirmed = TRUE
                WHERE u.is_blocked = FALSE
                GROUP BY
                    u.user_id,
                    u.username,
                    u.first_name
                ORDER BY referrals DESC, u.user_id
                LIMIT %s
                """,
                (limit,),
            )

            return cur.fetchall()


def update_streak(
    user_id: int,
    activity_date: Optional[date] = None,
) -> int:
    """
    Update user's daily streak.

    If the user was active yesterday, streak increases.
    If activity is already recorded today, it is not increased twice.
    """
    if activity_date is None:
        activity_date = date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT streak, last_daily_date
                FROM users
                WHERE user_id = %s
                FOR UPDATE
                """,
                (user_id,),
            )

            user = cur.fetchone()

            if user is None:
                raise ValueError("User does not exist")

            last_date = user["last_daily_date"]
            streak = user["streak"] or 0

            if last_date == activity_date:
                return streak

            if last_date == activity_date - timedelta(days=1):
                streak += 1
            else:
                streak = 1

            cur.execute(
                """
                UPDATE users
                SET
                    streak = %s,
                    last_daily_date = %s,
                    updated_at = NOW()
                WHERE user_id = %s
                """,
                (
                    streak,
                    activity_date,
                    user_id,
                ),
            )

            return streak


def get_streak(user_id: int) -> int:
    """Get current streak."""
    user = get_user(user_id)

    if not user:
        return 0

    return int(user["streak"] or 0)


def create_daily_task(
    user_id: int,
    task_date: Optional[date] = None,
) -> Dict[str, Any]:
    """Create or get daily task."""
    if task_date is None:
        task_date = date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_tasks (
                    user_id,
                    task_date
                )
                VALUES (%s, %s)
                ON CONFLICT (user_id, task_date)
                DO UPDATE SET user_id = EXCLUDED.user_id
                RETURNING *
                """,
                (
                    user_id,
                    task_date,
                ),
            )

            return cur.fetchone()


def get_daily_task(
    user_id: int,
    task_date: Optional[date] = None,
) -> Optional[Dict[str, Any]]:
    """Get daily task."""
    if task_date is None:
        task_date = date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM daily_tasks
                WHERE user_id = %s
                  AND task_date = %s
                """,
                (
                    user_id,
                    task_date,
                ),
            )

            return cur.fetchone()


def complete_daily_task(
    user_id: int,
    task_date: Optional[date] = None,
) -> bool:
    """Mark daily task as completed."""
    if task_date is None:
        task_date = date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE daily_tasks
                SET completed = TRUE
                WHERE user_id = %s
                  AND task_date = %s
                  AND completed = FALSE
                RETURNING id
                """,
                (
                    user_id,
                    task_date,
                ),
            )

            return cur.fetchone() is not None


def claim_daily_task_reward(
    user_id: int,
    task_date: Optional[date] = None,
) -> bool:
    """Claim daily task reward."""
    if task_date is None:
        task_date = date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE daily_tasks
                SET reward_claimed = TRUE
                WHERE user_id = %s
                  AND task_date = %s
                  AND completed = TRUE
                  AND reward_claimed = FALSE
                RETURNING id
                """,
                (
                    user_id,
                    task_date,
                ),
            )

            return cur.fetchone() is not None


def create_weekly_task(
    user_id: int,
    week_start: date,
) -> Dict[str, Any]:
    """Create or get weekly task."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO weekly_tasks (
                    user_id,
                    week_start
                )
                VALUES (%s, %s)
                ON CONFLICT (user_id, week_start)
                DO UPDATE SET user_id = EXCLUDED.user_id
                RETURNING *
                """,
                (
                    user_id,
                    week_start,
                ),
            )

            return cur.fetchone()


def get_weekly_task(
    user_id: int,
    week_start: date,
) -> Optional[Dict[str, Any]]:
    """Get weekly task."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM weekly_tasks
                WHERE user_id = %s
                  AND week_start = %s
                """,
                (
                    user_id,
                    week_start,
                ),
            )

            return cur.fetchone()


def complete_weekly_task(
    user_id: int,
    week_start: date,
) -> bool:
    """Mark weekly task as completed."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE weekly_tasks
                SET completed = TRUE
                WHERE user_id = %s
                  AND week_start = %s
                  AND completed = FALSE
                RETURNING id
                """,
                (
                    user_id,
                    week_start,
                ),
            )

            return cur.fetchone() is not None


def claim_weekly_task_reward(
    user_id: int,
    week_start: date,
) -> bool:
    """Claim weekly task reward."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE weekly_tasks
                SET reward_claimed = TRUE
                WHERE user_id = %s
                  AND week_start = %s
                  AND completed = TRUE
                  AND reward_claimed = FALSE
                RETURNING id
                """,
                (
                    user_id,
                    week_start,
                ),
            )

            return cur.fetchone() is not None
            def get_achievement(
    code: str,
) -> Optional[Dict[str, Any]]:
    """Get achievement by code."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM achievements
                WHERE code = %s
                """,
                (code,),
            )

            return cur.fetchone()


def get_all_achievements() -> List[Dict[str, Any]]:
    """Get all achievements."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM achievements
                ORDER BY id
                """
            )

            return cur.fetchall()


def has_achievement(
    user_id: int,
    code: str,
) -> bool:
    """Check whether user has achievement."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM user_achievements ua
                JOIN achievements a
                    ON a.id = ua.achievement_id
                WHERE ua.user_id = %s
                  AND a.code = %s
                """,
                (
                    user_id,
                    code,
                ),
            )

            return cur.fetchone() is not None


def award_achievement(
    user_id: int,
    code: str,
) -> bool:
    """
    Award achievement and its rewards.

    Returns True if achievement was awarded now.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM achievements
                WHERE code = %s
                """,
                (code,),
            )

            achievement = cur.fetchone()

            if achievement is None:
                return False

            cur.execute(
                """
                SELECT 1
                FROM user_achievements
                WHERE user_id = %s
                  AND achievement_id = %s
                """,
                (
                    user_id,
                    achievement["id"],
                ),
            )

            if cur.fetchone():
                return False

            cur.execute(
                """
                INSERT INTO user_achievements (
                    user_id,
                    achievement_id
                )
                VALUES (%s, %s)
                """,
                (
                    user_id,
                    achievement["id"],
                ),
            )

            xp_reward = achievement["xp_reward"] or 0
            score_reward = achievement["score_reward"] or 0

            if xp_reward:
                cur.execute(
                    """
                    UPDATE users
                    SET
                        xp = xp + %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (
                        xp_reward,
                        user_id,
                    ),
                )

                cur.execute(
                    """
                    INSERT INTO xp_transactions (
                        user_id,
                        amount,
                        type,
                        reason
                    )
                    VALUES (%s, %s, 'achievement', %s)
                    """,
                    (
                        user_id,
                        xp_reward,
                        achievement["title"],
                    ),
                )

            if score_reward:
                cur.execute(
                    """
                    UPDATE users
                    SET
                        score = score + %s,
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (
                        score_reward,
                        user_id,
                    ),
                )

            return True


def get_user_achievements(
    user_id: int,
) -> List[Dict[str, Any]]:
    """Get achievements earned by user."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    a.*,
                    ua.earned_at
                FROM user_achievements ua
                JOIN achievements a
                    ON a.id = ua.achievement_id
                WHERE ua.user_id = %s
                ORDER BY ua.earned_at DESC
                """,
                (user_id,),
            )

            return cur.fetchall()


def log_ai_usage(
    user_id: int,
    request_type: str,
    xp_spent: int = 0,
    is_premium: bool = False,
    success: bool = True,
) -> bool:
    """Save AI usage record."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_usage (
                    user_id,
                    request_type,
                    xp_spent,
                    is_premium,
                    success
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    request_type,
                    xp_spent,
                    is_premium,
                    success,
                ),
            )

            return True


def get_ai_usage_count(
    user_id: int,
    request_type: Optional[str] = None,
    since: Optional[datetime] = None,
) -> int:
    """Count AI requests."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT COUNT(*) AS cnt
                FROM ai_usage
                WHERE user_id = %s
            """

            params: List[Any] = [user_id]

            if request_type is not None:
                query += " AND request_type = %s"
                params.append(request_type)

            if since is not None:
                query += " AND created_at >= %s"
                params.append(since)

            cur.execute(query, params)

            return int(cur.fetchone()["cnt"])


def add_stars_purchase(
    user_id: int,
    stars_amount: int,
    product_type: str,
    product_value: Optional[int] = None,
    telegram_payment_charge_id: Optional[str] = None,
    provider_payment_charge_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Save Telegram Stars purchase."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stars_purchases (
                    user_id,
                    stars_amount,
                    product_type,
                    product_value,
                    telegram_payment_charge_id,
                    provider_payment_charge_id
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING *
                """,
                (
                    user_id,
                    stars_amount,
                    product_type,
                    product_value,
                    telegram_payment_charge_id,
                    provider_payment_charge_id,
                ),
            )

            return cur.fetchone()


def purchase_exists(
    telegram_payment_charge_id: Optional[str] = None,
    provider_payment_charge_id: Optional[str] = None,
) -> bool:
    """Check whether payment was already recorded."""
    if not telegram_payment_charge_id and not provider_payment_charge_id:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM stars_purchases
                WHERE
                    (
                        %s IS NOT NULL
                        AND telegram_payment_charge_id = %s
                    )
                    OR
                    (
                        %s IS NOT NULL
                        AND provider_payment_charge_id = %s
                    )
                LIMIT 1
                """,
                (
                    telegram_payment_charge_id,
                    telegram_payment_charge_id,
                    provider_payment_charge_id,
                    provider_payment_charge_id,
                ),
            )

            return cur.fetchone() is not None


def set_premium(
    user_id: int,
    days: int,
) -> Optional[datetime]:
    """Add premium days to user."""
    if days <= 0:
        return None

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET premium_until =
                    CASE
                        WHEN premium_until IS NULL
                             OR premium_until < NOW()
                        THEN NOW() + (%s * INTERVAL '1 day')
                        ELSE premium_until
                             + (%s * INTERVAL '1 day')
                    END,
                    updated_at = NOW()
                WHERE user_id = %s
                RETURNING premium_until
                """,
                (
                    days,
                    days,
                    user_id,
                ),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError("User does not exist")

            return row["premium_until"]


def is_premium(user_id: int) -> bool:
    """Check active premium."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    premium_until IS NOT NULL
                    AND premium_until > NOW() AS active
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )

            row = cur.fetchone()

            return bool(row and row["active"])


def get_premium_until(
    user_id: int,
) -> Optional[datetime]:
    """Get premium expiration date."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT premium_until
                FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )

            row = cur.fetchone()

            if not row:
                return None

            return row["premium_until"]


def check_subscription(
    user_id: int,
    is_subscribed: bool,
) -> bool:
    """Save subscription check result."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO subscription_checks (
                    user_id,
                    is_subscribed,
                    checked_at
                )
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    is_subscribed = EXCLUDED.is_subscribed,
                    checked_at = NOW()
                """,
                (
                    user_id,
                    is_subscribed,
                ),
            )

            return True


def get_subscription_status(
    user_id: int,
) -> Optional[Dict[str, Any]]:
    """Get last subscription check."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM subscription_checks
                WHERE user_id = %s
                """,
                (user_id,),
            )

            return cur.fetchone()


def save_daily_rank(
    rank_date: date,
    user_id: int,
    place: int,
    daily_score: int,
    reward_xp: int = 0,
) -> bool:
    """Save user's daily rank."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_rank_history (
                    rank_date,
                    user_id,
                    place,
                    daily_score,
                    reward_xp
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rank_date, user_id)
                DO UPDATE SET
                    place = EXCLUDED.place,
                    daily_score = EXCLUDED.daily_score,
                    reward_xp = EXCLUDED.reward_xp
                """,
                (
                    rank_date,
                    user_id,
                    place,
                    daily_score,
                    reward_xp,
                ),
            )

            return True
            def get_daily_rank_history(
    user_id: int,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Get daily rank history for a user."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM daily_rank_history
                WHERE user_id = %s
                ORDER BY rank_date DESC
                LIMIT %s
                """,
                (
                    user_id,
                    limit,
                ),
            )

            return cur.fetchall()


def get_daily_rank(
    rank_date: Optional[date] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get saved daily ranking."""
    if rank_date is None:
        rank_date = date.today()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    d.*,
                    u.username,
                    u.first_name,
                    u.last_name
                FROM daily_rank_history d
                JOIN users u
                    ON u.user_id = d.user_id
                WHERE d.rank_date = %s
                ORDER BY d.place ASC
                LIMIT %s
                """,
                (
                    rank_date,
                    limit,
                ),
            )

            return cur.fetchall()


def reward_daily_rank(
    rank_date: Optional[date] = None,
) -> int:
    """
    Save daily ranking and reward TOP-3.

    Returns number of rewarded users.
    """
    if rank_date is None:
        rank_date = date.today()

    rewarded = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    user_id,
                    daily_score
                FROM users
                WHERE is_blocked = FALSE
                  AND daily_score > 0
                ORDER BY daily_score DESC, score DESC
                """
            )

            users = cur.fetchall()

            reward_map = {
                1: get_setting_int("daily_rank_1", 100),
                2: get_setting_int("daily_rank_2", 70),
                3: get_setting_int("daily_rank_3", 50),
            }

            for place, user in enumerate(users, start=1):
                reward = reward_map.get(place, 0)

                cur.execute(
                    """
                    INSERT INTO daily_rank_history (
                        rank_date,
                        user_id,
                        place,
                        daily_score,
                        reward_xp
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (rank_date, user_id)
                    DO UPDATE SET
                        place = EXCLUDED.place,
                        daily_score = EXCLUDED.daily_score,
                        reward_xp = EXCLUDED.reward_xp
                    """,
                    (
                        rank_date,
                        user["user_id"],
                        place,
                        user["daily_score"],
                        reward,
                    ),
                )

                if reward > 0:
                    cur.execute(
                        """
                        SELECT reward_xp
                        FROM daily_rank_history
                        WHERE rank_date = %s
                          AND user_id = %s
                        """,
                        (
                            rank_date,
                            user["user_id"],
                        ),
                    )

                    saved = cur.fetchone()

                    if saved and saved["reward_xp"] == reward:
                        cur.execute(
                            """
                            SELECT COUNT(*) AS cnt
                            FROM xp_transactions
                            WHERE user_id = %s
                              AND type = 'daily_rank'
                              AND reason = %s
                            """,
                            (
                                user["user_id"],
                                f"Daily Rank {rank_date}",
                            ),
                        )

                        already = cur.fetchone()["cnt"]

                        if already == 0:
                            cur.execute(
                                """
                                UPDATE users
                                SET
                                    xp = xp + %s,
                                    updated_at = NOW()
                                WHERE user_id = %s
                                """,
                                (
                                    reward,
                                    user["user_id"],
                                ),
                            )

                            cur.execute(
                                """
                                INSERT INTO xp_transactions (
                                    user_id,
                                    amount,
                                    type,
                                    reason
                                )
                                VALUES (%s, %s, 'daily_rank', %s)
                                """,
                                (
                                    user["user_id"],
                                    reward,
                                    f"Daily Rank {rank_date}",
                                ),
                            )

                            rewarded += 1

            return rewarded


def cleanup_old_ai_usage(
    days: int = 90,
) -> int:
    """Delete old AI usage records."""
    if days < 1:
        days = 1

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM ai_usage
                WHERE created_at < NOW() - (%s * INTERVAL '1 day')
                """,
                (days,),
            )

            return cur.rowcount


def cleanup_old_rank_history(
    days: int = 365,
) -> int:
    """Delete old daily rank history."""
    if days < 1:
        days = 1

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM daily_rank_history
                WHERE rank_date < CURRENT_DATE - %s
                """,
                (days,),
            )

            return cur.rowcount


def log_admin_action(
    admin_id: int,
    action: str,
    target_id: Optional[int] = None,
    amount: Optional[int] = None,
    details: Optional[str] = None,
) -> bool:
    """Save admin action."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_logs (
                    admin_id,
                    action,
                    target_id,
                    amount,
                    details
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    admin_id,
                    action,
                    target_id,
                    amount,
                    details,
                ),
            )

            return True


def get_admin_logs(
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Get latest admin logs."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM admin_logs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

            return cur.fetchall()


def get_statistics() -> Dict[str, Any]:
    """Get general database statistics."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_users,
                    COUNT(*) FILTER (
                        WHERE is_blocked = FALSE
                    ) AS active_users,
                    COALESCE(SUM(xp), 0) AS total_xp,
                    COALESCE(SUM(score), 0) AS total_score,
                    COALESCE(SUM(solved_tasks), 0) AS solved_tasks
                FROM users
                """
            )

            users = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM referrals
                WHERE is_confirmed = TRUE
                """
            )

            referrals = cur.fetchone()["cnt"]

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM stars_purchases
                """
            )

            purchases = cur.fetchone()["cnt"]

            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM user_achievements
                """
            )

            achievements = cur.fetchone()["cnt"]

            return {
                "total_users": int(users["total_users"]),
                "active_users": int(users["active_users"]),
                "total_xp": int(users["total_xp"]),
                "total_score": int(users["total_score"]),
                "solved_tasks": int(users["solved_tasks"]),
                "confirmed_referrals": int(referrals),
                "purchases": int(purchases),
                "achievements": int(achievements),
            }


def delete_user(
    user_id: int,
) -> bool:
    """
    Delete user and dependent records.

    Because most tables use foreign keys without ON DELETE CASCADE,
    dependent rows are removed manually first.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM user_achievements
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM xp_transactions
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM stars_purchases
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM daily_tasks
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM weekly_tasks
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM daily_rank_history
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM ai_usage
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM subscription_checks
                WHERE user_id = %s
                """,
                (user_id,),
            )

            cur.execute(
                """
                DELETE FROM referrals
                WHERE referred_id = %s
                   OR referrer_id = %s
                """,
                (
                    user_id,
                    user_id,
                ),
            )

            cur.execute(
                """
                DELETE FROM users
                WHERE user_id = %s
                """,
                (user_id,),
            )

            return cur.rowcount > 0


def health_check() -> bool:
    """Check database connection."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS ok")
                row = cur.fetchone()
                return bool(row and row["ok"] == 1)
    except Exception:
        return False


def vacuum_analyze():
    """
    Run VACUUM ANALYZE.

    PostgreSQL does not allow VACUUM inside a transaction,
    so this function uses a separate autocommit connection.
    """
    conn = None

    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=RealDictCursor,
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            cur.execute("VACUUM ANALYZE")

    finally:
        if conn:
            conn.close()


__all__ = [
    "get_db_connection",
    "init_db",

    "create_user",
    "get_user",
    "user_exists",
    "is_user_blocked",
    "set_user_blocked",
    "update_user_profile",

    "get_setting",
    "get_setting_int",
    "set_setting",

    "add_xp",
    "calculate_level",
    "get_xp_history",

    "add_score",
    "add_daily_score",
    "increment_solved_tasks",

    "reset_daily_scores",
    "get_top_users",
    "get_daily_top_users",

    "create_referral",
    "get_referral",
    "get_referrer",
    "confirm_referral",
    "get_referral_count",
    "get_referrals",
    "get_referral_leaderboard",

    "update_streak",
    "get_streak",

    "create_daily_task",
    "get_daily_task",
    "complete_daily_task",
    "claim_daily_task_reward",

    "create_weekly_task",
    "get_weekly_task",
    "complete_weekly_task",
    "claim_weekly_task_reward",

    "get_achievement",
    "get_all_achievements",
    "has_achievement",
    "award_achievement",
    "get_user_achievements",

    "log_ai_usage",
    "get_ai_usage_count",

    "add_stars_purchase",
    "purchase_exists",

    "set_premium",
    "is_premium",
    "get_premium_until",

    "check_subscription",
    "get_subscription_status",

    "save_daily_rank",
    "get_daily_rank_history",
    "get_daily_rank",
    "reward_daily_rank",

    "cleanup_old_ai_usage",
    "cleanup_old_rank_history",

    "log_admin_action",
    "get_admin_logs",

    "get_statistics",
    "delete_user",

    "health_check",
    "vacuum_analyze",
                ]
