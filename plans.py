"""StudyGo — тарифы и права доступа."""

from typing import Dict, Any, Optional

# plan_id -> settings
PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "title": "Free",
        "stars": 0,
        "days": 30,
        "limit": 15,
        "features": ["text", "check", "explain"],
        "desc": "• Текст, проверка ответа, объяснение темы",
    },
    "free_plus": {
        "title": "Free+",
        "stars": 30,
        "days": 30,
        "limit": 40,
        "features": ["text", "check", "explain", "photo", "conspect"],
        "desc": "• Всё Free\n• Решение по фото\n• Краткий конспект темы",
    },
    "pro": {
        "title": "Pro",
        "stars": 50,
        "days": 30,
        "limit": 75,
        "features": ["text", "check", "explain", "photo", "conspect", "test", "error_review"],
        "desc": "• Всё Free+\n• Создание тестов\n• Разбор ошибки",
    },
    "pro_plus": {
        "title": "Pro+",
        "stars": 150,
        "days": 30,
        "limit": 135,
        "features": [
            "text", "check", "explain", "photo", "conspect",
            "test", "error_review", "week_plan", "hard_task",
        ],
        "desc": "• Всё Pro\n• План на неделю\n• Сложные задачи пошагово",
    },
    "ultra": {
        "title": "Ultra",
        "stars": 300,
        "days": 30,
        "limit": 250,
        "features": [
            "text", "check", "explain", "photo", "conspect",
            "test", "error_review", "week_plan", "hard_task",
            "priority", "big_analysis",
        ],
        "desc": "• Всё Pro+\n• Приоритет\n• Большой разбор темы / КР",
    },
}

PLAN_ORDER = ["free", "free_plus", "pro", "pro_plus", "ultra"]

# feature -> кнопки / типы запросов
FEATURE_LABELS = {
    "text": "AI-помощник",
    "photo": "По фото",
    "explain": "Тема",
    "test": "Тест",
    "check": "Проверить",
    "conspect": "Конспект",
    "error_review": "Разбор ошибки",
    "week_plan": "План недели",
    "hard_task": "Сложная задача",
    "big_analysis": "Большой разбор",
}

BIO_TAG = "StudyGotgkk"
BIO_BONUS = 5
CHAT_BONUS_PER = 2
CHAT_BONUS_MAX = 100
CHATS_NEED_MEMBERS = 5
START_PLAN = "pro"
START_DAYS = 3
REFERRER_PLAN = "free_plus"
REFERRER_DAYS = 3


def plan_title(plan_id: str) -> str:
    return PLANS.get(plan_id, PLANS["free"])["title"]


def plan_limit(plan_id: str) -> int:
    return int(PLANS.get(plan_id, PLANS["free"])["limit"])


def has_feature(plan_id: str, feature: str) -> bool:
    p = PLANS.get(plan_id, PLANS["free"])
    return feature in p["features"]


def plans_shop_text() -> str:
    lines = ["💎 <b>Подписки StudyGo</b>\n"]
    for pid in PLAN_ORDER:
        p = PLANS[pid]
        price = f"{p['stars']}⭐ / 30 дн." if p["stars"] else "бесплатно"
        lines.append(f"<b>{p['title']}</b> — {price}")
        lines.append(f"Лимит: <b>{p['limit']}</b> запросов/день")
        lines.append(p["desc"])
        lines.append("")
    lines.append(
        "Бонусы к лимиту:\n"
        f"• Приписка @{BIO_TAG}: +{BIO_BONUS}/день\n"
        f"• Чаты (>5 чел.): +{CHAT_BONUS_PER} за чат, макс +{CHAT_BONUS_MAX}"
    )
    return "\n".join(lines)
