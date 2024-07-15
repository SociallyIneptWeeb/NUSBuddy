import datetime
import unittest
from os import getenv

from dotenv import load_dotenv

from database import PostgresDb
from gpt import GPT, Intention

load_dotenv()


class DbAccountTest(unittest.TestCase):
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
        cls.username = 'TestUsername'
        cls.chat_id = 1
        cls.db.create_user_account_query(cls.username, cls.chat_id)

    @classmethod
    def tearDownClass(cls):
        cls.db.delete_user_account_query(cls.chat_id)
        cls.db.close()
        del cls.db

    def test_message(self):
        created_messages = [('This is a test', True), ('This is another test message', False)]
        for msg in created_messages:
            self.db.create_message_query(self.chat_id, msg[0], msg[1])
        db_messages = self.db.fetch_latest_messages_query(self.chat_id)
        self.assertEqual(created_messages, db_messages)

    def test_deadline(self):
        created_deadlines = [
            ('Orbital Milestone Submission', datetime.date(2024, 6, 15)),
            ('CS2030S Lab 3 Submission', datetime.date(2024, 7, 10))]

        for deadline in created_deadlines:
            self.assertFalse(self.db.deadline_exists_query(self.chat_id, deadline[0]))
            self.db.create_deadline_query(self.chat_id, deadline[0], deadline[1])
            self.assertTrue(self.db.deadline_exists_query(self.chat_id, deadline[0]))

        db_deadlines = self.db.fetch_deadlines_query(self.chat_id)
        self.assertEqual(created_deadlines, [deadline[1:] for deadline in db_deadlines])
        self.assertEqual(db_deadlines, self.db.fetch_deadlines_query_by_ids([deadline[0] for deadline in db_deadlines]))

        updated_deadline = ('Project slides submission', datetime.date(2024, 8, 1))
        self.db.update_deadline_query(db_deadlines[0][0], updated_deadline[0], updated_deadline[1])
        self.assertEqual(updated_deadline, self.db.fetch_deadlines_query_by_ids([db_deadlines[0][0]])[0][1:])

        self.db.delete_deadlines_query([deadline[0] for deadline in db_deadlines])
        self.assertEqual(self.db.fetch_deadlines_query(self.chat_id), [])

    def test_reminder(self):
        created_deadlines = [
            ('Orbital Milestone Submission', datetime.date(2100, 6, 15)),
            ('CS2030S Lab 3 Submission', datetime.date(2100, 7, 10))]

        for deadline in created_deadlines:
            self.db.create_deadline_query(self.chat_id, deadline[0], deadline[1])

        db_deadlines = self.db.fetch_deadlines_query(self.chat_id)
        reminder_datetime = datetime.datetime(2100, 6, 14, 0, 0, 0)
        self.db.create_reminders_query(db_deadlines[0][0], reminder_datetime)
        self.assertEqual(created_deadlines[0], self.db.fetch_reminders_query(reminder_datetime)[0][2:])
        self.assertEqual(1, len(self.db.fetch_reminders_query_by_deadline_ids([db_deadlines[0][0]])))

        db_reminder = self.db.fetch_reminder_query(db_deadlines[0][0], reminder_datetime)
        self.assertEqual(reminder_datetime, db_reminder[2])

        new_reminder_datetime = datetime.datetime(2100, 6, 13, 11, 20, 0)
        self.db.update_reminder_query(db_reminder[0], new_reminder_datetime)
        self.assertEqual(new_reminder_datetime, self.db.fetch_reminder_query(db_deadlines[0][0], new_reminder_datetime)[2])

        self.db.delete_reminder_query(db_reminder[0])
        self.assertIsNone(self.db.fetch_reminder_query(db_deadlines[0][0], new_reminder_datetime))


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
