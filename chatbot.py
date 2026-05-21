import json
import os
import random
import re
from datetime import datetime


MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")


QUOTES = [
    "Small steps still move you forward.",
    "Your future is built by what you repeat, not what you rush.",
    "Progress becomes visible after consistency has done quiet work.",
    "One focused hour can change the tone of an entire day.",
    "You do not need perfect energy to take the next useful step."
]


PROJECT_IDEAS = [
    "AI resume analyzer with role-specific feedback",
    "AgroVision crop disease dashboard with explainable predictions",
    "Personal finance tracker with spending insights",
    "Portfolio case-study generator for projects",
    "Interview prep bot that tracks weak topics",
    "Habit analytics dashboard with weekly reflections"
]


CODING_CHALLENGES = [
    "Build a function that groups words by anagram signature.",
    "Create a debounce utility in JavaScript and test it with an input box.",
    "Write a Flask route that validates JSON and returns helpful errors.",
    "Solve two-pointer pair sum for a sorted array.",
    "Design a SQLite schema for goals, habits, and progress entries."
]


APTITUDE_QUESTIONS = [
    {
        "question": "A train travels 180 km in 3 hours. What is its speed?",
        "answer": "60 km/h"
    },
    {
        "question": "If 12 workers finish a task in 8 days, how many days for 24 workers at the same rate?",
        "answer": "4 days"
    },
    {
        "question": "Find the next number: 3, 6, 12, 24, ?",
        "answer": "48"
    }
]


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)


def _normalize_list(values):
    return [value.strip() for value in values if value and value.strip()]


def update_memory_from_message(message):
    memory = load_memory()
    profile = memory.setdefault("profile", {})
    text = message.strip()
    lower = text.lower()

    name_match = re.search(r"\b(?:my name is|i am|i'm)\s+([A-Z][a-zA-Z]{1,24})\b", text)
    if name_match:
        profile["name"] = name_match.group(1)
        memory.setdefault("settings", {})["displayName"] = name_match.group(1)

    patterns = {
        "skills": r"(?:i know|my skills are|i can use|i am learning)\s+(.+)",
        "interests": r"(?:i like|i am interested in|my interests are)\s+(.+)",
        "projects": r"(?:i am working on|my project is|project called)\s+(.+)",
        "goals": r"(?:my goal is|i want to|i need to|goal is)\s+(.+)",
        "favorite_technologies": r"(?:favorite tech is|favorite technology is|i love using)\s+(.+)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, lower)
        if match:
            existing = profile.setdefault(key, [])
            extracted = re.split(r",| and | with ", match.group(1))
            for item in _normalize_list(extracted):
                cleaned = item[:60].strip(". ")
                if cleaned and cleaned not in existing:
                    existing.append(cleaned)

    mood_words = ["happy", "sad", "tired", "stressed", "anxious", "motivated", "excited", "confused", "low"]
    if any(word in lower for word in mood_words):
        profile.setdefault("daily_mood_logs", []).append({
            "mood": next(word for word in mood_words if word in lower),
            "note": text[:180],
            "timestamp": datetime.now().isoformat(timespec="seconds")
        })

    save_memory(memory)
    return memory


def _memory_hint(memory):
    profile = memory.get("profile", {})
    projects = profile.get("projects", [])
    goals = profile.get("goals", [])
    interests = profile.get("interests", [])

    hints = []
    if projects:
        hints.append(f"Last time you mentioned working on {projects[-1]}.")
    if goals:
        hints.append(f"You have been aiming to {goals[-1]}.")
    if interests:
        hints.append(f"I also remember your interest in {interests[-1]}.")
    return " ".join(hints[:2])


def generate_reply(user_message, history=None):
    memory = update_memory_from_message(user_message)
    profile = memory.get("profile", {})
    name = profile.get("name") or memory.get("settings", {}).get("displayName", "friend")
    lower = user_message.lower()
    hint = _memory_hint(memory)

    if any(word in lower for word in ["tired", "exhausted", "drained"]):
        reply = (
            f"{name}, you've been carrying a lot. Want to take a small reset first: water, stretch, "
            "and one quiet minute? Then we can choose the lightest next step together."
        )
    elif any(word in lower for word in ["motivation", "demotivated", "losing motivation", "give up"]):
        reply = (
            "Progress does not always feel exciting, but it still counts. Let's make today smaller: "
            "pick one task that takes 15 minutes, finish it, and let that be your win."
        )
    elif "project" in lower and any(word in lower for word in ["idea", "build", "make", "create"]):
        ideas = random.sample(PROJECT_IDEAS, 3)
        reply = (
            "Here are three portfolio-ready ideas: "
            f"1. {ideas[0]} 2. {ideas[1]} 3. {ideas[2]}. "
            "If you tell me your current skill level, I can shape one into a week-by-week plan."
        )
    elif any(word in lower for word in ["resume", "cv"]):
        reply = (
            "For your resume, lead with measurable outcomes: project name, problem solved, tech stack, "
            "and impact. Send me one bullet and I will help make it sharper."
        )
    elif any(word in lower for word in ["interview", "job", "career"]):
        reply = (
            "Let's prepare like a calm professional: one project story, one DSA topic, one behavioral answer, "
            "and one company-specific question per day. What role are you targeting?"
        )
    elif any(word in lower for word in ["study", "exam", "learn"]):
        reply = (
            "I can be your study partner. Try a 45-minute focus block: 25 minutes learning, 10 minutes notes, "
            "10 minutes recall. What subject should we start with?"
        )
    elif any(word in lower for word in ["goal", "habit", "productive", "productivity"]):
        reply = (
            "Let's turn that into a visible system: one daily action, one weekly milestone, and one reflection. "
            "What is the goal you want BuddyAI to check on?"
        )
    elif any(word in lower for word in ["hello", "hi", "hey"]):
        reply = (
            f"Hey {name}, I'm here. We can plan your day, talk through something heavy, practice interviews, "
            "or build momentum on a project. What's on your mind?"
        )
    else:
        reply = (
            "I hear you. Tell me a little more about what you want from this: advice, a plan, ideas, "
            "or just someone to think it through with you?"
        )

    if hint and random.random() > 0.25:
        reply = f"{reply} {hint}"
    return reply


def daily_content():
    return {
        "quote": random.choice(QUOTES),
        "codingChallenge": random.choice(CODING_CHALLENGES),
        "aptitude": random.choice(APTITUDE_QUESTIONS),
        "projectIdea": random.choice(PROJECT_IDEAS)
    }
