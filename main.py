import logging
import os
import io
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
from flask import Flask, request, Response

# --- Загрузка и настройка ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL') # URL вашего вебхука, его нужно будет задать в PythonAnywhere

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Логика бота (обработчики) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение при команде /start."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я бот, который умеет конвертировать стикеры в PNG. Просто отправь мне любой стикер!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет справочное сообщение при команде /help."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Чтобы начать, просто отправь мне стикер. Я превращу его в PNG файл и отправлю тебе в ответ."
    )

async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает стикер, конвертирует в PNG и отправляет обратно."""
    sticker = update.message.sticker
    if sticker.is_animated or sticker.is_video:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Извини, я пока не умею работать с анимированными стикерами."
        )
        return

    try:
        file = await context.bot.get_file(sticker.file_id)
        file_bytes = await file.download_as_bytearray()
        
        with io.BytesIO(file_bytes) as webp_stream:
            with Image.open(webp_stream) as img:
                png_stream = io.BytesIO()
                img.save(png_stream, 'PNG')
                png_stream.seek(0)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=png_stream,
            filename=f"{sticker.file_unique_id}.png"
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке стикера: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при конвертации стикера. Попробуй еще раз."
        )

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на сообщения, не являющиеся стикерами."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Пожалуйста, отправь мне стикер."
    )

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на любые команды, которые бот не распознает."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извини, я не знаю такой команды."
    )

# --- Настройка и запуск приложения ---

# Создаем объект приложения telegram-bot
ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()

# Регистрируем обработчики в приложении
ptb_app.add_handler(CommandHandler('start', start))
ptb_app.add_handler(CommandHandler('help', help_command))
ptb_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
ptb_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL, handle_other_messages))
ptb_app.add_handler(MessageHandler(filters.COMMAND, unknown))

# Создаем веб-сервер Flask
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return 'Ok'

@flask_app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
async def webhook():
    """Эндпоинт, который принимает обновления от Telegram."""
    logger.info("!!! Получен входящий запрос от Telegram.")
    json_data = request.get_json(force=True)
    logger.info(f"--> Данные: {json_data}")
    
    update = Update.de_json(json_data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status=200)

async def setup_webhook():
    """Устанавливает вебхук при запуске приложения."""
    if not WEBHOOK_URL:
        logger.error("Переменная WEBHOOK_URL не задана!")
        return
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    logger.info(f"Вебхук установлен на {WEBHOOK_URL}/{TELEGRAM_TOKEN}")

# Запускаем установку вебхука при старте
if __name__ != '__main__':
    # This part is executed when the application is run by a WSGI server
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())

# Для локального тестирования (не используется на PythonAnywhere)
if __name__ == '__main__':
    logger.warning("Запуск в режиме локального тестирования. Не для продакшена!")
    # Этот режим не будет работать без properly configured WEBHOOK_URL and a tool like ngrok
    flask_app.run(debug=True)