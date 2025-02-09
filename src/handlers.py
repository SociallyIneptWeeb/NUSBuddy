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

        due_date = datetime.datetime.fromisoformat(deadline['due_date']).date()

        if not deadline.get('confirmation'):
            response['text'] = (f'Are you sure to create deadline '
                                f'```\n{create_deadline_table([(-1, deadline["description"], due_date)])}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        if db.deadline_exists_query(chat_id, deadline['description']):
            response['text'] = 'Cannot create deadline as deadline already exists.'
            return

        deadline_id = db.create_deadline_query(chat_id, deadline['description'], due_date)
        reminder_timestamp = datetime.datetime.combine(due_date, datetime.time(8)) - datetime.timedelta(days=1)
        response['text'] = 'Your deadline has been saved.'

        if reminder_timestamp > datetime.datetime.now():
            db.create_reminders_query(deadline_id, reminder_timestamp)
            response['text'] += f' You will be reminded at {reminder_timestamp.strftime("%a %d %b %Y, %H:%M")}'

    def read_deadline():
        deadline_info = gpt.extract_fetch_info_query(user_msg)
        deadlines = db.fetch_deadlines_query(chat_id, deadline_info.get('start_date'), deadline_info.get('end_date'))

        if not deadlines:
            if deadline_info.get('start_date') or deadline_info.get('end_date'):
                response['text'] = 'No deadlines matched your query.'
            else:
                response['text'] = 'No deadlines in the database.'
            return

        if not deadline_info.get('description'):
            response['text'] = f'```\n{create_deadline_table(deadlines)}```'
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        deadline_ids = gpt.filter_deadlines_query(deadlines, deadline_info['description']).get('ids', [])
        if not deadline_ids:
            response['text'] = 'No deadlines matched your query.'
            return

        filtered_deadlines = db.fetch_deadlines_query_by_ids(deadline_ids)
        response['text'] = f'```\n{create_deadline_table(filtered_deadlines)}```'
        response['parse_mode'] = constants.ParseMode.MARKDOWN_V2

    def update_deadline():
        deadline = extract_deadline()
        if not deadline:
            return

        # Extract new description or new due date of the deadline
        update_info = gpt.extract_update_info_query(messages)

        if not update_info.get('new_description') and not update_info.get('new_due_date'):
            response['text'] = 'Please provide a new description or due date for the deadline you want to update.'
            return

        new_desc = update_info.get('new_description') or deadline[1]
        if update_info.get('new_due_date'):
            new_date = datetime.datetime.fromisoformat(update_info['new_due_date']).date()
        else:
            new_date = deadline[2]

        if not update_info.get('confirmation'):
            response['text'] = (f'Are you sure to update deadline:```\n{create_deadline_table([deadline])}``` to '
                                f'```\n{create_deadline_table([(deadline[0], new_desc, new_date)])}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        if new_desc != deadline[1] and db.deadline_exists_query(chat_id, new_desc):
            response['text'] = 'Cannot update deadline as new deadline description already exists.'
            return

        db.update_deadline_query(deadline[0], new_desc, new_date)
        response['text'] = 'Updated deadline.'

        # Update old reminder for deadline at 8am to new deadline if due date has changed
        if new_date != deadline[2]:
            old_reminder = db.fetch_reminder_query(
                deadline[0],
                datetime.datetime.combine(deadline[2], datetime.time(8)) - datetime.timedelta(days=1))
            new_reminder_time = datetime.datetime.combine(new_date, datetime.time(8)) - datetime.timedelta(days=1)

            if new_reminder_time > datetime.datetime.now():
                if old_reminder:
                    db.update_reminder_query(old_reminder[0], new_reminder_time)
                    response['text'] += f' Reminder has been updated to {new_reminder_time.strftime("%a %d %b %Y, %H:%M")}.'
                else:
                    db.create_reminders_query(deadline[0], new_reminder_time)
                    response['text'] += f' Reminder has been created on {new_reminder_time.strftime("%a %d %b %Y, %H:%M")}.'
            elif old_reminder:
                db.delete_reminder_query(old_reminder[0])

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
            response['text'] = (f'Are you sure to delete the following deadlines:'
                                f'```\n{create_deadline_table(deadlines_to_delete)}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        deleted = db.delete_deadlines_query(delete_ids['ids'])
        response['text'] = f'Deleted {len(deleted)} deadlines.'

    def create_reminder():
        deadline = extract_deadline()
        if not deadline:
            return

        reminder = gpt.create_reminder_query(messages)

        if not reminder.get('reminder_time'):
            response['text'] = (f'Please provide a specific date and time you want to be reminded of '
                                f'```\n{create_deadline_table([deadline])}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        reminder_time = datetime.datetime.fromisoformat(reminder['reminder_time'])
        if reminder_time < datetime.datetime.now():
            response['text'] = 'Cannot create reminder in the past.'
            return

        if not reminder.get('confirmation'):
            response['text'] = (f'Are you sure you want to be reminded at {reminder_time.strftime("%a %d %b %Y, %H:%M")} '
                                f'for ```\n{create_deadline_table([deadline])}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        db.create_reminders_query(deadline[0], reminder_time)
        response['text'] = 'Your reminder has been created.'

    def read_reminder():
        deadline_info = gpt.extract_fetch_info_query(user_msg)
        deadlines = db.fetch_deadlines_query(chat_id, deadline_info.get('start_date'), deadline_info.get('end_date'))

        if not deadlines:
            if deadline_info.get('start_date') or deadline_info.get('end_date'):
                response['text'] = 'No deadlines matched your query.'
            else:
                response['text'] = 'No deadlines in the database.'
            return

        if not deadline_info.get('description'):
            reminders = db.fetch_reminders_query_by_deadline_ids([deadline[0] for deadline in deadlines])
            response['text'] = f'```\n{create_reminder_table(reminders)}```'
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        deadline_ids = gpt.filter_deadlines_query(deadlines, deadline_info['description']).get('ids', [])
        if not deadline_ids:
            response['text'] = 'No deadlines matched your query.'
            return

        reminders = db.fetch_reminders_query_by_deadline_ids(deadline_ids)
        response['text'] = f'```\n{create_reminder_table(reminders)}```'
        response['parse_mode'] = constants.ParseMode.MARKDOWN_V2

    def update_reminder():
        deadline = extract_deadline()
        if not deadline:
            return

        # Extract old and new reminder times
        update_info = gpt.extract_update_reminder_query(messages)

        if not update_info.get('old_reminder_time'):
            reminders = db.fetch_reminders_query_by_deadline_ids([deadline[0]])
            response['text'] = (f'Please provide the specific reminder time you want to update from the following '
                                f'reminders:```\n{create_reminder_table(reminders)}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        now = datetime.datetime.now()
        old_reminder_time = datetime.datetime.fromisoformat(update_info['old_reminder_time'])
        if old_reminder_time < now:
            response['text'] = 'Cannot update reminder as old reminder time is in the past.'
            return

        reminder = db.fetch_reminder_query(deadline[0], old_reminder_time)
        if not reminder:
            response['text'] = 'No reminders matched your query.'
            return

        if not update_info.get('new_reminder_time'):
            response['text'] = 'Please provide a new reminder time for the reminder you want to update.'
            return

        new_reminder_time = datetime.datetime.fromisoformat(update_info['new_reminder_time'])
        if new_reminder_time < now:
            response['text'] = 'Cannot update reminder as new reminder time is in the past.'
            return

        if not update_info.get('confirmation'):
            response['text'] = (f'Are you sure to update reminder:```\n{create_reminder_table([(deadline[1], [reminder[2]])])}``` to '
                                f'```\n{create_reminder_table([(deadline[1], [new_reminder_time])])}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        if db.fetch_reminder_query(deadline[0], new_reminder_time):
            response['text'] = 'Cannot update reminder as new reminder already exists.'
            return

        db.update_reminder_query(reminder[0], new_reminder_time)
        response['text'] = 'Updated reminder.'

    def delete_reminder():
        deadline = extract_deadline()
        if not deadline:
            return

        delete_info = gpt.extract_delete_reminder_query(messages)

        if not delete_info.get('reminder_time'):
            response['text'] = 'Please provide a reminder time for the reminder you want to delete.'
            return

        reminder_time = datetime.datetime.fromisoformat(delete_info['reminder_time'])
        if reminder_time < datetime.datetime.now():
            response['text'] = 'Cannot delete reminder from the past.'
            return

        if not delete_info.get('confirmation'):
            response['text'] = (f'Are you sure to delete reminder:'
                                f'```\n{create_reminder_table([(deadline[1], [reminder_time])])}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        reminder = db.fetch_reminder_query(deadline[0], reminder_time)
        if not reminder:
            reminders = db.fetch_reminders_query_by_deadline_ids([deadline[0]])
            response['text'] = (f'Cannot delete reminder as reminder does not exist\. Please provide the specific '
                                f'reminder time you want to delete from the following reminders:'
                                f'```\n{create_reminder_table(reminders)}```')
            response['parse_mode'] = constants.ParseMode.MARKDOWN_V2
            return

        db.delete_reminder_query(reminder[0])
        response['text'] = 'Deleted reminder.'

    def converse():
        response['text'] = gpt.converse_query(messages, update.message.from_user.username)

    def extract_deadline():
        deadlines = db.fetch_deadlines_query(chat_id)

        if not deadlines:
            response['text'] = 'There are no deadlines in the database to update.'
            return

        deadline_info = gpt.extract_deadline_description_query(messages)

        if not deadline_info.get('old_deadline_description'):
            response['text'] = 'Please provide a specific description of the deadline you want to update.'
            return

        deadline_ids = gpt.filter_deadlines_query(deadlines, deadline_info['old_deadline_description']).get('ids', [])

        # Check if description provided exists in the database
        if not deadline_ids:
            response['text'] = 'No deadlines matched your query.'
            return

        if len(deadline_ids) > 1:
            response['text'] = ('Multiple deadlines matched your query. Please provide a more specific description of '
                                'the deadline you want to update.')
            return

        return db.fetch_deadlines_query_by_ids(deadline_ids)[0]

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
    response = {'text': '', 'parse_mode': ''}

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
        if not response['parse_mode']:
            response['text'] = gpt.response_query(intention, response['text'])

        db.create_message_query(chat_id, response['text'], False)
        await update.effective_message.reply_text(
            response['text'],
            parse_mode=response['parse_mode'] or None,
            reply_to_message_id=update.message.id)


def create_deadline_table(deadlines: list[tuple[int, str, datetime.date]]) -> str:
    table = PrettyTable(['Deadline', 'Due Date'], align='l', hrules=ALL)
    table.max_width['Deadline'] = 20
    table.max_width['Due Date'] = 15
    table.add_rows([[deadline[1], deadline[2].strftime("%a %d %b %Y")] for deadline in deadlines])

    return table.get_string()


def create_reminder_table(reminders: list[tuple[str, list[datetime]]]) -> str:
    table = PrettyTable(['Deadline', 'Upcoming Reminders'], align='l', hrules=ALL)
    table.max_width['Deadline'] = 15
    table.max_width['Upcoming Reminders'] = 20
    table.add_rows([[reminder[0], '\n\n'.join([dt.strftime("%a %d %b %Y, %H:%M") for dt in reminder[1]])]
                    for reminder in reminders])

    return table.get_string()


async def reminder_callback(context: CallbackContext):
    db: PostgresDb = context.bot_data['db']
    deadlines = db.fetch_reminders_query(datetime.datetime.now().replace(microsecond=0, second=0))

    user_deadlines = defaultdict(list)
    for deadline in deadlines:
        user_deadlines[deadline[0]].append(deadline[1:])

    for chat_id, deadlines in user_deadlines.items():
        text = f'This is a reminder for the following deadlines:```\n{create_deadline_table(deadlines)}```'
        await context.bot.sendMessage(
            chat_id,
            text=text,
            parse_mode=constants.ParseMode.MARKDOWN_V2)
