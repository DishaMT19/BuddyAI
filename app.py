import json
import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request

from chatbot import daily_content, generate_reply, load_memory, save_memory


BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                reactions TEXT DEFAULT '[]',
                pinned INTEGER DEFAULT 0,
                attachment TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                checked_today INTEGER DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            """
        )

        existing = connection.execute("SELECT COUNT(*) AS count FROM conversations").fetchone()["count"]
        if existing == 0:
            now = datetime.now().isoformat(timespec="seconds")
            cursor = connection.execute(
                "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
                ("Welcome to BuddyAI", now, now),
            )
            conversation_id = cursor.lastrowid
            welcome = (
                "Hey, I am BuddyAI. I can be your caring friend, mentor, study partner, motivation coach, "
                "and productivity helper. Tell me your name, goals, projects, or how you feel today."
            )
            connection.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (conversation_id, "bot", welcome, now),
            )

        if connection.execute("SELECT COUNT(*) AS count FROM goals").fetchone()["count"] == 0:
            now = datetime.now().isoformat(timespec="seconds")
            connection.executemany(
                "INSERT INTO goals (title, progress, completed, created_at) VALUES (?, ?, ?, ?)",
                [
                    ("Finish BuddyAI portfolio polish", 68, 0, now),
                    ("Practice interviews 4 days this week", 40, 0, now),
                    ("Build one strong project case study", 25, 0, now),
                ],
            )

        if connection.execute("SELECT COUNT(*) AS count FROM habits").fetchone()["count"] == 0:
            now = datetime.now().isoformat(timespec="seconds")
            connection.executemany(
                "INSERT INTO habits (title, streak, checked_today, updated_at) VALUES (?, ?, ?, ?)",
                [
                    ("Code for 60 minutes", 5, 1, now),
                    ("Review aptitude questions", 3, 0, now),
                    ("Write daily reflection", 2, 0, now),
                ],
            )


def row_to_message(row):
    return {
        "id": row["id"],
        "conversationId": row["conversation_id"],
        "role": row["role"],
        "content": row["content"],
        "timestamp": row["timestamp"],
        "reactions": json.loads(row["reactions"] or "[]"),
        "pinned": bool(row["pinned"]),
        "attachment": row["attachment"],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/bootstrap")
def bootstrap():
    with db() as connection:
        conversations = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        ]
        first_id = conversations[0]["id"] if conversations else None
        messages = []
        if first_id:
            messages = [
                row_to_message(row)
                for row in connection.execute(
                    "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
                    (first_id,),
                ).fetchall()
            ]
        goals = [dict(row) for row in connection.execute("SELECT * FROM goals ORDER BY id DESC").fetchall()]
        habits = [dict(row) for row in connection.execute("SELECT * FROM habits ORDER BY id DESC").fetchall()]

    memory = load_memory()
    return jsonify({
        "conversations": conversations,
        "activeConversationId": first_id,
        "messages": messages,
        "memory": memory,
        "daily": daily_content(),
        "goals": goals,
        "habits": habits,
        "dashboard": dashboard_stats(goals, habits, memory)
    })


def dashboard_stats(goals, habits, memory):
    completed_goals = sum(1 for goal in goals if goal["completed"])
    checked_habits = sum(1 for habit in habits if habit["checked_today"])
    total = max(len(goals) + len(habits), 1)
    productivity = round(((completed_goals + checked_habits) / total) * 100)
    moods = memory.get("profile", {}).get("daily_mood_logs", [])
    return {
        "productivityScore": productivity,
        "completedGoals": completed_goals,
        "activeGoals": len(goals) - completed_goals,
        "habitStreak": sum(habit["streak"] for habit in habits),
        "moodEntries": len(moods),
        "weeklySummary": "You are building momentum through coding, reflection, and career preparation."
    }


@app.post("/api/conversations")
def create_conversation():
    now = datetime.now().isoformat(timespec="seconds")
    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
            ("New growth chat", now, now),
        )
        conversation_id = cursor.lastrowid
        connection.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conversation_id, "bot", "New chat, fresh page. What should we work through together?", now),
        )
    return jsonify({"id": conversation_id, "title": "New growth chat", "created_at": now, "updated_at": now})


@app.get("/api/conversations/<int:conversation_id>/messages")
def get_messages(conversation_id):
    with db() as connection:
        rows = connection.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
    return jsonify([row_to_message(row) for row in rows])


@app.post("/api/chat")
def chat():
    payload = request.get_json(force=True)
    conversation_id = int(payload.get("conversationId"))
    content = (payload.get("message") or "").strip()
    attachment = payload.get("attachment")
    if not content and not attachment:
        return jsonify({"error": "Message cannot be empty"}), 400

    now = datetime.now().isoformat(timespec="seconds")
    with db() as connection:
        user_cursor = connection.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp, attachment) VALUES (?, ?, ?, ?, ?)",
            (conversation_id, "user", content, now, attachment),
        )

        reply = generate_reply(content)
        bot_time = datetime.now().isoformat(timespec="seconds")
        bot_cursor = connection.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (conversation_id, "bot", reply, bot_time),
        )

        title = content[:42] or "Attachment chat"
        connection.execute(
            "UPDATE conversations SET title = CASE WHEN title IN ('New growth chat', 'Welcome to BuddyAI') THEN ? ELSE title END, updated_at = ? WHERE id = ?",
            (title, bot_time, conversation_id),
        )

        user_row = connection.execute("SELECT * FROM messages WHERE id = ?", (user_cursor.lastrowid,)).fetchone()
        bot_row = connection.execute("SELECT * FROM messages WHERE id = ?", (bot_cursor.lastrowid,)).fetchone()

    return jsonify({"user": row_to_message(user_row), "bot": row_to_message(bot_row), "memory": load_memory()})


@app.patch("/api/messages/<int:message_id>")
def update_message(message_id):
    payload = request.get_json(force=True)
    with db() as connection:
        if "content" in payload:
            connection.execute("UPDATE messages SET content = ? WHERE id = ?", (payload["content"], message_id))
        if "reaction" in payload:
            row = connection.execute("SELECT reactions FROM messages WHERE id = ?", (message_id,)).fetchone()
            reactions = json.loads(row["reactions"] or "[]")
            reaction = payload["reaction"]
            reactions = [item for item in reactions if item != reaction] if reaction in reactions else reactions + [reaction]
            connection.execute("UPDATE messages SET reactions = ? WHERE id = ?", (json.dumps(reactions), message_id))
        if "pinned" in payload:
            connection.execute("UPDATE messages SET pinned = ? WHERE id = ?", (1 if payload["pinned"] else 0, message_id))
        row = connection.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return jsonify(row_to_message(row))


@app.delete("/api/messages/<int:message_id>")
def delete_message(message_id):
    with db() as connection:
        connection.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    return jsonify({"ok": True})


@app.post("/api/mood")
def add_mood():
    payload = request.get_json(force=True)
    memory = load_memory()
    memory.setdefault("profile", {}).setdefault("daily_mood_logs", []).append({
        "mood": payload.get("mood", "okay"),
        "note": payload.get("note", ""),
        "timestamp": datetime.now().isoformat(timespec="seconds")
    })
    save_memory(memory)
    return jsonify({"memory": memory})


@app.post("/api/goals")
def add_goal():
    payload = request.get_json(force=True)
    now = datetime.now().isoformat(timespec="seconds")
    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO goals (title, progress, completed, created_at) VALUES (?, ?, ?, ?)",
            (payload.get("title", "New goal"), int(payload.get("progress", 0)), 0, now),
        )
        row = connection.execute("SELECT * FROM goals WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row))


@app.patch("/api/goals/<int:goal_id>")
def update_goal(goal_id):
    payload = request.get_json(force=True)
    progress = max(0, min(100, int(payload.get("progress", 0))))
    with db() as connection:
        connection.execute(
            "UPDATE goals SET progress = ?, completed = ? WHERE id = ?",
            (progress, 1 if progress >= 100 else 0, goal_id),
        )
        row = connection.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    return jsonify(dict(row))


@app.post("/api/habits")
def add_habit():
    payload = request.get_json(force=True)
    now = datetime.now().isoformat(timespec="seconds")
    with db() as connection:
        cursor = connection.execute(
            "INSERT INTO habits (title, streak, checked_today, updated_at) VALUES (?, ?, ?, ?)",
            (payload.get("title", "New habit"), 0, 0, now),
        )
        row = connection.execute("SELECT * FROM habits WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(dict(row))


@app.patch("/api/habits/<int:habit_id>")
def toggle_habit(habit_id):
    now = datetime.now().isoformat(timespec="seconds")
    with db() as connection:
        row = connection.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
        checked = 0 if row["checked_today"] else 1
        streak = max(0, row["streak"] + (1 if checked else -1))
        connection.execute(
            "UPDATE habits SET checked_today = ?, streak = ?, updated_at = ? WHERE id = ?",
            (checked, streak, now, habit_id),
        )
        updated = connection.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
    return jsonify(dict(updated))


@app.post("/api/settings")
def save_settings():
    payload = request.get_json(force=True)
    memory = load_memory()
    settings = memory.setdefault("settings", {})
    profile = memory.setdefault("profile", {})
    for key in ["theme", "voiceReplies", "displayName", "focusArea"]:
        if key in payload:
            settings[key] = payload[key]
    if "displayName" in payload:
        profile["name"] = payload["displayName"]
    save_memory(memory)
    return jsonify(memory)


@app.get("/api/future-ai")
def future_ai_support():
    return jsonify({
        "ready": True,
        "message": "Replace generate_reply in chatbot.py or call an external model from this endpoint adapter.",
        "suggestedEnvVars": ["AI_API_KEY", "AI_MODEL_NAME", "AI_BASE_URL"]
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
