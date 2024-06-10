from datetime import datetime
from enum import Enum
from os import getenv

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

# TODO: Factorise into subclasses
class GPT:
    def __init__(self):
        self.llm = OpenAI(api_key=getenv('OPENAI_KEY'))

    def query(self, messages, json=False):
        completion = self.llm.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=messages,
            response_format=ResponseFormat(type='json_object') if json else ResponseFormat(type='text')
        )
        return completion.choices[0].message.content

    def intention_query(self, messages) -> Intention:
        with open(f'{PROMPT_DIR}/intention.txt') as infile:
            prompt = infile.read()

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
        with open(f'{PROMPT_DIR}/conversation.txt') as infile:
            prompt = infile.read().format(now=now, username=username)

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        response = self.query(messages)
        return response

    def create_deadline_query(self, messages):
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/create_deadline.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        response = self.query(messages, json=True)
        return response

    def extract_fetch_info_query(self, message):
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_fetch_info.txt') as infile:
            prompt = infile.read() % {'now': now}

        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': message}]
        response = self.query(messages, json=True)
        return response

    def extract_delete_ids_query(self, deadlines, messages):
        now = datetime.now().strftime('%I:%M%p on %B %d, %Y')
        with open(f'{PROMPT_DIR}/extract_delete_ids.txt') as infile:
            prompt = infile.read() % {'now': now, 'deadlines': deadlines}

        messages = messages.copy()
        messages.insert(0, {'role': 'system', 'content': prompt})
        response = self.query(messages, json=True)
        return response

    def filter_deadlines_query(self, deadlines, description):
        with open(f'{PROMPT_DIR}/filter_deadlines.txt') as infile:
            prompt = infile.read().format(deadlines=deadlines)
            
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': description}]
        response = self.query(messages)
        return response
