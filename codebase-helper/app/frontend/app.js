const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const statusEl = document.getElementById("status");
const reposListEl = document.getElementById("repos-list");
const newChatBtn = document.getElementById("new-chat");
const attachBtn = document.getElementById("attach-btn");
const fileInputEl = document.getElementById("file-input");
const attachedFilesEl = document.getElementById("attached-files");
const progressBarEl = document.getElementById("progress-bar");

const SESSION_KEY = "memgraph-codebase-helper-session";
let sessionId = localStorage.getItem(SESSION_KEY) || null;

const MODE_KEY = "memgraph-codebase-helper-mode";
const VALID_MODES = ["both", "usage", "implementation"];
let answerMode = localStorage.getItem(MODE_KEY);
if (!VALID_MODES.includes(answerMode)) answerMode = "both";

const MODEL_KEY = "memgraph-codebase-helper-model";
let currentModel = localStorage.getItem(MODEL_KEY) || null;
let availableModelIds = new Set();

const TEMPLATES = [
  {
    label: "Explain a subsystem",
    prompt: "Walk me through how <subsystem> is implemented in Memgraph — entry point, key classes, and the call chain.",
    placeholder: "<subsystem>",
  },
  {
    label: "Find a symbol",
    prompt: "Where is `<SymbolName>` defined and who calls it?",
    placeholder: "<SymbolName>",
  },
  {
    label: "Helm chart behaviour",
    prompt: "In helm-charts, how does <feature> get configured and rendered into the manifests?",
    placeholder: "<feature>",
  },
  {
    label: "AI toolkit usage",
    prompt: "In ai-toolkit, how does <integration> work and what's the minimal example of using it?",
    placeholder: "<integration>",
  },
];

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

if (window.marked) {
  marked.setOptions({ gfm: true, breaks: true });
}

function renderMarkdown(text) {
  if (!window.marked) return escapeHtml(text).replace(/\n/g, "<br/>");
  const html = marked.parse(text);
  return window.DOMPurify ? DOMPurify.sanitize(html) : html;
}

function scrollDown() {
  // Smart auto-scroll: only follow the stream if the user is within a
  // screenful of the bottom. This lets them scroll up mid-answer to
  // re-read something without being yanked back.
  const gap =
    messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight;
  if (gap < 300) messagesEl.scrollTop = messagesEl.scrollHeight;
}

function makeRow(side) {
  const row = document.createElement("div");
  row.className = "flex mx-auto max-w-3xl";
  if (side === "user") row.classList.add("justify-end");
  return row;
}

function addUserMessage(text) {
  const row = makeRow("user");
  const b = document.createElement("div");
  b.className = "bubble bubble-user";
  b.textContent = text;
  row.appendChild(b);
  messagesEl.appendChild(row);
  scrollDown();
}

function addAssistantContainer() {
  const row = makeRow("assistant");
  row.classList.add("flex-col", "gap-2");
  messagesEl.appendChild(row);
  return row;
}

function addTextBubble(container) {
  const b = document.createElement("div");
  b.className = "bubble bubble-assistant";
  b.dataset.raw = "";
  container.appendChild(b);
  return b;
}

function addToolCard(container, name, input) {
  const card = document.createElement("details");
  card.className = "tool-card";
  const summary = document.createElement("summary");
  let subtitle = "";
  if (name === "Bash" && input && input.command) {
    subtitle = input.command;
  } else if (name === "Read" && input && input.file_path) {
    subtitle = input.file_path;
  } else if (name === "Grep" && input && input.pattern) {
    subtitle = `${input.pattern}${input.path ? "  in  " + input.path : ""}`;
  } else if (name === "Glob" && input && input.pattern) {
    subtitle = input.pattern;
  } else if (input) {
    subtitle = Object.values(input).map((v) => String(v)).join(" ");
  }
  summary.innerHTML = `<span class="running-dot" aria-hidden="true"></span><span class="tool-name">${escapeHtml(
    name
  )}</span><span class="truncate text-brand-gray font-normal">${escapeHtml(
    subtitle.slice(0, 160)
  )}</span>`;
  card.appendChild(summary);
  const body = document.createElement("div");
  body.className = "tool-body";
  const inputPre = document.createElement("pre");
  inputPre.textContent =
    typeof input === "string" ? input : JSON.stringify(input, null, 2);
  body.appendChild(inputPre);
  const resultHolder = document.createElement("div");
  resultHolder.className = "mt-2";
  body.appendChild(resultHolder);
  card.appendChild(body);
  container.appendChild(card);
  return { card, resultHolder };
}

