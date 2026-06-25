import streamlit as st
from backend import LegalAnalyzer
from auth import login_user, register_user
import tempfile
import os

# ── Page Config ────────────────────────────────────────
st.set_page_config(page_title="ContractSentry AI", layout="wide")

# ── Session State Init ─────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ── Auth Screen ────────────────────────────────────────
def show_auth_screen():
    st.title("🛡️ ContractSentry AI")
    st.markdown("#### AI-Powered Legal Contract Risk Detection")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

        with tab1:
            st.subheader("Welcome Back")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")

            if st.button("Login", use_container_width=True):
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    success, message = login_user(username, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        with tab2:
            st.subheader("Create Account")
            new_username = st.text_input("Choose Username", key="reg_user")
            new_password = st.text_input("Choose Password", type="password", key="reg_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")

            if st.button("Register", use_container_width=True):
                if not new_username or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success, message = register_user(new_username, new_password)
                    if success:
                        st.success(message + " Please login.")
                    else:
                        st.error(message)

# ── Main App ───────────────────────────────────────────
def show_main_app():
    analyzer = LegalAnalyzer()

    # Top bar with username and logout
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("🛡️ ContractSentry: Legal Risk Detection")
    with col2:
        st.markdown(f"👤 **{st.session_state.username}**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    st.markdown("""
    Upload a PDF contract. The AI will scan for risky clauses like Non-Competes, 
    Indefinite Terms, or Liability Caps and highlight them with explanations.
    """)

    uploaded_file = st.file_uploader("Upload PDF Contract", type=["pdf"])

    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            uploaded_file.seek(0)
            f.write(uploaded_file.read())
            temp_path = f.name

        try:
            st.info("🔄 Processing document... This may take 10-30 seconds.")
            progress_bar = st.progress(0.0)

            result = analyzer.analyze_risk(temp_path)
            progress_bar.progress(1.0)

            # Risk Score
            risk_data = analyzer.calculate_risk_score(result)

            st.markdown("---")
            st.subheader("📊 Overall Risk Assessment")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Overall Score", f"{risk_data['score']}%")
            with col2:
                st.metric("🔴 High Risk", risk_data["breakdown"].get("HIGH", 0))
            with col3:
                st.metric("🟠 Medium Risk", risk_data["breakdown"].get("MEDIUM", 0))
            with col4:
                st.metric("🟢 Low Risk", risk_data["breakdown"].get("LOW", 0))

            color = risk_data["color"]
            label = risk_data["label"]
            st.markdown(f"""
            <div style="background-color: {color}22; border: 2px solid {color}; 
                        border-radius: 10px; padding: 15px; text-align: center; margin: 10px 0;">
                <h2 style="color: {color}; margin: 0;">{label}</h2>
                <p style="margin: 5px 0;">Contract Risk Score: {risk_data['score']}%</p>
            </div>
            """, unsafe_allow_html=True)

            st.progress(risk_data["score"] / 100)

            st.markdown("---")
            st.subheader("🚩 Detected Risks:")

            if result:
                for item in result:
                    risk_level = item.get("risk_level", "UNKNOWN")
                    clause_type = item.get("clause_type", "General")
                    explanation = item.get("explanation", "")
                    text_snippet = item.get("text_snippet", "")

                    color = "red" if risk_level == "HIGH" else ("orange" if risk_level == "MEDIUM" else "green")

                    st.markdown(f"""
                    <div style="border-left: 4px solid {color}; padding: 10px; 
                                margin-bottom: 10px; background-color: {color}11;
                                border-radius: 0 8px 8px 0;">
                        <b style="color: {color};">{clause_type}</b> &nbsp; 
                        <code style="background:{color}22;">{risk_level}</code><br><br>
                        <i>{explanation}</i><br>
                        {"<small><b>Snippet:</b> " + text_snippet + "</small>" if text_snippet else ""}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ No significant risks found in this document.")

 # ── Download Report Button ─────────────────────────────
st.markdown("---")
st.subheader("📄 Download Report")

try:
    pdf_buffer = analyzer.generate_pdf_report(result, risk_data)
    st.download_button(
        label="📥 Download PDF Report",
        data=pdf_buffer,
        file_name=f"contract_analysis_{uploaded_file.name.replace('.pdf', '')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
except Exception as e:
    st.error(f"Could not generate report: {e}")
        
        except Exception as e:
            st.error(f"Error processing file: {e}")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        st.info("⬆️ Please upload a PDF contract to begin analysis.")

# ── Router ─────────────────────────────────────────────
if st.session_state.logged_in:
    show_main_app()
else:
    show_auth_screen()

