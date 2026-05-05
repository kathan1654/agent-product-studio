"""
Agent Product Studio — Streamlit Chat UI
Wraps the ADK orchestrator agent in a premium chat interface.
"""
import asyncio
import uuid
import json
import os
import re
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from orchestrator.agent import root_agent
from orchestrator.tools.gcs_tools import list_projects

# ─── Directories & Helpers ───────────────────────────────────────────────────
SESSIONS_DIR = "C:/GCP/agent_product_studio/.adk/studio_sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def save_session_history(session_id, messages, active_project):
    """Save the chat history and active project to disk."""
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    # Determine a title from the first user message if available
    title = "New Session"
    for m in messages:
        if m["role"] == "user":
            title = m["content"][:30] + ("..." if len(m["content"]) > 30 else "")
            break
            
    data = {
        "id": session_id,
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "messages": messages,
        "active_project": active_project
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def load_session_history(session_id):
    """Load chat history from disk."""
    filepath = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return None

def get_all_sessions():
    """Get all saved sessions ordered by newest first."""
    sessions = []
    for filename in os.listdir(SESSIONS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SESSIONS_DIR, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    sessions.append(data)
            except:
                pass
    return sorted(sessions, key=lambda x: x.get("timestamp", ""), reverse=True)


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agent Product Studio",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp {
        font-family: 'Inter', sans-serif;
        background-color: #0d1117;
    }

    /* Header */
    .studio-header {
        background: linear-gradient(135deg, rgba(26, 26, 46, 0.8) 0%, rgba(22, 33, 62, 0.8) 50%, rgba(15, 52, 96, 0.8) 100%);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        text-align: center;
    }
    .studio-header h1 {
        background: linear-gradient(135deg, #e94560 0%, #ff6b6b 50%, #ffa07a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.5px;
    }
    .studio-header p {
        color: rgba(255, 255, 255, 0.7);
        font-size: 1.05rem;
        margin: 0;
        font-weight: 300;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #e94560;
        font-size: 1.1rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-top: 1rem;
    }

    /* Session List */
    .session-item {
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.3rem;
        background: rgba(255,255,255,0.03);
        border: 1px solid transparent;
        cursor: pointer;
        transition: all 0.2s;
        font-size: 0.85rem;
        color: #c9d1d9;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .session-item:hover {
        background: rgba(255,255,255,0.08);
    }
    .session-active {
        background: rgba(233, 69, 96, 0.1);
        border: 1px solid rgba(233, 69, 96, 0.3);
        color: white;
        font-weight: 500;
    }

    /* Project cards & Active highlighting */
    .project-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .project-card .project-name {
        color: #c9d1d9;
        font-weight: 500;
        font-size: 0.9rem;
    }
    /* The active project glow animation */
    @keyframes pulse-border {
        0% { box-shadow: 0 0 0 0 rgba(88, 166, 255, 0.4); }
        70% { box-shadow: 0 0 0 6px rgba(88, 166, 255, 0); }
        100% { box-shadow: 0 0 0 0 rgba(88, 166, 255, 0); }
    }
    .project-active {
        background: rgba(88, 166, 255, 0.1);
        border: 1px solid #58a6ff;
        animation: pulse-border 2s infinite;
    }
    .project-active .project-name {
        color: white;
        font-weight: 600;
    }

    /* Chat messages */
    .stChatMessage {
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        background: rgba(255, 255, 255, 0.02) !important;
        padding: 1.5rem !important;
    }
    
    /* Terminal-style agent activity log */
    .terminal-container {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        margin-top: 0.5rem;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.5);
    }
    .terminal-header {
        color: #8b949e;
        border-bottom: 1px solid #30363d;
        padding-bottom: 0.5rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 1px;
    }
    .agent-activity {
        margin: 0.4rem 0;
        color: #c9d1d9;
    }
    .agent-name {
        color: #ff7b72;
        font-weight: 600;
    }
    .tool-call {
        color: #79c0ff;
    }
    .terminal-cursor {
        display: inline-block;
        width: 8px;
        height: 15px;
        background: #3fb950;
        animation: blink 1s step-end infinite;
        vertical-align: middle;
        margin-left: 4px;
    }
    @keyframes blink { 50% { opacity: 0; } }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ────────────────────────────────────────────
if "session_service" not in st.session_state:
    st.session_state.session_service = InMemorySessionService()

if "runner" not in st.session_state:
    st.session_state.runner = Runner(
        agent=root_agent,
        app_name="agent-product-studio",
        session_service=st.session_state.session_service,
    )

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "user_id" not in st.session_state:
    st.session_state.user_id = "kathan"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_initialized" not in st.session_state:
    st.session_state.session_initialized = False

if "active_project" not in st.session_state:
    st.session_state.active_project = None


# ─── Helper: Initialize ADK Session ─────────────────────────────────────────
async def ensure_session():
    """Create the ADK session if it doesn't exist yet."""
    if not st.session_state.session_initialized:
        await st.session_state.session_service.create_session(
            app_name="agent-product-studio",
            user_id=st.session_state.user_id,
            session_id=st.session_state.session_id,
        )
        st.session_state.session_initialized = True

def switch_session(new_session_id):
    """Switch to a different saved session."""
    data = load_session_history(new_session_id)
    if data:
        st.session_state.session_id = new_session_id
        st.session_state.messages = data.get("messages", [])
        st.session_state.active_project = data.get("active_project")
        st.session_state.session_initialized = False # Re-init adk session
        st.rerun()

def extract_project_name(text):
    """Attempt to extract project name from agent tool calls."""
    # Look for save_requirements(project_name='xyz') or list_files(project_name='xyz')
    match = re.search(r"project_name=['\"]([^'\"]+)['\"]", text)
    if match:
        return match.group(1)
    return None

# ─── Helper: Run Agent ───────────────────────────────────────────────────────
async def run_agent(prompt: str):
    """Send a message to the orchestrator and collect the response."""
    await ensure_session()

    # Fixed bug: pass prompt to text keyword argument
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)],
    )

    full_response = ""
    agent_activities = []

    async for event in st.session_state.runner.run_async(
        user_id=st.session_state.user_id,
        session_id=st.session_state.session_id,
        new_message=content,
    ):
        # Track agent activities (tool calls, sub-agent handoffs)
        if event.author and event.author != "orchestrator":
            agent_activities.append(f"<span class='agent-name'>[{event.author}]</span> Processing requirements...")

        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args_str = ', '.join(f'{k}={v}' for k, v in (fc.args or {}).items())
                    activity_str = f"<span class='tool-call'>➜ {fc.name}</span>({args_str})"
                    agent_activities.append(activity_str)
                    
                    # Auto-detect active project
                    proj = extract_project_name(args_str)
                    if proj:
                        st.session_state.active_project = proj

                elif hasattr(part, "text") and part.text:
                    # Only capture final orchestrator responses
                    if event.author == "orchestrator" or not event.author:
                        full_response += part.text

    # Auto-detect project from full response if not found in tools
    if not st.session_state.active_project:
        # Check if the orchestrator mentions "Updating <project_name>"
        match = re.search(r"Updating\s+([a-zA-Z0-9-]+)", full_response)
        if match:
            st.session_state.active_project = match.group(1)

    return full_response, agent_activities


