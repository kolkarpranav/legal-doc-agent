import streamlit as st
import os
import json
import time
from dotenv import load_dotenv

from agents.extractor import extract_case_entities
from agents.generator import generate_affidavit
from agents.validator import run_deterministic_validation
from agents.llm_evaluator import run_llm_evaluation
from agents.reporter import compile_evaluation_report

load_dotenv()

st.set_page_config(page_title="AI Legal Agent", layout="wide")

# Session state initialization
if "pipeline_complete" not in st.session_state:
    st.session_state.pipeline_complete = False

# ================= SIDEBAR =================
with st.sidebar:
    st.title("Settings & Controls")
    
    # API Key guard status
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "your_gemini_api_key_here":
        st.success("✅ GEMINI_API_KEY Detected")
    else:
        st.error("❌ GEMINI_API_KEY Missing/Invalid")
        
    st.info("🤖 Model: gemini-1.5-flash (Google)")
    
    st.subheader("Source Documents")
    pdf1 = st.file_uploader("Rules PDF (01)", type=["pdf"])
    pdf2 = st.file_uploader("Sample PDF (02)", type=["pdf"])
    pdf3 = st.file_uploader("Case Facts PDF (03)", type=["pdf"])
    st.caption("Uploads are optional. Pipeline will fall back to 'inputs/' folder files if not provided.")
    
    run_button = st.button("🚀 Run Pipeline", type="primary", use_container_width=True)

# ================= MAIN AREA: BEFORE RUN =================
if not st.session_state.pipeline_complete and not run_button:
    st.title("🏛️ AI Legal Document Agent")
    st.markdown("""
    Welcome! This agentic system automates the drafting and evaluation of an **Affidavit in Reply**.
    
    It uses a 4-Agent Pipeline:
    1. **Extractor**: Extracts structured case facts from provided PDF documents.
    2. **Generator**: Drafts the legal document formatted perfectly according to rules.
    3. **Evaluators**: Audits the document for structural flaws and hallucinations.
    4. **Reporter**: Generates a graded scorecard of the AI's performance.
    
    👈 Click **Run Pipeline** in the sidebar to start!
    """)
    st.stop()

# ================= MAIN AREA: RUNNING PIPELINE =================
if run_button:
    if not api_key or api_key == "your_gemini_api_key_here":
        st.error("GEMINI_API_KEY is not set. Add it to your .env file and restart.")
        st.stop()
        
    # Handle file uploads (save them temporarily to inputs/ if uploaded)
    os.makedirs("inputs", exist_ok=True)
    if pdf1:
        with open("inputs/01_Affidavit_Format_Explained.pdf", "wb") as f:
            f.write(pdf1.getbuffer())
    if pdf2:
        with open("inputs/02_Affidavit_in_Reply_Sample.pdf", "wb") as f:
            f.write(pdf2.getbuffer())
    if pdf3:
        with open("inputs/03_Case_Information.pdf", "wb") as f:
            f.write(pdf3.getbuffer())
            
    # Run pipeline with progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Agent 1
        status_text.info("Agent 1/4: Extracting entities from PDFs...")
        extract_case_entities("inputs", "outputs/entities.json")
        progress_bar.progress(25)
        
        # Agent 2
        status_text.info("Agent 2/4: Generating Affidavit in Reply...")
        generate_affidavit("outputs/entities.json", "inputs", "outputs/affidavit.docx")
        progress_bar.progress(50)
        
        # Agent 3
        status_text.info("Agent 3/4: Validating and Evaluating Output...")
        det_res = run_deterministic_validation("outputs/affidavit.docx", "outputs/affidavit.txt")
        progress_bar.progress(65)
        llm_res = run_llm_evaluation("outputs/entities.json", "outputs/affidavit.txt")
        progress_bar.progress(85)
        
        # Agent 4
        status_text.info("Agent 4/4: Compiling Evaluation Report...")
        compile_evaluation_report(det_res, llm_res, "outputs/evaluation_report.json", "outputs/evaluation_report.md")
        progress_bar.progress(100)
        
        status_text.success("✅ Pipeline Complete!")
        st.session_state.pipeline_complete = True
        time.sleep(1) # Brief pause before showing results
        st.rerun() # Refresh to show results
        
    except Exception as e:
        st.error(f"Pipeline failed: {e}")
        st.stop()

