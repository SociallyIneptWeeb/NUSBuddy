from enum import Enum
from os import getenv

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

PROMPT_DIR = 'prompts'


class Intention(Enum):
    CREATE = 1
    READ = 2
    UPDATE = 3
    DELETE = 4
    NONE = 5


class GPT:
    def __init__(self):
        self.llm = OpenAI(api_key=getenv('OPENAI_KEY'))

    def query(self, messages):
        completion = self.llm.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=messages
        )
        return completion.choices[0].message

    def query_intention(self, messages) -> Intention:
        prompt = open(f'{PROMPT_DIR}/intention.txt').read()
        messages.insert(0, {'role': 'system', 'message': prompt})
        response = self.query(messages).lower()
        if response.contains('create'):
            return Intention.CREATE
        elif response.contains('read'):
            return Intention.READ
        elif response.contains('update'):
            return Intention.UPDATE
        elif response.contains('delete'):
            return Intention.DELETE

        return Intention.NONE
