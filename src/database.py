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

    def username_taken_query(self, username):
        query = sql.SQL("SELECT 1 FROM {table} WHERE {field} = %s").format(
            table=sql.Identifier('users'),
            field=sql.Identifier('username')
        )
        self.query(query, (username,))
        return self.cursor.fetchone() is not None

    def account_exists_query(self, chat_id):
        query = sql.SQL("SELECT 1 FROM {table} WHERE {field} = %s").format(
            table=sql.Identifier('users'),
            field=sql.Identifier('chat_id')
        )
        self.query(query, (chat_id,))
        return self.cursor.fetchone() is not None

    def create_user_account_query(self, username, chat_id):
        query = sql.SQL("INSERT INTO {table} ({field1}, {field2}) VALUES(%s, %s)").format(
            table=sql.Identifier('users'),
            field1=sql.Identifier('username'),
            field2=sql.Identifier('chat_id')
        )
        self.query(query, (username, chat_id))
        self.conn.commit()
