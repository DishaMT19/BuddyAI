const state = {
  conversations: [],
  activeConversationId: null,
  messages: [],
  memory: {},
  goals: [],
  habits: [],
  daily: {},
  dashboard: {},
  attachment: null,
  voiceReplies: false
};

// Determine API base URL - use current origin in production, localhost for development
const getApiUrl = () => {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:5000';
  }
  return window.location.origin;
};

const API_BASE = getApiUrl();

const $ = (selector) => document.querySelector(selector);
const api = (url, options = {}) => {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  return fetch(fullUrl, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  }).then((res) => {
    if (!res.ok) {
      console.error(`API Error: ${res.status} ${res.statusText}`);
      throw new Error(`Request failed: ${res.status}`);
    }
    return res.json();
  }).catch((error) => {
    console.error('Fetch error:', error);
    throw error;
  });
};

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderConversations(filter = "") {
  const history = $("#chatHistory");
  const filtered = state.conversations.filter((chat) =>
    chat.title.toLowerCase().includes(filter.toLowerCase())
  );
  history.innerHTML = filtered.map((chat) => `
    <button class="history-item ${chat.id === state.activeConversationId ? "active" : ""}" data-chat="${chat.id}">
      ${escapeHtml(chat.title)}
      <span>${new Date(chat.updated_at).toLocaleDateString()}</span>
    </button>
  `).join("");
}

function renderMessages() {
  const messages = $("#messages");
  messages.innerHTML = state.messages.map((message) => {
    const isUser = message.role === "user";
    const reactions = ["❤️", "👍", "😂"].map((reaction) => `
      <button class="reaction ${message.reactions.includes(reaction) ? "active" : ""}" data-action="react" data-id="${message.id}" data-reaction="${reaction}">${reaction}</button>
    `).join("");
    const attachment = message.attachment ? `<div class="message-meta">Attached: ${escapeHtml(message.attachment)}</div>` : "";
    return `
      <article class="message ${isUser ? "user" : "bot"}">
        <div class="avatar ${isUser ? "user-avatar" : "bot-avatar"}">${isUser ? "You" : "AI"}</div>
        <div class="bubble-wrap">
          <div class="message-meta">
            <strong>${isUser ? "You" : "BuddyAI"}</strong>
            <span>${formatTime(message.timestamp)}</span>
            ${message.pinned ? "<span>📌 Pinned</span>" : ""}
          </div>
          <div class="bubble">${escapeHtml(message.content)}</div>
          ${attachment}
          <div class="message-actions">
            ${reactions}
            <button data-action="copy" data-id="${message.id}">Copy</button>
            ${isUser ? `<button data-action="edit" data-id="${message.id}">Edit</button>` : ""}
            <button data-action="pin" class="${message.pinned ? "pin-on" : ""}" data-id="${message.id}">Pin</button>
            <button data-action="delete" data-id="${message.id}">Delete</button>
          </div>
        </div>
      </article>
    `;
  }).join("");
  messages.scrollTop = messages.scrollHeight;
}

function renderDashboard() {
  const memory = state.memory || {};
  const profile = memory.profile || {};
  const settings = memory.settings || {};
  $("#profileName").textContent = settings.displayName || profile.name || "Friend";
  $("#profileFocus").textContent = settings.focusArea || "Career growth";
  $("#displayName").value = settings.displayName || profile.name || "";
  $("#focusArea").value = settings.focusArea || "";
  $("#dailyQuote").textContent = state.daily.quote || "";
  $("#challengeText").textContent = `Coding: ${state.daily.codingChallenge || ""}`;
  $("#aptitudeText").textContent = state.daily.aptitude ? `Aptitude: ${state.daily.aptitude.question}` : "";
  $("#weeklySummary").textContent = state.dashboard.weeklySummary || "";
  $("#productivityScore").textContent = `${state.dashboard.productivityScore || 0}%`;
  $("#badges").innerHTML = (memory.badges || []).map((badge) => `<span>${escapeHtml(badge)}</span>`).join("");

  $("#goalList").innerHTML = state.goals.map((goal) => `
    <div class="goal-item" data-goal="${goal.id}">
      <strong>${escapeHtml(goal.title)}</strong>
      <div class="progress"><span style="width:${goal.progress}%"></span></div>
      <div class="message-meta">${goal.progress}% complete</div>
    </div>
  `).join("");

  $("#habitList").innerHTML = state.habits.map((habit) => `
    <div class="habit-item">
      <div>
        <strong>${escapeHtml(habit.title)}</strong>
        <div class="message-meta">${habit.streak} day streak</div>
      </div>
      <button class="habit-check ${habit.checked_today ? "pin-on" : ""}" data-habit="${habit.id}">${habit.checked_today ? "✓" : "+"}</button>
    </div>
  `).join("");
}