function fillToolResult(holder, text, isError) {
  const label = document.createElement("div");
  label.className =
    "mt-2 mb-1 text-xs font-semibold uppercase tracking-[0.06em] text-brand-gray";
  label.textContent = isError ? "Error" : "Output";
  const pre = document.createElement("pre");
  pre.textContent = text;
  holder.holder.appendChild(label);
  holder.holder.appendChild(pre);
  if (isError) holder.card.classList.add("error");
  // Clear the running-state dot once the result lands.
  const runningDot = holder.card.querySelector(".running-dot");
  if (runningDot) runningDot.remove();
}

function addThinkingBubble(container) {
  const existing = container.querySelector(".thinking-bubble");
  if (existing) return existing;
  const bubble = document.createElement("div");
  bubble.className = "thinking-bubble";
  bubble.innerHTML =
    '<span class="dot"></span><span class="dot"></span><span class="dot"></span><span>Thinking…</span>';
  container.appendChild(bubble);
  return bubble;
}

function removeThinkingBubble(container) {
  const existing = container.querySelector(".thinking-bubble");
  if (existing) existing.remove();
}

function setStatus(text) {
  statusEl.textContent = text;
}

// ---- Activity indicator (progress bar, elapsed timer, Send/Stop toggle) ----

let busy = false;
let activityTimer = null;
let activityStart = 0;
let activityBaseLabel = "thinking…";

function setSendButtonMode(mode) {
  if (mode === "stop") {
    sendBtn.textContent = "Stop";
    sendBtn.dataset.mode = "stop";
    sendBtn.disabled = false;
  } else {
    sendBtn.textContent = "Send";
    sendBtn.dataset.mode = "send";
    sendBtn.disabled = false;
  }
}

function tickActivity() {
  const elapsed = ((performance.now() - activityStart) / 1000).toFixed(1);
  setStatus(`${activityBaseLabel} · ${elapsed}s`);
}

function beginActivity(label = "thinking…") {
  busy = true;
  activityBaseLabel = label;
  activityStart = performance.now();
  progressBarEl.classList.add("active");
  setSendButtonMode("stop");
  tickActivity();
  if (activityTimer) clearInterval(activityTimer);
  activityTimer = setInterval(tickActivity, 200);
}

function endActivity(finalStatus) {
  busy = false;
  if (activityTimer) {
    clearInterval(activityTimer);
    activityTimer = null;
  }
  progressBarEl.classList.remove("active");
  setSendButtonMode("send");
  if (finalStatus !== undefined) setStatus(finalStatus);
}

async function interruptActiveRun() {
  if (!sessionId) return;
  activityBaseLabel = "stopping…";
  tickActivity();
  try {
    const resp = await fetch("/api/interrupt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "", session_id: sessionId }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      setStatus(`stop failed: ${body.detail || resp.status}`);
    }
  } catch (err) {
    setStatus(`stop failed: ${err.message}`);
  }
}

async function sendMessage(text) {
  addUserMessage(text);
  const container = addAssistantContainer();
  addThinkingBubble(container);
  let currentText = null;
  const toolHolders = new Map(); // tool_use_id -> {card, holder}
  let resultStatus = null;
  beginActivity("thinking…");

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        mode: answerMode,
        model: currentModel || undefined,
      }),
    });

    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        if (!payload) continue;
        let event;
        try {
          event = JSON.parse(payload);
        } catch {
          continue;
        }
        // The first real content event (text, thinking, or a tool call)
        // replaces the initial "Thinking…" placeholder.
        if (
          event.type === "text" ||
          event.type === "thinking" ||
          event.type === "tool_use"
        ) {
          removeThinkingBubble(container);
        }
        resultStatus = handleEvent(
          event,
          container,
          toolHolders,
          (bubble) => {
            currentText = bubble;
          },
          () => currentText
        ) || resultStatus;
      }
    }
    endActivity(resultStatus || "ready");
  } catch (err) {
    removeThinkingBubble(container);
    const errBubble = document.createElement("div");
    errBubble.className = "bubble bubble-assistant";
    errBubble.textContent = `Error: ${err.message}`;
    container.appendChild(errBubble);
    endActivity("error");
  }
}

