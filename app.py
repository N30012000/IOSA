"""
Sial-Compliance-Pro - Standalone Aviation Compliance Analysis Tool
A simplified, self-contained version for IOSA/EASA Gap Analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import os
import tempfile
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Application configuration"""
    # Directories
    BASE_DIR = Path(tempfile.gettempdir()) / "sial_compliance"
    ISM_DIR = BASE_DIR / "ism"
    MANUALS_DIR = BASE_DIR / "manuals"
    EVIDENCE_DIR = BASE_DIR / "evidence"
    OUTPUTS_DIR = BASE_DIR / "outputs"
    
    # ISARP Categories
    ISARP_CATEGORIES = {
        "ORG": "Organization and Management",
        "FLT": "Flight Operations",
        "OPS": "Operational Control",
        "MNT": "Maintenance",
        "GRH": "Ground Handling",
        "CGO": "Cargo",
        "SEC": "Security",
        "DSP": "Dangerous Goods"
    }
    
    # Status Types
    CONFORMITY = "Conformity"
    FINDING = "Finding"
    OBSERVATION = "Observation"
    PENDING_EVIDENCE = "Pending Evidence"
    NOT_ASSESSED = "Not Assessed"
    
    # Evidence Types
    EVIDENCE_TYPES = [
        "Policy Document",
        "Standard Operating Procedure",
        "Training Record",
        "Maintenance Log",
        "Flight Record",
        "Audit Report",
        "Meeting Minutes",
        "Resource Allocation Document"
    ]
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories"""
        for directory in [cls.ISM_DIR, cls.MANUALS_DIR, cls.EVIDENCE_DIR, cls.OUTPUTS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

# Initialize directories
Config.setup_directories()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Sial-Compliance-Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4788;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4788;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize all session state variables"""
    if 'ism_files' not in st.session_state:
        st.session_state.ism_files = []
    if 'manual_files' not in st.session_state:
        st.session_state.manual_files = []
    if 'evidence_files' not in st.session_state:
        st.session_state.evidence_files = {}
    if 'isarps' not in st.session_state:
        st.session_state.isarps = []
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = []

initialize_session_state()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def save_uploaded_file(uploaded_file, directory):
    """Save an uploaded file to the specified directory"""
    try:
        file_path = directory / uploaded_file.name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.read())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def extract_text_from_pdf(file_path):
    """Extract text from PDF using PyMuPDF"""
    try:
        import fitz
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        st.error("PyMuPDF not installed. Run: pip install PyMuPDF")
        return ""
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def parse_isarps_from_text(text, filename):
    """Simple ISARP parser using regex"""
    import re
    isarps = []
    
    pattern = r'\b([A-Z]{3})\s+(\d+\.\d+\.\d+)\b'
    matches = re.finditer(pattern, text)
    
    for match in matches:
        category = match.group(1)
        number = match.group(2)
        code = f"{category} {number}"
        
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 500)
        context = text[start:end].strip()
        
        isarps.append({
            'code': code,
            'category': category,
            'number': number,
            'requirement': context,
            'source': filename,
            'status': Config.NOT_ASSESSED
        })
    
    return isarps

def get_statistics():
    """Calculate current statistics"""
    total = len(st.session_state.isarps)
    analyzed = len(st.session_state.analysis_results)
    
    conformity = sum(1 for r in st.session_state.analysis_results if r['status'] == Config.CONFORMITY)
    findings = sum(1 for r in st.session_state.analysis_results if r['status'] == Config.FINDING)
    observations = sum(1 for r in st.session_state.analysis_results if r['status'] == Config.OBSERVATION)
    pending = sum(1 for r in st.session_state.analysis_results if r['status'] == Config.PENDING_EVIDENCE)
    
    return {
        'total_isarps': total,
        'analyzed_isarps': analyzed,
        'conformity_count': conformity,
        'findings_count': findings,
        'observations_count': observations,
        'pending_evidence_count': pending
    }

