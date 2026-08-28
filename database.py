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
                    streak          INTEGER NOT NULL DEFAULT 0,
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
        ("first_task", "Первое задание", "Решил первое задание", 20, 10, "🟢"),
        ("streak_7", "7 дней активности", "Активность 7 дней подряд", 100, 50, "🔥"),
        ("solved_100", "100 решённых заданий", "Решил 100 заданий", 200, 100, "📚"),
        ("referrals_10", "10 успешных рефералов", "Пригласил 10 друзей", 150, 80, "👥"),
        ("referrals_50", "50 успешных рефералов", "Пригласил 50 друзей", 500, 250, "🚀"),
        ("top10", "TOP-10", "Попал в TOP-10 Daily Rank", 100, 50, "🏆"),
        ("first_premium", "Первая покупка Premium", "Купил Premium впервые", 50, 30, "💎"),
    ]
    for code, title, desc, xp, score, icon in defaults:
        cur.execute(
            """
            INSERT INTO achievements (code, title, description, xp_reward, score_reward, icon)
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


def get_setting(key: str, default: str = "0") -> str:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM economy_settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row["value"] if row else default


def get_setting_int(key: str, default: int = 0) -> int:
    try:
        return int(get_setting(key, str(default)))
    except ValueError:
        return default


def set_setting(key: str, value: str, admin_id: Optional[int] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO economy_settings (key, value, updated_at, updated_by)
                VALUES (%s, %s, NOW(), %s)
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value,
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                """,
                (key, value, admin_id),
            )


def ensure_user(
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Create user if not exists, otherwise update username/name and return user."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                cur.execute(
                    """
                    UPDATE users
                    SET username = COALESCE(%s, username),
                        first_name = COALESCE(%s, first_name),
                        last_name = COALESCE(%s, last_name),
                        updated_at = NOW()
                    WHERE user_id = %s
                    RETURNING *
                    """,
                    (username, first_name, last_name, user_id),
                )
                return dict(cur.fetchone())
            cur.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, username, first_name, last_name),
            )
            return dict(cur.fetchone())


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def is_blocked(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user.get("is_blocked"))


def set_blocked(user_id: int, blocked: bool, admin_id: Optional[int] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_blocked = %s, updated_at = NOW() WHERE user_id = %s",
                (blocked, user_id),
            )
            if admin_id is not None:
                action = "BAN" if blocked else "UNBAN"
                cur.execute(
                    """
                    INSERT INTO admin_logs (admin_id, action, target_id)
                    VALUES (%s, %s, %s)
                    """,
                    (admin_id, action, user_id),
                )


def is_premium(user_id: int) -> bool:
    user = get_user(user_id)
    if not user or not user.get("premium_until"):
        return False
    return user["premium_until"] > datetime.now(user["premium_until"].tzinfo)


