import logging
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)

# Начальный баланс
current_balance = 1000000

def send_message(text):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        logger.info(f'Сообщение отправлено: {text}')
    except Exception as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')

def get_balance():
    """Получение текущего баланса."""
    return f'Текущий баланс: {current_balance:.2f}'

def update_balance(new_balance):
    """Обновление текущего баланса."""
    global current_balance
    current_balance = new_balance

def start(update: Update, context: CallbackContext):
    """Обработчик команды /start."""
    update.message.reply_text('Добро пожаловать! Используйте команду /balance для проверки текущего баланса.')
    logger.info('Команда /start получена.')

def balance(update: Update, context: CallbackContext):
    """Обработчик команды /balance."""
    balance_message = get_balance()
    update.message.reply_text(balance_message)
    logger.info('Команда /balance получена.')

def main():
    """Запуск бота."""
    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))

    # Логирование всех текстовых сообщений для отладки
    def log_updates(update: Update, context: CallbackContext):
        logger.info(f'Получено сообщение: {update}')

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, log_updates))  # Логирование текстовых сообщений

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()