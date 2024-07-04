import asyncio
import datetime
from os import getenv
from math import ceil

from dotenv import load_dotenv
from faster_whisper import WhisperModel
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from database import PostgresDb
from gpt import GPT
from handlers import hourly_reminder, handle_start, handle_message, handle_unknown, handle_voice

load_dotenv()


class Telebot:
    def __init__(self):
        self.token = getenv('TELEGRAM_TOKEN')
        self.db = PostgresDb(
            getenv('POSTGRES_DB'),
            getenv('POSTGRES_HOST'),
            int(getenv('POSTGRES_PORT')),
            getenv('POSTGRES_USER'),
            getenv('POSTGRES_PASSWORD')
        )
        self.db.connect()
        self.gpt = GPT()
        self.app = ApplicationBuilder().token(self.token).build()
        self.whisper = WhisperModel('small.en', device='cpu')
        self.setup()

    def setup(self):
        self.app.add_handlers([
            CommandHandler('start', handle_start),
            MessageHandler(filters.COMMAND, handle_unknown),
            MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message),
            MessageHandler(filters.VOICE, handle_voice)])
        # pass useful objects to context for handlers
        self.app.context_types.context.bot_data = {
            'db': self.db,
            'gpt': self.gpt,
            'whisper': self.whisper
        }
        job_queue = self.app.job_queue
        # for testing purposes
        # job_queue.run_once(callback=hourly_reminder, when=5)

        start = datetime.datetime.now().replace(microsecond=0, second=0)
        minutes_to_add = ceil(start.minute / 5) * 5 - start.minute
        start += datetime.timedelta(minutes=minutes_to_add)

        job_queue.run_repeating(
            callback=hourly_reminder,
            interval=datetime.timedelta(minutes=5),
            first=start.astimezone())

    def run(self):
        self.app.run_polling()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    bot = Telebot()
    bot.run()
