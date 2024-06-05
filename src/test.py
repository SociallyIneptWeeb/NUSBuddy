import unittest
from gpt import GPT, Intention


class GPTQueryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gpt = GPT()

    @classmethod
    def tearDownClass(cls):
        del cls.gpt

    def test_intention(self):
        tests = [
            ([{'role': 'user', 'content': 'I have a project submission due soon, can you help me remember that?'}], Intention.CREATE),
            ([{'role': 'user', 'content': 'When is my orbital submission due?'}], Intention.READ),
            ([{'role': 'user', 'content': 'What deadlines do I have next week?'}], Intention.READ),
            ([{'role': 'user', 'content': 'Can you help me change the due date for one of my deadlines?'}], Intention.UPDATE),
            ([{'role': 'user', 'content': 'I have completed my submission for my orbital milestone. Can you remove it?'}], Intention.DELETE),
            ([{'role': 'user', 'content': 'Do you know what time it is?'}], Intention.NONE),
        ]
        for test in tests:
            with self.subTest(messages=test[0], intent=test[1]):
                self.assertEqual(self.gpt.intention_query(test[0]), test[1])


if __name__ == '__main__':
    unittest.main()