function setTyping(show) {
  $("#typing").classList.toggle("hidden", !show);
}

async function loadConversation(id) {
  state.activeConversationId = id;
  state.messages = await api(`/api/conversations/${id}/messages`);
  const active = state.conversations.find((chat) => chat.id === id);
  $("#activeTitle").textContent = active?.title || "BuddyAI";
  renderConversations($("#searchChats").value);
  renderMessages();
  $(".sidebar").classList.remove("open");
}

async function sendMessage(text) {
  const optimistic = {
    id: `temp-${Date.now()}`,
    conversationId: state.activeConversationId,
    role: "user",
    content: text,
    timestamp: new Date().toISOString(),
    reactions: [],
    pinned: false,
    attachment: state.attachment
  };
  state.messages.push(optimistic);
  renderMessages();
  setTyping(true);

  const data = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      conversationId: state.activeConversationId,
      message: text,
      attachment: state.attachment
    })
  });

  state.messages = state.messages.filter((message) => message.id !== optimistic.id);
  state.messages.push(data.user, data.bot);
  state.memory = data.memory;
  setTyping(false);
  renderMessages();
  renderDashboard();
  if (state.voiceReplies) speak(data.bot.content);
  state.attachment = null;
  $("#attachmentPreview").classList.add("hidden");
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 1.02;
  speechSynthesis.cancel();
  speechSynthesis.speak(utterance);
}

function setupEmojiPicker() {
  const emojis = "😊 😌 🔥 ✨ 💪 ❤️ 👍 😂 🚀 📚 🧠 🎯 🌱 🙌".split(" ");
  $("#emojiPicker").innerHTML = emojis.map((emoji) => `<button type="button">${emoji}</button>`).join("");
}

function utilityPrompt(type) {
  const prompts = {
    resume: "Help me improve my resume with strong project bullets.",
    portfolio: "Suggest portfolio improvements based on my projects and skills.",
    coding: "Be my coding helper and give me a practical challenge.",
    study: "Create a focused study plan for today.",
    interview: "Start an interview preparation session with me.",
    career: "Give me career guidance based on my goals."
  };
  $("#messageInput").value = prompts[type] || "";
  $("#messageInput").focus();
}

