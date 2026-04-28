import os

os.environ["BOT_TOKEN"] = "8740742680:AAEWg_lmlk8pHFIyZ-KXUYZajVQjj4pexnU"
os.environ["GEMINI_API_KEY"] = "AIzaSyCrDoVKjWG-jL3RHvY0jqyV-TbeCIeovFQ"

import json
import logging
import datetime
import google.generativeai as genai
import json
import logging
import datetime
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Константы ─────────────────────────────────────────────────
DATA_FILE = "users.json"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DAILY_AI_LIMIT = 10
STREAK_RESTORE_COST = 200

SUBJECTS = {
    "Математика": ["Алгебра", "Геометрия", "Тригонометрия", "Производные", "Интегралы",
                   "Уравнения", "Неравенства", "Логарифмы", "Комбинаторика", "Вероятность"],
    "Физика": ["Механика", "Термодинамика", "Электричество", "Магнетизм",
               "Оптика", "Атомная физика", "Волны", "Законы Ньютона"],
    "История Казахстана": ["Древний Казахстан", "Средние века", "Казахское ханство",
                           "Колониальный период", "Советский период", "Независимость", "Современность"],
    "Русский язык": ["Фонетика", "Морфология", "Синтаксис", "Орфография", "Пунктуация", "Стилистика"],
    "Информатика": ["Алгоритмы", "Программирование", "Базы данных", "Сети", "ОС", "Безопасность"],
}
SUBJECT_LIST = list(SUBJECTS.keys())

REWARDS = {
    5:  ("🥉 Новичок", 100),
    10: ("🥈 Ученик", 200),
    25: ("🥇 Знаток", 500),
    50: ("💎 Мастер", 1000),
}

NAME, GRADES, ATTENDANCE, EXAM_SUBJECT, EXAM_DAYS, AI_CHAT = range(6)

# ─── База данных ───────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid):
    data = load_data()
    if uid not in data:
        data[uid] = {
            "name": "", "grades": {}, "streak": 0, "last_active": "",
            "coins": 0, "badges": [], "total_tasks": 0,
            "levels": {s: 1 for s in SUBJECT_LIST},
            "ai_used_today": 0, "ai_date": "",
        }
        save_data(data)
    return data[uid]

def save_user(uid, user):
    data = load_data()
    data[uid] = user
    save_data(data)

def update_streak(uid):
    user = get_user(uid)
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    bonus = 0
    if user["last_active"] == today:
        return user["streak"], 0
    user["streak"] = user["streak"] + 1 if user["last_active"] == yesterday else 1
    user["last_active"] = today
    if user["streak"] % 7 == 0:
        bonus = 300
        user["coins"] += bonus
    save_user(uid, user)
    return user["streak"], bonus

def check_badges(uid):
    user = get_user(uid)
    new_badges = []
    for needed, (name, reward) in REWARDS.items():
        if user["total_tasks"] >= needed and name not in user["badges"]:
            user["badges"].append(name)
            user["coins"] += reward
            new_badges.append((name, reward))
    save_user(uid, user)
    return new_badges

# ─── Меню ──────────────────────────────────────────────────────
def main_menu():
    return ReplyKeyboardMarkup([
        ["📊 Анализ успеваемости", "🆘 Экзамен-спасатель"],
        ["🤖 Чат с ИИ", "🔥 Мой прогресс"],
        ["📚 Мои уровни", "💰 Монеты и награды"],
    ], resize_keyboard=True)

# ─── /start ────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    streak, bonus = update_streak(uid)

    if user["name"]:
        fire = "🔥" * min(streak, 7)
        bonus_text = f"\n🎉 Бонус за {streak}-дневную серию: +{bonus} монет!" if bonus else ""
        await update.message.reply_text(
            f"С возвращением, *{user['name']}*! {fire}\n"
            f"Серия: *{streak} дней* | Монеты: 💰{user['coins']}{bonus_text}\n\nЧто делаем?",
            parse_mode="Markdown", reply_markup=main_menu()
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Привет! Я *Альтрон* — ИИ-помощник в учёбе.\n\n"
        "🔥 Серии и монеты за каждый день\n"
        "📊 Анализ твоих оценок\n"
        "🆘 Ускоренный план перед экзаменом\n"
        "🤖 Чат с ИИ по любой теме\n\n"
        "Как тебя зовут?",
        parse_mode="Markdown"
    )
    return NAME