function handleEvent(event, container, toolHolders, setCurrent, getCurrent) {
  switch (event.type) {
    case "session":
      sessionId = event.session_id;
      localStorage.setItem(SESSION_KEY, sessionId);
      break;
    case "text": {
      let bubble = getCurrent();
      if (!bubble) {
        bubble = addTextBubble(container);
        setCurrent(bubble);
      }
      bubble.dataset.raw = (bubble.dataset.raw || "") + event.text;
      bubble.innerHTML = renderMarkdown(bubble.dataset.raw);
      scrollDown();
      break;
    }
    case "tool_use": {
      setCurrent(null); // text stream ends when a tool call starts
      activityBaseLabel = `running ${event.name}`;
      const holders = addToolCard(container, event.name, event.input);
      toolHolders.set(event.id, { card: holders.card, holder: holders.resultHolder });
      scrollDown();
      break;
    }
    case "tool_result": {
      const holder = toolHolders.get(event.tool_use_id);
      if (holder) {
        fillToolResult(holder, event.content || "(empty)", event.is_error);
      }
      activityBaseLabel = "thinking…";
      scrollDown();
      break;
    }
    case "result": {
      const fmtTokens = (n) => {
        if (!n) return "0";
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
        if (n >= 1_000) return (n / 1_000).toFixed(1) + "k";
        return String(n);
      };
      const inTok = event.input_tokens || 0;
      const outTok = event.output_tokens || 0;
      const turns = `${event.num_turns} turn${event.num_turns === 1 ? "" : "s"}`;
      const tokens =
        inTok || outTok
          ? ` · ${fmtTokens(inTok)} in · ${fmtTokens(outTok)} out`
          : "";
      return `done · ${turns}${tokens}`;
    }
    case "error": {
      const errBubble = document.createElement("div");
      errBubble.className = "bubble bubble-assistant";
      errBubble.textContent = `Error: ${event.message}`;
      container.appendChild(errBubble);
      break;
    }
    case "done":
      break;
  }
  return null;
}

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 14 * 16) + "px";
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (busy) {
      interruptActiveRun();
      return;
    }
    formEl.requestSubmit();
  }
});

formEl.addEventListener("submit", (e) => {
  e.preventDefault();
  if (busy) {
    interruptActiveRun();
    return;
  }
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  inputEl.style.height = "auto";
  sendMessage(text);
});

newChatBtn.addEventListener("click", async () => {
  await fetch("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "", session_id: sessionId }),
  });
  sessionId = null;
  localStorage.removeItem(SESSION_KEY);
  messagesEl.innerHTML = "";
  renderAttachedFiles([]);
  setStatus("ready");
});

// ----- File attachments -------------------------------------------------

function ensureSessionId() {
  if (!sessionId) {
    sessionId =
      (crypto.randomUUID && crypto.randomUUID()) ||
      String(Date.now()) + "-" + Math.random().toString(36).slice(2);
    localStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function renderAttachedFiles(files) {
  attachedFilesEl.innerHTML = "";
  if (!files || files.length === 0) {
    attachedFilesEl.classList.add("hidden");
    attachedFilesEl.classList.remove("flex");
    return;
  }
  attachedFilesEl.classList.remove("hidden");
  attachedFilesEl.classList.add("flex");
  for (const f of files) {
    const chip = document.createElement("div");
    chip.className = "file-chip";
    const nameEl = document.createElement("span");
    nameEl.className = "file-chip-name";
    nameEl.textContent = f.name;
    nameEl.title = f.path || f.name;
    const sizeEl = document.createElement("span");
    sizeEl.className = "file-chip-size";
    sizeEl.textContent = formatSize(f.size);
    const rmBtn = document.createElement("button");
    rmBtn.type = "button";
    rmBtn.className = "file-chip-remove";
    rmBtn.title = "Remove";
    rmBtn.textContent = "×";
    rmBtn.addEventListener("click", () => removeAttachedFile(f.name));
    chip.appendChild(nameEl);
    chip.appendChild(sizeEl);
    chip.appendChild(rmBtn);
    attachedFilesEl.appendChild(chip);
  }
}

async function refreshAttachedFiles() {
  if (!sessionId) {
    renderAttachedFiles([]);
    return;
  }
  try {
    const resp = await fetch(
      `/api/uploads/${encodeURIComponent(sessionId)}`
    );
    if (!resp.ok) return;
    const data = await resp.json();
    renderAttachedFiles(data.files || []);
  } catch (_) {}
}

async function uploadFile(file) {
  ensureSessionId();
  const fd = new FormData();
  fd.append("session_id", sessionId);
  fd.append("file", file);
  const resp = await fetch("/api/upload", { method: "POST", body: fd });
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (body && body.detail) msg = body.detail;
    } catch (_) {}
    throw new Error(msg);
  }
  const data = await resp.json();
  renderAttachedFiles(data.files || []);
}

