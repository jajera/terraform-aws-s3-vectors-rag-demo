const loginScreen = document.getElementById("login-screen");
const appScreen = document.getElementById("app-screen");
const loginForm = document.getElementById("login-form");
const loginError = document.getElementById("login-error");
const messagesEl = document.getElementById("messages");
const sourcesEl = document.getElementById("sources-list");
const corpusStatsEl = document.getElementById("corpus-stats");
const refreshBtn = document.getElementById("refresh-btn");
const chatForm = document.getElementById("chat-form");
const questionInput = document.getElementById("question");
const askBtn = document.getElementById("ask-btn");

if (window.marked) {
  marked.setOptions({ breaks: true, gfm: true });
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(text) {
  if (!text) return "";
  if (window.marked && window.DOMPurify) {
    return DOMPurify.sanitize(marked.parse(text));
  }
  return escapeHtml(text).replace(/\n/g, "<br>");
}

function formatRelativeTime(isoTimestamp) {
  if (!isoTimestamp) return "never";
  try {
    const ingested = new Date(isoTimestamp);
    const deltaMs = Date.now() - ingested.getTime();
    const minutes = Math.floor(deltaMs / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 48) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return isoTimestamp;
  }
}

function formatPublished(isoTimestamp) {
  if (!isoTimestamp) return "unknown date";
  try {
    return new Intl.DateTimeFormat("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(new Date(isoTimestamp));
  } catch {
    return isoTimestamp;
  }
}

function feedLabel(feed) {
  if (feed === "aws-whats-new") return "What's New";
  if (feed === "aws-news-blog") return "News Blog";
  return feed || "AWS";
}

function truncate(text, max = 220) {
  if (!text || text.length <= max) return text || "";
  return `${text.slice(0, max).trim()}…`;
}

function hideWelcome() {
  document.getElementById("welcome")?.classList.add("hidden");
}

function showLogin() {
  loginScreen.classList.remove("hidden");
  appScreen.classList.add("hidden");
}

function showApp() {
  loginScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
}

function scrollMessages() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(isLoading) {
  questionInput.disabled = isLoading;
  askBtn.disabled = isLoading;
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.disabled = isLoading;
  });
}

function addLoadingMessage() {
  removeLoadingMessage();
  const div = document.createElement("div");
  div.className = "message assistant loading";
  div.id = "loading-message";
  div.innerHTML = `
    <div class="message-inner">
      <div class="avatar assistant-avatar" aria-hidden="true">AI</div>
      <div class="bubble">
        <div class="typing" aria-label="Generating answer">
          <span></span><span></span><span></span>
        </div>
        <span class="loading-text">Searching announcements and generating answer…</span>
      </div>
    </div>
  `;
  messagesEl.appendChild(div);
  scrollMessages();
}

function removeLoadingMessage() {
  document.getElementById("loading-message")?.remove();
}

function renderInlineSources(sources) {
  if (!sources?.length) return "";
  const items = sources
    .map((source, index) => {
      const title = source.url
        ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.title)}</a>`
        : `<strong>${escapeHtml(source.title)}</strong>`;
      return `
        <li>
          <span class="source-rank">${index + 1}</span>
          <div>
            ${title}
            <div class="source-meta">${escapeHtml(feedLabel(source.feed))} · ${escapeHtml(formatPublished(source.published))}</div>
          </div>
        </li>
      `;
    })
    .join("");

  return `
    <details class="inline-sources" open>
      <summary>Sources (${sources.length})</summary>
      <ol>${items}</ol>
    </details>
  `;
}

function addMessage(role, text, sources = null) {
  hideWelcome();
  const div = document.createElement("div");
  div.className = `message ${role}`;

  const avatarLabel = role === "user" ? "You" : "AI";
  const avatarClass = role === "user" ? "user-avatar" : "assistant-avatar";
  const body =
    role === "assistant"
      ? `<div class="markdown-body">${renderMarkdown(text)}</div>${renderInlineSources(sources)}`
      : `<p>${escapeHtml(text)}</p>`;

  div.innerHTML = `
    <div class="message-inner">
      <div class="avatar ${avatarClass}" aria-hidden="true">${avatarLabel}</div>
      <div class="bubble">${body}</div>
    </div>
  `;

  messagesEl.appendChild(div);
  scrollMessages();
}

function renderSources(sources) {
  sourcesEl.innerHTML = "";
  if (!sources?.length) {
    sourcesEl.innerHTML = '<p class="muted empty-state">No sources returned.</p>';
    return;
  }

  sources.forEach((source, index) => {
    const article = document.createElement("article");
    const title = source.url
      ? `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.title)}</a>`
      : `<strong>${escapeHtml(source.title)}</strong>`;
    article.innerHTML = `
      <div class="source-card-header">
        <span class="source-rank">${index + 1}</span>
        <div class="source-card-title">${title}</div>
      </div>
      <div class="source-meta">${escapeHtml(feedLabel(source.feed))} · ${escapeHtml(formatPublished(source.published))}</div>
      <p class="source-excerpt">${escapeHtml(truncate(source.excerpt))}</p>
    `;
    sourcesEl.appendChild(article);
  });
}

async function refreshStatus() {
  const status = await getStatus();
  const relative = formatRelativeTime(status.last_ingested_at);
  corpusStatsEl.textContent = `${status.article_count} articles · updated ${relative}`;
}

async function bootApp() {
  showApp();
  const session = await getSession();
  if (isAdmin(session)) {
    refreshBtn.classList.remove("hidden");
  }
  await refreshStatus();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.classList.add("hidden");
  try {
    await signIn(
      document.getElementById("email").value.trim(),
      document.getElementById("password").value
    );
    await bootApp();
  } catch (error) {
    loginError.textContent = error.message || "Sign in failed";
    loginError.classList.remove("hidden");
  }
});

function resetChat() {
  messagesEl.replaceChildren();
  const welcome = document.createElement("div");
  welcome.id = "welcome";
  welcome.className = "welcome";
  welcome.innerHTML =
    "<p>Ask about recent AWS announcements — Bedrock, storage, generative AI, and more.</p>";
  messagesEl.appendChild(welcome);
  sourcesEl.innerHTML =
    '<p class="muted empty-state">Ask a question to see matched announcements.</p>';
}

document.getElementById("logout-btn").addEventListener("click", () => {
  signOut();
  resetChat();
  showLogin();
});

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  try {
    await postIngest();
    addMessage("assistant", "Corpus refresh started. Check back in a few minutes.");
    setTimeout(refreshStatus, 5000);
  } catch (error) {
    addMessage("assistant", `Refresh failed: ${error.message}`);
  } finally {
    refreshBtn.disabled = false;
  }
});

async function submitQuestion(question) {
  const trimmed = question.trim();
  if (!trimmed) return;

  hideWelcome();
  addMessage("user", trimmed);
  setLoading(true);
  addLoadingMessage();

  try {
    const result = await postQuery(trimmed);
    removeLoadingMessage();
    addMessage("assistant", result.answer, result.sources);
    renderSources(result.sources);
  } catch (error) {
    removeLoadingMessage();
    addMessage("assistant", `Query failed: ${error.message}`);
  } finally {
    setLoading(false);
    questionInput.focus();
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value;
  questionInput.value = "";
  await submitQuestion(question);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    submitQuestion(chip.dataset.query);
  });
});

getSession()
  .then(() => bootApp())
  .catch(() => showLogin());