def add_premium_days(user_id: int, days: int, admin_id: Optional[int] = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT premium_until FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            now = datetime.utcnow()
            current = row["premium_until"] if row and row["premium_until"] else None
            if current and current.replace(tzinfo=None) > now:
                new_until = current.replace(tzinfo=None) + timedelta(days=days)
            else:
                new_until = now + timedelta(days=days)
            cur.execute(
                """
                UPDATE users
                SET premium_until = %s, updated_at = NOW()
                WHERE user_id = %s
                """,
                (new_until, user_id),
            )
            if admin_id is not None:
                cur.execute(
                    """
                    INSERT INTO admin_logs (admin_id, action, target_id, amount, details)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (admin_id, "PREMIUM", user_id, days, f"+{days} days"),
                )


def change_xp(
    user_id: int,
    amount: int,
    tx_type: str,
    reason: Optional[str] = None,
    admin_id: Optional[int] = None,
) -> int:
    """
    Change XP by amount (can be negative).
    Returns new XP balance.
    Raises ValueError if insufficient XP on spend.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT xp FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("User not found")
            new_xp = row["xp"] + amount
            if new_xp < 0:
                raise ValueError("Insufficient XP")
            cur.execute(
                "UPDATE users SET xp = %s, updated_at = NOW() WHERE user_id = %s",
                (new_xp, user_id),
            )
            cur.execute(
                """
                INSERT INTO xp_transactions (user_id, amount, type, reason)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, amount, tx_type, reason),
            )
            if admin_id is not None:
                cur.execute(
                    """
                    INSERT INTO admin_logs (admin_id, action, target_id, amount, details)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (admin_id, "XP", user_id, amount, reason or tx_type),
                )
            return new_xp


def get_xp(user_id: int) -> int:
    user = get_user(user_id)
    return user["xp"] if user else 0


LEVEL_THRESHOLDS = [
    (1, 0),
    (2, 100),
    (3, 300),
    (4, 600),
    (5, 1000),
    (10, 5000),
    (20, 20000),
    (50, 100000),
]


def _calc_level(score: int) -> int:
    level = 1
    for lvl, threshold in LEVEL_THRESHOLDS:
        if score >= threshold:
            level = lvl
        else:
            break
    for i in range(len(LEVEL_THRESHOLDS) - 1):
        l1, t1 = LEVEL_THRESHOLDS[i]
        l2, t2 = LEVEL_THRESHOLDS[i + 1]
        if t1 <= score < t2:
            progress = (score - t1) / (t2 - t1)
            level = l1 + int(progress * (l2 - l1))
            break
    else:
        if score >= LEVEL_THRESHOLDS[-1][1]:
            level = LEVEL_THRESHOLDS[-1][0]
    return max(1, level)


def add_score(user_id: int, amount: int) -> Tuple[int, int]:
    """Add permanent Score, recalculate level. Returns (new_score, new_level)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT score FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("User not found")
            new_score = row["score"] + amount
            new_level = _calc_level(new_score)
            cur.execute(
                """
                UPDATE users
                SET score = %s, level = %s, updated_at = NOW()
                WHERE user_id = %s
                """,
                (new_score, new_level, user_id),
            )
            return new_score, new_level


def add_daily_score(user_id: int, amount: int) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET daily_score = daily_score + %s, updated_at = NOW()
                WHERE user_id = %s
                RETURNING daily_score
                """,
                (amount, user_id),
            )
            row = cur.fetchone()
            return row["daily_score"] if row else 0


def reset_all_daily_scores():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET daily_score = 0")


def get_level_progress(user_id: int) -> Dict[str, Any]:
    user = get_user(user_id)
    if not user:
        return {}
    score = user["score"]
    level = user["level"]
    next_threshold = None
    for lvl, thr in LEVEL_THRESHOLDS:
        if thr > score:
            next_threshold = thr
            break
    if next_threshold is None:
        next_threshold = score
    return {
        "level": level,
        "score": score,
        "next_threshold": next_threshold,
        "progress": min(100, int(score / next_threshold * 100)) if next_threshold else 100,
      }def create_referral(referrer_id: int, referred_id: int) -> bool:
    """Create pending referral. Returns False if already exists or self-ref."""
    if referrer_id == referred_id:
        return False
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM referrals WHERE referred_id = %s",
                (referred_id,),
            )
            if cur.fetchone():
                return False
            cur.execute(
                """
                INSERT INTO referrals (referred_id, referrer_id, is_confirmed)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (referred_id) DO NOTHING
                """,
                (referred_id, referrer_id),
            )
            return cur.rowcount > 0


def confirm_referral(referred_id: int) -> Optional[int]:
    """
    Confirm referral after channel subscription check.
    Awards XP to both parties.
    Returns referrer_id if confirmed, else None.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT referrer_id, is_confirmed
                FROM referrals
                WHERE referred_id = %s
                FOR UPDATE
                """,
                (referred_id,),
            )
            row = cur.fetchone()
            if not row or row["is_confirmed"]:
                return None
            referrer_id = row["referrer_id"]
            cur.execute(
                """
                UPDATE referrals
                SET is_confirmed = TRUE, confirmed_at = NOW()
                WHERE referred_id = %s
                """,
                (referred_id,),
            )
    referrer_xp = get_setting_int("referral_referrer_xp", 100)
    referred_xp = get_setting_int("referral_referred_xp", 20)
    change_xp(referrer_id, referrer_xp, "referral", f"Referral of {referred_id}")
    change_xp(referred_id, referred_xp, "referral", f"Joined via {referrer_id}")
    return referrer_id


def get_referral_count(user_id: int, confirmed_only: bool = True) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if confirmed_only:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM referrals WHERE referrer_id = %s AND is_confirmed = TRUE",
                    (user_id,),
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM referrals WHERE referrer_id = %s",
                    (user_id,),
                )
            return cur.fetchone()["cnt"]


