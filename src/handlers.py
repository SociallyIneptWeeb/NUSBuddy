from telegram import Update
from telegram.ext import ContextTypes

from database import PostgresDb


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.startswith('/start '):
        await update.effective_message.reply_text(
            'Available commands:\n/start username: Create a new account with the given username.',
            reply_to_message_id=update.message.id)
        return

    username = update.message.text[7:]
    db: PostgresDb = context.data['db']
    if db.account_exists_query(update.message.chat_id):
        await update.effective_message.reply_text(
            'You have already created an account.',
            reply_to_message_id=update.message.id)
        return

    if db.username_taken_query(username):
        await update.effective_message.reply_text(
            f'The username {username} is already taken. Please provide another one.',
            reply_to_message_id=update.message.id)
        return

    db.create_user_account_query(username, update.message.chat_id)
    await update.effective_message.reply_text(
        f'Welcome {username}! I will do my best to help you keep track of any deadlines!',
        reply_to_message_id=update.message.id)
