from datetime import datetime
from enum import Enum
from os import getenv

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat.completion_create_params import ResponseFormat

load_dotenv()

PROMPT_DIR = 'prompts'
JSON_RESPONSE = ResponseFormat(type='json_object')
TEXT_RESPONSE = ResponseFormat(type='text')


class Intention(Enum):
    CREATE = 1
    READ = 2
    UPDATE = 3
    DELETE = 4
    NONE = 5


class GPT:
    def __init__(self):
        self.llm = OpenAI(api_key=getenv('OPENAI_KEY'))

    def query(self, messages, json=False):
        completion = self.llm.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=messages,
            response_format=JSON_RESPONSE if json else TEXT_RESPONSE
        )
        return completion.choices[0].message.content

    def intention_query(self, messages) -> Intention:
        prompt = open(f'{PROMPT_DIR}/intention.txt').read()
        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        response = self.query(messages).lower()
        if 'create' in response:
            return Intention.CREATE
        elif 'read' in response:
            return Intention.READ
        elif 'update' in response:
            return Intention.UPDATE
        elif 'delete' in response:
            return Intention.DELETE

        return Intention.NONE

    def converse_query(self, messages, username):
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        prompt = open(f'{PROMPT_DIR}/conversation.txt').read().format(now=now, username=username)
        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        response = self.query(messages)
        return response

    def create_deadline_query(self, message):
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        prompt = open(f'{PROMPT_DIR}/create_deadline.txt').read() % {'now': now}
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}]
        response = self.query(messages, json=True)
        return response

    def fetch_deadline_query(self, message):
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        prompt = open(f'{PROMPT_DIR}/fetch_deadline.txt').read() % {'now': now}
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}]
        response = self.query(messages, json=True)
        return response
