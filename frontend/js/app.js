/**
 * Agent Product Studio — Main Application
 */

// ─── State ──────────────────────────────────────────────────────────────────
const state = {
  sessionId: crypto.randomUUID(),
  userId: 'kathan',
  messages: [],
  activeProject: null,
  pendingFiles: [],
  isStreaming: false,
  activities: [],        // recent activity feed
  currentTimeline: null, // timeline DOM element for current response
};

const AGENT_EMOJIS = {
  orchestrator: '🧠', architect_agent: '📐', coder_agent: '💻',
  infra_agent: '🏗️', reviewer_agent: '🔍',
};
const AGENT_LABELS = {
  orchestrator: 'Orchestrator', architect_agent: 'Architect', coder_agent: 'Coder',
  infra_agent: 'Infra', reviewer_agent: 'Reviewer',
};

// ─── DOM refs ───────────────────────────────────────────────────────────────
const $messages    = document.getElementById('messages-container');
const $welcome     = document.getElementById('welcome-state');
const $chatInput   = document.getElementById('chat-input');
const $sendBtn     = document.getElementById('send-btn');
const $fileInput   = document.getElementById('file-input');
const $fileBar     = document.getElementById('file-preview-bar');
const $previewDot  = document.getElementById('preview-dot');
const $previewName = document.getElementById('preview-project-name');
const $iframe      = document.getElementById('preview-iframe');
const $previewEmpty = document.getElementById('preview-empty');
const $historyList  = document.getElementById('chat-history-list');
const $activityFeed = document.getElementById('activity-feed');
const $sessionLabel = document.getElementById('session-label');

// ─── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadSessions();
  loadProjects();
  setupPaste();
  setupInputWatch();
});

function setupInputWatch() {
  $chatInput.addEventListener('input', () => {
    $sendBtn.disabled = !$chatInput.textContent.trim() && !state.pendingFiles.length;
  });
}

// Paste image from clipboard
function setupPaste() {
  document.addEventListener('paste', (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) addPendingFile(file);
      }
    }
  });
}

// ─── Tab switching ──────────────────────────────────────────────────────────
function switchTab(tab) {
  const chatView = document.getElementById('view-chat');
  const previewView = document.getElementById('view-preview');
  const tabChat = document.getElementById('tab-chat');
  const tabPreview = document.getElementById('tab-preview');
  if (tab === 'chat') {
    chatView.classList.remove('hidden'); chatView.style.display = 'flex';
    previewView.classList.add('hidden'); previewView.style.display = '';
    tabChat.className = 'tab tab-active';
    tabPreview.className = 'tab tab-inactive';
  } else {
    chatView.classList.add('hidden'); chatView.style.display = '';
    previewView.classList.remove('hidden'); previewView.style.display = 'flex';
    tabChat.className = 'tab tab-inactive';
    tabPreview.className = 'tab tab-active';
    $previewDot.classList.add('hidden');
    if (state.activeProject) loadPreview(state.activeProject);
  }
}

// ─── Sessions ───────────────────────────────────────────────────────────────
async function loadSessions() {
  const sessions = await fetchSessions();
  $historyList.innerHTML = '';
  sessions.forEach(s => {
    const active = s.id === state.sessionId;
    const div = document.createElement('div');
    div.className = `history-item${active ? ' active' : ''}`;
    div.innerHTML = `<div class="title">${esc(s.title || 'New Session')}</div>
      <div class="date">${formatDate(s.timestamp)}</div>`;
    div.onclick = () => loadSession(s.id);
    $historyList.appendChild(div);
  });
}

function loadSession(id) {
  // TODO: load session from backend and restore messages
  state.sessionId = id;
  loadSessions();
}

function newSession() {
  state.sessionId = crypto.randomUUID();
  state.messages = [];
  state.activeProject = null;
  state.activities = [];
  $messages.innerHTML = '';
  $messages.appendChild(createWelcome());
  $sessionLabel.textContent = 'New Session';
  $previewDot.classList.add('hidden');
  loadSessions();
  updateActivityFeed();
}

function persistSession() {
  const title = state.messages.find(m => m.role === 'user')?.content?.slice(0, 40) || 'New Session';
  saveSession(state.sessionId, {
    id: state.sessionId,
    title,
    timestamp: new Date().toISOString(),
    messages: state.messages,
    active_project: state.activeProject,
  });
  loadSessions();
}

// ─── Projects / Activity ────────────────────────────────────────────────────
async function loadProjects() {
  const projects = await fetchProjects();
  if (projects.length) {
    projects.forEach(p => addActivity('📦', `Project <strong>${esc(p)}</strong> exists`, ''));
  }
}

