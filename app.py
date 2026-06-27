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
st.set_page_config(page_title="ContractSentry AI", layout="wide")

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
if "breach_obligations" not in st.session_state:
    st.session_state.breach_obligations = None
if "breach_predictions" not in st.session_state:
    st.session_state.breach_predictions = None

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

    # Top bar
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("🛡️ ContractSentry: Legal Risk Detection")
    with col2:
        st.markdown(f"👤 **{st.session_state.username}**")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.vectorstore = None
            st.session_state.chat_history = []
            st.session_state.analysis_done = False
            st.session_state.analysis_result = None
            st.session_state.risk_data = None
            st.rerun()

    st.markdown("""
    Upload a PDF contract. The AI will scan for risky clauses like Non-Competes, 
    Indefinite Terms, or Liability Caps and highlight them with explanations.
    """)

    uploaded_file = st.file_uploader("Upload PDF Contract", type=["pdf"])

    if uploaded_file is not None:

        # Reset if new file uploaded
        if uploaded_file.name != st.session_state.uploaded_filename:
            st.session_state.analysis_done = False
            st.session_state.analysis_result = None
            st.session_state.risk_data = None
            st.session_state.vectorstore = None
            st.session_state.chat_history = []
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.breach_obligations = None
            st.session_state.breach_predictions = None

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
            tab1, tab2, tab3 = st.tabs(["📊 Risk Analysis", "💬 Chat with Contract", "⚠️ Breach Predictor"])

            # ── Tab 1: Risk Analysis ───────────────────────────
            with tab1:
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
                    <p style="color: #333333; margin: 5px 0;">Contract Risk Score: {risk_data['score']}%</p>
                </div>
                """, unsafe_allow_html=True)

                st.progress(risk_data["score"] / 100)

                st.markdown("---")
                st.subheader("🚩 Detected Risks:")

                if result:
                    for i, item in enumerate(result):
                        risk_level = item.get("risk_level", "UNKNOWN")
                        clause_type = item.get("clause_type", "General")
                        explanation = item.get("explanation", "")
                        text_snippet = item.get("text_snippet", "")

                        color = "red" if risk_level == "HIGH" else ("orange" if risk_level == "MEDIUM" else "green")

                        st.markdown(f"""
                        <div style="border-left: 4px solid {color}; padding: 10px; 
                                    margin-bottom: 5px; background-color: {color}11;
                                    border-radius: 0 8px 8px 0;">
                            <b style="color: {color};">{clause_type}</b> &nbsp; 
                            <code style="background:{color}22; color: #333333;">{risk_level}</code><br><br>
                            <span style="color: #333333;"><i>{explanation}</i></span><br>
                            {"<small style='color:#555555;'><b>Snippet:</b> " + text_snippet + "</small>" if text_snippet else ""}
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
                                if st.button("✍️ Rewrite Clause", key=rewrite_key):
                                    with st.spinner("Generating safer clause..."):
                                        try:
                                            rewrite = analyzer.rewrite_clause(
                                                clause_type, explanation, text_snippet
                                            )
                                            st.session_state[rewrite_result_key] = rewrite
                                        except Exception as e:
                                            st.error(f"Rewrite failed: {e}")
                            with col_btn2:
                                if st.session_state[rewrite_result_key]:
                                    if st.button("❌ Hide", key=f"hide_{i}"):
                                        st.session_state[rewrite_result_key] = None

                            if st.session_state[rewrite_result_key]:
                                rewrite = st.session_state[rewrite_result_key]
                                risk_reduction = rewrite.get("risk_reduction", "MEDIUM")
                                reduction_color = (
                                    "green" if risk_reduction == "HIGH"
                                    else "orange" if risk_reduction == "MEDIUM"
                                    else "blue"
                                )
                                st.markdown(f"""
                                <div style="border: 2px solid #28a745; border-radius: 8px; 
                                            padding: 15px; margin: 5px 0 10px 0; 
                                            background-color: #f0fff4;">
                                    <h4 style="color: #28a745; margin: 0 0 10px 0;">✅ Suggested Safer Clause</h4>
                                    <p style="color: #333333;"><b>Issue:</b> {rewrite.get("original_issue", "")}</p>
                                    <hr style="border-color: #28a74544;">
                                    <p style="color: #333333;"><b>Rewritten Clause:</b></p>
                                    <p style="background: white; padding: 10px; border-radius: 5px; 
                                               border-left: 3px solid #28a745; font-style: italic; color: #222222;">
                                        {rewrite.get("rewritten_clause", "")}
                                    </p>
                                    <p style="color: #333333;"><b>Key Changes:</b></p>
                                    <ul style="color: #333333;">
                                        {"".join(f'<li style="color: #333333;">{change}</li>' for change in rewrite.get("key_changes", []))}
                                    </ul>
                                    <p style="color: #333333;"><b>Risk Reduction:</b> 
                                        <span style="color: {reduction_color}; font-weight: bold;">{risk_reduction}</span>
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)
                else:
                    st.success("✅ No significant risks found in this document.")

                # Download Report
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

            # ── Tab 2: Chat with Contract ──────────────────────
            with tab2:
                st.subheader("💬 Chat with Your Contract")
                st.markdown("Ask any question about the contract and get an instant answer.")

                # Suggested questions
                st.markdown("**💡 Suggested Questions:**")
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
                            st.session_state.chat_history.append({
                                "role": "user",
                                "content": question
                            })
                            with st.spinner("Thinking..."):
                                try:
                                    answer = analyzer.chat_with_contract(
                                        question,
                                        st.session_state.vectorstore
                                    )
                                    st.session_state.chat_history.append({
                                        "role": "assistant",
                                        "content": answer
                                    })
                                except Exception as e:
                                    st.error(f"Chat failed: {e}")
                            st.rerun()

                st.markdown("---")

                # Chat history display
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div style="background-color: #e3f2fd; border-radius: 10px; 
                                    padding: 10px 15px; margin: 5px 0; 
                                    border-left: 4px solid #1976d2;">
                            <b style="color: #1976d2;">👤 You:</b><br>
                            <span style="color: #333333;">{message["content"]}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: #f3e5f5; border-radius: 10px; 
                                    padding: 10px 15px; margin: 5px 0;
                                    border-left: 4px solid #7b1fa2;">
                            <b style="color: #7b1fa2;">🤖 ContractSentry:</b><br>
                            <span style="color: #333333;">{message["content"]}</span>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Chat input
                col_input, col_send = st.columns([5, 1])
                with col_input:
                    user_question = st.text_input(
                        "Ask a question about your contract...",
                        key="chat_input",
                        label_visibility="collapsed",
                        placeholder="e.g. What happens if I break this contract?"
                    )
                with col_send:
                    send_clicked = st.button("Send 📨", use_container_width=True)

                if send_clicked and user_question.strip():
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_question
                    })
                    with st.spinner("Thinking..."):
                        try:
                            answer = analyzer.chat_with_contract(
                                user_question,
                                st.session_state.vectorstore
                            )
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": answer
                            })
                        except Exception as e:
                            st.error(f"Chat failed: {e}")
                    st.rerun()

                # Clear chat button
                if st.session_state.chat_history:
                    if st.button("🗑️ Clear Chat", use_container_width=True):
                        st.session_state.chat_history = []
                        st.rerun()

            # ── Tab 3: Breach Predictor ────────────────────────
            with tab3:
                st.subheader("⚠️ Operational Bottleneck & Breach Predictor")
                st.markdown("Tell us about your team's capacity and we'll predict which contract obligations are at risk of breach.")

                st.markdown("### 📋 Step 1: Your Team's Operational Capacity")

                col_a, col_b = st.columns(2)
                with col_a:
                    avg_delivery = st.text_input(
                        "⏱️ Average task/delivery time",
                        placeholder="e.g. 7 business days",
                        key="avg_delivery"
                    )
                    team_size = st.text_input(
                        "👥 Team size",
                        placeholder="e.g. 3 developers, 1 project manager",
                        key="team_size"
                    )
                with col_b:
                    current_workload = st.selectbox(
                        "📦 Current workload level",
                        ["Low (plenty of capacity)", "Medium (some projects running)", "High (near full capacity)", "Overloaded"],
                        key="workload"
                    )
                    revision_time = st.text_input(
                        "🔄 Time to process revision requests",
                        placeholder="e.g. 3-5 days per revision round",
                        key="revision_time"
                    )

                additional_notes = st.text_area(
                    "📝 Any other operational constraints?",
                    placeholder="e.g. Team goes on leave in August, dependent on a third-party API that has slow response times...",
                    key="op_notes",
                    height=80
                )

                if "breach_obligations" not in st.session_state:
                    st.session_state.breach_obligations = None
                if "breach_predictions" not in st.session_state:
                    st.session_state.breach_predictions = None

                st.markdown("### 🔍 Step 2: Extract Obligations & Predict Breaches")

                if st.button("🚀 Run Breach Prediction Analysis", use_container_width=True, type="primary"):
                    if not avg_delivery and not team_size:
                        st.warning("Please fill in at least your average delivery time and team size.")
                    else:
                        capacity_summary = f"""
                        - Average delivery time: {avg_delivery or 'Not specified'}
                        - Team size/composition: {team_size or 'Not specified'}
                        - Current workload: {current_workload}
                        - Revision request turnaround: {revision_time or 'Not specified'}
                        - Additional constraints: {additional_notes or 'None'}
                        """

                        with st.spinner("📄 Extracting obligations from contract..."):
                            try:
                                st.session_state.breach_obligations = analyzer.extract_obligations(temp_path)
                            except Exception as e:
                                st.error(f"Failed to extract obligations: {e}")
                                st.session_state.breach_obligations = []

                        if st.session_state.breach_obligations:
                            with st.spinner("🧠 Running breach prediction analysis..."):
                                try:
                                    st.session_state.breach_predictions = analyzer.predict_breach(
                                        st.session_state.breach_obligations,
                                        capacity_summary
                                    )
                                except Exception as e:
                                    st.error(f"Breach prediction failed: {e}")
                                    st.session_state.breach_predictions = []
                        st.rerun()

                # Show extracted obligations
                if st.session_state.breach_obligations is not None:
                    st.markdown("---")
                    st.markdown("### 📅 Extracted Contract Obligations")

                    if not st.session_state.breach_obligations:
                        st.info("No specific obligations or deadlines were found in this contract.")
                    else:
                        for i, ob in enumerate(st.session_state.breach_obligations, 1):
                            with st.expander(f"📌 Obligation {i}: {ob.get('obligation', 'Unknown')[:80]}..."):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**⏰ Deadline:** {ob.get('deadline', 'Not specified')}")
                                    st.markdown(f"**👤 Responsible:** {ob.get('party_responsible', 'Not specified')}")
                                with col2:
                                    st.markdown(f"**🔗 Dependency:** {ob.get('dependency') or 'None'}")
                                    st.markdown(f"**📄 Clause:** {ob.get('clause_reference', 'Not specified')}")

                # Show breach predictions
                if st.session_state.breach_predictions is not None:
                    st.markdown("---")
                    st.markdown("### 🚨 Breach Risk Predictions")

                    if not st.session_state.breach_predictions:
                        st.success("✅ Great news! Based on your operational capacity, no high-risk breaches were predicted. Your team appears capable of meeting all contract obligations.")
                    else:
                        high_risks = [p for p in st.session_state.breach_predictions if p.get("breach_probability") == "HIGH"]
                        medium_risks = [p for p in st.session_state.breach_predictions if p.get("breach_probability") == "MEDIUM"]

                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("🔴 High Breach Risk", len(high_risks))
                        with col2:
                            st.metric("🟠 Medium Breach Risk", len(medium_risks))

                        for pred in st.session_state.breach_predictions:
                            prob = pred.get("breach_probability", "MEDIUM")
                            bg = "#fff5f5" if prob == "HIGH" else "#fff8f0"
                            border = "#dc3545" if prob == "HIGH" else "#fd7e14"
                            emoji = "🔴" if prob == "HIGH" else "🟠"

                            st.markdown(f"""
                            <div style="background: {bg}; border-left: 5px solid {border}; 
                                        border-radius: 8px; padding: 15px; margin: 10px 0;">
                                <div style="font-size: 16px; font-weight: bold; color: {border}; margin-bottom: 8px;">
                                    {emoji} {prob} BREACH RISK
                                </div>
                                <div style="font-size: 13px; color: #333; margin-bottom: 6px;">
                                    <b>Obligation:</b> {pred.get('obligation', '')}
                                </div>
                                <div style="font-size: 13px; color: #333; margin-bottom: 6px;">
                                    <b>Deadline:</b> {pred.get('deadline', 'Not specified')}
                                </div>
                                <div style="background: #fff; border-radius: 6px; padding: 10px; margin: 8px 0; 
                                            border: 1px solid {border}; font-size: 13px; color: #555; font-style: italic;">
                                    🔔 {pred.get('alert_message', '')}
                                </div>
                                <div style="font-size: 13px; color: #555; margin-bottom: 4px;">
                                    <b>Why at risk:</b> {pred.get('reason', '')}
                                </div>
                                <div style="font-size: 13px; color: #2e7d32; margin-top: 8px;">
                                    <b>💡 Recommendation:</b> {pred.get('recommendation', '')}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                    if st.button("🔄 Reset Breach Analysis", key="reset_breach"):
                        st.session_state.breach_obligations = None
                        st.session_state.breach_predictions = None
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
        st.info("⬆️ Please upload a PDF contract to begin analysis.")

def show_how_it_works():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("📖 How ContractSentry Works")
    with col2:
        st.markdown(f"👤 **{st.session_state.username}**")
        if st.button("Logout"):
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
