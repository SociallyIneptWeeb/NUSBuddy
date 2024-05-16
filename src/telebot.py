import asyncio
from os import getenv

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from database import PostgresDb
from handlers import handle_command

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
        self.app = ApplicationBuilder().token(self.token).build()

    def run(self):
        # message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
        self.app.add_handler(MessageHandler(filters.COMMAND, handle_command))
        # pass the db object to context for handlers
        self.app.context_types.context.data = {'db': self.db}
        self.app.run_polling()


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    bot = Telebot()
    bot.run()