def get_pending_referral(referred_id: int) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM referrals WHERE referred_id = %s AND is_confirmed = FALSE",
                (referred_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def mark_daily_completed(user_id: int, task_date: Optional[date] = None) -> bool:
    task_date = task_date or date.today()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO daily_tasks (user_id, task_date, completed)
                VALUES (%s, %s, TRUE)
                ON CONFLICT (user_id, task_date) DO UPDATE
                SET completed = TRUE
                RETURNING id
                """,
                (user_id, task_date),
            )
            return cur.rowcount > 0


def claim_daily_reward(user_id: int) -> Optional[int]:
    """Claim daily reward + streak bonuses. Returns XP awarded or None."""
    today = date.today()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT completed, reward_claimed
                FROM daily_tasks
                WHERE user_id = %s AND task_date = %s
                FOR UPDATE
                """,
                (user_id, today),
            )
            row = cur.fetchone()
            if not row or not row["completed"] or row["reward_claimed"]:
                return None
            cur.execute(
                """
                UPDATE daily_tasks SET reward_claimed = TRUE
                WHERE user_id = %s AND task_date = %s
                """,
                (user_id, today),
            )
            cur.execute(
                "SELECT streak, last_daily_date FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            u = cur.fetchone()
            last = u["last_daily_date"]
            streak = u["streak"] or 0
            if last == today - timedelta(days=1):
                streak += 1
            elif last != today:
                streak = 1
            cur.execute(
                """
                UPDATE users
                SET streak = %s, last_daily_date = %s, updated_at = NOW()
                WHERE user_id = %s
                """,
                (streak, today, user_id),
            )

    base = get_setting_int("daily_task_reward", 30)
    bonus = 0
    if streak >= 30:
        bonus = get_setting_int("daily_streak_30", 500)
    elif streak >= 7:
        bonus = get_setting_int("daily_streak_7", 100)
    elif streak >= 3:
        bonus = get_setting_int("daily_streak_3", 50)

    total = base + bonus
    change_xp(user_id, total, "daily_task", f"Daily + streak {streak}")
    add_score(user_id, get_setting_int("score_daily_task", 30))
    add_daily_score(user_id, get_setting_int("ds_daily_task", 20))
    return total


def get_streak(user_id: int) -> int:
    user = get_user(user_id)
    return user["streak"] if user else 0


def get_daily_rank(limit: int = 30) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, username, first_name, daily_score, level
                FROM users
                WHERE daily_score > 0 AND is_blocked = FALSE
                ORDER BY daily_score DESC, score DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_user_daily_place(user_id: int) -> Optional[int]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) + 1 AS place
                FROM users
                WHERE daily_score > (SELECT daily_score FROM users WHERE user_id = %s)
                  AND is_blocked = FALSE
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return row["place"] if row else None


def close_daily_rank_and_reward():
    """
    Called at 23:59: award top-3, save history, then reset daily scores.
    """
    top = get_daily_rank(limit=3)
    rewards = [
        get_setting_int("daily_rank_1", 100),
        get_setting_int("daily_rank_2", 70),
        get_setting_int("daily_rank_3", 50),
    ]
    today = date.today()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for i, user in enumerate(top):
                place = i + 1
                reward = rewards[i] if i < len(rewards) else 0
                cur.execute(
                    """
                    INSERT INTO daily_rank_history
                        (rank_date, user_id, place, daily_score, reward_xp)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (rank_date, user_id) DO NOTHING
                    """,
                    (today, user["user_id"], place, user["daily_score"], reward),
                )
                if reward > 0:
                    change_xp(
                        user["user_id"],
                        reward,
                        "daily_rank",
                        f"Daily Rank #{place}",
                    )
    full_top = get_daily_rank(limit=30)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for i, user in enumerate(full_top):
                place = i + 1
                if place <= 3:
                    continue
                cur.execute(
                    """
                    INSERT INTO daily_rank_history
                        (rank_date, user_id, place, daily_score, reward_xp)
                    VALUES (%s, %s, %s, %s, 0)
                    ON CONFLICT (rank_date, user_id) DO NOTHING
                    """,
                    (today, user["user_id"], place, user["daily_score"]),
                )
    reset_all_daily_scores()


def get_rank_history(user_id: int, limit: int = 14) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rank_date, place, daily_score, reward_xp
                FROM daily_rank_history
                WHERE user_id = %s
                ORDER BY rank_date DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]


