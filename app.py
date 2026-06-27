import streamlit as st
from backend import LegalAnalyzer
from auth import login_user, register_user
import tempfile
import os

# At the top of your app, after imports
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"  # or whatever your default page is

# ── Load Secrets First ─────────────────────────────────
os.environ["SUPABASE_URL"] = st.secrets["SUPABASE_URL"]
os.environ["SUPABASE_KEY"] = st.secrets["SUPABASE_KEY"]
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]

# ── Page Config ────────────────────────────────────────
st.set_page_config(page_title="ContractSentry AI", layout="wide", page_icon="🛡️")

# ── Global CSS Design System ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 2rem 2rem 2rem !important; max-width: 1200px; }

/* ── Dark navy background ── */
.stApp {
    background: #080d1a;
    color: #e2e8f0;
}

/* ── Sidebar-style top bar ── */
.cs-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 0 18px 0;
    border-bottom: 1px solid #1e2d4a;
    margin-bottom: 28px;
}
.cs-logo {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.3px;
}
.cs-logo span { color: #3b82f6; }
.cs-user-pill {
    background: #0f1f3d;
    border: 1px solid #1e3a5f;
    border-radius: 999px;
    padding: 6px 16px;
    font-size: 13px;
    color: #94a3b8;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}
.cs-user-pill b { color: #e2e8f0; }

/* ── Auth screen ── */
.cs-auth-hero {
    text-align: center;
    padding: 60px 0 40px 0;
}
.cs-auth-hero h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 48px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -1px;
    margin-bottom: 12px;
}
.cs-auth-hero h1 span { color: #3b82f6; }
.cs-auth-hero p {
    color: #64748b;
    font-size: 17px;
    max-width: 480px;
    margin: 0 auto;
    line-height: 1.6;
}
.cs-auth-card {
    background: #0c1628;
    border: 1px solid #1e2d4a;
    border-radius: 16px;
    padding: 32px;
    max-width: 420px;
    margin: 0 auto;
}

/* ── Risk score banner ── */
.cs-risk-banner {
    border-radius: 14px;
    padding: 28px 32px;
    margin: 0 0 24px 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 24px;
}
.cs-risk-banner.high  { background: linear-gradient(135deg, #1f0a0a 0%, #2d1010 100%); border: 1px solid #7f1d1d; }
.cs-risk-banner.medium { background: linear-gradient(135deg, #1a1200 0%, #2a1f00 100%); border: 1px solid #78350f; }
.cs-risk-banner.low   { background: linear-gradient(135deg, #031a0e 0%, #0a2818 100%); border: 1px solid #14532d; }
.cs-risk-score {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 64px;
    font-weight: 700;
    line-height: 1;
}
.cs-risk-banner.high  .cs-risk-score { color: #f87171; }
.cs-risk-banner.medium .cs-risk-score { color: #fbbf24; }
.cs-risk-banner.low   .cs-risk-score { color: #34d399; }
.cs-risk-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
}
.cs-risk-banner.high  .cs-risk-label { color: #fca5a5; }
.cs-risk-banner.medium .cs-risk-label { color: #fde68a; }
.cs-risk-banner.low   .cs-risk-label { color: #6ee7b7; }
.cs-risk-sub { color: #64748b; font-size: 13px; }

/* ── Metric chips ── */
.cs-metrics {
    display: flex;
    gap: 12px;
    flex-direction: column;
}
.cs-chip {
    background: #080d1a;
    border-radius: 10px;
    padding: 10px 18px;
    text-align: center;
    min-width: 90px;
}
.cs-chip-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 26px;
    font-weight: 700;
}
.cs-chip-lbl { font-size: 11px; color: #64748b; margin-top: 2px; }
.cs-chip.h .cs-chip-num { color: #f87171; }
.cs-chip.m .cs-chip-num { color: #fbbf24; }
.cs-chip.l .cs-chip-num { color: #34d399; }

/* ── Clause cards ── */
.cs-clause {
    background: #0c1628;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
}
.cs-clause::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 4px;
    border-radius: 4px 0 0 4px;
}
.cs-clause.high::before  { background: #ef4444; }
.cs-clause.medium::before { background: #f59e0b; }
.cs-clause.low::before   { background: #10b981; }
.cs-clause-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}
.cs-clause-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
}
.cs-badge {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 3px 10px;
    border-radius: 999px;
}
.cs-badge.high   { background: #450a0a; color: #f87171; border: 1px solid #7f1d1d; }
.cs-badge.medium { background: #431407; color: #fbbf24; border: 1px solid #78350f; }
.cs-badge.low    { background: #052e16; color: #34d399; border: 1px solid #14532d; }
.cs-clause-explanation { color: #94a3b8; font-size: 13.5px; line-height: 1.6; margin-bottom: 10px; }
.cs-snippet {
    background: #060c18;
    border-left: 3px solid #1e3a5f;
    border-radius: 0 6px 6px 0;
    padding: 10px 14px;
    font-size: 12px;
    color: #64748b;
    font-style: italic;
    margin-top: 8px;
}

/* ── Rewrite card ── */
.cs-rewrite {
    background: #031a0e;
    border: 1px solid #14532d;
    border-radius: 10px;
    padding: 18px 20px;
    margin-top: 10px;
}
.cs-rewrite-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #34d399;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.cs-rewrite-body {
    background: #042010;
    border-radius: 8px;
    padding: 14px;
    font-size: 13px;
    color: #a7f3d0;
    line-height: 1.7;
    font-style: italic;
    margin-bottom: 12px;
}
.cs-change-item {
    font-size: 12.5px;
    color: #6ee7b7;
    padding: 3px 0;
}
.cs-change-item::before { content: "✓ "; color: #34d399; font-weight: bold; }

/* ── Chat bubbles ── */
.cs-bubble-user {
    background: #0f1f3d;
    border: 1px solid #1e3a5f;
    border-radius: 12px 12px 4px 12px;
    padding: 12px 16px;
    margin: 8px 0 8px 60px;
    font-size: 14px;
    color: #e2e8f0;
}
.cs-bubble-bot {
    background: #0c1628;
    border: 1px solid #1a2d45;
    border-radius: 12px 12px 12px 4px;
    padding: 12px 16px;
    margin: 8px 60px 8px 0;
    font-size: 14px;
    color: #cbd5e1;
    line-height: 1.6;
}
.cs-bubble-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
    text-transform: uppercase;
}
.cs-bubble-user .cs-bubble-label { color: #3b82f6; text-align: right; }
.cs-bubble-bot  .cs-bubble-label { color: #6366f1; }

/* ── Upload zone ── */
.cs-upload-hint {
    background: #0c1628;
    border: 2px dashed #1e3a5f;
    border-radius: 14px;
    padding: 28px;
    text-align: center;
    color: #475569;
    font-size: 14px;
    margin-bottom: 20px;
}

/* ── Section headers ── */
.cs-section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 16px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 28px 0 16px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
.cs-section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #1e2d4a;
}

/* ── Streamlit widget overrides ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #0c1628 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
.stButton > button {
    background: #1e3a5f !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d5a8e !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover {
    background: #2d5a8e !important;
    border-color: #3b82f6 !important;
    color: #fff !important;
}
.stButton > button[kind="primary"] {
    background: #2563eb !important;
    border-color: #3b82f6 !important;
    color: #fff !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1d4ed8 !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: #080d1a !important;
    border-bottom: 1px solid #1e2d4a !important;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748b !important;
    border-radius: 8px 8px 0 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
}
.stTabs [aria-selected="true"] {
    background: #0c1628 !important;
    color: #3b82f6 !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.stProgress > div > div > div > div {
    background: #3b82f6 !important;
    border-radius: 999px !important;
}
.stProgress > div > div > div {
    background: #1e2d4a !important;
    border-radius: 999px !important;
}
.stDownloadButton > button {
    background: #052e16 !important;
    color: #34d399 !important;
    border: 1px solid #14532d !important;
    font-weight: 600 !important;
}
.stDownloadButton > button:hover {
    background: #065f46 !important;
    color: #6ee7b7 !important;
}
[data-testid="stFileUploader"] {
    background: #0c1628 !important;
    border: 2px dashed #1e3a5f !important;
    border-radius: 14px !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: #3b82f6 !important;
}
label, .stSelectbox label, .stTextInput label, .stTextArea label {
    color: #94a3b8 !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}
.stSelectbox > div > div {
    background: #0c1628 !important;
    border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}
.stAlert {
    border-radius: 10px !important;
    border: none !important;
}
[data-testid="stMetricValue"] {
    color: #e2e8f0 !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.stExpander {
    background: #0c1628 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 10px !important;
}
div[data-testid="stExpander"] summary {
    color: #94a3b8 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session State Init ─────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "risk_data" not in st.session_state:
    st.session_state.risk_data = None
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = ""

# ── Auth Screen ────────────────────────────────────────
def show_auth_screen():
    st.markdown("""
    <div class="cs-auth-hero">
        <h1>Contract<span>Sentry</span></h1>
        <p>AI-powered contract risk detection for small businesses and freelancers. Know what you're signing before you sign it.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Sign In", "Create Account"])

        with tab1:
            username = st.text_input("Username", key="login_user", placeholder="your username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign In →", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    success, message = login_user(username, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error(message)

        with tab2:
            new_username = st.text_input("Choose a username", key="reg_user", placeholder="your username")
            new_password = st.text_input("Password", type="password", key="reg_pass", placeholder="min. 6 characters")
            confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create Account →", use_container_width=True, type="primary"):
                if not new_username or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success, message = register_user(new_username, new_password)
                    if success:
                        st.success("Account created. Sign in above.")
                    else:
                        st.error(message)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex; gap:24px; justify-content:center; flex-wrap:wrap; margin-bottom:48px;">
        <div style="background:#0c1628;border:1px solid #1e2d4a;border-radius:12px;padding:20px 28px;text-align:center;min-width:160px;">
            <div style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:700;color:#3b82f6;">5</div>
            <div style="font-size:12px;color:#64748b;margin-top:4px;">Risk clause types detected</div>
        </div>
        <div style="background:#0c1628;border:1px solid #1e2d4a;border-radius:12px;padding:20px 28px;text-align:center;min-width:160px;">
            <div style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:700;color:#6366f1;">RAG</div>
            <div style="font-size:12px;color:#64748b;margin-top:4px;">Powered by LangChain + ChromaDB</div>
        </div>
        <div style="background:#0c1628;border:1px solid #1e2d4a;border-radius:12px;padding:20px 28px;text-align:center;min-width:160px;">
            <div style="font-family:'Space Grotesk',sans-serif;font-size:32px;font-weight:700;color:#34d399;">Free</div>
            <div style="font-size:12px;color:#64748b;margin-top:4px;">No lawyers required</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Main App ───────────────────────────────────────────
def show_main_app():
    analyzer = LegalAnalyzer()

    # Top bar
    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown("""
        <div class="cs-topbar">
            <div class="cs-logo">Contract<span>Sentry</span> <span style="font-size:13px;font-weight:400;color:#334155;margin-left:8px;">AI Risk Detection</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="padding-top:18px;">
            <div class="cs-user-pill">👤 <b>{st.session_state.username}</b></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign out", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.vectorstore = None
            st.session_state.chat_history = []
            st.session_state.analysis_done = False
            st.session_state.analysis_result = None
            st.session_state.risk_data = None
            st.rerun()

    st.markdown('<div class="cs-section-title">Upload Contract</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Drop a PDF contract here or click to browse", type=["pdf"], label_visibility="collapsed")

    if uploaded_file is not None:

        # Reset if new file uploaded
        if uploaded_file.name != st.session_state.uploaded_filename:
            st.session_state.analysis_done = False
            st.session_state.analysis_result = None
            st.session_state.risk_data = None
            st.session_state.vectorstore = None
            st.session_state.chat_history = []
            st.session_state.uploaded_filename = uploaded_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            uploaded_file.seek(0)
            f.write(uploaded_file.read())
            temp_path = f.name

        try:
            # Run analysis only once per file
            if not st.session_state.analysis_done:
                st.info("🔄 Processing document... This may take 10-30 seconds.")
                progress_bar = st.progress(0.0)

                # Build vectorstore and save to session
                st.session_state.vectorstore = analyzer.get_vectorstore(temp_path)
                progress_bar.progress(0.4)

                # Run risk analysis
                st.session_state.analysis_result = analyzer.analyze_risk(temp_path)
                progress_bar.progress(0.8)

                # Calculate risk score
                st.session_state.risk_data = analyzer.calculate_risk_score(
                    st.session_state.analysis_result
                )
                progress_bar.progress(1.0)
                st.session_state.analysis_done = True
                st.rerun()

            result = st.session_state.analysis_result
            risk_data = st.session_state.risk_data

            # ── Tabs ───────────────────────────────────────────
            tab1, tab2 = st.tabs(["Risk Analysis", "Chat with Contract"])

            # ── Tab 1: Risk Analysis ───────────────────────────
            with tab1:
                # Risk banner
                banner_class = "high" if risk_data["color"] == "red" else ("medium" if risk_data["color"] == "orange" else "low")
                label_clean = risk_data["label"].replace("🔴 ", "").replace("🟠 ", "").replace("🟢 ", "")
                h = risk_data["breakdown"].get("HIGH", 0)
                m = risk_data["breakdown"].get("MEDIUM", 0)
                l = risk_data["breakdown"].get("LOW", 0)

                st.markdown(f"""
                <div class="cs-risk-banner {banner_class}">
                    <div>
                        <div class="cs-risk-label">{label_clean}</div>
                        <div class="cs-risk-sub">Based on {len(result)} detected clauses · {uploaded_file.name}</div>
                    </div>
                    <div class="cs-risk-score">{risk_data['score']}%</div>
                    <div class="cs-metrics">
                        <div class="cs-chip h"><div class="cs-chip-num">{h}</div><div class="cs-chip-lbl">HIGH</div></div>
                        <div class="cs-chip m"><div class="cs-chip-num">{m}</div><div class="cs-chip-lbl">MEDIUM</div></div>
                        <div class="cs-chip l"><div class="cs-chip-num">{l}</div><div class="cs-chip-lbl">LOW</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.progress(risk_data["score"] / 100)

                st.markdown('<div class="cs-section-title">Detected Risk Clauses</div>', unsafe_allow_html=True)

                if result:
                    for i, item in enumerate(result):
                        risk_level = item.get("risk_level", "UNKNOWN")
                        clause_type = item.get("clause_type", "General")
                        explanation = item.get("explanation", "")
                        text_snippet = item.get("text_snippet", "")
                        level_class = risk_level.lower()

                        snippet_html = f'<div class="cs-snippet">"{text_snippet}"</div>' if text_snippet else ""

                        st.markdown(f"""
                        <div class="cs-clause {level_class}">
                            <div class="cs-clause-header">
                                <div class="cs-clause-title">{clause_type}</div>
                                <div class="cs-badge {level_class}">{risk_level}</div>
                            </div>
                            <div class="cs-clause-explanation">{explanation}</div>
                            {snippet_html}
                        </div>
                        """, unsafe_allow_html=True)

                        # Rewrite Button
                        if risk_level in ["HIGH", "MEDIUM"]:
                            rewrite_key = f"rewrite_{i}"
                            rewrite_result_key = f"rewrite_result_{i}"

                            if rewrite_result_key not in st.session_state:
                                st.session_state[rewrite_result_key] = None

                            col_btn1, col_btn2 = st.columns([1, 5])
                            with col_btn1:
                                if st.button("✍️ Rewrite", key=rewrite_key):
                                    with st.spinner("Drafting safer clause..."):
                                        try:
                                            rewrite = analyzer.rewrite_clause(clause_type, explanation, text_snippet)
                                            st.session_state[rewrite_result_key] = rewrite
                                        except Exception as e:
                                            st.error(f"Rewrite failed: {e}")
                            with col_btn2:
                                if st.session_state[rewrite_result_key]:
                                    if st.button("Hide", key=f"hide_{i}"):
                                        st.session_state[rewrite_result_key] = None

                            if st.session_state[rewrite_result_key]:
                                rewrite = st.session_state[rewrite_result_key]
                                changes_html = "".join(f'<div class="cs-change-item">{c}</div>' for c in rewrite.get("key_changes", []))
                                st.markdown(f"""
                                <div class="cs-rewrite">
                                    <div class="cs-rewrite-title">✦ Suggested Safer Clause</div>
                                    <div style="font-size:12px;color:#64748b;margin-bottom:8px;">{rewrite.get("original_issue","")}</div>
                                    <div class="cs-rewrite-body">{rewrite.get("rewritten_clause","")}</div>
                                    <div style="margin-bottom:4px;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">Key changes</div>
                                    {changes_html}
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                else:
                    st.success("✅ No significant risks found in this document.")

                # Download Report
                st.markdown('<div class="cs-section-title">Report</div>', unsafe_allow_html=True)
                try:
                    pdf_buffer = analyzer.generate_pdf_report(result, risk_data)
                    st.download_button(
                        label="⬇ Download PDF Report",
                        data=pdf_buffer,
                        file_name=f"contract_analysis_{uploaded_file.name.replace('.pdf', '')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Could not generate report: {e}")

            # ── Tab 2: Chat with Contract ──────────────────────
            with tab2:
                st.markdown('<div class="cs-section-title">Ask Anything About This Contract</div>', unsafe_allow_html=True)

                # Suggested questions
                suggested = [
                    "What is the notice period?",
                    "Is there a non-compete clause?",
                    "What are the payment terms?",
                    "Can I terminate this contract early?",
                    "What data is being collected?"
                ]
                cols = st.columns(len(suggested))
                for idx, question in enumerate(suggested):
                    with cols[idx]:
                        if st.button(question, key=f"suggest_{idx}", use_container_width=True):
                            st.session_state.chat_history.append({"role": "user", "content": question})
                            with st.spinner("Searching contract..."):
                                try:
                                    answer = analyzer.chat_with_contract(question, st.session_state.vectorstore)
                                    st.session_state.chat_history.append({"role": "assistant", "content": answer})
                                except Exception as e:
                                    st.error(f"Chat failed: {e}")
                            st.rerun()

                st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

                # Chat history
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="cs-bubble-user">
                            <div class="cs-bubble-label">You</div>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="cs-bubble-bot">
                            <div class="cs-bubble-label">ContractSentry</div>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

                col_input, col_send = st.columns([5, 1])
                with col_input:
                    user_question = st.text_input(
                        "message", key="chat_input",
                        label_visibility="collapsed",
                        placeholder="Ask a question about the contract…"
                    )
                with col_send:
                    send_clicked = st.button("Send →", use_container_width=True, type="primary")

                if send_clicked and user_question.strip():
                    st.session_state.chat_history.append({"role": "user", "content": user_question})
                    with st.spinner("Searching contract..."):
                        try:
                            answer = analyzer.chat_with_contract(user_question, st.session_state.vectorstore)
                            st.session_state.chat_history.append({"role": "assistant", "content": answer})
                        except Exception as e:
                            st.error(f"Chat failed: {e}")
                    st.rerun()

                if st.session_state.chat_history:
                    if st.button("Clear conversation", use_container_width=True):
                        st.session_state.chat_history = []
                        st.rerun()

        except Exception as e:
            st.error(f"Error processing file: {e}")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    else:
        st.session_state.analysis_done = False
        st.session_state.analysis_result = None
        st.session_state.risk_data = None
        st.session_state.vectorstore = None
        st.session_state.chat_history = []
        st.markdown("""
        <div class="cs-upload-hint">
            <div style="font-size:36px;margin-bottom:12px;">📄</div>
            <div style="font-size:15px;color:#475569;margin-bottom:6px;">No contract uploaded yet</div>
            <div style="font-size:13px;">Upload a PDF above to start your risk analysis</div>
        </div>
        """, unsafe_allow_html=True)

def show_how_it_works():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown("""
        <div class="cs-topbar">
            <div class="cs-logo">Contract<span>Sentry</span> <span style="font-size:13px;font-weight:400;color:#334155;margin-left:8px;">How It Works</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="padding-top:18px;">
            <div class="cs-user-pill">👤 <b>{st.session_state.username}</b></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign out", key="logout_how"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    st.markdown("---")

    # ── Step by Step ───────────────────────────────────────
    st.subheader("🔄 Step-by-Step Process")
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin: 15px 0;">

        <div style="flex: 1; min-width: 140px; background: #e3f2fd; border-radius: 12px; padding: 15px; text-align: center;">
            <div style="font-size: 32px;">📤</div>
            <div style="font-weight: bold; color: #1565c0; margin: 8px 0;">Step 1</div>
            <div style="font-weight: bold; color: #333;">Upload PDF</div>
            <div style="font-size: 12px; color: #555; margin-top: 5px;">Upload your contract in PDF format</div>
        </div>

        <div style="display: flex; align-items: center; font-size: 24px; color: #90caf9;">→</div>

        <div style="flex: 1; min-width: 140px; background: #f3e5f5; border-radius: 12px; padding: 15px; text-align: center;">
            <div style="font-size: 32px;">📝</div>
            <div style="font-weight: bold; color: #6a1b9a; margin: 8px 0;">Step 2</div>
            <div style="font-weight: bold; color: #333;">Text Extraction</div>
            <div style="font-size: 12px; color: #555; margin-top: 5px;">PyPDF extracts all text from pages</div>
        </div>

        <div style="display: flex; align-items: center; font-size: 24px; color: #90caf9;">→</div>

        <div style="flex: 1; min-width: 140px; background: #e8f5e9; border-radius: 12px; padding: 15px; text-align: center;">
            <div style="font-size: 32px;">✂️</div>
            <div style="font-weight: bold; color: #2e7d32; margin: 8px 0;">Step 3</div>
            <div style="font-weight: bold; color: #333;">Chunking</div>
            <div style="font-size: 12px; color: #555; margin-top: 5px;">Split into 500-token chunks with overlap</div>
        </div>

        <div style="display: flex; align-items: center; font-size: 24px; color: #90caf9;">→</div>

        <div style="flex: 1; min-width: 140px; background: #fff3e0; border-radius: 12px; padding: 15px; text-align: center;">
            <div style="font-size: 32px;">🧠</div>
            <div style="font-weight: bold; color: #e65100; margin: 8px 0;">Step 4</div>
            <div style="font-weight: bold; color: #333;">Embedding</div>
            <div style="font-size: 12px; color: #555; margin-top: 5px;">HuggingFace BGE converts chunks to vectors</div>
        </div>

        <div style="display: flex; align-items: center; font-size: 24px; color: #90caf9;">→</div>

        <div style="flex: 1; min-width: 140px; background: #fce4ec; border-radius: 12px; padding: 15px; text-align: center;">
            <div style="font-size: 32px;">🔍</div>
            <div style="font-weight: bold; color: #880e4f; margin: 8px 0;">Step 5</div>
            <div style="font-weight: bold; color: #333;">Retrieval</div>
            <div style="font-size: 12px; color: #555; margin-top: 5px;">Top 5 relevant chunks fetched from ChromaDB</div>
        </div>

        <div style="display: flex; align-items: center; font-size: 24px; color: #90caf9;">→</div>

        <div style="flex: 1; min-width: 140px; background: #e0f7fa; border-radius: 12px; padding: 15px; text-align: center;">
            <div style="font-size: 32px;">🤖</div>
            <div style="font-weight: bold; color: #006064; margin: 8px 0;">Step 6</div>
            <div style="font-weight: bold; color: #333;">AI Analysis</div>
            <div style="font-size: 12px; color: #555; margin-top: 5px;">Groq LLaMA 3.1 analyzes for risks</div>
        </div>

    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Features ───────────────────────────────────────────
    st.subheader("✨ Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background: #fff8f0; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: #e65100; margin: 0 0 10px 0;">🚩 Risk Detection</h4>
            <p style="color: #333; font-size: 14px;">Automatically identifies 5 high-risk clause types:</p>
            <ul style="color: #555; font-size: 13px;">
                <li>Non-Compete / Restricted Activity</li>
                <li>Indefinite Term / Auto-Renewal</li>
                <li>Broad Liability Caps</li>
                <li>Arbitration Clauses</li>
                <li>Data Privacy / GDPR Issues</li>
            </ul>
        </div>

        <div style="background: #f0fff4; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: #276749; margin: 0 0 10px 0;">📊 Risk Score</h4>
            <p style="color: #333; font-size: 14px;">Each contract gets an overall risk score from 0-100%:</p>
            <ul style="color: #555; font-size: 13px;">
                <li>🔴 HIGH RISK — Score ≥ 60%</li>
                <li>🟠 MEDIUM RISK — Score ≥ 30%</li>
                <li>🟢 LOW RISK — Score below 30%</li>
            </ul>
        </div>

        <div style="background: #f3e5f5; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: #6a1b9a; margin: 0 0 10px 0;">✍️ Clause Rewriting</h4>
            <p style="color: #333; font-size: 14px;">For each HIGH or MEDIUM risk clause, the AI suggests a safer, fairer alternative with:</p>
            <ul style="color: #555; font-size: 13px;">
                <li>Plain English explanation</li>
                <li>Key changes made</li>
                <li>Risk reduction level</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background: #e3f2fd; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: #1565c0; margin: 0 0 10px 0;">💬 Chat with Contract</h4>
            <p style="color: #333; font-size: 14px;">Ask any question about your contract in plain English:</p>
            <ul style="color: #555; font-size: 13px;">
                <li>What is the notice period?</li>
                <li>Can I terminate early?</li>
                <li>What are the payment terms?</li>
                <li>Is there a non-compete clause?</li>
            </ul>
        </div>

        <div style="background: #e8f5e9; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: #2e7d32; margin: 0 0 10px 0;">📄 PDF Report</h4>
            <p style="color: #333; font-size: 14px;">Download a professional PDF report containing:</p>
            <ul style="color: #555; font-size: 13px;">
                <li>Overall risk score & breakdown</li>
                <li>All detected risk clauses</li>
                <li>Explanations & contract snippets</li>
                <li>Generated timestamp & disclaimer</li>
            </ul>
        </div>

        <div style="background: #fce4ec; border-radius: 12px; padding: 20px; margin-bottom: 15px;">
            <h4 style="color: #880e4f; margin: 0 0 10px 0;">🔐 Secure Login</h4>
            <p style="color: #333; font-size: 14px;">Your account is protected with:</p>
            <ul style="color: #555; font-size: 13px;">
                <li>SHA-256 password hashing</li>
                <li>Supabase cloud database</li>
                <li>Session-based authentication</li>
                <li>Secure logout</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tech Stack ─────────────────────────────────────────
    st.subheader("🛠️ Tech Stack")

    tech = [
        ("🎨", "Streamlit",             "Frontend UI",          "#e3f2fd", "#1565c0"),
        ("⚡", "Groq + LLaMA 3.1",      "AI Inference",         "#f3e5f5", "#6a1b9a"),
        ("🧠", "HuggingFace BGE",       "Embeddings",           "#e8f5e9", "#2e7d32"),
        ("🗄️", "ChromaDB",              "Vector Store",         "#fff3e0", "#e65100"),
        ("🔗", "LangChain",             "RAG Pipeline",         "#fce4ec", "#880e4f"),
        ("📄", "PyPDF + ReportLab",     "PDF Processing",       "#e0f7fa", "#006064"),
        ("🔐", "Supabase",              "Auth & Database",      "#f9fbe7", "#558b2f"),
        ("☁️", "Streamlit Cloud",       "Deployment",           "#e8eaf6", "#283593"),
    ]

    cols = st.columns(4)
    for i, (icon, name, role, bg, color) in enumerate(tech):
        with cols[i % 4]:
            st.markdown(f"""
            <div style="background: {bg}; border-radius: 10px; padding: 12px; 
                        text-align: center; margin-bottom: 10px;">
                <div style="font-size: 24px;">{icon}</div>
                <div style="font-weight: bold; color: {color}; font-size: 13px;">{name}</div>
                <div style="color: #555; font-size: 11px;">{role}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Disclaimer ─────────────────────────────────────────
    st.markdown("""
    <div style="background: #fff8e1; border: 1px solid #ffc107; border-radius: 10px; padding: 15px;">
        <h4 style="color: #f57f17; margin: 0 0 8px 0;">⚠️ Disclaimer</h4>
        <p style="color: #555; font-size: 13px; margin: 0;">
            ContractSentry AI is an informational tool only. It does not constitute legal advice. 
            Always consult a qualified lawyer before signing any contract. 
            AI analysis may not catch all risks in complex legal documents.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Start Analyzing Contracts", use_container_width=True):
        st.session_state.current_page = "main"
        st.rerun()

# ── Router ─────────────────────────────────────────────
if st.session_state.logged_in:
    if st.session_state.current_page == "how_it_works":
        show_how_it_works()
    else:
        show_main_app()
else:
    show_auth_screen()
