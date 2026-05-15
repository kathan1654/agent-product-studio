/**
 * Agent Product Studio — API Layer
 * WebSocket streaming + REST endpoints
 */

const API_BASE = window.location.origin;
const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;

// ─── REST helpers ───────────────────────────────────────────────────────────
async function fetchProjects() {
  try {
    const res = await fetch(`${API_BASE}/api/projects`);
    const data = await res.json();
    return data.projects || [];
  } catch { return []; }
}

async function fetchSessions() {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`);
    const data = await res.json();
    return data.sessions || [];
  } catch { return []; }
}

async function saveSession(sessionId, data) {
  try {
    await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  } catch (e) { console.warn('Failed to save session:', e); }
}

async function fetchPreviewUrl(projectName) {
  return `${API_BASE}/api/preview/${encodeURIComponent(projectName)}`;
}

// ─── WebSocket streaming chat ───────────────────────────────────────────────
function streamChat({ sessionId, userId, message, files, onAgentStart, onToolCall, onTextDelta, onDone, onError }) {
  return new Promise((resolve) => {
    const ws = new WebSocket(`${WS_BASE}/api/chat`);

    ws.onopen = () => {
      ws.send(JSON.stringify({
        session_id: sessionId,
        user_id: userId || 'kathan',
        message: message,
        files: files || [],
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'agent_start':
          onAgentStart?.(data);
          break;
        case 'tool_call':
          onToolCall?.(data);
          break;
        case 'text_delta':
          onTextDelta?.(data);
          break;
        case 'done':
          onDone?.(data);
          resolve(data);
          break;
        case 'error':
          onError?.(data);
          resolve(data);
          break;
      }
    };

    ws.onerror = (err) => {
      onError?.({ message: 'WebSocket connection failed' });
      resolve({ type: 'error' });
    };

    ws.onclose = () => {};
  });
}