async function removeAttachedFile(name) {
  if (!sessionId) return;
  const resp = await fetch(
    `/api/uploads/${encodeURIComponent(sessionId)}/${encodeURIComponent(name)}`,
    { method: "DELETE" }
  );
  if (!resp.ok) return;
  const data = await resp.json();
  renderAttachedFiles(data.files || []);
}

attachBtn.addEventListener("click", () => fileInputEl.click());

fileInputEl.addEventListener("change", async () => {
  const files = Array.from(fileInputEl.files || []);
  fileInputEl.value = "";
  if (files.length === 0) return;
  attachBtn.classList.add("busy");
  attachBtn.disabled = true;
  try {
    for (const f of files) {
      try {
        await uploadFile(f);
      } catch (err) {
        alert(`Upload failed (${f.name}): ${err.message}`);
      }
    }
  } finally {
    attachBtn.classList.remove("busy");
    attachBtn.disabled = false;
  }
});

function renderTemplates() {
  const el = document.getElementById("templates");
  if (!el) return;
  el.innerHTML = "";
  for (const t of TEMPLATES) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = t.label;
    btn.addEventListener("click", () => {
      inputEl.value = t.prompt;
      inputEl.focus();
      inputEl.style.height = "auto";
      inputEl.style.height =
        Math.min(inputEl.scrollHeight, 14 * 16) + "px";
      const start = t.prompt.indexOf(t.placeholder);
      if (start >= 0) {
        inputEl.setSelectionRange(start, start + t.placeholder.length);
      }
    });
    el.appendChild(btn);
  }
}

async function loadRepos() {
  try {
    const resp = await fetch("/api/repos");
    const data = await resp.json();
    reposListEl.innerHTML = "";
    for (const repo of data.repos || []) {
      const li = document.createElement("li");
      li.className = "skill-card";
      const status = repo.ready
        ? `<span class="repo-head">@${escapeHtml(repo.head || "?")}</span>`
        : `<span class="repo-head repo-head-pending">cloning…</span>`;
      li.innerHTML = `<div class="skill-name">${escapeHtml(
        repo.name
      )} ${status}</div><div class="skill-desc">${escapeHtml(
        repo.description || ""
      )}</div>`;
      reposListEl.appendChild(li);
    }
  } catch (_) {
    reposListEl.innerHTML =
      '<li class="text-sm font-normal text-brand-gray">Could not load repo list.</li>';
  }
}

function renderModeToggle() {
  const group = document.getElementById("mode-toggle");
  if (!group) return;
  for (const btn of group.querySelectorAll(".mode-btn")) {
    const isActive = btn.dataset.mode === answerMode;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-checked", isActive ? "true" : "false");
  }
}

document.getElementById("mode-toggle")?.addEventListener("click", (e) => {
  const btn = e.target.closest(".mode-btn");
  if (!btn || !VALID_MODES.includes(btn.dataset.mode)) return;
  answerMode = btn.dataset.mode;
  localStorage.setItem(MODE_KEY, answerMode);
  renderModeToggle();
});

// ----- Model selection + API key --------------------------------------

const modelSelectEl = document.getElementById("model-select");
const apiKeySetEl = document.getElementById("api-key-set");
const apiKeyEditEl = document.getElementById("api-key-edit");
const apiKeyPreviewEl = document.getElementById("api-key-preview");
const apiKeyInput = document.getElementById("api-key-input");
const apiKeySave = document.getElementById("api-key-save");
const apiKeyStatus = document.getElementById("api-key-status");
const apiKeyChangeBtn = document.getElementById("api-key-change");
const apiKeyCancelBtn = document.getElementById("api-key-cancel");

let apiKeyIsSet = false;

