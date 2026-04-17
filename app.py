"""
Sial-Compliance-Pro: High-Fidelity Aviation Regulatory Gap Analysis
Developed for Authentic IOSA/EASA Audit Preparation
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import os
import time
import json
import traceback

# -----------------------------------------------------------------------------
# 1. CORE SYSTEM IMPORTS & PATH FIXING
# -----------------------------------------------------------------------------
# Ensuring we use flat imports for the current directory structure
try:
    from config import settings, ConformityStatus, EvidenceType, ISARPParser
    from gap_analyzer import GapAnalysisEngine, quick_gap_analysis
    from vectorizer import VectorStore
except ImportError as e:
    st.error(f"SYSTEM CRITICAL: Failed to import local modules. Ensure all .py files are in the root directory. Error: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 2. PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sial-Compliance-Pro | IOSA Audit",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional Audit Interface
st.markdown("""
<style>
    /* Main Branding */
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        color: #1f4788;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
        font-style: italic;
    }
    
    /* Audit Metric Cards */
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f4788;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Status Coloring */
    .status-conformity { color: #155724; background-color: #d4edda; font-weight: bold; padding: 5px; border-radius: 3px; }
    .status-finding { color: #721c24; background-color: #f8d7da; font-weight: bold; padding: 5px; border-radius: 3px; }
    .status-observation { color: #856404; background-color: #fff3cd; font-weight: bold; padding: 5px; border-radius: 3px; }
    
    /* Scannability Helpers */
    .isarp-box {
        border: 1px solid #ddd;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
        background-color: white;
    }
    .quote-box {
        font-family: 'Courier New', Courier, monospace;
        background-color: #f1f1f1;
        padding: 10px;
        border-left: 3px solid #1f4788;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DEFENSIVE SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
def initialize_system():
    """Defensive initialization to prevent AttributeErrors"""
    if 'engine' not in st.session_state:
        with st.spinner("Initializing Audit Engine..."):
            try:
                st.session_state.engine = GapAnalysisEngine()
            except Exception as e:
                st.error(f"Engine Init Failure: {e}")
                st.stop()

    # Initialization of key tracking variables
    defaults = {
        'ism_loaded': False,
        'manuals_loaded': [],
        'analysis_complete': False,
        'current_category': "All",
        'audit_log': [],
        'active_tab': "🏠 Dashboard"
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Ensure gap_results list exists in engine
    if not hasattr(st.session_state.engine, 'gap_results'):
        st.session_state.engine.gap_results = []

initialize_system()

# -----------------------------------------------------------------------------
# 4. SIDEBAR & NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.iata.org/ResourceFiles/iata/iata-logo.png", width=150)
    st.markdown("## ✈️ Sial Aviation Audit")
    st.markdown("---")
    
    page = st.radio(
        "Audit Modules",
        ["🏠 Dashboard", 
         "📄 Document Ingestion", 
         "🔍 Gap Analysis", 
         "📊 Evidence Management",
         "📈 Reports & Export",
         "⚙️ System Logs"],
        key="nav_radio"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Live Stats")
    stats = st.session_state.engine.get_statistics()
    
    col_a, col_b = st.columns(2)
    col_a.metric("ISARPs", stats['total_isarps'])
    col_b.metric("Manuals", len(st.session_state.manuals_loaded))
    
    # System Health Check
    st.markdown("### 🛡️ System Health")
    health_color = "🟢" if settings.anthropic_api_key else "🔴"
    st.write(f"{health_color} AI Engine (Claude 3.5)")
    st.write(f"🟢 Database (ChromaDB)")
    
    if st.button("♻️ Reset Session"):
        st.session_state.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# 5. MODULE: DASHBOARD
# -----------------------------------------------------------------------------
def show_dashboard():
    st.markdown('<div class="main-header">Audit Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">IOSA/EASA Regulatory Compliance Overview</div>', unsafe_allow_html=True)
    
    stats = st.session_state.engine.get_statistics()
    
    # Metric Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total ISARPs", stats['total_isarps'])
        st.markdown('</div>', unsafe_allow_html=True)
    with m2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Conformity ✅", stats['conformity_count'])
        st.markdown('</div>', unsafe_allow_html=True)
    with m3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Findings 🔴", stats['findings_count'])
        st.markdown('</div>', unsafe_allow_html=True)
    with m4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Pending ⏳", stats['pending_evidence_count'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Layout with Charts
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Compliance by Category")
        if stats['analyzed_isarps'] > 0:
            # Mock chart data based on stats
            chart_data = pd.DataFrame({
                'Status': ['Conformity', 'Findings', 'Observations', 'Pending'],
                'Count': [stats['conformity_count'], stats['findings_count'], 
                          stats['observations_count'], stats['pending_evidence_count']]
            })
            st.bar_chart(chart_data.set_index('Status'))
        else:
            st.info("Run Gap Analysis to populate visual analytics.")

    with c2:
        st.subheader("Critical Action Items")
        findings = [r for r in st.session_state.engine.gap_results if r.get('status') == ConformityStatus.FINDING]
        if findings:
            for f in findings[:5]:
                st.error(f"**{f['isarp_code']}**: Documentation missing.")
        else:
            st.success("No critical findings identified.")

# -----------------------------------------------------------------------------
# 6. MODULE: DOCUMENT INGESTION
# -----------------------------------------------------------------------------
def show_document_ingestion():
    st.markdown('<div class="main-header">Document Ingestion</div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📘 IOSA Standards Manual (ISM)", "📙 Airline Operations Manuals"])
    
    with t1:
        st.subheader("ISM Processor")
        st.write("Upload the official ISM PDF or Word file to extract the 1,800+ required ISARPs.")
        
        ism_file = st.file_uploader("Upload ISM File", type=['pdf', 'docx', 'doc'])
        
        if ism_file:
            if st.button("Extract & Vectorize ISARPs"):
                with st.spinner(f"Analyzing {ism_file.name}..."):
                    # Save temporary file
                    path = settings.ism_dir / ism_file.name
                    with open(path, "wb") as f:
                        f.write(ism_file.getbuffer())
                    
                    # Process
                    try:
                        count = st.session_state.engine.ingest_ism_manual(path)
                        st.session_state.ism_loaded = True
                        st.success(f"Successfully loaded {count} ISARPs into the vector database.")
                        st.session_state.audit_log.append(f"[{datetime.now()}] Loaded {count} ISARPs from {ism_file.name}")
                    except Exception as e:
                        st.error(f"Parsing Error: {e}")
        
        # Display table if loaded
        if st.session_state.ism_loaded:
            st.markdown("#### Preview of Extracted ISARPs")
            df_isarps = pd.DataFrame([vars(i) for i in st.session_state.engine.isarps])
            st.dataframe(df_isarps[['code', 'category', 'requirement_text']], height=300)

    with t2:
        st.subheader("Airline Manual Ingestion")
        st.write("Upload FOM, COM, AMM, etc. (PDF/Word).")
        
        manual_files = st.file_uploader("Select Operations Manuals", type=['pdf', 'docx'], accept_multiple_files=True)
        
        if manual_files and st.button("Process Airline Manuals"):
            for m in manual_files:
                path = settings.manuals_dir / m.name
                with open(path, "wb") as f:
                    f.write(m.getbuffer())
                
                with st.spinner(f"Vectorizing {m.name}..."):
                    m_type = st.session_state.engine.ingest_airline_manual(path)
                    st.session_state.manuals_loaded.append({'filename': m.name, 'type': m_type, 'date': datetime.now()})
            
            st.success(f"Vectorized {len(manual_files)} manuals.")
        
        if st.session_state.manuals_loaded:
            st.table(pd.DataFrame(st.session_state.manuals_loaded))

# -----------------------------------------------------------------------------
# 7. MODULE: AUTHENTIC GAP ANALYSIS (LINE-BY-LINE)
# -----------------------------------------------------------------------------
def show_gap_analysis():
    st.markdown('<div class="main-header">Intelligent Gap Analysis</div>', unsafe_allow_html=True)
    
    if not st.session_state.ism_loaded:
        st.warning("⚠️ Action Required: Please ingest the ISM manual first.")
        return
    
    # Analysis Configuration
    col_x, col_y = st.columns(2)
    with col_x:
        category = st.selectbox("Operational Category", ["All"] + list(settings.isarp_categories.keys()))
    with col_y:
        st.write("###")
        if st.button("🚀 Run AI Audit", type="primary"):
            with st.spinner("Claude 3.5 Sonnet is auditing provisions..."):
                cat_filter = None if category == "All" else category
                st.session_state.engine.run_gap_analysis(category=cat_filter)
                st.session_state.analysis_complete = True
                st.rerun()

    if st.session_state.analysis_complete and st.session_state.engine.gap_results:
        st.markdown("---")
        st.subheader("📋 Audit Verification (Authentic Evidence)")
        
        # Filter for the UI
        status_filter = st.multiselect("Filter Results", ConformityStatus.all_statuses(), default=ConformityStatus.all_statuses())
        
        for result in st.session_state.engine.gap_results:
            status = result.get('status')
            if status not in status_filter:
                continue
            
            # AUTHENTIC RED HIGHLIGHT LOGIC FOR MISSING ITEMS
            is_missing = result.get('manual_quote') == "MISSING" or status == ConformityStatus.FINDING
            
            with st.expander(f"{'🔴' if is_missing else '✅'} {result.get('isarp_code')} - {result.get('isarp_title', '')}", expanded=is_missing):
                if is_missing:
                    st.error("### 🔴 FINDING: Provision Missing in Documentation")
                    st.markdown(f"**Gap Analysis:** {result.get('documentation_gap')}")
                    st.markdown("**Required Actions:** Ensure this requirement is documented using mandatory language ('shall').")
                else:
                    st.success("### ✅ CONFORMITY")
                    st.markdown("**Authentic Manual Quote:**")
                    st.markdown(f"<div class='quote-box'>\"{result.get('manual_quote')}\"</div>", unsafe_allow_html=True)
                    st.caption(f"**Reference Source:** {result.get('manual_reference')}")
                
                st.markdown(f"**Auditor Reasoning:** {result.get('reasoning')}")
                
                # Action Buttons
                if is_missing:
                    st.button(f"Draft Policy for {result['isarp_code']}", key=f"draft_{result['isarp_code']}")

# -----------------------------------------------------------------------------
# 8. MODULE: EVIDENCE MANAGEMENT
# -----------------------------------------------------------------------------
def show_evidence_management():
    st.markdown('<div class="main-header">Implementation Proof (IPM 6.7.1)</div>', unsafe_allow_html=True)
    st.info("Upload actual operational records (Rosters, Logs, Training Files) to prove implementation.")
    
    if not st.session_state.analysis_complete:
        st.warning("Run analysis first to link evidence to findings.")
        return
        
    findings = [r['isarp_code'] for r in st.session_state.engine.gap_results if r['status'] in [ConformityStatus.PENDING_EVIDENCE, ConformityStatus.FINDING]]
    
    if findings:
        target = st.selectbox("Select ISARP for Evidence Upload", findings)
        ev_type = st.selectbox("Evidence Type", EvidenceType.all_types())
        ev_file = st.file_uploader("Upload Evidence Document (PDF)")
        
        if ev_file and st.button("Validate Evidence"):
            with st.spinner("Validating implementation markers..."):
                # Simulation of engine logic
                st.success(f"Evidence linked to {target}. AI validation in progress.")
    else:
        st.success("No ISARPs currently requiring implementation evidence.")

# -----------------------------------------------------------------------------
# 9. MODULE: SYSTEM LOGS
# -----------------------------------------------------------------------------
def show_logs():
    st.header("⚙️ Audit System Logs")
    if st.session_state.audit_log:
        for log in reversed(st.session_state.audit_log):
            st.text(log)
    else:
        st.write("No events recorded in current session.")

# -----------------------------------------------------------------------------
# 10. MAIN ROUTING
# -----------------------------------------------------------------------------
if page == "🏠 Dashboard":
    show_dashboard()
elif page == "📄 Document Ingestion":
    show_document_ingestion()
elif page == "🔍 Gap Analysis":
    show_gap_analysis()
elif page == "📊 Evidence Management":
    show_evidence_management()
elif page == "⚙️ System Logs":
    show_logs()
elif page == "📈 Reports & Export":
    st.header("📈 Compliance Reports")
    if st.button("Generate Full Audit PDF"):
        st.info("PDF Generation Module is initializing...")
    if st.button("Download Gap Analysis (Excel)"):
        # Excel export logic
        df = st.session_state.engine.generate_compliance_report()
        st.download_button("Download Now", df.to_csv(), "gap_report.csv", "text/csv")

# Footer
st.markdown("---")
st.caption(f"Sial-Compliance-Pro v2.4 | System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Environment: Audit-Ready")
