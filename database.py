"""
StudyGo — Database (тарифы, лимиты, без XP)
"""

import os
from contextlib import contextmanager
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from plans import (
    PLANS,
    plan_limit,
    BIO_BONUS,
    CHAT_BONUS_PER,
    CHAT_BONUS_MAX,
    START_PLAN,
    START_DAYS,
)

DATABASE_URL = os.getenv("DATABASE_URL")


@contextmanager
def get_db_connection():
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
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id         BIGINT PRIMARY KEY,
                    username        TEXT,
                    first_name      TEXT,
                    last_name       TEXT,
                    plan            TEXT NOT NULL DEFAULT 'free',
                    plan_until      TIMESTAMP WITH TIME ZONE,
                    ai_used_today   INTEGER NOT NULL DEFAULT 0,
                    ai_usage_date   DATE,
                    is_blocked      BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """)
            for col, ddl in [
                ("plan", "TEXT DEFAULT 'free'"),
                ("plan_until", "TIMESTAMP WITH TIME ZONE"),
                ("ai_used_today", "INTEGER DEFAULT 0"),
                ("ai_usage_date", "DATE"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {ddl}")
                except Exception:
                    pass

            cur.execute("""
                CREATE TABLE IF NOT EXISTS referrals (
                    referred_id     BIGINT PRIMARY KEY,
                    referrer_id     BIGINT NOT NULL,
                    is_confirmed    BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    confirmed_at    TIMESTAMP WITH TIME ZONE
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id SERIAL PRIMARY KEY,
                    admin_id BIGINT NOT NULL,
                    action TEXT NOT NULL,
                    target_id BIGINT,
                    amount INTEGER,
                    details TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS stars_purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    stars_amount INTEGER NOT NULL,
                    product_type TEXT NOT NULL,
                    product_value INTEGER,
                    telegram_payment_charge_id TEXT,
                    provider_payment_charge_id TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_usage (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    request_type TEXT NOT NULL,
                    plan TEXT,
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_user ON ai_usage(user_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage(created_at);")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_chats (
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    chat_type TEXT,
                    title TEXT,
                    members INTEGER,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (user_id, chat_id)
                );
            """)


def ensure_user(user_id, username=None, first_name=None, last_name=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()
            if user:
                cur.execute(
                    """UPDATE users SET
                        username = COALESCE(%s, username),
                        first_name = COALESCE(%s, first_name),
                        last_name = COALESCE(%s, last_name),
                        updated_at = NOW()
                    WHERE user_id = %s RETURNING *""",
                    (username, first_name, last_name, user_id),
                )
                return dict(cur.fetchone())
            until = datetime.utcnow() + timedelta(days=START_DAYS)
            cur.execute(
                """INSERT INTO users (user_id, username, first_name, last_name, plan, plan_until)
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                (user_id, username, first_name, last_name, START_PLAN, until),
            )
            return dict(cur.fetchone())


def get_user(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def is_blocked(user_id):
    u = get_user(user_id)
    return bool(u and u.get("is_blocked"))


def set_blocked(user_id, blocked, admin_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_blocked = %s, updated_at = NOW() WHERE user_id = %s",
                (blocked, user_id),
            )
            if admin_id is not None:
                cur.execute(
                    "INSERT INTO admin_logs (admin_id, action, target_id) VALUES (%s, %s, %s)",
                    (admin_id, "BAN" if blocked else "UNBAN", user_id),
                )


def get_active_plan(user_id):
    u = get_user(user_id)
    if not u:
        return "free"
    plan = u.get("plan") or "free"
    until = u.get("plan_until")
    if plan == "free" or not until:
        return plan if plan in PLANS else "free"
    until_naive = until.replace(tzinfo=None) if getattr(until, "tzinfo", None) else until
    if until_naive > datetime.utcnow():
        return plan if plan in PLANS else "free"
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET plan = 'free', plan_until = NULL, updated_at = NOW() WHERE user_id = %s",
                (user_id,),
            )
    return "free"


def add_plan_days(user_id, plan_id, days, admin_id=None):
    if plan_id not in PLANS:
        plan_id = "free"
    ensure_user(user_id)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT plan, plan_until FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            now = datetime.utcnow()
            current_until = row["plan_until"]
            current_plan = row["plan"] or "free"
            if (
                current_plan == plan_id
                and current_until
                and current_until.replace(tzinfo=None) > now
            ):
                new_until = current_until.replace(tzinfo=None) + timedelta(days=days)
            else:
                new_until = now + timedelta(days=days)
            cur.execute(
                "UPDATE users SET plan = %s, plan_until = %s, updated_at = NOW() WHERE user_id = %s",
                (plan_id, new_until, user_id),
            )
            if admin_id is not None:
                cur.execute(
                    "INSERT INTO admin_logs (admin_id, action, target_id, amount, details) VALUES (%s,%s,%s,%s,%s)",
                    (admin_id, "PLAN", user_id, days, plan_id),
                )
            return new_until


def set_plan_free(user_id, admin_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET plan = 'free', plan_until = NULL, updated_at = NOW() WHERE user_id = %s",
                (user_id,),
            )
            if admin_id is not None:
                cur.execute(
                    "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (%s,%s,%s,%s)",
                    (admin_id, "PLAN_FREE", user_id, "free"),
                )


def count_user_chats(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM user_chats WHERE user_id = %s", (user_id,))
            return int(cur.fetchone()["cnt"] or 0)


def chats_bonus(user_id):
    return min(CHAT_BONUS_MAX, count_user_chats(user_id) * CHAT_BONUS_PER)


def get_daily_limit(user_id, has_bio=False):
    plan = get_active_plan(user_id)
    base = plan_limit(plan)
    bonus = chats_bonus(user_id) + (BIO_BONUS if has_bio else 0)
    return base + bonus


def _reset_daily_if_needed(cur, user_id):
    today = date.today()
    cur.execute(
        "SELECT ai_used_today, ai_usage_date FROM users WHERE user_id = %s FOR UPDATE",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        return 0
    if row["ai_usage_date"] != today:
        cur.execute(
            "UPDATE users SET ai_used_today = 0, ai_usage_date = %s, updated_at = NOW() WHERE user_id = %s",
            (today, user_id),
        )
        return 0
    return int(row["ai_used_today"] or 0)


def get_used_today(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            return _reset_daily_if_needed(cur, user_id)


def try_consume_request(user_id, has_bio=False):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            used = _reset_daily_if_needed(cur, user_id)
            plan = get_active_plan(user_id)
            limit = plan_limit(plan) + chats_bonus(user_id) + (BIO_BONUS if has_bio else 0)
            if used >= limit:
                title = PLANS.get(plan, PLANS["free"])["title"]
                return False, (
                    f"⏳ Лимит на сегодня: <b>{used}/{limit}</b>\n"
                    f"Тариф: <b>{title}</b>\n\n"
                    f"Купи подписку или бонусы (приписка / чаты)."
                )
            cur.execute(
                """UPDATE users SET ai_used_today = ai_used_today + 1,
                    ai_usage_date = CURRENT_DATE, updated_at = NOW()
                WHERE user_id = %s""",
                (user_id,),
            )
            return True, ""


def log_ai_usage(user_id, request_type, success=True):
    plan = get_active_plan(user_id)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ai_usage (user_id, request_type, plan, success) VALUES (%s,%s,%s,%s)",
                (user_id, request_type, plan, success),
            )


def admin_reset_limit(user_id, admin_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET ai_used_today = 0, ai_usage_date = CURRENT_DATE, updated_at = NOW() WHERE user_id = %s",
                (user_id,),
            )
            if admin_id is not None:
                cur.execute(
                    "INSERT INTO admin_logs (admin_id, action, target_id) VALUES (%s,%s,%s)",
                    (admin_id, "RESET_LIMIT", user_id),
                )


def create_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return False
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM referrals WHERE referred_id = %s", (referred_id,))
            if cur.fetchone():
                return False
            cur.execute(
                "INSERT INTO referrals (referred_id, referrer_id, is_confirmed) VALUES (%s,%s,FALSE) ON CONFLICT DO NOTHING",
                (referred_id, referrer_id),
            )
            return cur.rowcount > 0


def confirm_referral(referred_id):
    from plans import REFERRER_PLAN, REFERRER_DAYS
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT referrer_id, is_confirmed FROM referrals WHERE referred_id = %s FOR UPDATE",
                (referred_id,),
            )
            row = cur.fetchone()
            if not row or row["is_confirmed"]:
                return None
            referrer_id = row["referrer_id"]
            cur.execute(
                "UPDATE referrals SET is_confirmed = TRUE, confirmed_at = NOW() WHERE referred_id = %s",
                (referred_id,),
            )
    add_plan_days(referrer_id, REFERRER_PLAN, REFERRER_DAYS)
    return referrer_id


def get_referral_count(user_id, confirmed_only=True):
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


def get_pending_referral(referred_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM referrals WHERE referred_id = %s AND is_confirmed = FALSE",
                (referred_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def register_forward_chat(user_id, chat_id, chat_type=None, title=None, members=None):
    if not user_id or not chat_id:
        return
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO user_chats (user_id, chat_id, chat_type, title, members, updated_at)
                   VALUES (%s,%s,%s,%s,%s,NOW())
                   ON CONFLICT (user_id, chat_id) DO UPDATE SET
                     chat_type = COALESCE(EXCLUDED.chat_type, user_chats.chat_type),
                     title = COALESCE(EXCLUDED.title, user_chats.title),
                     members = COALESCE(EXCLUDED.members, user_chats.members),
                     updated_at = NOW()""",
                (user_id, chat_id, chat_type, title, members),
            )


def record_stars_purchase(user_id, stars_amount, product_type, product_value=None,
                          telegram_payment_charge_id=None, provider_payment_charge_id=None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO stars_purchases
                   (user_id, stars_amount, product_type, product_value,
                    telegram_payment_charge_id, provider_payment_charge_id)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (user_id, stars_amount, product_type, product_value,
                 telegram_payment_charge_id, provider_payment_charge_id),
            )


def get_stars_stats(period="all"):
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
                f"SELECT COALESCE(SUM(stars_amount),0) AS total_stars, COUNT(*) AS purchases FROM stars_purchases WHERE {cond}"
            )
            return dict(cur.fetchone())


def get_ai_stats(period="today"):
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
                f"""SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE request_type = 'photo') AS photo
                    FROM ai_usage WHERE {cond} AND success = TRUE"""
            )
            return dict(cur.fetchone())


def get_users_stats():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE) AS new_today,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS new_week,
                    COUNT(*) FILTER (WHERE plan != 'free' AND (plan_until IS NULL OR plan_until > NOW())) AS paid,
                    COUNT(*) FILTER (WHERE is_blocked) AS blocked
                FROM users"""
            )
            return dict(cur.fetchone())


def get_referral_stats():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE is_confirmed) AS confirmed,
                    COUNT(*) FILTER (WHERE confirmed_at >= CURRENT_DATE) AS today
                FROM referrals"""
            )
            return dict(cur.fetchone())


def search_user(query):
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


def get_top_referrers(limit=10):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT r.referrer_id, u.username, u.first_name, COUNT(*) AS cnt
                FROM referrals r JOIN users u ON u.user_id = r.referrer_id
                WHERE r.is_confirmed = TRUE
                GROUP BY r.referrer_id, u.username, u.first_name
                ORDER BY cnt DESC LIMIT %s""",
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]


def get_admin_logs(limit=50):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(r) for r in cur.fetchall()]


def get_all_user_ids():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE is_blocked = FALSE")
            return [r["user_id"] for r in cur.fetchall()]
