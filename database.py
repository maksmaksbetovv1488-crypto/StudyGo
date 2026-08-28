import os
from contextlib import contextmanager
from datetime import datetime, timedelta, date

import psycopg2


DATABASE_URL = os.getenv("DATABASE_URL")


@contextmanager
def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не найден в Environment Variables")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    xp INTEGER NOT NULL DEFAULT 0,
                    score INTEGER NOT NULL DEFAULT 0,
                    daily_score INTEGER NOT NULL DEFAULT 0,
                    level INTEGER NOT NULL DEFAULT 1,
                    premium_until TIMESTAMP,
                    streak INTEGER NOT NULL DEFAULT 0,
                    last_daily_date DATE,
                    tasks_completed INTEGER NOT NULL DEFAULT 0,
                    ai_requests INTEGER NOT NULL DEFAULT 0,
                    photo_requests INTEGER NOT NULL DEFAULT 0,
                    referral_count INTEGER NOT NULL DEFAULT 0,
                    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referrer_id BIGINT NOT NULL,
                    referred_id BIGINT PRIMARY KEY,
                    subscription_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    reward_given BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    verified_at TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS xp_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    amount INTEGER NOT NULL,
                    transaction_type TEXT NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS stars_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    stars INTEGER NOT NULL,
                    product_type TEXT NOT NULL,
                    product_id TEXT,
                    telegram_payment_id TEXT UNIQUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS premium_purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    stars INTEGER NOT NULL,
                    days INTEGER NOT NULL,
                    payment_id TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_tasks (
                    id SERIAL PRIMARY KEY,
                    task_key TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    xp_reward INTEGER NOT NULL DEFAULT 0,
                    score_reward INTEGER NOT NULL DEFAULT 0,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_daily_tasks (
                    user_id BIGINT NOT NULL,
                    task_id INTEGER NOT NULL,
                    task_date DATE NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    PRIMARY KEY (user_id, task_id, task_date)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS weekly_tasks (
                    id SERIAL PRIMARY KEY,
                    task_key TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    xp_reward INTEGER NOT NULL DEFAULT 0,
                    score_reward INTEGER NOT NULL DEFAULT 0,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_weekly_tasks (
                    user_id BIGINT NOT NULL,
                    task_id INTEGER NOT NULL,
                    week_start DATE NOT NULL,
                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                    completed_at TIMESTAMP,
                    PRIMARY KEY (user_id, task_id, week_start)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS daily_rank_history (
                    id SERIAL PRIMARY KEY,
                    rank_date DATE NOT NULL,
                    user_id BIGINT NOT NULL,
                    daily_score INTEGER NOT NULL,
                    rank_position INTEGER NOT NULL,
                    xp_reward INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (rank_date, user_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS channel_subscriptions (
                    user_id BIGINT PRIMARY KEY,
                    subscribed BOOLEAN NOT NULL DEFAULT FALSE,
                    checked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT NOT NULL,
                    action TEXT NOT NULL,
                    target_id BIGINT,
                    amount INTEGER,
                    details TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_usage (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    request_type TEXT NOT NULL,
                    xp_cost INTEGER NOT NULL DEFAULT 0,
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS economy_settings (
                    setting_key TEXT PRIMARY KEY,
                    setting_value TEXT NOT NULL
                );
            """)def is_premium(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT premium_until
                FROM users
                WHERE user_id = %s;
            """, (user_id,))

            result = cur.fetchone()

            return bool(
                result
                and result[0]
                and result[0] > datetime.now()
            )


def add_premium(user_id, days):
    if days <= 0:
        return None

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT premium_until
                FROM users
                WHERE user_id = %s;
            """, (user_id,))

            result = cur.fetchone()

            now = datetime.now()

            if result and result[0] and result[0] > now:
                start = result[0]
            else:
                start = now

            expires = start + timedelta(days=days)

            cur.execute("""
                UPDATE users
                SET premium_until = %s
                WHERE user_id = %s;
            """, (expires, user_id))

            return expires


def save_premium_purchase(
    user_id,
    stars,
    days,
    payment_id,
    expires_at
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO premium_purchases
                (
                    user_id,
                    stars,
                    days,
                    payment_id,
                    expires_at
                )
                VALUES (%s, %s, %s, %s, %s);
            """, (
                user_id,
                stars,
                days,
                payment_id,
                expires_at
            ))


def save_stars_transaction(
    user_id,
    stars,
    product_type,
    product_id=None,
    payment_id=None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO stars_transactions
                (
                    user_id,
                    stars,
                    product_type,
                    product_id,
                    telegram_payment_id
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (telegram_payment_id)
                DO NOTHING;
            """, (
                user_id,
                stars,
                product_type,
                product_id,
                payment_id
            ))


def create_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO referrals
                (
                    referrer_id,
                    referred_id
                )
                VALUES (%s, %s)
                ON CONFLICT (referred_id)
                DO NOTHING
                RETURNING referred_id;
            """, (
                referrer_id,
                referred_id
            ))

            return bool(cur.fetchone())


def verify_referral(referred_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE referrals
                SET subscription_verified = TRUE,
                    verified_at = CURRENT_TIMESTAMP
                WHERE referred_id = %s
                  AND subscription_verified = FALSE
                RETURNING referrer_id;
            """, (referred_id,))

            result = cur.fetchone()

            return result[0] if result else None


def reward_referral(
    referrer_id,
    referred_id,
    referrer_reward=100,
    referred_reward=20
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT reward_given,
                       subscription_verified
                FROM referrals
                WHERE referred_id = %s
                  AND referrer_id = %s;
            """, (
                referred_id,
                referrer_id
            ))

            result = cur.fetchone()

            if not result:
                return False

            reward_given, verified = result

            if reward_given or not verified:
                return False

            cur.execute("""
                UPDATE users
                SET xp = xp + %s,
                    referral_count = referral_count + 1
                WHERE user_id = %s;
            """, (
                referrer_reward,
                referrer_id
            ))

            if cur.rowcount == 0:
                return False

            cur.execute("""
                UPDATE users
                SET xp = xp + %s
                WHERE user_id = %s;
            """, (
                referred_reward,
                referred_id
            ))

            if cur.rowcount == 0:
                return False

            cur.execute("""
                INSERT INTO xp_transactions
                (
                    user_id,
                    amount,
                    transaction_type,
                    reason
                )
                VALUES
                (%s, %s, 'referral', 'Успешный реферал'),
                (%s, %s, 'referral_bonus',
                 'Бонус новому пользователю');
            """, (
                referrer_id,
                referrer_reward,
                referred_id,
                referred_reward
            ))

            cur.execute("""
                UPDATE referrals
                SET reward_given = TRUE
                WHERE referred_id = %s;
            """, (referred_id,))

            return True


def save_subscription_status(user_id, subscribed):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO channel_subscriptions
                (
                    user_id,
                    subscribed
                )
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    subscribed = EXCLUDED.subscribed,
                    checked_at = CURRENT_TIMESTAMP;
            """, (
                user_id,
                subscribed
            ))


def is_channel_subscribed(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT subscribed
                FROM channel_subscriptions
                WHERE user_id = %s;
            """, (user_id,))

            result = cur.fetchone()

            return bool(result and result[0])            settings = {
                "xp_per_star": 10,

                "ai_simple": 10,
                "ai_normal": 20,
                "ai_explanation": 20,
                "ai_photo": 30,
                "ai_test": 30,
                "ai_complex": 40,
                "ai_very_complex": 50,

                "premium_1_day_stars": 50,
                "premium_7_days_stars": 200,
                "premium_30_days_stars": 750,

                "referrer_reward": 100,
                "referred_reward": 20,

                "daily_task_reward": 30,
                "weekly_task_reward": 200,

                "daily_rank_1": 100,
                "daily_rank_2": 70,
                "daily_rank_3": 50
            }

            for key, value in settings.items():
                cur.execute("""
                    INSERT INTO economy_settings
                    (setting_key, setting_value)
                    VALUES (%s, %s)
                    ON CONFLICT (setting_key) DO NOTHING;
                """, (key, str(value)))


def get_or_create_user(user_id, username=None, first_name=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE user_id = %s;",
                (user_id,)
            )
            user = cur.fetchone()

            if user:
                cur.execute("""
                    UPDATE users
                    SET username = %s,
                        first_name = %s,
                        last_active = CURRENT_TIMESTAMP
                    WHERE user_id = %s;
                """, (username, first_name, user_id))

                cur.execute(
                    "SELECT * FROM users WHERE user_id = %s;",
                    (user_id,)
                )
                return cur.fetchone()

            cur.execute("""
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                RETURNING *;
            """, (user_id, username, first_name))

            return cur.fetchone()


def get_user(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE user_id = %s;",
                (user_id,)
            )
            return cur.fetchone()


def get_xp(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT xp FROM users WHERE user_id = %s;",
                (user_id,)
            )
            result = cur.fetchone()
            return result[0] if result else 0


def add_xp(user_id, amount, transaction_type="reward", reason=None):
    if amount <= 0:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET xp = xp + %s
                WHERE user_id = %s;
            """, (amount, user_id))

            if cur.rowcount == 0:
                return False

            cur.execute("""
                INSERT INTO xp_transactions
                (user_id, amount, transaction_type, reason)
                VALUES (%s, %s, %s, %s);
            """, (
                user_id,
                amount,
                transaction_type,
                reason
            ))

            return True


def spend_xp(user_id, amount, reason=None):
    if amount <= 0:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET xp = xp - %s
                WHERE user_id = %s
                  AND xp >= %s
                RETURNING xp;
            """, (amount, user_id, amount))

            if not cur.fetchone():
                return False

            cur.execute("""
                INSERT INTO xp_transactions
                (user_id, amount, transaction_type, reason)
                VALUES (%s, %s, 'spend', %s);
            """, (
                user_id,
                -amount,
                reason
            ))

            return True


def add_score(user_id, amount, daily=True):
    if amount <= 0:
        return False

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if daily:
                cur.execute("""
                    UPDATE users
                    SET score = score + %s,
                        daily_score = daily_score + %s
                    WHERE user_id = %s;
                """, (amount, amount, user_id))
            else:
                cur.execute("""
                    UPDATE users
                    SET score = score + %s
                    WHERE user_id = %s;
                """, (amount, user_id))

            if cur.rowcount == 0:
                return False

            _update_level(user_id, cur)
            return True


def _update_level(user_id, cur):
    cur.execute(
        "SELECT score FROM users WHERE user_id = %s;",
        (user_id,)
    )

    result = cur.fetchone()

    if not result:
        return

    score = result[0]

    if score >= 100000:
        level = 50
    elif score >= 20000:
        level = 20
    elif score >= 5000:
        level = 10
    elif score >= 1000:
        level = 5
    elif score >= 600:
        level = 4
    elif score >= 300:
        level = 3
    elif score >= 100:
        level = 2
    else:
        level = 1

    cur.execute("""
        UPDATE users
        SET level = %s
        WHERE user_id = %s;
    """, (level, user_id))def get_daily_rank(limit=30):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    user_id,
                    username,
                    first_name,
                    daily_score
                FROM users
                WHERE is_blocked = FALSE
                ORDER BY daily_score DESC,
                         user_id ASC
                LIMIT %s;
            """, (limit,))

            return cur.fetchall()


def get_user_daily_rank(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT daily_score
                FROM users
                WHERE user_id = %s;
            """, (user_id,))

            result = cur.fetchone()

            if not result:
                return None

            cur.execute("""
                SELECT COUNT(*) + 1
                FROM users
                WHERE is_blocked = FALSE
                  AND daily_score > %s;
            """, (result[0],))

            return cur.fetchone()[0]


def save_daily_rank(rank_date=None):
    rank_date = rank_date or date.today()

    rewards = {
        1: get_setting_int(
            "daily_rank_1",
            100
        ),
        2: get_setting_int(
            "daily_rank_2",
            70
        ),
        3: get_setting_int(
            "daily_rank_3",
            50
        )
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    user_id,
                    daily_score
                FROM users
                WHERE is_blocked = FALSE
                  AND daily_score > 0
                ORDER BY daily_score DESC,
                         user_id ASC
                LIMIT 30;
            """)

            rows = cur.fetchall()

            for position, (user_id, daily_score) in enumerate(
                rows,
                1
            ):
                reward = rewards.get(position, 0)

                cur.execute("""
                    INSERT INTO daily_rank_history
                    (
                        rank_date,
                        user_id,
                        daily_score,
                        rank_position,
                        xp_reward
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (rank_date, user_id)
                    DO NOTHING;
                """, (
                    rank_date,
                    user_id,
                    daily_score,
                    position,
                    reward
                ))

                if cur.rowcount == 1 and reward > 0:
                    cur.execute("""
                        UPDATE users
                        SET xp = xp + %s
                        WHERE user_id = %s;
                    """, (
                        reward,
                        user_id
                    ))

                    cur.execute("""
                        INSERT INTO xp_transactions
                        (
                            user_id,
                            amount,
                            transaction_type,
                            reason
                        )
                        VALUES (%s, %s, 'daily_rank', %s);
                    """, (
                        user_id,
                        reward,
                        f"Ежедневный рейтинг #{position}"
                    ))

            cur.execute("""
                UPDATE users
                SET daily_score = 0;
            """)


def log_ai_usage(
    user_id,
    request_type,
    xp_cost=0,
    success=True
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ai_usage
                (
                    user_id,
                    request_type,
                    xp_cost,
                    success
                )
                VALUES (%s, %s, %s, %s);
            """, (
                user_id,
                request_type,
                xp_cost,
                success
            ))

            if success:
                cur.execute("""
                    UPDATE users
                    SET ai_requests = ai_requests + 1
                    WHERE user_id = %s;
                """, (user_id,))


def add_admin_log(
    admin_id,
    action,
    target_id=None,
    amount=None,
    details=None
):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO admin_logs
                (
                    admin_id,
                    action,
                    target_id,
                    amount,
                    details
                )
                VALUES (%s, %s, %s, %s, %s);
            """, (
                admin_id,
                action,
                target_id,
                amount,
                details
            ))


def set_blocked(user_id, blocked):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET is_blocked = %s
                WHERE user_id = %s;
            """, (
                blocked,
                user_id
            ))


def is_blocked(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT is_blocked
                FROM users
                WHERE user_id = %s;
            """, (user_id,))

            result = cur.fetchone()

            return bool(result and result[0])


def get_setting(key, default=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT setting_value
                FROM economy_settings
                WHERE setting_key = %s;
            """, (key,))

            result = cur.fetchone()

            return result[0] if result else default


def get_setting_int(key, default=0):
    value = get_setting(key)

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def set_setting(key, value):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO economy_settings
                (
                    setting_key,
                    setting_value
                )
                VALUES (%s, %s)
                ON CONFLICT (setting_key)
                DO UPDATE SET
                    setting_value = EXCLUDED.setting_value;
            """, (
                key,
                str(value)
            ))def xp_from_stars(stars):
    if stars < 0:
        return 0

    return stars * get_setting_int(
        "xp_per_star",
        10
    )


def increment_task_count(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET tasks_completed = tasks_completed + 1
                WHERE user_id = %s;
            """, (user_id,))


def increment_photo_count(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET photo_requests = photo_requests + 1
                WHERE user_id = %s;
            """, (user_id,))


def get_total_users():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM users;
            """)

            return cur.fetchone()[0]


def get_total_premium_users():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM users
                WHERE premium_until > CURRENT_TIMESTAMP;
            """)

            return cur.fetchone()[0]


def get_total_xp():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(xp), 0)
                FROM users;
            """)

            return cur.fetchone()[0]


def get_referral_count(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT referral_count
                FROM users
                WHERE user_id = %s;
            """, (user_id,))

            result = cur.fetchone()

            return result[0] if result else 0


if __name__ == "__main__":
    print("Initializing StudyGo database...")

    init_db()

    print("StudyGo database initialized successfully.")