function addActivity(icon, text, time) {
  state.activities.unshift({ icon, text, time: time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
  if (state.activities.length > 20) state.activities.pop();
  updateActivityFeed();
}

function updateActivityFeed() {
  if (!state.activities.length) {
    $activityFeed.innerHTML = '<div class="activity-empty">No activity yet. Start a conversation!</div>';
    return;
  }
  $activityFeed.innerHTML = state.activities.map(a =>
    `<div class="activity-item slide-in">
      <span class="activity-icon">${a.icon}</span>
      <span class="activity-text">${a.text}</span>
      <span class="activity-time">${a.time}</span>
    </div>`
  ).join('');
}

// ─── File handling ──────────────────────────────────────────────────────────
function handleFiles(fileList) {
  for (const f of fileList) addPendingFile(f);
  $fileInput.value = '';
}

function addPendingFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    state.pendingFiles.push({ name: file.name, type: file.type, data: reader.result.split(',')[1] });
    renderFileBar();
    $sendBtn.disabled = false;
  };
  reader.readAsDataURL(file);
}

function removePendingFile(idx) {
  state.pendingFiles.splice(idx, 1);
  renderFileBar();
  $sendBtn.disabled = !$chatInput.textContent.trim() && !state.pendingFiles.length;
}

function renderFileBar() {
  if (!state.pendingFiles.length) { $fileBar.classList.add('hidden'); return; }
  $fileBar.classList.remove('hidden');
  $fileBar.innerHTML = state.pendingFiles.map((f, i) =>
    `<span class="file-chip">📎 ${esc(f.name)} <button onclick="removePendingFile(${i})">×</button></span>`
  ).join('');
}

// ─── Send message ───────────────────────────────────────────────────────────
function handleInputKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function sendSuggestion(text) {
  $chatInput.textContent = text;
  sendMessage();
}

async function sendMessage() {
  const text = $chatInput.textContent.trim();
  if (!text && !state.pendingFiles.length) return;
  if (state.isStreaming) return;

  // Hide welcome
  if ($welcome) $welcome.remove();

  // Build display
  let display = text;
  const fileNames = state.pendingFiles.map(f => f.name);
  if (fileNames.length) display += (text ? '\n' : '') + fileNames.map(n => `📎 ${n}`).join('\n');

  // Add user message
  state.messages.push({ role: 'user', content: display });
  appendUserMessage(display);

  // Clear input
  $chatInput.textContent = '';
  const files = [...state.pendingFiles];
  state.pendingFiles = [];
  renderFileBar();
  $sendBtn.disabled = true;

  // Update session label
  if (state.messages.filter(m => m.role === 'user').length === 1) {
    $sessionLabel.textContent = text.slice(0, 50);
  }

  // Create assistant message container
  const { msgEl, textEl, timelineEl } = appendAssistantMessage();
  state.currentTimeline = timelineEl;
  state.isStreaming = true;

  // Add typing indicator
  const typingEl = document.createElement('div');
  typingEl.className = 'typing-indicator';
  typingEl.innerHTML = '<span></span><span></span><span></span>';
  textEl.appendChild(typingEl);

  let fullText = '';
  let toolCalls = [];

  await streamChat({
    sessionId: state.sessionId,
    userId: state.userId,
    message: text,
    files: files,

    onAgentStart: (data) => {
      const emoji = AGENT_EMOJIS[data.agent] || '🤖';
      const label = data.label || AGENT_LABELS[data.agent] || data.agent;
      addTimelineItem(timelineEl, data.agent, emoji, label, 'Activated', '');
      addActivity(emoji, `<strong>${label}</strong> activated`, '');
    },

    onToolCall: (data) => {
      const emoji = AGENT_EMOJIS[data.agent] || '🤖';
      const label = data.label || AGENT_LABELS[data.agent] || data.agent;
      const argStr = Object.entries(data.args || {}).map(([k, v]) => {
        const val = typeof v === 'string' ? v : JSON.stringify(v);
        return `<span class="highlight">${val.length > 40 ? val.slice(0, 40) + '...' : val}</span>`;
      }).join(', ');
      addTimelineItem(timelineEl, data.agent, emoji, label, `${data.tool}(${argStr})`, '');
      toolCalls.push(data);

      // Detect project name
      if (data.args?.project_name) {
        state.activeProject = data.args.project_name;
        $previewName.textContent = state.activeProject;
      }

      // Detect preview ready
      if (data.preview_ready) {
        $previewDot.classList.remove('hidden');
        addActivity('👁️', `Preview ready for <strong>${esc(state.activeProject)}</strong>`, '');
      }

      addActivity(emoji, `<strong>${label}</strong> → ${esc(data.tool)}()`, '');
    },

    onTextDelta: (data) => {
      if (typingEl.parentNode) typingEl.remove();
      fullText += data.content;
      textEl.innerHTML = marked.parse(fullText);
    },

    onDone: (data) => {
      if (typingEl.parentNode) typingEl.remove();
      if (!fullText) {
        fullText = "I've processed your request.";
        textEl.innerHTML = marked.parse(fullText);
      }
      if (data.active_project) {
        state.activeProject = data.active_project;
        $previewName.textContent = state.activeProject;
      }
      state.messages.push({ role: 'assistant', content: fullText, tools: toolCalls });
      state.isStreaming = false;
      persistSession();
    },

    onError: (data) => {
      if (typingEl.parentNode) typingEl.remove();
      fullText = `⚠️ Error: ${data.message}`;
      textEl.innerHTML = `<p style="color:#ef4444">${esc(fullText)}</p>`;
      state.messages.push({ role: 'assistant', content: fullText });
      state.isStreaming = false;
    },
  });

  scrollToBottom();
}

