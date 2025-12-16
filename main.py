import logging
import os
import io
import asyncio
import secrets
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image

# --- Загрузка и настройка ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
# Генерируем секретный токен, если он не задан, для повышения безопасности
SECRET_TOKEN = os.getenv('SECRET_TOKEN', secrets.token_hex(32))

# Настройка логирования
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

    png_stream = io.BytesIO()
    try:
        file = await context.bot.get_file(sticker.file_id)
        file_bytes = await file.download_as_bytearray()
        
        with io.BytesIO(file_bytes) as webp_stream:
            with Image.open(webp_stream) as img:
                img.save(png_stream, 'PNG')
                png_stream.seek(0)
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=png_stream,
            filename=f"{sticker.file_unique_id}.png"
        )
    except Exception:
        logger.exception("Произошла ошибка при обработке стикера.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла ошибка при конвертации стикера. Попробуй еще раз."
        )
    finally:
        png_stream.close()

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

def main() -> None:
    """Основная функция запуска бота."""
    if not all([TELEGRAM_TOKEN, WEBHOOK_URL]):
        logger.error("Не заданы обязательные переменные окружения: TELEGRAM_TOKEN, WEBHOOK_URL")
        return

    # Создаем объект приложения
    ptb_app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрируем обработчики
    ptb_app.add_handler(CommandHandler('start', start))
    ptb_app.add_handler(CommandHandler('help', help_command))
    ptb_app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    ptb_app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL, handle_other_messages))
    ptb_app.add_handler(MessageHandler(filters.COMMAND, unknown))

    # Получаем порт из переменной окружения, предоставленной Render
    port = int(os.environ.get('PORT', 8443))
    
    # Запускаем бота в режиме вебхука
    ptb_app.run_webhook(
        listen="0.0.0.0",
        port=port,
        secret_token=SECRET_TOKEN,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    main()