def sync_run_agent(prompt: str):
    """Synchronous wrapper for the async agent runner."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run_agent(prompt))
    finally:
        loop.close()


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏭 Agent Product Studio")
    st.markdown("---")

    # New Session button
    if st.button("➕ New Session", use_container_width=True, type="primary"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.active_project = None
        st.session_state.session_initialized = False
        st.rerun()
        
    # Chat History
    all_sessions = get_all_sessions()
    if all_sessions:
        st.markdown("## 💬 Chat History")
        for s in all_sessions:
            # Highlight active session
            is_active = (s["id"] == st.session_state.session_id)
            active_class = "session-active" if is_active else ""
            date_str = datetime.fromisoformat(s["timestamp"]).strftime("%b %d, %H:%M")
            
            # Use columns for button-like behavior without native st.button weirdness
            if st.button(f"📄 {s['title']} \n ({date_str})", key=f"btn_{s['id']}", use_container_width=True):
                if not is_active:
                    switch_session(s["id"])

    st.markdown("---")

    # Project Explorer
    st.markdown("## 📂 Products Created")
    try:
        projects = list_projects()
        if projects and projects[0] != "(no projects yet)":
            for proj in projects:
                is_active_proj = (proj == st.session_state.active_project)
                active_class = "project-active" if is_active_proj else ""
                icon = "🔥" if is_active_proj else "📦"
                
                st.markdown(
                    f'<div class="project-card {active_class}">'
                    f'<span style="font-size: 1.2rem;">{icon}</span>'
                    f'<span class="project-name">{proj}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No projects yet. Start building!")
    except Exception:
        st.caption("Unable to load projects.")

    st.markdown("---")

    # Session info
    st.markdown("## ⚙️ Environment")
    st.caption(f"**Model:** Gemini 2.5 Pro")
    st.caption(f"**Agents:** 5-Agent Hierarchy")

    st.markdown("---")
    st.markdown(
        '<p style="color: rgba(255,255,255,0.3); font-size: 0.75rem; text-align: center;">'
        "Powered by Google ADK + Vertex AI</p>",
        unsafe_allow_html=True,
    )


# ─── Main Content ────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="studio-header">
        <h1>Agent Product Studio</h1>
        <p>Build production-ready Streamlit applications on GCP using natural language.<br>
        Powered by a multi-agent AI factory.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_chat, tab_preview = st.tabs(["💬 Chat", "👁️ Visual Preview"])

with tab_chat:
    # Empty State
    if not st.session_state.messages:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.info("👋 **Welcome to the Studio!**\n\nTry asking me to build something:\n\n"
                    "- *\"Build a marketing dashboard using the sales_raw dataset\"*\n"
                    "- *\"Update the police-data-viewer to add a priority heatmap\"*\n"
                    "- *\"What projects exist in my workspace?\"*")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🏭" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])
            if msg.get("activities"):
                with st.expander("Terminal Logs", expanded=False):
                    st.markdown('<div class="terminal-container">', unsafe_allow_html=True)
                    st.markdown('<div class="terminal-header">sys.stdout — Agent Trace</div>', unsafe_allow_html=True)
                    for activity in msg["activities"]:
                        st.markdown(f'<div class="agent-activity">{activity}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="agent-activity">> Execution complete.<span class="terminal-cursor"></span></div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

with tab_preview:
    if st.session_state.active_project:
        from orchestrator.tools.gcs_tools import read_file
        try:
            mockup_html = read_file(st.session_state.active_project, "mockup.html")
            if mockup_html and "File not found" not in mockup_html:
                st.components.v1.html(mockup_html, height=800, scrolling=True)
            else:
                st.info("No visual wireframe has been generated for this project yet. Ask the agents to build one!")
        except Exception:
            st.info("No visual wireframe available.")
    else:
        st.info("Select or create a project to see its visual wireframe.")

# Chat input
if prompt := st.chat_input("Tell me what to build...", accept_file="multiple"):
    prompt_text = ""
    uploaded_files = []
    
    if hasattr(prompt, "text"):
        prompt_text = prompt.text
        uploaded_files = prompt.files or []
    else:
        prompt_text = prompt
        
    # Build the display message (including file info if any)
    display_content = prompt_text
    if uploaded_files:
        display_content += "\n\n" + "\n".join(f"📎 `{f.name}`" for f in uploaded_files)
        if not prompt_text:
            display_content = "\n".join(f"📎 `{f.name}`" for f in uploaded_files)

    # Add user message to history
    st.session_state.messages.append({
        "role": "user", 
        "content": display_content,
        "files": [{"name": f.name, "type": f.type, "bytes": f.getvalue()} for f in uploaded_files]
    })
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(display_content)

    # Get agent response
    with st.chat_message("assistant", avatar="🏭"):
        with st.spinner("Initializing AI factory..."):
            try:
                # Prepare parts for the ADK Runner
                parts = []
                if prompt_text:
                    parts.append(types.Part.from_text(text=prompt_text))
                for f in uploaded_files:
                    parts.append(types.Part.from_data(data=f.getvalue(), mime_type=f.type))
                
                # If no text was provided but files were uploaded, add a generic prompt
                if not prompt_text and uploaded_files:
                    parts.append(types.Part.from_text(text="Please analyze these attached files."))

                content = types.Content(role="user", parts=parts)
                
                # Run the agent with the prepared content
                full_response = ""
                agent_activities = []
                
                # Create an event loop for the async call
                loop = asyncio.new_event_loop()
                
                async def run_with_files(msg_content):
                    await ensure_session()
                    f_resp = ""
                    activities = []
                    async for event in st.session_state.runner.run_async(
                        user_id=st.session_state.user_id,
                        session_id=st.session_state.session_id,
                        new_message=msg_content,
                    ):
                        if event.author and event.author != "orchestrator":
                            activities.append(f"<span class='agent-name'>[{event.author}]</span> Processing requirements...")
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if hasattr(part, "function_call") and part.function_call:
                                    fc = part.function_call
                                    args_str = ', '.join(f'{k}={v}' for k, v in (fc.args or {}).items())
                                    activities.append(f"<span class='tool-call'>➜ {fc.name}</span>({args_str})")
                                    if fc.args and "project_name" in fc.args:
                                        st.session_state.active_project = fc.args["project_name"]
                                elif hasattr(part, "text") and part.text:
                                    if event.author == "orchestrator" or not event.author:
                                        f_resp += part.text
                    return f_resp, activities
                
                try:
                    response, activities = loop.run_until_complete(run_with_files(content))
                finally:
                    loop.close()
                
                # Auto-detect project from full response if not found in tools
                if not st.session_state.active_project:
                    match = re.search(r"Updating\s+([a-zA-Z0-9-]+)", response)
                    if match:
                        st.session_state.active_project = match.group(1)

                if response:
                    st.markdown(response)
                else:
                    response = "I've processed your request. Changes have been applied."
                    st.markdown(response)

                if activities:
                    with st.expander("Terminal Logs", expanded=False):
                        st.markdown('<div class="terminal-container">', unsafe_allow_html=True)
                        st.markdown('<div class="terminal-header">sys.stdout — Agent Trace</div>', unsafe_allow_html=True)
                        for activity in activities:
                            st.markdown(f'<div class="agent-activity">{activity}</div>', unsafe_allow_html=True)
                        st.markdown('<div class="agent-activity">> Execution complete.<span class="terminal-cursor"></span></div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                response = f"⚠️ Error communicating with agents: {str(e)}"
                activities = []
                st.error(response)

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "activities": activities,
    })
    
    # Persist session to disk
    save_session_history(
        st.session_state.session_id, 
        st.session_state.messages,
        st.session_state.active_project
    )
    
    # Rerun to update sidebar active project / history if needed
    st.rerun()