// ─── Preview ────────────────────────────────────────────────────────────────
async function loadPreview(projectName) {
  const url = await fetchPreviewUrl(projectName);
  try {
    const res = await fetch(url);
    if (res.ok) {
      const html = await res.text();
      if (html && html.trim().length > 0) {
        $iframe.srcdoc = html;
        $iframe.style.display = 'block';
        $previewEmpty.classList.add('hidden');
      } else {
        $iframe.style.display = 'none';
        $previewEmpty.classList.remove('hidden');
      }
    } else {
      $iframe.style.display = 'none';
      $previewEmpty.classList.remove('hidden');
    }
  } catch {
    $iframe.style.display = 'none';
    $previewEmpty.classList.remove('hidden');
  }
}

function requestChanges() {
  switchTab('chat');
  $chatInput.textContent = 'I want to change the design: ';
  $chatInput.focus();
  // Move cursor to end
  const range = document.createRange();
  range.selectNodeContents($chatInput);
  range.collapse(false);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}

function approveDesign() {
  switchTab('chat');
  $chatInput.textContent = 'Looks great! Go ahead and build it.';
  sendMessage();
}

// ─── DOM builders ───────────────────────────────────────────────────────────
function appendUserMessage(content) {
  const div = document.createElement('div');
  div.className = 'msg fade-in';
  div.innerHTML = `
    <div class="msg-avatar msg-avatar-user">K</div>
    <div class="msg-content">
      <div class="msg-text">${marked.parse(content)}</div>
    </div>`;
  $messages.appendChild(div);
  scrollToBottom();
}

function appendAssistantMessage() {
  const div = document.createElement('div');
  div.className = 'msg fade-in';
  const textEl = document.createElement('div');
  textEl.className = 'msg-text';
  const timelineEl = document.createElement('div');
  timelineEl.className = 'agent-timeline hidden';
  timelineEl.innerHTML = '<div class="timeline-label">Agent Activity</div>';

  div.innerHTML = `
    <div class="msg-avatar" style="background:linear-gradient(135deg,rgba(167,139,250,0.2),rgba(99,102,241,0.2)); border:1px solid rgba(167,139,250,0.3)">🧠</div>
    <div class="msg-content">
      <div class="msg-author" style="color:#a78bfa">Orchestrator</div>
    </div>`;
  div.querySelector('.msg-content').appendChild(textEl);
  div.querySelector('.msg-content').appendChild(timelineEl);
  $messages.appendChild(div);
  scrollToBottom();
  return { msgEl: div, textEl, timelineEl };
}

function addTimelineItem(container, agent, emoji, label, detail, time) {
  container.classList.remove('hidden');
  const item = document.createElement('div');
  item.className = `timeline-item tl-${agent}`;
  item.innerHTML = `
    <span class="timeline-icon">${emoji}</span>
    <span class="timeline-agent">${label}</span>
    <span class="timeline-arrow">→</span>
    <span class="timeline-detail">${detail}</span>`;
  container.appendChild(item);
  scrollToBottom();
}

function createWelcome() {
  const div = document.createElement('div');
  div.id = 'welcome-state';
  div.className = 'welcome-state';
  div.innerHTML = `<div class="welcome-card">
    <div class="welcome-icon">🏭</div>
    <h2 class="welcome-title">What would you like to build?</h2>
    <p class="welcome-sub">Describe your application and I'll design it, code it, and deploy it.</p>
    <div class="welcome-suggestions">
      <button class="suggestion-chip" onclick="sendSuggestion(this.textContent)">Build a marketing analytics dashboard</button>
      <button class="suggestion-chip" onclick="sendSuggestion(this.textContent)">Update the police-data-viewer with a heatmap</button>
      <button class="suggestion-chip" onclick="sendSuggestion(this.textContent)">What projects exist in my workspace?</button>
    </div>
  </div>`;
  return div;
}

// ─── Helpers ────────────────────────────────────────────────────────────────
function scrollToBottom() {
  requestAnimationFrame(() => { $messages.scrollTop = $messages.scrollHeight; });
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return `Today, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ', ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