async function patchMessage(id, payload) {
  const updated = await api(`/api/messages/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
  state.messages = state.messages.map((message) => message.id === updated.id ? updated : message);
  renderMessages();
}

function bindEvents() {
  $("#chatForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = $("#messageInput");
    const text = input.value.trim();
    if (!text && !state.attachment) return;
    input.value = "";
    await sendMessage(text || "I attached a file. Please help me think through it.");
  });

  $("#messageInput").addEventListener("input", (event) => {
    event.target.style.height = "auto";
    event.target.style.height = `${Math.min(event.target.scrollHeight, 150)}px`;
  });

  $("#chatHistory").addEventListener("click", (event) => {
    const button = event.target.closest("[data-chat]");
    if (button) loadConversation(Number(button.dataset.chat));
  });

  $("#searchChats").addEventListener("input", (event) => renderConversations(event.target.value));

  $("#newChat").addEventListener("click", async () => {
    const chat = await api("/api/conversations", { method: "POST", body: "{}" });
    state.conversations.unshift(chat);
    await loadConversation(chat.id);
  });

  $("#themeToggle").addEventListener("click", async () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    $("#themeToggle").textContent = next === "light" ? "☀" : "☾";
    state.memory = await api("/api/settings", { method: "POST", body: JSON.stringify({ theme: next }) });
  });

  $("#voiceToggle").addEventListener("click", async () => {
    state.voiceReplies = !state.voiceReplies;
    $("#voiceToggle").classList.toggle("pin-on", state.voiceReplies);
    state.memory = await api("/api/settings", { method: "POST", body: JSON.stringify({ voiceReplies: state.voiceReplies }) });
  });

  $("#messages").addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const id = Number(button.dataset.id);
    const message = state.messages.find((item) => item.id === id);
    if (!message) return;
    if (button.dataset.action === "react") await patchMessage(id, { reaction: button.dataset.reaction });
    if (button.dataset.action === "pin") await patchMessage(id, { pinned: !message.pinned });
    if (button.dataset.action === "copy") await navigator.clipboard.writeText(message.content);
    if (button.dataset.action === "delete") {
      await api(`/api/messages/${id}`, { method: "DELETE" });
      state.messages = state.messages.filter((item) => item.id !== id);
      renderMessages();
    }
    if (button.dataset.action === "edit") {
      const next = prompt("Edit your message", message.content);
      if (next !== null && next.trim()) await patchMessage(id, { content: next.trim() });
    }
  });

  $("#emojiBtn").addEventListener("click", () => $("#emojiPicker").classList.toggle("hidden"));
  $("#emojiPicker").addEventListener("click", (event) => {
    if (event.target.tagName !== "BUTTON") return;
    $("#messageInput").value += event.target.textContent;
    $("#messageInput").focus();
  });

  $("#gifBtn").addEventListener("click", () => {
    $("#messageInput").value += " https://media.giphy.com/media/3o7abB06u9bNzA8lu8/giphy.gif ";
    $("#messageInput").focus();
  });

  $("#fileInput").addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    state.attachment = file.name;
    $("#attachmentPreview").textContent = `Ready to attach: ${file.name}`;
    $("#attachmentPreview").classList.remove("hidden");
  });

  $("#voiceInput").addEventListener("click", () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      $("#messageInput").value = "Voice input is not supported in this browser, but I want to talk about ";
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      $("#messageInput").value = event.results[0][0].transcript;
    };
    recognition.start();
  });

  $("#moodRow").addEventListener("click", async (event) => {
    if (event.target.tagName !== "BUTTON") return;
    const mood = event.target.textContent;
    const data = await api("/api/mood", { method: "POST", body: JSON.stringify({ mood, note: "Mood selected from dashboard" }) });
    state.memory = data.memory;
    renderDashboard();
    await sendMessage(`My mood today is ${mood}. Check in with me and suggest one helpful next step.`);
  });

  $("#addGoal").addEventListener("click", async () => {
    const title = prompt("Goal title");
    if (!title) return;
    const goal = await api("/api/goals", { method: "POST", body: JSON.stringify({ title }) });
    state.goals.unshift(goal);
    renderDashboard();
  });

  $("#goalList").addEventListener("click", async (event) => {
    const item = event.target.closest("[data-goal]");
    if (!item) return;
    const goal = state.goals.find((entry) => entry.id === Number(item.dataset.goal));
    const progress = prompt("Update progress 0-100", goal.progress);
    if (progress === null) return;
    const updated = await api(`/api/goals/${goal.id}`, { method: "PATCH", body: JSON.stringify({ progress }) });
    state.goals = state.goals.map((entry) => entry.id === updated.id ? updated : entry);
    renderDashboard();
  });

  $("#addHabit").addEventListener("click", async () => {
    const title = prompt("Habit title");
    if (!title) return;
    const habit = await api("/api/habits", { method: "POST", body: JSON.stringify({ title }) });
    state.habits.unshift(habit);
    renderDashboard();
  });

  $("#habitList").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-habit]");
    if (!button) return;
    const updated = await api(`/api/habits/${button.dataset.habit}`, { method: "PATCH", body: "{}" });
    state.habits = state.habits.map((habit) => habit.id === updated.id ? updated : habit);
    renderDashboard();
  });

  document.querySelectorAll("[data-utility]").forEach((button) => {
    button.addEventListener("click", () => utilityPrompt(button.dataset.utility));
  });

  $("#projectIdeaBtn").addEventListener("click", () => {
    $("#messageInput").value = "Generate a personalized project idea based on my skills, interests, and previous projects.";
    $("#messageInput").focus();
  });

  $("#saveSettings").addEventListener("click", async () => {
    state.memory = await api("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        displayName: $("#displayName").value || "Friend",
        focusArea: $("#focusArea").value || "Personal growth"
      })
    });
    renderDashboard();
  });

  $("#menuToggle").addEventListener("click", () => $(".sidebar").classList.toggle("open"));
}

async function init() {
  setupEmojiPicker();
  bindEvents();
  const data = await api("/api/bootstrap");
  Object.assign(state, data);
  const settings = state.memory.settings || {};
  document.documentElement.dataset.theme = settings.theme || "dark";
  state.voiceReplies = Boolean(settings.voiceReplies);
  $("#voiceToggle").classList.toggle("pin-on", state.voiceReplies);
  renderConversations();
  renderMessages();
  renderDashboard();
  $("#loading").classList.add("hide");
}

init().catch((error) => {
  console.error(error);
  $("#loading p").textContent = "BuddyAI needs a refresh. Please restart the Flask server.";
});