def simulate_gap_analysis(isarp_code):
    """Simulate gap analysis"""
    import random
    
    statuses = [Config.CONFORMITY, Config.FINDING, Config.OBSERVATION, Config.PENDING_EVIDENCE]
    
    result = {
        'isarp_code': isarp_code,
        'status': random.choice(statuses),
        'confidence': random.uniform(0.6, 0.95),
        'documentation_gap': f"Simulated gap analysis for {isarp_code}",
        'implementation_gap': "Evidence of implementation required",
        'manual_references': ["Manual Page 45", "Section 2.3"],
        'evidence_required': ["Training Records", "Audit Reports"],
        'recommended_actions': [
            "Update policy documentation",
            "Provide implementation evidence"
        ]
    }
    
    return result

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    st.markdown('<div class="main-header">✈️ Sial-Compliance-Pro</div>', unsafe_allow_html=True)
    st.markdown("**IOSA/EASA Regulatory Gap Analysis System**")
    st.markdown("---")
    
    with st.sidebar:
        st.markdown("### 🛩️ Sial Aviation")
        st.markdown("### Navigation")
        
        page = st.radio(
            "Select Module",
            ["🏠 Dashboard", 
             "📄 Document Ingestion", 
             "🔍 Gap Analysis", 
             "📊 Evidence Management",
             "📈 Reports"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### System Status")
        stats = get_statistics()
        st.metric("ISARPs Loaded", stats['total_isarps'])
        st.metric("Manuals Loaded", len(st.session_state.manual_files))
        st.metric("Analyses Complete", stats['analyzed_isarps'])
    
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📄 Document Ingestion":
        show_document_ingestion()
    elif page == "🔍 Gap Analysis":
        show_gap_analysis()
    elif page == "📊 Evidence Management":
        show_evidence_management()
    elif page == "📈 Reports":
        show_reports()

def show_dashboard():
    st.header("📊 System Dashboard")
    stats = get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total ISARPs", stats['total_isarps'])
    with col2:
        st.metric("Analyzed", stats['analyzed_isarps'])
    with col3:
        st.metric("Conformity", stats['conformity_count'])
    with col4:
        st.metric("Findings", stats['findings_count'])
    
    if stats['analyzed_isarps'] > 0:
        st.subheader("Compliance Status")
        
        df = pd.DataFrame({
            'Status': ['Conformity', 'Findings', 'Observations', 'Pending'],
            'Count': [
                stats['conformity_count'],
                stats['findings_count'],
                stats['observations_count'],
                stats['pending_evidence_count']
            ]
        })
        
        st.bar_chart(df.set_index('Status'))
    else:
        st.info("Upload documents and run analysis to see results")

def show_document_ingestion():
    st.header("📄 Document Ingestion")
    
    # Updated to include Word documents
    supported_types = ['pdf', 'docx', 'doc']
    
    tab1, tab2 = st.tabs(["IOSA Standards Manual", "Airline Manuals"])
    
    with tab1:
        st.subheader("Upload IOSA Standards Manual (ISM)")
        
        ism_file = st.file_uploader("Select ISM PDF", type=['pdf'], key="ism")
        
        if ism_file and st.button("Process ISM"):
            with st.spinner("Extracting ISARPs..."):
                file_path = save_uploaded_file(ism_file, Config.ISM_DIR)
                
                if file_path:
                    text = extract_text_from_pdf(file_path)
                    
                    if text:
                        isarps = parse_isarps_from_text(text, ism_file.name)
                        st.session_state.isarps = isarps
                        st.session_state.ism_files.append(ism_file.name)
                        
                        st.success(f"✅ Loaded {len(isarps)} ISARPs")
                        
                        if isarps:
                            df = pd.DataFrame(isarps)
                            st.dataframe(df[['code', 'category']])
    
    with tab2:
        st.subheader("Upload Airline Manuals")
        
        manual_files = st.file_uploader(
            "Select Manual PDFs",
            type=['pdf'],
            accept_multiple_files=True,
            key="manuals"
        )
        
        if manual_files and st.button("Process Manuals"):
            with st.spinner("Processing manuals..."):
                for manual_file in manual_files:
                    file_path = save_uploaded_file(manual_file, Config.MANUALS_DIR)
                    
                    if file_path:
                        text = extract_text_from_pdf(file_path)
                        
                        if text:
                            st.session_state.manual_files.append({
                                'filename': manual_file.name,
                                'text': text[:5000],
                                'date': datetime.now().isoformat()
                            })
                            st.success(f"✅ {manual_file.name}")
        
        if st.session_state.manual_files:
            st.markdown("### Loaded Manuals")
            df = pd.DataFrame([{'Filename': m['filename']} for m in st.session_state.manual_files])
            st.dataframe(df)

def show_gap_analysis():
    st.header("🔍 Gap Analysis")
    
    if not st.session_state.isarps:
        st.warning("⚠️ Upload ISM first")
        return
    
    if not st.session_state.manual_files:
        st.warning("⚠️ Upload manuals first")
        return
    
    analysis_mode = st.selectbox(
        "Analysis Scope",
        ["Sample (5 ISARPs)", "By Category", "All ISARPs"]
    )
    
    if analysis_mode == "By Category":
        category = st.selectbox("Category", list(Config.ISARP_CATEGORIES.keys()))
    
    if st.button("🚀 Run Analysis", type="primary"):
        with st.spinner("Analyzing..."):
            if analysis_mode == "Sample (5 ISARPs)":
                isarps = st.session_state.isarps[:5]
            elif analysis_mode == "By Category":
                isarps = [i for i in st.session_state.isarps if i['category'] == category]
            else:
                isarps = st.session_state.isarps
            
            results = []
            progress = st.progress(0)
            
            for idx, isarp in enumerate(isarps):
                result = simulate_gap_analysis(isarp['code'])
                results.append(result)
                progress.progress((idx + 1) / len(isarps))
            
            st.session_state.analysis_results = results
            st.success(f"✅ Analyzed {len(results)} ISARPs")
    
    if st.session_state.analysis_results:
        st.subheader("Results")
        
        df = pd.DataFrame([
            {
                'ISARP': r['isarp_code'],
                'Status': r['status'],
                'Confidence': f"{r['confidence']*100:.0f}%"
            }
            for r in st.session_state.analysis_results
        ])
        
        st.dataframe(df, use_container_width=True)

def show_evidence_management():
    st.header("📊 Evidence Management")
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Run analysis first")
        return
    
    pending = [r for r in st.session_state.analysis_results 
               if r['status'] in [Config.PENDING_EVIDENCE, Config.OBSERVATION]]
    
    if not pending:
        st.success("✅ No ISARPs pending evidence")
        return
    
    selected_isarp = st.selectbox("Select ISARP", [r['isarp_code'] for r in pending])
    evidence_type = st.selectbox("Evidence Type", Config.EVIDENCE_TYPES)
    evidence_file = st.file_uploader("Upload Evidence PDF", type=['pdf'])
    
    if evidence_file and st.button("Submit Evidence"):
        file_path = save_uploaded_file(evidence_file, Config.EVIDENCE_DIR)
        
        if file_path:
            if selected_isarp not in st.session_state.evidence_files:
                st.session_state.evidence_files[selected_isarp] = []
            
            st.session_state.evidence_files[selected_isarp].append({
                'filename': evidence_file.name,
                'type': evidence_type,
                'date': datetime.now().isoformat()
            })
            
            st.success(f"✅ Evidence uploaded for {selected_isarp}")
    
    if st.session_state.evidence_files:
        st.subheader("Evidence Registry")
        for isarp, files in st.session_state.evidence_files.items():
            with st.expander(f"{isarp} ({len(files)} files)"):
                for f in files:
                    st.write(f"📄 {f['filename']} - {f['type']}")

def show_reports():
    st.header("📈 Reports & Export")
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Run analysis first")
        return
    
    st.subheader("Executive Summary")
    stats = get_statistics()
    
    st.markdown(f"""
### IOSA Gap Analysis Summary

**Date:** {datetime.now().strftime('%Y-%m-%d')}

**Total ISARPs:** {stats['analyzed_isarps']}

**Status:**
- ✅ Conformity: {stats['conformity_count']}
- 🔴 Findings: {stats['findings_count']}
- ⚠️ Observations: {stats['observations_count']}
- ⏳ Pending Evidence: {stats['pending_evidence_count']}
""")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Download Excel"):
            df = pd.DataFrame(st.session_state.analysis_results)
            path = Config.OUTPUTS_DIR / f"report_{datetime.now().strftime('%Y%m%d')}.xlsx"
            df.to_excel(path, index=False, engine='openpyxl')
            
            with open(path, 'rb') as f:
                st.download_button("⬇️ Excel Report", f, file_name=path.name)
    
    with col2:
        if st.button("Download JSON"):
            data = {
                'date': datetime.now().isoformat(),
                'statistics': stats,
                'results': st.session_state.analysis_results
            }
            
            json_str = json.dumps(data, indent=2)
            st.download_button("⬇️ JSON Export", json_str, file_name="report.json")

if __name__ == "__main__":
    main()
