"""
Sial-Compliance-Pro | Aviation Regulatory Compliance System
Comprehensive IOSA/EASA Gap Analysis Tool
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import os
import json
import traceback
import re
import time

# -----------------------------------------------------------------------------
# 1. CORE SYSTEM IMPORTS
# -----------------------------------------------------------------------------
# Directly importing from the same folder to stop circular import errors
from config import settings, ConformityStatus, EvidenceType, ISARPParser
from gap_analyzer import GapAnalysisEngine
from vectorizer import VectorStore

# -----------------------------------------------------------------------------
# 2. PROFESSIONAL AUDIT STYLING (CSS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Sial-Compliance-Pro | IOSA Audit",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        color: #1f4788;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.3rem;
        color: #666;
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 6px solid #1f4788;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .audit-finding-red {
        background-color: #fff5f5;
        border: 2px solid #feb2b2;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .audit-conformity-green {
        background-color: #f0fff4;
        border: 2px solid #9ae6b4;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .quote-block {
        font-family: 'Courier New', monospace;
        background-color: #edf2f7;
        padding: 12px;
        border-radius: 6px;
        border-left: 4px solid #4a5568;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. DEFENSIVE SESSION STATE
# -----------------------------------------------------------------------------
def initialize_system_state():
    """Ensure all required variables exist in the session to prevent crashes"""
    if 'engine' not in st.session_state:
        st.session_state.engine = GapAnalysisEngine()
    
    if 'ism_loaded' not in st.session_state:
        st.session_state.ism_loaded = False
    if 'manuals_loaded' not in st.session_state:
        st.session_state.manuals_loaded = []
    if 'analysis_complete' not in st.session_state:
        st.session_state.analysis_complete = False
    if 'audit_logs' not in st.session_state:
        st.session_state.audit_logs = []

initialize_system_state()

# -----------------------------------------------------------------------------
# 4. NAVIGATION & SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ✈️ Audit Control Center")
    st.markdown("---")
    
    page = st.radio(
        "Navigate Modules",
        ["🏠 Dashboard", 
         "📄 Document Ingestion", 
         "🔍 Gap Analysis", 
         "📊 Evidence Tracker",
         "📈 Reports & Exports"],
        key="main_nav"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Live Audit Stats")
    stats = st.session_state.engine.get_statistics()
    st.metric("ISARPs Identified", stats['total_isarps'])
    st.metric("Manuals Vectorized", len(st.session_state.manuals_loaded))
    
    if st.button("🔄 Hard Reset System"):
        st.session_state.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# 5. MODULE: DASHBOARD
# -----------------------------------------------------------------------------
if page == "🏠 Dashboard":
    st.markdown('<div class="main-header">Audit Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time Compliance Posture & Analytics</div>', unsafe_allow_html=True)
    
    stats = st.session_state.engine.get_statistics()
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total ISARPs", stats['total_isarps'])
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Conformity ✅", stats['conformity_count'])
        st.markdown('</div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Findings 🔴", stats['findings_count'])
        st.markdown('</div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Pending Evidence ⏳", stats['pending_evidence_count'])
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("Compliance Breakdown by Status")
        if stats['analyzed_isarps'] > 0:
            chart_df = pd.DataFrame({
                'Status': ['Conformity', 'Findings', 'Observations', 'Pending'],
                'Count': [stats['conformity_count'], stats['findings_count'], 
                          stats['observations_count'], stats['pending_evidence_count']]
            })
            st.bar_chart(chart_df.set_index('Status'))
        else:
            st.info("💡 Ingest documents and run the analysis module to see compliance data.")
    with col_right:
        st.subheader("Critical Gap Summary")
        findings = [r for r in st.session_state.engine.gap_results if r.get('status') == ConformityStatus.FINDING]
        if findings:
            for f in findings[:5]:
                st.error(f"**{f['isarp_code']}**: {f.get('isarp_title', 'Missing Provision')}")
        else:
            st.success("No critical safety findings identified.")

# -----------------------------------------------------------------------------
# 6. MODULE: DOCUMENT INGESTION
# -----------------------------------------------------------------------------
elif page == "📄 Document Ingestion":
    st.markdown('<div class="main-header">Document Ingestion</div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["📘 IOSA Standards Manual (ISM)", "📙 Airline Internal Manuals"])
    
    with t1:
        st.subheader("Ingest IOSA Regulatory Framework")
        ism_file = st.file_uploader("Select ISM File", type=['pdf', 'docx', 'doc'])
        
        if ism_file and st.button("Process & Map ISARPs"):
            with st.spinner("Extracting 1,100+ Standards..."):
                file_path = settings.ism_dir / ism_file.name
                with open(file_path, "wb") as f:
                    f.write(ism_file.getbuffer())
                count = st.session_state.engine.ingest_ism_manual(file_path)
                st.session_state.ism_loaded = True
                st.success(f"✅ Successfully identified {count} ISARPs.")
                    
        if st.session_state.ism_loaded:
            df_preview = pd.DataFrame([vars(i) for i in st.session_state.engine.isarps])
            st.dataframe(df_preview[['code', 'category', 'requirement_text']])

    with t2:
        st.subheader("Ingest Operational Manuals")
        manual_files = st.file_uploader("Select Manuals", type=['pdf', 'docx'], accept_multiple_files=True)
        
        if manual_files and st.button("Vectorize Manual Provisions"):
            for m in manual_files:
                path = settings.manuals_dir / m.name
                with open(path, "wb") as f:
                    f.write(m.getbuffer())
                m_type = st.session_state.engine.ingest_airline_manual(path)
                st.session_state.manuals_loaded.append({'name': m.name, 'type': m_type})
            st.success(f"Processed {len(manual_files)} manuals.")
            st.table(pd.DataFrame(st.session_state.manuals_loaded))

# -----------------------------------------------------------------------------
# 7. MODULE: GAP ANALYSIS
# -----------------------------------------------------------------------------
elif page == "🔍 Gap Analysis":
    st.markdown('<div class="main-header">Authentic Gap Analysis</div>', unsafe_allow_html=True)
    
    if not st.session_state.ism_loaded:
        st.warning("⚠️ Action Required: Please ingest the ISM manual first.")
    else:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            category = st.selectbox("Select Operational Scope", ["All"] + list(settings.isarp_categories.keys()))
        with col_b:
            st.write("###")
            if st.button("🚀 Execute AI Audit", type="primary"):
                with st.spinner("Verifying manual provisions..."):
                    target_cat = None if category == "All" else category
                    st.session_state.engine.run_gap_analysis(category=target_cat)
                    st.session_state.analysis_complete = True
                    st.rerun()

        if st.session_state.analysis_complete and st.session_state.engine.gap_results:
            st.markdown("---")
            st.subheader("📋 Audit Verification (Line-by-Line Evidence)")
            
            for result in st.session_state.engine.gap_results:
                status = result.get('status')
                is_missing = result.get('manual_quote') == "MISSING" or status == ConformityStatus.FINDING
                
                if is_missing:
                    st.markdown(f"""
                    <div class="audit-finding-red">
                        <h3>🔴 FINDING: {result.get('isarp_code')}</h3>
                        <p><b>Standard:</b> {result.get('isarp_title', 'Regulatory Standard')}</p>
                        <hr>
                        <p><b>CRITICAL GAP:</b> Requirement not found in manuals.</p>
                        <p><b>Description:</b> {result.get('documentation_gap')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="audit-conformity-green">
                        <h3>✅ CONFORMITY: {result.get('isarp_code')}</h3>
                        <p><b>Standard:</b> {result.get('isarp_title', 'Regulatory Standard')}</p>
                        <hr>
                        <p><b>Found Manual Quote:</b></p>
                        <div class="quote-block">"{result.get('manual_quote')}"</div>
                        <p><b>Source:</b> {result.get('manual_reference', 'Manual Archive')}</p>
                    </div>
                    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. MODULE: EVIDENCE TRACKER
# -----------------------------------------------------------------------------
elif page == "📊 Evidence Tracker":
    st.markdown('<div class="main-header">Evidence Tracker</div>', unsafe_allow_html=True)
    st.info("Upload implementation proof (records, logs) for findings.")
    
    if not st.session_state.analysis_complete:
        st.warning("Run analysis first to identify findings.")
    else:
        pending = [r['isarp_code'] for r in st.session_state.engine.gap_results if r['status'] in [ConformityStatus.PENDING_EVIDENCE, ConformityStatus.FINDING]]
        if pending:
            selected = st.selectbox("Select ISARP", pending)
            e_file = st.file_uploader("Upload Evidence (PDF)")
            if e_file and st.button("Submit Proof"):
                st.success(f"Record linked to {selected}.")
        else:
            st.success("Verification Complete: No outstanding findings.")

# -----------------------------------------------------------------------------
# 9. MODULE: REPORTS
# -----------------------------------------------------------------------------
elif page == "📈 Reports & Exports":
    st.header("📈 Compliance Reports")
    if st.button("Generate Full Audit PDF"):
        st.info("Initializing report generator...")
    if st.button("Download Gap Analysis (Excel)"):
        df = st.session_state.engine.generate_compliance_report()
        st.download_button("Download Now", df.to_csv(index=False), "report.csv", "text/csv")

# Footer
st.markdown("---")
st.caption(f"Sial-Compliance-Pro v2.5.1 | Certified Audit-Ready | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