def grant_achievement(user_id: int, code: str) -> bool:
    """Grant achievement if not already earned. Returns True if newly granted."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, xp_reward, score_reward FROM achievements WHERE code = %s", (code,))
            ach = cur.fetchone()
            if not ach:
                return False
            cur.execute(
                """
                INSERT INTO user_achievements (user_id, achievement_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                RETURNING user_id
                """,
                (user_id, ach["id"]),
            )
            if cur.rowcount == 0:
                return False
    if ach["xp_reward"]:
        change_xp(user_id, ach["xp_reward"], "achievement", code)
    if ach["score_reward"]:
        add_score(user_id, ach["score_reward"])
    return True


def get_user_achievements(user_id: int) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.code, a.title, a.description, a.icon, ua.earned_at
                FROM user_achievements ua
                JOIN achievements a ON a.id = ua.achievement_id
                WHERE ua.user_id = %s
                ORDER BY ua.earned_at
                """,
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]


def record_stars_purchase(
    user_id: int,
    stars_amount: int,
    product_type: str,
    product_value: Optional[int] = None,
    telegram_payment_charge_id: Optional[str] = None,
    provider_payment_charge_id: Optional[str] = None,
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO stars_purchases
                    (user_id, stars_amount, product_type, product_value,
                     telegram_payment_charge_id, provider_payment_charge_id)
                VALUES (%s, %s, %s, %s, %s, %s)
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


def get_stars_stats(period: str = "all") -> Dict[str, Any]:
    """period: today / week / month / all"""
    intervals = {
        "today": "created_at >= CURRENT_DATE",
        "week": "created_at >= CURRENT_DATE - INTERVAL '7 days'",
        "month": "created_at >= CURRENT_DATE - INTERVAL '30 days'",
        "all": "TRUE",
    }
    cond = intervals.get(period, "TRUE")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    COALESCE(SUM(stars_amount), 0) AS total_stars,
                    COUNT(*) FILTER (WHERE product_type = 'xp') AS xp_purchases,
                    COUNT(*) FILTER (WHERE product_type = 'premium') AS premium_purchases
                FROM stars_purchases
                WHERE {cond}
                """
            )
            return dict(cur.fetchone())


def log_ai_usage(
    user_id: int,
    request_type: str,
    xp_spent: int = 0,
    is_premium: bool = False,
    success: bool = True,
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_usage (user_id, request_type, xp_spent, is_premium, success)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, request_type, xp_spent, is_premium, success),
            )
            if success:
                cur.execute(
                    """
                    UPDATE users
                    SET solved_tasks = solved_tasks + 1, updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )


def get_ai_stats(period: str = "today") -> Dict[str, Any]:
    intervals = {
        "today": "created_at >= CURRENT_DATE",
        "week": "created_at >= CURRENT_DATE - INTERVAL '7 days'",
        "month": "created_at >= CURRENT_DATE - INTERVAL '30 days'",
        "all": "TRUE",
    }
    cond = intervals.get(period, "TRUE")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE request_type = 'photo') AS photo,
                    COUNT(*) FILTER (WHERE is_premium) AS premium_requests,
                    COALESCE(SUM(xp_spent), 0) AS xp_spent
                FROM ai_usage
                WHERE {cond} AND success = TRUE
                """
            )
            return dict(cur.fetchone())


def get_users_stats() -> Dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) AS new_today,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_week,
                    COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE) AS active_today,
                    COUNT(*) FILTER (WHERE updated_at >= CURRENT_DATE - INTERVAL '7 days') AS active_week,
                    COUNT(*) FILTER (WHERE premium_until > NOW()) AS premium,
                    COUNT(*) FILTER (WHERE is_blocked) AS blocked
                FROM users
                """
            )
            return dict(cur.fetchone())


def get_referral_stats() -> Dict[str, Any]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE is_confirmed) AS confirmed,
                    COUNT(*) FILTER (WHERE confirmed_at >= CURRENT_DATE) AS today
                FROM referrals
                """
            )
            return dict(cur.fetchone())


def search_user(query: str) -> Optional[Dict[str, Any]]:
    """Search by user_id or username."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if query.isdigit():
                cur.execute("SELECT * FROM users WHERE user_id = %s", (int(query),))
            else:
                cur.execute(
                    "SELECT * FROM users WHERE username ILIKE %s LIMIT 1",
                    (query.lstrip("@"),),
                )
            row = cur.fetchone()
            return dict(row) if row else None


def get_top_referrers(limit: int = 10) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.referrer_id, u.username, u.first_name, COUNT(*) AS cnt
                FROM referrals r
                JOIN users u ON u.user_id = r.referrer_id
                WHERE r.is_confirmed = TRUE
                GROUP BY r.referrer_id, u.username, u.first_name
                ORDER BY cnt DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_admin_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM admin_logs
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_all_user_ids() -> List[int]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE is_blocked = FALSE")
            return [r["user_id"] for r in cur.fetchall()]
