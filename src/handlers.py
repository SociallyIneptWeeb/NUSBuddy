import datetime
import os
from collections import defaultdict
from prettytable import PrettyTable, ALL

from telegram import Update, constants
from telegram.ext import CallbackContext, ContextTypes

from database import PostgresDb
from gpt import GPT, Intention


async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        'Available commands:\n/start: Create a new account with your telegram handle as your username.',
        reply_to_message_id=update.message.id)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: PostgresDb = context.bot_data['db']
    if db.account_exists_query(update.message.chat_id):
        await update.effective_message.reply_text(
            'You have already created an account.',
            reply_to_message_id=update.message.id)
        return

    username = update.message.from_user.username
    db.create_user_account_query(username, update.message.chat_id)
    await update.effective_message.reply_text(
        f'Welcome {username}! Let me know of any deadlines you may have and I will help you keep track of them! '
        'Reminders for any deadlines will be sent a day before the due date at 8am.',
        reply_to_message_id=update.message.id)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    whisper = context.bot_data['whisper']
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    filename = f'{update.message.voice.file_id}.ogg'
    try:
        await voice_file.download_to_drive(filename)
        segments, _ = whisper.transcribe(filename)
        speech = ''.join(map(lambda x: x.text, segments)).strip()
        await update.message.reply_text(f"<i>Heard: \"{speech}\"</i>", parse_mode=constants.ParseMode.HTML,
                                        reply_to_message_id=update.message.id)
        await handle_query(update, context, speech)

    finally:
        if os.path.isfile(filename):
            os.remove(filename)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_query(update, context, update.message.text)


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE, user_msg: str):
    def create_deadline():
        deadline = gpt.create_deadline_query(messages)

        if not deadline.get('description'):
            response['text'] = 'Please provide a specific description for the deadline you want to create.'
            return

        if not deadline.get('due_date'):
            response['text'] = 'Please provide a specific due date for the deadline you want to create.'
            return

        if not deadline.get('confirmation'):
            response['text'] = f"Are you sure to create deadline '{deadline['description']}' due on {deadline['due_date']}?"
            return

        deadline_id = db.create_deadline_query(chat_id, deadline['description'], deadline['due_date'])
        db.create_reminders_query(
            deadline_id,
            datetime.datetime.combine(datetime.date.fromisoformat(deadline['due_date']), datetime.time(8)))
        response['text'] = (f"Your deadline for '{deadline['description']}' due on {deadline['due_date']} "
                            f"has been saved! You will be reminded a day before the due date at 8am.")

    def read_deadline():
        deadline_info = gpt.extract_fetch_info_query(user_msg)
        deadlines = db.fetch_deadlines_query(chat_id, deadline_info.get('start_date'), deadline_info.get('end_date'))

        if not deadlines:
            response['text'] = 'No deadlines matched your query.'
            return

        if not deadline_info.get('description'):
            response['text'] = f'```\n{create_table(deadlines)}```'
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        deadline_ids = gpt.filter_deadlines_query(deadlines, deadline_info['description']).get('ids')
        if not deadline_ids:
            response['text'] = 'No deadlines matched your query.'
            return

        filtered_deadlines = db.fetch_deadlines_query_by_ids(deadline_ids)
        response['text'] = f'```\n{create_table(filtered_deadlines)}```'
        response['parse_mode'] = constants.ParseMode.MARKDOWN_V2

    def update_deadline():
        deadlines = db.fetch_deadlines_query(chat_id)

        if not deadlines:
            response['text'] = 'There are no deadlines in the database to update.'
            return

        # Extract description of the deadline to be updated
        deadline_info = gpt.extract_update_description_query(messages)

        if not deadline_info.get('old_description'):
            response['text'] = 'Please provide a specific description of the deadline you want to update.'
            return

        deadline_id = gpt.filter_deadlines_query(deadlines, deadline_info['old_description']).get('ids')
        if len(deadline_id) != 1:
            # Check if description provided exists in the database
            response['text'] = ('No deadlines matched your query. Please provide a more specific description of the '
                                'deadline you want to update.')
            return

        deadline = db.fetch_deadlines_query_by_ids(deadline_id)[0]

        # Extract new description or new due date of the deadline
        update_info = gpt.extract_update_info_query(messages)

        if not update_info.get('new_description') and not update_info.get('new_due_date'):
            response['text'] = 'Please provide a new description or due date for the deadline you want to update.'
            return

        if not update_info.get('confirmation'):
            response['text'] = (f"Are you sure to update deadline '{deadline[1]}' due on {deadline[2]} "
                                f"to '{update_info['new_description'] or deadline[1]}' due on "
                                f"{update_info['new_due_date'] or deadline[2]}?")
            return

        db.update_deadline_query(deadline_id[0], update_info['new_description'], update_info['new_due_date'])
        response['text'] = f'Updated deadline.'

    def delete_deadline():
        deadlines = db.fetch_deadlines_query(chat_id)

        if not deadlines:
            response['text'] = 'There are no deadlines in the database to delete.'
            return

        delete_ids = gpt.extract_delete_ids_query(deadlines, messages)

        if not delete_ids.get('ids'):
            response['text'] = 'No deadlines matched your query.'
            return

        if not delete_ids.get('confirmation'):
            deadlines_to_delete = db.fetch_deadlines_query_by_ids(delete_ids['ids'])
            response['text'] = f'Are you sure to delete the following deadlines:```\n{create_table(deadlines_to_delete)}```'
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        deleted = db.delete_deadlines_query(delete_ids['ids'])
        response['text'] = f'Deleted {len(deleted)} deadlines.'

    def create_reminder():
        print('create_reminder')

    def read_reminder():
        print('read_reminder')

    def update_reminder():
        print('update_reminder')

    def delete_reminder():
        print('delete_reminder')

    def converse():
        response['text'] = gpt.converse_query(messages, update.message.from_user.username)

    db: PostgresDb = context.bot_data['db']
    gpt: GPT = context.bot_data['gpt']
    chat_id = update.message.chat_id
    if not db.account_exists_query(chat_id):
        await update.effective_message.reply_text(
            'You need to first create an account with the /start command.',
            reply_to_message_id=update.message.id)
        return

    history = db.fetch_latest_messages_query(chat_id)
    messages = [{'role': 'user' if msg[1] else 'assistant', 'content': msg[0]} for msg in history]
    messages.append({'role': 'user', 'content': user_msg})
    db.create_message_query(chat_id, user_msg, True)
    intention = gpt.intention_query(messages)
    response = {'text': '', 'parse_mode': None}

    if intention.get('target') == 'deadline':
        action_map = {
            Intention.CREATE: create_deadline,
            Intention.READ: read_deadline,
            Intention.UPDATE: update_deadline,
            Intention.DELETE: delete_deadline,
            Intention.NONE: converse
        }
        action_map.get(intention['action'], converse)()

    elif intention.get('target') == 'reminder':
        action_map = {
            Intention.CREATE: create_reminder,
            Intention.READ: read_reminder,
            Intention.UPDATE: update_reminder,
            Intention.DELETE: delete_reminder,
            Intention.NONE: converse
        }
        action_map.get(intention['action'], converse)()

    else:
        converse()

    if response['text']:
        db.create_message_query(chat_id, response['text'], False)
        await update.effective_message.reply_text(
            response['text'],
            parse_mode=response['parse_mode'],
            reply_to_message_id=update.message.id)


def create_table(deadlines) -> str:
    table = PrettyTable(['Deadline', 'Due Date'], align='l', hrules=ALL)
    table.max_width['Deadline'] = 20
    table.max_width['Due Date'] = 15
    table.add_rows([[deadline[1], deadline[2].strftime("%B %d, %Y")] for deadline in deadlines])

    return table.get_string()


# TODO: Add custom reminder times
async def hourly_reminder(context: CallbackContext):
    db: PostgresDb = context.bot_data['db']
    deadlines = db.fetch_reminders_query(datetime.datetime.now().replace(microsecond=0, second=0, minute=0))

    user_deadlines = defaultdict(list)
    for deadline in deadlines:
        user_deadlines[deadline[0]].append(deadline[1:])

    for chat_id, deadlines in user_deadlines.items():
        text = f'This is a reminder for the following deadlines:```\n{create_table(deadlines)}```'
        await context.bot.sendMessage(
            chat_id,
            text=text,
            parse_mode=constants.ParseMode.MARKDOWN_V2)
