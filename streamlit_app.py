import uuid
import requests
import streamlit as st
from urllib.parse import urlparse

# =====================================================
# CONFIG
# =====================================================

API_BASE_URL = "http://127.0.0.1:8000"

SUPPORTED_TYPES = ["pdf", "txt", "md", "csv", "json", "docx"]

INTENT_CONFIG = {
    "general": {"icon": "🌐", "label": "Web Search"},
    "rag_only": {"icon": "📄", "label": "Document RAG"},
    "hybrid": {"icon": "🔀", "label": "Hybrid"},
    "summary": {"icon": "📋", "label": "Summary"},
    "comparison": {"icon": "⚖️", "label": "Comparison"},
}

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# SIMPLE CHATGPT-LIKE CSS
# =====================================================

st.markdown("""
<style>

/* Global */
html, body, [class*="css"] {
    font-family: "Inter", sans-serif;
}

.stApp {
    background-color: #ffffff;
    color: #111827;
}

/* Main layout */
.main .block-container {
    max-width: 900px;
    padding-top: 2rem;
    padding-bottom: 6rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #f7f7f8;
    border-right: 1px solid #e5e7eb;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border: none;
    background: transparent;
    padding: 1rem 0rem;
}

/* User message */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background-color: #f7f7f8;
    border-radius: 12px;
    padding: 1rem;
}

/* Assistant message */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background-color: #ffffff;
}

/* Chat input */
[data-testid="stChatInput"] {
    border-top: 1px solid #e5e7eb;
    background: white;
}

/* Buttons */
.stButton > button {
    width: 100%;
    border-radius: 10px;
    border: 1px solid #d1d5db;
    background: white;
    color: black;
    padding: 0.5rem;
}

.stButton > button:hover {
    background: #f3f4f6;
}

/* File uploader */
[data-testid="stFileUploader"] {
    border: 1px dashed #cbd5e1;
    border-radius: 10px;
    padding: 1rem;
    background: white;
}

/* Expanders */
details {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 0.5rem;
    background: #fafafa;
}

/* Metrics */
[data-testid="metric-container"] {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1rem;
    background: white;
}

/* Chunk cards */
.chunk-card {
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 12px;
    background: #fafafa;
}

/* Intent badge */
.intent-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background: #f3f4f6;
    color: #374151;
    font-size: 12px;
    margin-bottom: 10px;
    font-weight: 500;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# BACKEND CHECK
# =====================================================

backend_ok = False

try:
    r = requests.get(f"{API_BASE_URL}/health", timeout=5)
    backend_ok = r.status_code == 200
except:
    pass

# =====================================================
# SESSION STATE
# =====================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "last_uploaded" not in st.session_state:
    st.session_state.last_uploaded = None

# =====================================================
# HELPERS
# =====================================================

def get_active_documents():
    try:
        r = requests.get(f"{API_BASE_URL}/documents", timeout=5)
        if r.status_code == 200:
            return r.json().get("documents", []), r.json().get("vector_count", 0)
    except:
        pass

    return [], 0


def intent_badge(intent):
    cfg = INTENT_CONFIG.get(intent, INTENT_CONFIG["general"])
    return f"""
    <div class="intent-badge">
        {cfg["icon"]} {cfg["label"]}
    </div>
    """


def format_source_url(source):
    try:
        parsed = urlparse(source)
        if parsed.netloc:
            return parsed.netloc, source
    except:
        pass

    return source, None

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:

    st.title("AI Assistant")

    if backend_ok:
        st.success("Backend Connected")
    else:
        st.error("Backend Offline")

    st.divider()

    st.subheader("Upload Document")

    uploaded_file = st.file_uploader(
        "Upload",
        type=SUPPORTED_TYPES,
        label_visibility="collapsed"
    )

    if uploaded_file is not None:

        if st.session_state.last_uploaded != uploaded_file.name:

            with st.spinner("Uploading and indexing..."):

                try:
                    response = requests.post(
                        f"{API_BASE_URL}/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file,
                                uploaded_file.type or "application/octet-stream"
                            )
                        },
                        timeout=300
                    )

                    if response.status_code == 200:

                        data = response.json()

                        st.success(
                            f"Indexed {data.get('vector_count', '?')} chunks"
                        )

                        st.session_state.last_uploaded = uploaded_file.name

                    else:
                        st.error("Upload failed")

                except Exception as e:
                    st.error(str(e))

    st.divider()

    docs, vector_count = get_active_documents()

    st.subheader("Indexed Documents")

    if docs:
        for doc in docs:
            st.markdown(f"📄 {doc}")

        st.caption(f"{vector_count} vectors indexed")

        if st.button("Clear Documents"):
            try:
                r = requests.delete(
                    f"{API_BASE_URL}/documents",
                    timeout=10
                )

                if r.status_code == 200:
                    st.success("Documents cleared")
                    st.session_state.messages = []
                    st.rerun()

            except Exception as e:
                st.error(str(e))

    else:
        st.caption("No documents uploaded")

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# =====================================================
# MAIN HEADER
# =====================================================

if not backend_ok:
    st.error(
        "Backend not running. Start FastAPI using:\n\n"
        "`uvicorn app.main:app --reload`"
    )
    st.stop()

st.title("Chat")

st.caption(
    "Ask questions about your documents or search the web."
)

# =====================================================
# CHAT HISTORY
# =====================================================

for message in st.session_state.messages:

    role = message["role"]
    content = message["content"]
    meta = message.get("meta", {})

    with st.chat_message(role):

        if role == "assistant" and meta.get("intent"):
            st.markdown(
                intent_badge(meta["intent"]),
                unsafe_allow_html=True
            )

        st.markdown(content)

        if role == "assistant" and meta.get("sources"):

            with st.expander("Sources"):

                for src in meta["sources"]:

                    label, url = format_source_url(src)

                    if url:
                        st.markdown(f"- [{label}]({url})")
                    else:
                        st.markdown(f"- {label}")

# =====================================================
# CHAT INPUT
# =====================================================

query = st.chat_input(
    "Message AI Assistant..."
)

# =====================================================
# PROCESS QUERY
# =====================================================

if query and query.strip():

    st.session_state.messages.append({
        "role": "user",
        "content": query
    })

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):

        with st.spinner("Thinking..."):

            try:

                response = requests.post(
                    f"{API_BASE_URL}/chat",
                    json={
                        "query": query,
                        "history": st.session_state.messages[:-1],
                        "session_id": st.session_state.session_id
                    },
                    timeout=300
                )

            except Exception as e:
                st.error(str(e))
                st.stop()

        if response.status_code != 200:
            st.error("Backend Error")
            st.stop()

        data = response.json()

        answer = data.get("answer", "No response")
        intent = data.get("intent", "general")
        sources = data.get("sources", [])
        chunks = data.get("retrieved_chunks", [])

        # Intent Badge
        st.markdown(
            intent_badge(intent),
            unsafe_allow_html=True
        )

        # Answer
        st.markdown(answer)

        # Metrics
        if chunks:

            avg_score = (
                sum(c.get("score", 0) for c in chunks)
                / len(chunks)
            )

            c1, c2, c3 = st.columns(3)

            c1.metric("Chunks", len(chunks))
            c2.metric("Grounding", f"{avg_score*100:.1f}%")
            c3.metric("Sources", len(sources))

        # Sources
        if sources:

            with st.expander("Sources"):

                for src in sources:

                    label, url = format_source_url(src)

                    if url:
                        st.markdown(f"- [{label}]({url})")
                    else:
                        st.markdown(f"- {label}")

        # Retrieved Chunks
        if chunks:

            with st.expander("Retrieved Chunks"):

                for idx, chunk in enumerate(chunks):

                    score = round(chunk.get("score", 0) * 100, 1)

                    content = chunk.get("content", "")[:700]

                    doc_name = chunk.get(
                        "document_name",
                        "Unknown"
                    )

                    st.markdown(
                        f"""
                        <div class="chunk-card">
                            <strong>{idx+1}. {doc_name}</strong><br><br>
                            {content}<br><br>
                            <small>Score: {score}%</small>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "meta": {
                "intent": intent,
                "sources": sources
            }
        })