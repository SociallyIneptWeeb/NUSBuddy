CREATE TABLE "users" (
  "id" SERIAL PRIMARY KEY,
  "username" varchar,
  "chat_id" integer
);

CREATE TABLE "deadlines" (
  "id" SERIAL PRIMARY KEY,
  "user_id" integer,
  "description" text,
  "due_date" date
);

CREATE TABLE "reminders" (
  "id" SERIAL PRIMARY KEY,
  "deadline_id" integer,
  "reminder_time" timestamp
);

CREATE TABLE "messages" (
  "id" SERIAL PRIMARY KEY,
  "user_id" integer,
  "text" text,
  "fromUser" boolean,
  "created_at" timestamp DEFAULT (now())
);

ALTER TABLE "messages" ADD CONSTRAINT fk_messages_users FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;

ALTER TABLE "deadlines" ADD CONSTRAINT fk_deadlines_users FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;
ALTER TABLE "deadlines" ADD UNIQUE ("user_id", "description");

ALTER TABLE "reminders" ADD CONSTRAINT fk_reminders_deadlines FOREIGN KEY ("deadline_id") REFERENCES "deadlines" ("id") ON DELETE CASCADE;