function renderApiKeyUI(config) {
  apiKeyIsSet = !!(config && config.has_api_key);
  if (apiKeyIsSet) {
    apiKeyPreviewEl.textContent = (config && config.api_key_preview) || "";
    apiKeySetEl.classList.remove("hidden");
    apiKeyEditEl.classList.add("hidden");
    // Leaving the edit form mid-typing and coming back: clear it.
    apiKeyInput.value = "";
    apiKeyStatus.textContent = "";
  } else {
    apiKeySetEl.classList.add("hidden");
    apiKeyEditEl.classList.remove("hidden");
    // Cancel only makes sense when a key is already set to revert to.
    apiKeyCancelBtn.classList.add("hidden");
  }
}

function showApiKeyEditor() {
  apiKeySetEl.classList.add("hidden");
  apiKeyEditEl.classList.remove("hidden");
  // With a key already configured, offer Cancel to go back to the set view.
  if (apiKeyIsSet) {
    apiKeyCancelBtn.classList.remove("hidden");
  } else {
    apiKeyCancelBtn.classList.add("hidden");
  }
  apiKeyInput.focus();
}

async function resetSession() {
  try {
    await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "", session_id: sessionId }),
    });
  } catch (_) {}
  sessionId = null;
  localStorage.removeItem(SESSION_KEY);
  messagesEl.innerHTML = "";
  renderAttachedFiles([]);
  setStatus("ready");
}

async function loadConfig() {
  try {
    const resp = await fetch("/api/config");
    if (!resp.ok) return;
    const data = await resp.json();

    // --- populate the model dropdown ---------------------------------
    modelSelectEl.innerHTML = "";
    availableModelIds = new Set();
    for (const m of data.models || []) {
      availableModelIds.add(m.id);
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.label;
      modelSelectEl.appendChild(opt);
    }
    let chosen = currentModel;
    if (!chosen || !availableModelIds.has(chosen)) {
      chosen = data.default_model;
    }
    if (!chosen && data.models && data.models.length) {
      chosen = data.models[0].id;
    }
    if (chosen) {
      modelSelectEl.value = chosen;
      currentModel = chosen;
      localStorage.setItem(MODEL_KEY, chosen);
    }

    // --- render the API-key section -----------------------------------
    renderApiKeyUI(data);
  } catch (_) {}
}

modelSelectEl.addEventListener("change", async (e) => {
  const newModel = e.target.value;
  if (newModel === currentModel) return;

  const hasMessages = !!messagesEl.querySelector(".bubble");
  if (hasMessages) {
    const ok = confirm(
      "Switching the model starts a fresh chat — conversation history for the current model will be lost. Continue?"
    );
    if (!ok) {
      modelSelectEl.value = currentModel;
      return;
    }
    await resetSession();
  }

  currentModel = newModel;
  localStorage.setItem(MODEL_KEY, newModel);
  setStatus(`model · ${modelSelectEl.options[modelSelectEl.selectedIndex].text}`);
});

apiKeySave.addEventListener("click", async () => {
  const key = (apiKeyInput.value || "").trim();
  if (!key) {
    apiKeyStatus.textContent = "Paste a key first.";
    return;
  }
  apiKeyStatus.textContent = "Saving…";
  apiKeySave.disabled = true;
  try {
    const resp = await fetch("/api/api-key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${resp.status}`);
    }
    // Re-fetch config so the preview reflects the key we just stored,
    // and flip the sidebar back to the "configured" state.
    await loadConfig();
    apiKeyStatus.textContent = "";
  } catch (err) {
    apiKeyStatus.textContent = `Failed: ${err.message}`;
  } finally {
    apiKeySave.disabled = false;
  }
});

apiKeyChangeBtn.addEventListener("click", showApiKeyEditor);

apiKeyCancelBtn.addEventListener("click", () => {
  apiKeyInput.value = "";
  apiKeyStatus.textContent = "";
  if (apiKeyIsSet) {
    apiKeySetEl.classList.remove("hidden");
    apiKeyEditEl.classList.add("hidden");
  }
});

renderModeToggle();
renderTemplates();
loadRepos();
loadConfig();
refreshAttachedFiles();
// Poll the repo list every 10s until every clone is finished — the initial
// clone on a cold container can take a minute or two.
const repoPoll = setInterval(async () => {
  try {
    const resp = await fetch("/api/repos");
    const data = await resp.json();
    if ((data.repos || []).every((r) => r.ready)) {
      clearInterval(repoPoll);
    }
    await loadRepos();
  } catch (_) {}
}, 10_000);
