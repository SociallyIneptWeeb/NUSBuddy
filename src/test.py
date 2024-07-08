import unittest
from os import getenv

from dotenv import load_dotenv

from database import PostgresDb
from gpt import GPT, Intention

load_dotenv()


class DbQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = PostgresDb(
            getenv('POSTGRES_DB'),
            getenv('POSTGRES_HOST'),
            int(getenv('POSTGRES_PORT')),
            getenv('POSTGRES_USER'),
            getenv('POSTGRES_PASSWORD')
        )
        cls.db.connect()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        del cls.db

    def test_account(self):
        username = 'TestUsername'
        chat_id = 1
        self.db.create_user_account_query(username, chat_id)
        self.assertTrue(self.db.account_exists_query(chat_id))
        self.db.delete_user_account_query(chat_id)
        self.assertFalse(self.db.account_exists_query(chat_id))


class GPTQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gpt = GPT()

    @classmethod
    def tearDownClass(cls):
        del cls.gpt

    def test_intention(self):
        tests = [
            ([{'role': 'user', 'content': 'I have a project submission due soon, can you help me create a deadline for that?'}], {'action': Intention.CREATE, 'target': 'deadline'}),
            ([{'role': 'user', 'content': 'When is my orbital submission due?'}], {'action': Intention.READ, 'target': 'deadline'}),
            ([{'role': 'user', 'content': 'What deadlines do I have next week?'}], {'action': Intention.READ, 'target': 'deadline'}),
            ([{'role': 'user', 'content': 'Can you help me change the due date for one of my deadlines?'}], {'action': Intention.UPDATE, 'target': 'deadline'}),
            ([{'role': 'user', 'content': 'I have completed my submission for my orbital milestone. Can you remove it?'}], {'action': Intention.DELETE, 'target': 'deadline'}),
            ([{'role': 'user', 'content': 'Can you create a reminder for my submission?'}], {'action': Intention.CREATE, 'target': 'reminder'}),
            ([{'role': 'user', 'content': 'When is the reminder for my orbital submission?'}], {'action': Intention.READ, 'target': 'reminder'}),
            ([{'role': 'user', 'content': 'Could you postpone my reminder to next Sunday?'}], {'action': Intention.UPDATE, 'target': 'reminder'}),
            ([{'role': 'user', 'content': 'I want to remove all of my reminders.'}], {'action': Intention.DELETE, 'target': 'reminder'}),
        ]
        for test in tests:
            with self.subTest(messages=test[0], intent=test[1]):
                self.assertEqual(self.gpt.intention_query(test[0]), test[1])


if __name__ == '__main__':
    unittest.main()
