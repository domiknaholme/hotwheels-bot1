import os
import sys
import json
import logging
import uuid

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import firebase_admin
from firebase_admin import credentials, db

# Настройка логирования и вывод версии Python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.info(f"Python version: {sys.version}")

# Получаем JSON ключ из переменной окружения
firebase_key_json = os.environ.get('FIREBASE_CREDENTIALS')
if not firebase_key_json:
    raise Exception("Переменная окружения FIREBASE_CREDENTIALS не установлена")

cred_dict = json.loads(firebase_key_json)

# Заменяем экранированные \n на настоящие переводы строк
if 'private_key' in cred_dict:
    cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')

cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred, {
    'databaseURL': "https://hot-wheels-1-default-rtdb.europe-west1.firebasedatabase.app/"
})

root_ref = db.reference('/activation_codes')

# Команды бота

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Выберите подписку:\n"
        "1. Подписка на месяц — 149₽\n"
        "2. Подписка на год — 1099₽\n\n"
        "Отправьте 1 или 2, чтобы получить ссылку на оплату."
    )

async def choose_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '1':
        pay_link = "https://t.me/UnionBot?start=pay_month"  # Заменить на реальную ссылку
        await update.message.reply_text(f"Оплатите подписку на месяц по ссылке:\n{pay_link}")
    elif text == '2':
        pay_link = "https://t.me/UnionBot?start=pay_year"
        await update.message.reply_text(f"Оплатите подписку на год по ссылке:\n{pay_link}")
    else:
        await update.message.reply_text("Пожалуйста, отправьте '1' или '2'.")

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /confirm <month|year>")
        return
    plan = args[0].lower()
    if plan not in ['month', 'year']:
        await update.message.reply_text("План должен быть 'month' или 'year'")
        return

    code = str(uuid.uuid4()).replace("-", "").upper()[:10]
    root_ref.child(user_id).set({
        'code': code,
        'plan': plan,
    })
    await update.message.reply_text(f"Оплата подтверждена. Ваш код активации: {code}")

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    data = root_ref.child(user_id).get()
    if data and 'code' in data:
        await update.message.reply_text(f"Ваш код активации: {data['code']}\nПодписка: {data.get('plan', 'не указана')}")
    else:
        await update.message.reply_text("Код активации не найден. Пожалуйста, оплатите подписку.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — начать\n"
        "/confirm <month|year> — подтвердить оплату (тест)\n"
        "/code — получить код активации\n"
        "/help — помощь"
    )

def main():
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise Exception("Переменная окружения TELEGRAM_TOKEN не установлена")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm_payment))
    app.add_handler(CommandHandler("code", get_code))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), choose_plan))

    app.run_polling()

if __name__ == "__main__":
    main()
