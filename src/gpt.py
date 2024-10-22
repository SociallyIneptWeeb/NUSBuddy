import json
from datetime import datetime, date
from enum import Enum
from os import getenv
from typing import Optional, TypedDict

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat.completion_create_params import ResponseFormat

load_dotenv()

PROMPT_DIR = 'prompts'


class Intention(Enum):
    CREATE = 1
    READ = 2
    UPDATE = 3
    DELETE = 4
    NONE = 5


class IntentionType(TypedDict):
    action: Intention
    target: str


class GPTMessageType(TypedDict):
    role: str
    content: str


class DeadlineCreationType(TypedDict):
    description: str
    due_date: str
    confirmation: bool


class FetchInfoType(TypedDict):
    description: str
    start_date: str
    end_date: str


class DeleteIdsType(TypedDict):
    ids: list[int]
    confirmation: bool


class FilterDeadlinesType(TypedDict):
    ids: list[int]


class DeadlineDescriptionType(TypedDict):
    old_deadline_description: str


class UpdateInfoType(TypedDict):
    new_description: str
    new_due_date: str
    confirmation: bool


class ReminderCreationType(TypedDict):
    deadline_description: str
    reminder_time: str
    confirmation: bool


class ReminderUpdateType(TypedDict):
    old_reminder_time: str
    new_reminder_time: str
    confirmation: bool


class ReminderDeleteType(TypedDict):
    reminder_time: str
    confirmation: bool


class GPT:
    def __init__(self):
        self.llm = OpenAI(api_key=getenv('OPENAI_KEY'))

    def query(self, messages: list, json: Optional[bool] = False) -> str:
        completion = self.llm.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            response_format=ResponseFormat(type='json_object') if json else ResponseFormat(type='text')
        )
        return completion.choices[0].message.content

    def intention_query(self, messages: list[GPTMessageType]) -> IntentionType:
        with open(f'{PROMPT_DIR}/intention.txt') as infile:
            prompt = infile.read()

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        response = json.loads(self.query(messages, json=True))
        response['action'] = Intention[response.get('action', 'NONE').upper()]

        return response

    def response_query(self, intention: IntentionType, message: str) -> str:
        with open(f'{PROMPT_DIR}/response.txt') as infile:
            prompt = infile.read() % {'intention': intention['action'].name + ' ' + intention['target']}

        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}]
        return self.query(messages)

    def converse_query(self, messages: list[GPTMessageType], username: str) -> str:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/conversation.txt') as infile:
            prompt = infile.read().format(now=now, username=username)

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return self.query(messages)

    def create_deadline_query(self, messages: list[GPTMessageType]) -> DeadlineCreationType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/create_deadline.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))

    def extract_fetch_info_query(self, message: str) -> FetchInfoType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_fetch_info.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}]
        return json.loads(self.query(messages, json=True))

    def extract_delete_ids_query(self, deadlines: list[tuple[int, str, date]], messages: list[GPTMessageType]) -> DeleteIdsType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_delete_ids.txt') as infile:
            prompt = infile.read() % {'now': now, 'deadlines': deadlines}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))

    def filter_deadlines_query(self, deadlines: list[tuple[int, str, date]], description: str) -> FilterDeadlinesType:
        with open(f'{PROMPT_DIR}/filter_deadlines.txt') as infile:
            prompt = infile.read() % {'deadlines': deadlines}

        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': description}]
        return json.loads(self.query(messages, json=True))

    def extract_deadline_description_query(self, messages: list[GPTMessageType]) -> DeadlineDescriptionType:
        with open(f'{PROMPT_DIR}/extract_deadline_description.txt') as infile:
            prompt = infile.read()

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))

    def extract_update_info_query(self, messages: list[GPTMessageType]) -> UpdateInfoType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_update_info.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))

    def create_reminder_query(self, messages: list[GPTMessageType]) -> ReminderCreationType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/create_reminder.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))

    def extract_update_reminder_query(self, messages: list[GPTMessageType]) -> ReminderUpdateType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_update_reminder.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))

    def extract_delete_reminder_query(self, messages: list[GPTMessageType]) -> ReminderDeleteType:
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_delete_reminder.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        return json.loads(self.query(messages, json=True))
