# BuddyAI

BuddyAI is a modern Flask-powered AI companion chat application designed to feel like a caring friend, mentor, study partner, motivation coach, and productivity helper.

## Features

- Responsive desktop and mobile chat UI
- Light and dark mode
- Glassmorphism panels, soft shadows, smooth message animations
- Chat history sidebar with search and new chat support
- Natural companion-style chatbot behavior
- Persistent memory for name, skills, interests, projects, goals, technologies, and mood logs
- SQLite storage for conversations, messages, goals, and habits
- Message timestamps, reactions, copy, edit, delete, and pin actions
- Daily mood tracker
- Goal and habit tracking
- Progress dashboard with productivity score, weekly summary, and badges
- Daily quote, coding challenge, aptitude question, and project idea generator
- Resume, portfolio, coding, study, interview, and career helper prompts
- File attachment labels, emoji picker, GIF shortcut, speech-to-text, and text-to-speech support
- Future AI integration adapter endpoint

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Project Structure

```text
BuddyAI/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── templates/
│   └── index.html
├── app.py
├── chatbot.py
├── memory.json
├── database.db
├── requirements.txt
└── README.md
```

## Future AI Integration

The current chatbot uses a local supportive response engine in `chatbot.py`. To connect a hosted AI model later, replace `generate_reply()` or add a provider call using environment variables such as:

```text
AI_API_KEY
AI_MODEL_NAME
AI_BASE_URL
```