# ─── Регистрация ───────────────────────────────────────────────
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    user["name"] = update.message.text.strip()
    save_user(uid, user)
    subjects_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(SUBJECT_LIST)])
    await update.message.reply_text(
        f"Отлично, *{user['name']}*! 🎓\n\n"
        f"Введи оценки через пробел (1–5):\n{subjects_str}\n\n*Пример:* `4 5 3 5 4 3`",
        parse_mode="Markdown"
    )
    return GRADES

async def get_grades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    try:
        grades = list(map(int, update.message.text.strip().split()))
        if len(grades) != len(SUBJECT_LIST) or any(g < 1 or g > 5 for g in grades):
            raise ValueError
    except ValueError:
        await update.message.reply_text(f"⚠️ Нужно {len(SUBJECT_LIST)} оценок от 1 до 5. Пример: `4 5 3 5 4 3`", parse_mode="Markdown")
        return GRADES
    user = get_user(uid)
    user["grades"] = {SUBJECT_LIST[i]: grades[i] for i in range(len(SUBJECT_LIST))}
    save_user(uid, user)
    await update.message.reply_text(
        "📅 Процент посещаемости?",
        reply_markup=ReplyKeyboardMarkup([["90–100%", "75–89%"], ["50–74%", "Менее 50%"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return ATTENDANCE

async def get_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    attendance = update.message.text
    user = get_user(uid)
    grades = user["grades"]
    avg = sum(grades.values()) / len(grades)
    weak = [(s, g) for s, g in grades.items() if g <= 3]
    strong = [s for s, g in grades.items() if g == 5]

    if avg >= 4.5 and "90" in attendance:
        risk, risk_text = "🟢 Низкий", "Отличный результат!"
    elif avg >= 3.5:
        risk, risk_text = "🟡 Средний", "Есть потенциал для роста."
    else:
        risk, risk_text = "🔴 Высокий", "Требуется помощь. Альтрон готов!"

    recs = [f"📌 *{s}* ({g}): {'консультация + онлайн-модули' if g <= 2 else 'повтори ключевые темы'}" for s, g in weak]
    if "50" in attendance or "Менее" in attendance:
        recs.append("📌 *Посещаемость*: старайся посещать ≥85% занятий")
    if not recs:
        recs.append("✅ Всё отлично! Попробуй олимпиадные задачи.")

    bar = "⬛" * round(avg) + "⬜" * (5 - round(avg))
    user["total_tasks"] += 1
    user["coins"] += 50
    save_user(uid, user)
    new_badges = check_badges(uid)
    badge_text = ("\n\n🏆 " + " | ".join([f"{b} (+{c} монет)" for b, c in new_badges])) if new_badges else ""

    await update.message.reply_text(
        f"📊 *Отчёт Альтрон — {user['name']}*\n{'─'*28}\n\n"
        f"*Средний балл:* {avg:.1f}/5 {bar}\n"
        f"*Посещаемость:* {attendance}\n"
        f"*Риск:* {risk} — _{risk_text}_\n\n"
        f"💪 *Сильные:* {', '.join(strong) if strong else 'пока нет'}\n\n"
        f"🎯 *Рекомендации:*\n" + "\n".join(recs) +
        f"\n\n💰 +50 монет за анализ!{badge_text}\n{'─'*28}\n_Альтрон · Матрица знаний_",
        parse_mode="Markdown", reply_markup=main_menu()
    )
    return ConversationHandler.END

# ─── Экзамен-спасатель ─────────────────────────────────────────
async def exam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Экзамен-спасатель*\n\n"
        "3 часа ночи. Завтра экзамен. Не понимаешь тему.\n"
        "Альтрон спасёт тебя за 20 минут — только главное, без воды.\n\n"
        "По какому предмету?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([[s] for s in SUBJECT_LIST], one_time_keyboard=True, resize_keyboard=True)
    )
    return EXAM_SUBJECT

async def exam_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text not in SUBJECT_LIST:
        await update.message.reply_text("Выбери предмет из списка.")
        return EXAM_SUBJECT
    context.user_data["exam_subject"] = update.message.text
    await update.message.reply_text(
        f"Предмет: *{update.message.text}*\n\nСколько дней до экзамена?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["1 день", "2 дня", "3 дня"], ["5 дней", "7 дней"]], one_time_keyboard=True, resize_keyboard=True)
    )
    return EXAM_DAYS

async def exam_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    days_map = {"1 день": 1, "2 дня": 2, "3 дня": 3, "5 дней": 5, "7 дней": 7}
    days = days_map.get(update.message.text, 3)
    subject = context.user_data.get("exam_subject", SUBJECT_LIST[0])
    topics = SUBJECTS[subject]
    tpd = max(1, len(topics) // days)

    lines = [f"⚡ *Ускоренный план: {subject}*\n_{days} дн. до экзамена_\n{'─'*28}"]
    for day in range(1, days + 1):
        s = (day - 1) * tpd
        e = s + tpd if day < days else len(topics)
        day_topics = topics[s:e]
        if not day_topics:
            break
        lines.append(f"\n📅 *День {day}:*")
        for t in day_topics:
            lines.append(f"  ▸ {t}")

    lines += [
        f"\n{'─'*28}",
        "💡 *Советы для быстрого освоения:*",
        "  • 25 мин учёба → 5 мин отдых (Помодоро)",
        "  • После каждой темы — одно практическое задание",
        "  • Повторяй пройденное перед сном",
        f"\n_Альтрон · Матрица знаний_"
    ]

    user = get_user(uid)
    user["coins"] += 30
    user["total_tasks"] += 1
    save_user(uid, user)

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=main_menu())
    return ConversationHandler.END

# ─── Чат с ИИ ──────────────────────────────────────────────────
async def ai_chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    today = datetime.date.today().isoformat()
    if user["ai_date"] != today:
        user["ai_used_today"] = 0
        user["ai_date"] = today
        save_user(uid, user)
    remaining = DAILY_AI_LIMIT - user["ai_used_today"]
    await update.message.reply_text(
        f"🤖 *Чат с ИИ-преподавателем*\n\n"
        f"Задавай любые вопросы по школьным предметам!\n"
        f"Осталось вопросов сегодня: *{remaining}/{DAILY_AI_LIMIT}*\n\n"
        f"Напиши вопрос или /menu чтобы выйти.",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove()
    )
    return AI_CHAT

async def ai_chat_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    today = datetime.date.today().isoformat()
    if user["ai_date"] != today:
        user["ai_used_today"] = 0
        user["ai_date"] = today

    if user["ai_used_today"] >= DAILY_AI_LIMIT:
        await update.message.reply_text("⛔ Дневной лимит исчерпан. Возвращайся завтра! 🌅", reply_markup=main_menu())
        return ConversationHandler.END

    await update.message.reply_text("⏳ Думаю...")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Ты школьный ИИ-преподаватель. Отвечай ТОЛЬКО на учебные вопросы по школьным предметам. "
            f"Если вопрос не учебный — вежливо откажи. Отвечай кратко и понятно по-русски, максимум 200 слов.\n\n"
            f"Вопрос: {update.message.text}"
        )
        user["ai_used_today"] += 1
        user["coins"] += 10
        save_user(uid, user)
        remaining = DAILY_AI_LIMIT - user["ai_used_today"]
        await update.message.reply_text(
            f"🤖 {response.text}\n\n💰 +10 монет | Осталось: *{remaining}* вопросов",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        await update.message.reply_text("⚠️ ИИ временно недоступен. Попробуй позже.", reply_markup=main_menu())
        return ConversationHandler.END
    return AI_CHAT

# ─── Прогресс ──────────────────────────────────────────────────
async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    streak = user["streak"]
    fire = "🔥" * min(streak, 7) if streak > 0 else "❄️"
    next_bonus = 7 - (streak % 7) if streak % 7 != 0 else 7

    kb = []
    if streak == 0 and user["coins"] >= STREAK_RESTORE_COST:
        kb = [[InlineKeyboardButton(f"🔄 Восстановить серию за {STREAK_RESTORE_COST} монет", callback_data="restore_streak")]]

    await update.message.reply_text(
        f"📈 *Прогресс {user['name']}*\n{'─'*28}\n\n"
        f"{fire} *Серия:* {streak} дней подряд\n"
        f"💰 *Монеты:* {user['coins']}\n"
        f"📝 *Заданий:* {user['total_tasks']}\n"
        f"🏆 *Значки:* {' '.join(user['badges']) if user['badges'] else 'пока нет'}\n\n"
        f"{'💪 Ещё ' + str(next_bonus) + ' дней до бонуса 300 монет!' if streak > 0 else '💡 Начни учиться сегодня!'}\n"
        f"{'─'*28}\n_Альтрон · Матрица знаний_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb) if kb else None
    )

async def restore_streak_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = str(query.from_user.id)
    user = get_user(uid)
    if user["coins"] >= STREAK_RESTORE_COST:
        user["coins"] -= STREAK_RESTORE_COST
        user["streak"] = 1
        user["last_active"] = datetime.date.today().isoformat()
        save_user(uid, user)
        await query.answer("🔥 Серия восстановлена!")
        await query.edit_message_text(f"✅ Серия восстановлена!\n💰 Осталось монет: {user['coins']}", parse_mode="Markdown")
    else:
        await query.answer("❌ Недостаточно монет!")

# ─── Уровни ────────────────────────────────────────────────────
async def show_levels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    lines = [f"📚 *Уровни по предметам*\n{'─'*28}\n"]
    for subject, topics in SUBJECTS.items():
        level = user["levels"].get(subject, 1)
        total = len(topics)
        done = min(level - 1, total)
        bar = "🟩" * done + "⬜" * (total - done)
        current = topics[level - 1] if level <= total else "✅ Пройдено"
        lines.append(f"*{subject}* — ур. {level}/{total}")
        lines.append(f"{bar}")
        lines.append(f"Сейчас: _{current}_\n")
    lines.append(f"{'─'*28}\n_Выполняй задания чтобы повышать уровень!_")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=main_menu())

# ─── Монеты ────────────────────────────────────────────────────
async def show_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    lines = [
        f"💰 *Монеты и награды*\n{'─'*28}\n",
        f"*Твои монеты:* {user['coins']} 💰\n",
        f"*Как зарабатывать:*",
        f"  • Анализ успеваемости → +50",
        f"  • Экзамен-спасатель → +30",
        f"  • Вопрос ИИ → +10",
        f"  • Серия 7 дней → +300\n",
        f"*Значки:*",
    ]
    for needed, (badge, reward) in REWARDS.items():
        status = "✅" if badge in user["badges"] else "🔒"
        lines.append(f"  {status} {badge} — {needed} заданий (+{reward} монет)")
    lines.append(f"\n*Твои значки:* {' '.join(user['badges']) if user['badges'] else 'Выполняй задания!'}")
    lines.append(f"\n{'─'*28}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=main_menu())

# ─── Роутер ────────────────────────────────────────────────────
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Главное меню 👇", reply_markup=main_menu())
    return ConversationHandler.END

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📊 Анализ успеваемости":
        s = "\n".join([f"{i+1}. {s}" for i, s in enumerate(SUBJECT_LIST)])
        await update.message.reply_text(f"Введи оценки (1–5) через пробел:\n{s}\n\n*Пример:* `4 5 3 5 4 3`", parse_mode="Markdown")
        return GRADES
    elif text == "🆘 Экзамен-спасатель":
        return await exam_start(update, context)
    elif text == "🤖 Чат с ИИ":
        return await ai_chat_start(update, context)
    elif text == "🔥 Мой прогресс":
        await show_progress(update, context)
    elif text == "📚 Мои уровни":
        await show_levels(update, context)
    elif text == "💰 Монеты и награды":
        await show_coins(update, context)

# ─── main ───────────────────────────────────────────────────────
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не задан!")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu_cmd),
            MessageHandler(filters.TEXT & ~filters.COMMAND, button_router),
        ],
        states={
            NAME:         [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GRADES:       [MessageHandler(filters.TEXT & ~filters.COMMAND, get_grades)],
            ATTENDANCE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_attendance)],
            EXAM_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exam_subject)],
            EXAM_DAYS:    [MessageHandler(filters.TEXT & ~filters.COMMAND, exam_days)],
            AI_CHAT:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_reply)],
        },
        fallbacks=[CommandHandler("menu", menu_cmd), CommandHandler("start", start)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(restore_streak_cb, pattern="restore_streak"))
    logger.info("Альтрон запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
