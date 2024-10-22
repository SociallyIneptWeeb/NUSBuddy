from typing import Optional

import psycopg2
from psycopg2 import sql
from datetime import datetime, date


class PostgresDb:
    def __init__(self, db: str, host: str, port: int, user: str, password: str):
        self.db = db
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = psycopg2.connect(
            dbname=self.db,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password)
        self.cursor = self.conn.cursor()

    def close(self):
        self.cursor.close()
        self.conn.close()

    def query(self, query: sql.Composed, vals: tuple):
        self.cursor.execute(query, vals)

    def account_exists_query(self, chat_id: int) -> bool:
        query = sql.SQL('SELECT 1 FROM {table} WHERE {field} = %s').format(
            table=sql.Identifier('users'),
            field=sql.Identifier('chat_id')
        )
        self.query(query, (chat_id,))
        return self.cursor.fetchone() is not None

    def delete_user_account_query(self, chat_id: int):
        query = sql.SQL('DELETE FROM {table} WHERE {field} = %s').format(
            table=sql.Identifier('users'),
            field=sql.Identifier('chat_id')
        )
        self.query(query, (chat_id,))
        self.conn.commit()

    def create_user_account_query(self, username: str, chat_id: int):
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}) VALUES(%s, %s)').format(
            table=sql.Identifier('users'),
            field1=sql.Identifier('username'),
            field2=sql.Identifier('chat_id')
        )
        self.query(query, (username, chat_id))
        self.conn.commit()

    def get_userid_from_chatid(self, chat_id: int) -> int:
        query = sql.SQL('SELECT {field1} FROM {table} WHERE {field2} = %s').format(
            table=sql.Identifier('users'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('chat_id')
        )
        self.query(query, (chat_id,))
        return self.cursor.fetchone()[0]

    def fetch_latest_messages_query(self, chat_id: int) -> list[tuple[str, bool]]:
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('SELECT {field1}, {field2} FROM {table} WHERE {field3} = %s '
                        'ORDER BY {field4} DESC LIMIT 10').format(
            table=sql.Identifier('messages'),
            field1=sql.Identifier('text'),
            field2=sql.Identifier('fromUser'),
            field3=sql.Identifier('user_id'),
            field4=sql.Identifier('created_at')
        )
        self.query(query, (user_id,))
        messages = self.cursor.fetchall()
        messages.reverse()
        return messages

    def create_message_query(self, chat_id: int, text: str, from_user: bool):
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}, {field3}) VALUES(%s, %s, %s)').format(
            table=sql.Identifier('messages'),
            field1=sql.Identifier('user_id'),
            field2=sql.Identifier('text'),
            field3=sql.Identifier('fromUser')
        )
        self.query(query, (user_id, text, from_user))
        self.conn.commit()

    def create_deadline_query(self, chat_id: int, description: str, due_date: date) -> int:
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}, {field3}) VALUES(%s, %s, %s) RETURNING {field4}').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('user_id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date'),
            field4=sql.Identifier('id')
        )
        self.query(query, (user_id, description, due_date))
        self.conn.commit()
        return self.cursor.fetchone()[0]

    def deadline_exists_query(self, chat_id: int, description: str) -> bool:
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('SELECT 1 FROM {table} WHERE {field1} = %s AND {field2} = %s').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('user_id'),
            field2=sql.Identifier('description')
        )
        self.query(query, (user_id, description))
        return self.cursor.fetchone() is not None

    def fetch_deadlines_query(
            self,
            chat_id: int,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None) -> list[tuple[int, str, date]]:
        start_date = start_date or '1900-1-1'
        end_date = end_date or '2100-12-30'
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('SELECT {field1}, {field2}, {field3} FROM {table} '
                        'WHERE {field4} = %s AND ({field3} >= %s AND {field3} <= %s) '
                        'ORDER BY {field3} ASC').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date'),
            field4=sql.Identifier('user_id')
        )
        self.query(query, (user_id, start_date, end_date))
        return self.cursor.fetchall()

    def fetch_deadlines_query_by_ids(self, ids: list[int]) -> list[tuple[int, str, date]]:
        query = sql.SQL('SELECT {field1}, {field2}, {field3} FROM {table} '
                        'WHERE {field1} = ANY(%s) ORDER BY {field3} ASC').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date'),
        )
        self.query(query, (ids,))
        return self.cursor.fetchall()

    def fetch_reminders_query(self, timestamp: datetime) -> list[tuple[int, int, str, date]]:
        query = sql.SQL('SELECT {table1}.{field1}, {table2}.{field2}, {table2}.{field3}, {table2}.{field4} FROM {table1} '
                        'INNER JOIN {table2} ON {table1}.{field2} = {table2}.{field5} '
                        'INNER JOIN {table3} ON {table2}.{field2} = {table3}.{field6} '
                        'WHERE {table3}.{field7} = %s').format(
            table1=sql.Identifier('users'),
            table2=sql.Identifier('deadlines'),
            table3=sql.Identifier('reminders'),
            field1=sql.Identifier('chat_id'),
            field2=sql.Identifier('id'),
            field3=sql.Identifier('description'),
            field4=sql.Identifier('due_date'),
            field5=sql.Identifier('user_id'),
            field6=sql.Identifier('deadline_id'),
            field7=sql.Identifier('reminder_time')
        )

        self.query(query, (timestamp,))
        return self.cursor.fetchall()

    def delete_deadlines_query(self, ids: list[int]) -> list[tuple[str, date]]:
        query = sql.SQL('DELETE FROM {table} WHERE {field1} = ANY(%s) RETURNING {field2}, {field3}').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date')
        )
        self.query(query, (ids,))
        return self.cursor.fetchall()

    def update_deadline_query(self, id: int, description: Optional[str], due_date: Optional[date]):
        query = sql.SQL('UPDATE {table} SET {field1} = COALESCE(%s, {field1}), {field2} = COALESCE(%s, {field2}) '
                        'WHERE {field3} = %s').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('description'),
            field2=sql.Identifier('due_date'),
            field3=sql.Identifier('id')
        )
        self.query(query, (description, due_date, id))
        self.conn.commit()

    def create_reminders_query(self, deadline_id: int, reminder_time: datetime):
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}) VALUES(%s, %s)').format(
            table=sql.Identifier('reminders'),
            field1=sql.Identifier('deadline_id'),
            field2=sql.Identifier('reminder_time'),
        )
        self.query(query, (deadline_id, reminder_time))
        self.conn.commit()

    def fetch_reminders_query_by_deadline_ids(self, ids: list[int]) -> list[tuple[str, list[datetime]]]:
        query = sql.SQL('SELECT {table1}.{field1}, ARRAY_AGG({table2}.{field2} ORDER BY {table2}.{field2}) FROM {table1} '
                        'INNER JOIN {table2} ON {table1}.{field3} = {table2}.{field4} '
                        'WHERE {field2} >= %s AND {field4} = ANY(%s) GROUP BY {table1}.{field1}').format(
            table1=sql.Identifier('deadlines'),
            table2=sql.Identifier('reminders'),
            field1=sql.Identifier('description'),
            field2=sql.Identifier('reminder_time'),
            field3=sql.Identifier('id'),
            field4=sql.Identifier('deadline_id')
        )
        self.query(query, (datetime.now(), ids,))
        return self.cursor.fetchall()

    def fetch_reminder_query(self, deadline_id: int, reminder_time: datetime) -> tuple[int, str, datetime]:
        query = sql.SQL('SELECT * FROM {table} WHERE {field1} = %s AND {field2} = %s').format(
            table=sql.Identifier('reminders'),
            field1=sql.Identifier('deadline_id'),
            field2=sql.Identifier('reminder_time')
        )
        self.query(query, (deadline_id, reminder_time))
        return self.cursor.fetchone()

    def update_reminder_query(self, reminder_id: int, reminder_time: datetime):
        query = sql.SQL('UPDATE {table} SET {field1} = %s WHERE {field2} = %s').format(
            table=sql.Identifier('reminders'),
            field1=sql.Identifier('reminder_time'),
            field2=sql.Identifier('id')
        )
        self.query(query, (reminder_time, reminder_id))
        self.conn.commit()

    def delete_reminder_query(self, reminder_id: int):
        query = sql.SQL('DELETE FROM {table} WHERE {field} = %s').format(
            table=sql.Identifier('reminders'),
            field=sql.Identifier('id')
        )
        self.query(query, (reminder_id,))
        self.conn.commit()