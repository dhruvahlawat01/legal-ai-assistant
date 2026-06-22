import streamlit as st
from backend import LegalAnalyzer
import tempfile
import os

# Initialize the Analyzer (Load once at start)
analyzer = LegalAnalyzer()

st.set_page_config(page_title="ContractSentry AI", layout="wide")

st.title("🛡️ ContractSentry: Legal Risk Detection")
st.markdown("""
Upload a PDF contract. The AI will scan for risky clauses like Non-Competes, 
Indefinite Terms, or Liability Caps and highlight them with explanations.
""")

# File Uploader
uploaded_file = st.file_uploader("Upload PDF Contract", type=["pdf"])

if uploaded_file is not None:
    # Save file temporarily (in real app use a temp folder)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(uploaded_file.read())
        temp_path = f.name
    
    try:
        st.info("🔄 Processing document... This may take 10-30 seconds.")
        
        # Show a progress bar (simulated for demo)
        progress_bar = st.progress(0.0)
        
        # Run Analysis
        result = analyzer.analyze_risk(temp_path)
        
        # Update Progress Bar
        progress_bar.progress(1.0)
        
        # Display Results
        st.subheader("🚩 Detected Risks:")
        
        if result:
            for item in result:
                risk_level = item.get("risk_level", "UNKNOWN")
                clause_type = item.get("clause_type", "General")
                explanation = item.get("explanation", "")
                
                # Color code based on risk level
                color = "red" if risk_level == "HIGH" else ("orange" if risk_level == "MEDIUM" else "green")
                
                st.markdown(f"""
                **{clause_type}** (`{risk_level}`)  
                *Explanation:* {explanation[:200]}...
                """, unsafe_allow_html=True)
        else:
            st.warning("No specific risks found in this document.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

else:
    st.info("Waiting for file upload...")



import traceback

try:
    result = analyzer.process_file(uploaded_file)
except Exception as e:
    st.error(traceback.format_exc())  # shows full stack trace in UI