# ================= MAIN AREA: RESULTS =================
if st.session_state.pipeline_complete:
    st.title("🏛️ AI Legal Document Agent")
    st.success("🎉 Pipeline executed successfully!")
    
    # Load dynamic data
    try:
        with open("outputs/evaluation_report.json", "r", encoding="utf-8") as f:
            report = json.load(f)
        with open("outputs/entities.json", "r", encoding="utf-8") as f:
            entities = json.load(f)
    except FileNotFoundError:
        st.error("Output files not found. Try running the pipeline again.")
        st.stop()
        
    # Dynamic KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Score", f"{report.get('overall_score', 0)}/100")
    col2.metric("Dimensions Audited", len(report.get("dimensions", [])))
    col3.metric("Body Paragraph Count", entities.get("paragraph_count", 0))
    col4.metric("Case Reference", f"WP No. {entities.get('case_number', '')} of {entities.get('year', '')}")
    
    # Download buttons
    st.divider()
    st.subheader("📥 Download Outputs")
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)
    
    if os.path.exists("outputs/affidavit.docx"):
        with open("outputs/affidavit.docx", "rb") as f:
            d_col1.download_button("Word Doc (.docx)", f, "affidavit.docx")
            
    if os.path.exists("outputs/evaluation_report.md"):
        with open("outputs/evaluation_report.md", "r", encoding="utf-8") as f:
            d_col2.download_button("Report (.md)", f.read(), "evaluation_report.md")
            
    if os.path.exists("outputs/evaluation_report.json"):
        with open("outputs/evaluation_report.json", "r", encoding="utf-8") as f:
            d_col3.download_button("Report (.json)", f.read(), "evaluation_report.json")
            
    if os.path.exists("outputs/entities.json"):
        with open("outputs/entities.json", "r", encoding="utf-8") as f:
            d_col4.download_button("Entities (.json)", f.read(), "entities.json")
        
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Evaluation Scorecard", 
        "📄 Generated Affidavit", 
        "🧩 Extracted Entities", 
        "⚠️ Issues & Deductions", 
        "🏗️ Architecture"
    ])
    
    with tab1:
        st.subheader("Scorecard")
        score = report.get("overall_score", 0)
        color = "green" if score >= 75 else "red"
        st.markdown(f"<h1 style='text-align: center; color: {color};'>{score}/100</h1>", unsafe_allow_html=True)
        
        st.markdown("### Dimension Breakdowns")
        for dim in report.get("dimensions", []):
            d_col1, d_col2 = st.columns([1, 4])
            d_col1.write(f"**{dim['name']}**")
            score_disp = int(dim['score']) if dim['score'] % 1 == 0 else dim['score']
            d_col1.write(f"{score_disp} / {dim['max']} ({dim['type']})")
            
            # Prevent division by zero
            progress_val = int((dim['score'] / dim['max']) * 100) if dim['max'] > 0 else 0
            d_col2.progress(min(max(progress_val, 0), 100)) # Ensure between 0-100
            
    with tab2:
        st.subheader("Raw Text Preview")
        if os.path.exists("outputs/affidavit.txt"):
            with open("outputs/affidavit.txt", "r", encoding="utf-8") as f:
                st.text_area("Affidavit Text", f.read(), height=600)
        else:
            st.info("No raw text available.")
            
    with tab3:
        st.subheader("Structured Case Facts")
        st.json(entities)
        
    with tab4:
        st.subheader("Issues Found")
        issues = report.get("issues", [])
        if not issues:
            st.success("✅ Zero issues found! Perfect score.")
        else:
            for issue in issues:
                st.warning(issue)
                
    with tab5:
        st.subheader("4-Agent Flow")
        mermaid_code = """
        ```mermaid
        graph TD
            A[3 Input PDFs] -->|Read & Parse| B[Agent 1: Extractor]
            B -->|Pydantic Validation| C[entities.json]
            C -->|Few-Shot Prompt| D[Agent 2: Generator]
            A -->|Format Rules| D
            D -->|Word Formatting| E[affidavit.docx]
            D -->|Raw Text| F[affidavit.txt]
            C --> G[Agent 3a & 3b: Validators]
            F --> G
            G -->|Scores & Issues| H[Agent 4: Reporter]
            H --> I[evaluation_report.md]
        ```
        """
        st.markdown(mermaid_code)
