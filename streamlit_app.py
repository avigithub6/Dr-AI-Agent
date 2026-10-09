import os
from uuid import UUID, uuid4
import requests
import streamlit as st
# ============================================================
# CONFIGURATION
# ============================================================
API_URL = os.getenv(
    "DR_AI_API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")
st.set_page_config(
    page_title="Dr AI | Medical Intelligence",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)
# ============================================================
# UI STYLING
# ============================================================
st.markdown("""
<style>
.stApp {
    background: #F5F8FC;
    color: #172B4D;
}
[data-testid="stHeader"] {
    background: #F5F8FC;
}
[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid #E4EAF1;
}
[data-testid="stSidebar"] * {
    color: #172B4D;
}
.block-container {
    max-width: 1250px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}
h1, h2, h3, p {
    color: #172B4D !important;
}
.hero {
    background: linear-gradient(120deg, #123C69, #087F8C);
    padding: 32px 36px;
    border-radius: 18px;
    margin-bottom: 25px;
    box-shadow: 0 8px 24px rgba(18,60,105,.12);
}
.hero h1, .hero h2, .hero p {
    color: white !important;
}
.hero p {
    opacity: .9;
}
.metric-card {
    background: white;
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #E4EAF1;
    margin-bottom: 15px;
}
.metric-card h3 {
    font-size: 14px;
    color: #64748B !important;
}
.metric-card strong {
    font-size: 25px;
    color: #123C69;
}
.info-card {
    background: #FFFFFF;
    border: 1px solid #E4EAF1;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
}
.info-card h3 {
    margin-top: 0;
}
.stButton > button[kind="primary"] {
    background: #087F8C;
    border-color: #087F8C;
    border-radius: 10px;
}
.stButton > button {
    border-radius: 10px;
}
[data-testid="stChatMessage"] {
    background: white;
    border: 1px solid #E4EAF1;
    border-radius: 14px;
    margin-bottom: 10px;
}
[data-testid="stChatInput"] {
    background: white;
}
div[data-testid="stForm"] {
    background: white;
    border: 1px solid #E4EAF1;
    border-radius: 16px;
    padding: 22px;
}
.login-heading {
    text-align: center;
    margin: 20px 0 25px;
}
.login-heading h1 {
    font-size: 34px;
    margin-bottom: 8px;
}
.login-heading p {
    color: #64748B !important;
}
footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)
# ============================================================
# SESSION STATE
# ============================================================
def initialize():
    defaults = {
        "token": None,
        "refresh_token": None,
        "page": "Dashboard",
        "messages": [],
        "patient_id": None,
        "patient_name": None,
        "session_id": None,
        "history_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
# ============================================================
# AUTHENTICATION
# ============================================================
def clear_session():
    st.session_state.token = None
    st.session_state.refresh_token = None
    st.session_state.messages = []
    st.session_state.patient_id = None
    st.session_state.patient_name = None
    st.session_state.session_id = None
    st.session_state.page = "Dashboard"
def logout():
    current_refresh = st.session_state.get("refresh_token")
    if current_refresh:
        try:
            requests.post(
                f"{API_URL}/auth/logout",
                json={"refresh_token": current_refresh},
                timeout=10,
            )
        except requests.RequestException:
            pass
    clear_session()
def refresh_token():
    current_refresh = st.session_state.get("refresh_token")
    if not current_refresh:
        return False
    try:
        response = requests.post(
            f"{API_URL}/auth/refresh",
            json={"refresh_token": current_refresh},
            timeout=15,
        )
        if response.status_code != 200:
            return False
        data = response.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        if not new_access or not new_refresh:
            return False
        st.session_state.token = new_access
        st.session_state.refresh_token = new_refresh
        return True
    except (requests.RequestException, ValueError):
        return False
# ============================================================
# API CLIENT
# ============================================================
def api(method, endpoint, retry=True, **kwargs):
    headers = kwargs.pop("headers", {}).copy()
    for attempt in range(2 if retry else 1):
        request_headers = headers.copy()
        request_headers["Authorization"] = (
            f"Bearer {st.session_state.token}"
        )
        response = requests.request(
            method,
            f"{API_URL}{endpoint}",
            headers=request_headers,
            timeout=180,
            **kwargs,
        )
        if response.status_code == 401:
            if attempt == 0 and retry and refresh_token():
                continue
            clear_session()
            raise PermissionError(
                "Your session has expired. Please sign in again."
            )
        if not response.ok:
            try:
                detail = response.json().get("detail")
                if detail:
                    raise requests.HTTPError(
                        f"HTTP {response.status_code}: {detail}",
                        response=response,
                    )
            except ValueError:
                pass
            response.raise_for_status()
        return response.json() if response.content else {}
    raise PermissionError("Authentication failed.")
# ============================================================
# REUSABLE UI
# ============================================================
def hero(title, subtitle):
    st.markdown(
        f"""
        <div class="hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
# ============================================================
# LOGIN PAGE
# ============================================================
def login_page():
    st.markdown(
        "<div style='height:35px'></div>",
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        st.markdown("""
        <div class="login-heading">
            <h1>🩺 Dr AI Agent</h1>
            <p>Your intelligent medical knowledge assistant</p>
        </div>
        """, unsafe_allow_html=True)
        with st.form("login"):
            st.subheader("Sign in to your account")
            username = st.text_input(
                "Email / Username",
                placeholder="Enter your email",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )
            submit = st.form_submit_button(
                "Sign In",
                type="primary",
                use_container_width=True,
            )
        if submit:
            if not username or not password:
                st.warning("Please enter your credentials.")
                return
            try:
                response = requests.post(
                    f"{API_URL}/auth/login",
                    data={
                        "username": username,
                        "password": password,
                    },
                    timeout=20,
                )
                response.raise_for_status()
                data = response.json()
                access = data.get("access_token")
                refresh = data.get("refresh_token")
                if not access or not refresh:
                    st.error(
                        "Login response is missing authentication tokens."
                    )
                    return
                st.session_state.token = access
                st.session_state.refresh_token = refresh
                st.rerun()
            except requests.RequestException as error:
                st.error(f"Login failed: {error}")
        st.caption(
            "For medical information only. "
            "Not a substitute for professional medical diagnosis."
        )
# ============================================================
# SIDEBAR
# ============================================================
def get_conversations():
    """Fetch the most recent saved sessions for the active patient."""
    patient_id = st.session_state.patient_id
    if not patient_id:
        return []
    data = api(
        "GET",
        f"/patients/{patient_id}/history",
        params={"limit": 100, "offset": 0},
    )
    items = data.get("items", [])
    if not isinstance(items, list):
        raise ValueError("Unexpected conversation list response")
    return sorted(items, key=lambda x: x.get("updated_at") or "", reverse=True)


def open_conversation(session_id):
    """Load saved messages before changing the currently open session."""
    patient_id = st.session_state.patient_id
    if not patient_id:
        return
    all_messages = []
    offset = 0
    while True:
        data = api(
            "GET",
            f"/patients/{patient_id}/history/{session_id}",
            params={"offset": offset, "limit": 200},
        )
        batch = data.get("messages", [])
        if not isinstance(batch, list):
            raise ValueError("Unexpected saved messages response")
        all_messages.extend(batch)
        offset += len(batch)
        total = data.get("total", offset)
        if not batch or offset >= total:
            break
        if offset > 10000:
            raise ValueError("Conversation is too long to load safely")
    st.session_state.messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in all_messages
        if msg.get("role") in ("user", "assistant")
        and isinstance(msg.get("content"), str)
    ]
    st.session_state.session_id = session_id
    st.session_state.page = "AI Chat"


def sidebar():
    with st.sidebar:
        st.markdown("## 🩺 Dr AI")
        st.caption("MEDICAL INTELLIGENCE PLATFORM")
        st.divider()
        options = ["Dashboard", "AI Chat", "Medical Knowledge", "System Status"]
        selected = st.radio(
            "Workspace", options, index=options.index(st.session_state.page)
        )
        st.session_state.page = selected
        st.divider()
        if st.session_state.patient_id:
            st.caption("ACTIVE PATIENT")
            st.write(st.session_state.patient_name or "Test Patient")
            st.caption(f"ID: {st.session_state.patient_id}")
            if st.button("Switch Patient", use_container_width=True):
                st.session_state.patient_id = None
                st.session_state.patient_name = None
                st.session_state.session_id = None
                st.session_state.messages = []
                st.session_state.page = "AI Chat"
                st.rerun()

        if st.button("＋ New Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid4())
            st.session_state.page = "AI Chat"
            st.rerun()

        if st.session_state.patient_id:
            st.divider()
            st.markdown("**Previous Conversations**")
            if st.button("↻ Refresh History", use_container_width=True):
                st.rerun()
            try:
                sessions = get_conversations()
                if not sessions:
                    st.caption("No saved conversations yet. Start a chat.")
                for entry in sessions:
                    sid = entry.get("session_id")
                    if not sid:
                        continue
                    date_label = (entry.get("updated_at") or "")[:16].replace("T", " ")
                    count = entry.get("message_count", 0)
                    active = "● " if sid == st.session_state.session_id else ""
                    label = f"{active}{date_label or 'Conversation'} · {count} messages"
                    if st.button(label, key=f"history_{sid}", use_container_width=True):
                        try:
                            open_conversation(sid)
                            st.rerun()
                        except (requests.RequestException, PermissionError, ValueError, KeyError) as error:
                            st.error(f"Could not open conversation: {error}")
                if len(sessions) == 100:
                    st.caption("Showing latest 100 conversations.")
            except (requests.RequestException, PermissionError, ValueError) as error:
                st.error(f"Could not list conversations: {error}")

        st.divider()
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()
        st.caption("Local Development Environment")

# ============================================================
# DASHBOARD
# ============================================================
def dashboard():
    hero(
        "Welcome to Dr AI",
        "Your AI-powered medical research and knowledge workspace.",
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="metric-card">
            <h3>AI Assistant</h3>
            <strong>Ready</strong>
            <p>Ask medical knowledge questions</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="metric-card">
            <h3>Knowledge Base</h3>
            <strong>Connected</strong>
            <p>Medical document retrieval</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="metric-card">
            <h3>Environment</h3>
            <strong>Localhost</strong>
            <p>Running in development mode</p>
        </div>
        """, unsafe_allow_html=True)
    st.subheader("Quick Actions")
    a, b = st.columns(2)
    with a:
        st.markdown("""
        <div class="info-card">
            <h3>💬 AI Medical Chat</h3>
            <p>Ask questions and explore medical information
            using your AI assistant.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(
            "Open AI Chat",
            use_container_width=True,
        ):
            st.session_state.page = "AI Chat"
            st.rerun()
    with b:
        st.markdown("""
        <div class="info-card">
            <h3>📚 Medical Knowledge</h3>
            <p>Search WHO and CDC documents and upload
            additional medical knowledge.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(
            "Open Knowledge Base",
            use_container_width=True,
        ):
            st.session_state.page = "Medical Knowledge"
            st.rerun()
# ============================================================
# PATIENT CREATION
# ============================================================
def create_test_patient():
    st.subheader("Create Test Patient")
    st.info(
        "Create a fictional patient to test the AI Chat. "
        "Do not enter real patient information."
    )
    with st.form("create_patient"):
        full_name = st.text_input(
            "Patient Name",
            value="Test Patient",
        )
        age = st.number_input(
            "Age",
            min_value=0,
            max_value=130,
            value=30,
        )
        gender = st.selectbox(
            "Gender",
            [
                "male",
                "female",
                "other",
                "prefer_not_to_say",
            ],
        )
        create = st.form_submit_button(
            "Create Patient",
            type="primary",
            use_container_width=True,
        )
    if create:
        if len(full_name.strip()) < 2:
            st.warning(
                "Patient name must contain at least 2 characters."
            )
            return
        try:
            patient = api(
                "POST",
                "/patients/",
                json={
                    "full_name": full_name.strip(),
                    "age": int(age),
                    "gender": gender,
                },
            )
            patient_id = patient.get("id")
            if not patient_id:
                st.error(
                    "Patient created, but response did not include an ID."
                )
                return
            st.session_state.patient_id = patient_id
            st.session_state.patient_name = full_name.strip()
            st.session_state.session_id = str(uuid4())
            st.session_state.messages = []
            st.success("Test patient created successfully.")
            st.rerun()
        except (
            requests.RequestException,
            PermissionError,
            KeyError,
        ) as error:
            st.error(str(error))
# ============================================================
# AI CHAT
# ============================================================
def select_existing_patient():
    st.subheader("Use an Existing Patient")
    st.caption("Enter a patient UUID you saved previously. No patient records are created.")
    with st.form("existing_patient"):
        entered_id = st.text_input("Existing Patient ID (UUID)")
        submit = st.form_submit_button("Open Patient", use_container_width=True)
    if submit:
        try:
            patient_id = str(UUID(entered_id.strip()))
        except (ValueError, AttributeError):
            st.error("Please enter a valid Patient ID (UUID).")
            return
        try:
            patient = api("GET", f"/patients/{patient_id}")
            if not isinstance(patient, dict):
                raise ValueError("Unexpected patient response")
            st.session_state.patient_id = patient_id
            st.session_state.patient_name = patient.get("full_name") or "Existing Patient"
            st.session_state.session_id = str(uuid4())
            st.session_state.messages = []
            st.rerun()
        except (requests.RequestException, PermissionError, ValueError) as error:
            st.error(f"Could not open patient: {error}")


def chat_page():
    hero(
        "AI Medical Assistant",
        "Ask medical questions powered by your local AI and knowledge base.",
    )
    if not st.session_state.patient_id:
        create_tab, existing_tab = st.tabs(["Create Test Patient", "Use Existing Patient"])
        with create_tab:
            create_test_patient()
        with existing_tab:
            select_existing_patient()
        return

    if not st.session_state.session_id:
        st.session_state.session_id = str(uuid4())
    st.caption(f"Patient: {st.session_state.patient_name or 'Test Patient'}")
    st.caption(f"Conversation ID: {st.session_state.session_id}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a medical question...")
    if not question:
        return
    question = question.strip()
    if len(question) < 2:
        st.warning("Please enter a longer question.")
        return
    if len(question) > 1000:
        st.warning("Question must be 1000 characters or fewer.")
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Dr AI is thinking..."):
            try:
                data = api(
                    "POST", "/chat/",
                    json={
                        "patient_id": st.session_state.patient_id,
                        "session_id": st.session_state.session_id,
                        "message": question,
                    },
                )
                answer = data.get("response")
                if not isinstance(answer, str):
                    st.warning("Unexpected chat response format.")
                    st.json(data)
                    return
                if data.get("session_id"):
                    st.session_state.session_id = data["session_id"]
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except (requests.RequestException, PermissionError) as error:
                st.error(str(error))
                st.info("If the request timed out, refresh history before resending to avoid duplicates.")

# ============================================================
# MEDICAL KNOWLEDGE
# ============================================================
def knowledge_page():
    hero(
        "Medical Knowledge Base",
        "Search and manage your indexed medical documents.",
    )
    search_tab, upload_tab = st.tabs([
        "🔎 Knowledge Search",
        "📄 Upload Documents",
    ])
    with search_tab:
        with st.form("search"):
            query = st.text_input(
                "Medical Question",
                placeholder="What are the symptoms of sepsis?",
            )
            limit = st.slider(
                "Number of results",
                1,
                10,
                3,
            )
            submit = st.form_submit_button(
                "Search Knowledge"
            )
        if submit:
            if len(query.strip()) < 3:
                st.warning(
                    "Enter a medical question of at least 3 characters."
                )
            else:
                try:
                    result = api(
                        "POST",
                        "/knowledge/search",
                        json={
                            "question": query.strip(),
                            "limit": limit,
                        },
                    )
                    st.json(result)
                except (
                    requests.RequestException,
                    PermissionError,
                ) as error:
                    st.error(str(error))
    with upload_tab:
        st.info(
            "Upload a PDF or TXT document to the medical knowledge base."
        )
        uploaded = st.file_uploader(
            "Choose PDF or TXT",
            type=["pdf", "txt"],
        )
        admin_key = st.text_input(
            "Knowledge Admin Key",
            type="password",
        )
        if st.button(
            "Upload and Index",
            type="primary",
        ):
            if not uploaded:
                st.warning(
                    "Please select a document."
                )
            elif not admin_key:
                st.warning(
                    "Enter the admin key."
                )
            else:
                try:
                    result = api(
                        "POST",
                        "/knowledge/documents",
                        headers={
                            "X-Knowledge-Admin-Key": admin_key,
                        },
                        files={
                            "file": (
                                uploaded.name,
                                uploaded.getvalue(),
                                uploaded.type
                                or "application/octet-stream",
                            )
                        },
                    )
                    st.success(
                        "Document uploaded successfully."
                    )
                    st.json(result)
                except (
                    requests.RequestException,
                    PermissionError,
                ) as error:
                    st.error(str(error))
# ============================================================
# SYSTEM STATUS
# ============================================================
def status_page():
    hero(
        "System Status",
        "Monitor your local Dr AI backend and API availability.",
    )
    st.subheader("FastAPI Connection")
    st.code(API_URL)
    try:
        response = requests.get(
            f"{API_URL}/openapi.json",
            timeout=10,
        )
        response.raise_for_status()
        st.success(
            "FastAPI backend is reachable."
        )
        schema = response.json()
        with st.expander("Available API Endpoints"):
            for endpoint, methods in sorted(
                schema.get("paths", {}).items()
            ):
                st.write(
                    f"`{endpoint}` — "
                    + ", ".join(
                        method.upper()
                        for method in methods
                    )
                )
    except requests.RequestException as error:
        st.error(
            f"Backend connection failed: {error}"
        )
# ============================================================
# APPLICATION ENTRY POINT
# ============================================================
initialize()
if not st.session_state.token:
    login_page()
else:
    sidebar()
    if st.session_state.page == "Dashboard":
        dashboard()
    elif st.session_state.page == "AI Chat":
        chat_page()
    elif st.session_state.page == "Medical Knowledge":
        knowledge_page()
    elif st.session_state.page == "System Status":
        status_page()
