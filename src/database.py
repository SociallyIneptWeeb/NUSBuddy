import psycopg2
from psycopg2 import sql


class PostgresDb:
    def __init__(self, db, host, port, user, password):
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

    def query(self, query, vals):
        return self.cursor.execute(query, vals)

    def account_exists_query(self, chat_id):
        query = sql.SQL('SELECT 1 FROM {table} WHERE {field} = %s').format(
            table=sql.Identifier('users'),
            field=sql.Identifier('chat_id')
        )
        self.query(query, (chat_id,))
        return self.cursor.fetchone() is not None

    def create_user_account_query(self, username, chat_id):
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}) VALUES(%s, %s)').format(
            table=sql.Identifier('users'),
            field1=sql.Identifier('username'),
            field2=sql.Identifier('chat_id')
        )
        self.query(query, (username, chat_id))
        self.conn.commit()

    def get_userid_from_chatid(self, chat_id):
        query = sql.SQL('SELECT {field1} FROM {table} WHERE {field2} = %s').format(
            table=sql.Identifier('users'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('chat_id')
        )
        self.query(query, (chat_id,))
        return self.cursor.fetchone()[0]

    def fetch_latest_messages_query(self, chat_id):
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('SELECT {field1}, {field2} FROM {table} WHERE {field3} = %s '
                        'ORDER BY {field4} DESC LIMIT 3').format(
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

    def create_message_query(self, chat_id, text, from_user):
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}, {field3}) VALUES(%s, %s, %s)').format(
            table=sql.Identifier('messages'),
            field1=sql.Identifier('user_id'),
            field2=sql.Identifier('text'),
            field3=sql.Identifier('fromUser')
        )
        self.query(query, (user_id, text, from_user))
        self.conn.commit()

    def create_deadline_query(self, chat_id, description, due_date):
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('INSERT INTO {table} ({field1}, {field2}, {field3}) VALUES(%s, %s, %s)').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('user_id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date')
        )
        self.query(query, (user_id, description, due_date))
        self.conn.commit()

    def fetch_deadlines_query(self, chat_id, start_date, end_date):
        user_id = self.get_userid_from_chatid(chat_id)
        query = sql.SQL('SELECT {field1}, {field2}, {field3} FROM {table} '
                        'WHERE {field4} = %s AND ({field3} >= %s OR {field3} <= %s)').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date'),
            field4=sql.Identifier('user_id')
        )
        self.query(query, (user_id, start_date if start_date else '1900-1-1', end_date if end_date else '2100-12-30'))
        return self.cursor.fetchall()

    def delete_deadlines_query(self, ids):
        query = sql.SQL('DELETE FROM {table} WHERE {field1} = ANY(%s) RETURNING {field2}, {field3}').format(
            table=sql.Identifier('deadlines'),
            field1=sql.Identifier('id'),
            field2=sql.Identifier('description'),
            field3=sql.Identifier('due_date')
        )
        self.query(query, (ids,))
        return self.cursor.fetchall()
