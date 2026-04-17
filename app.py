"""
Sial-Compliance-Pro - Professional IOSA/EASA Gap Analysis System
Enterprise-grade Aviation Regulatory Compliance Tool with AI-Powered Analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import tempfile
import json
import re
import io
from typing import List, Dict, Optional
import time

# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class Config:
    """Application configuration and constants"""
    
    # Directories
    BASE_DIR = Path(tempfile.gettempdir()) / "sial_compliance_pro"
    ISM_DIR = BASE_DIR / "ism"
    MANUALS_DIR = BASE_DIR / "manuals"
    EVIDENCE_DIR = BASE_DIR / "evidence"
    OUTPUTS_DIR = BASE_DIR / "outputs"
    
    # ISARP Categories (Official IOSA Standards)
    ISARP_CATEGORIES = {
        "ORG": "Organization and Management System",
        "FLT": "Flight Operations",
        "OPS": "Operational Control and Flight Dispatch",
        "MNT": "Aircraft Maintenance and Continuing Airworthiness",
        "GRH": "Ground Handling",
        "CGO": "Cargo Operations",
        "SEC": "Security Management",
        "DSP": "Dangerous Goods and Special Loads"
    }
    
    # Conformity Status (IOSA Standard Classifications)
    STATUS_CONFORMITY = "Conformity"
    STATUS_FINDING = "Finding"
    STATUS_OBSERVATION = "Observation"
    STATUS_PENDING_EVIDENCE = "Pending Evidence"
    STATUS_NOT_ASSESSED = "Not Assessed"
    
    # Evidence Types (IPM 6.7.1 Requirements)
    EVIDENCE_TYPES = [
        "Policy Document",
        "Standard Operating Procedure (SOP)",
        "Training Records",
        "Maintenance Logs",
        "Flight Records",
        "Audit Reports",
        "Safety Reports",
        "Meeting Minutes",
        "Resource Allocation Documentation",
        "Competency Assessment Records",
        "Quality Control Records"
    ]
    
    # Mandatory Keywords (for requirement identification)
    MANDATORY_KEYWORDS = ["shall", "must", "required", "mandatory", "ensure"]
    
    @classmethod
    def setup(cls):
        """Initialize application directories"""
        for directory in [cls.ISM_DIR, cls.MANUALS_DIR, cls.EVIDENCE_DIR, cls.OUTPUTS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

Config.setup()

# ============================================================================
# AI ANALYSIS ENGINE (Google Gemini Integration)
# ============================================================================

class GeminiAnalyzer:
    """Google Gemini AI integration for gap analysis"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.model_name = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Gemini API client"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            # Try these models in order
            model_names = [
                'gemini-2.0-flash-exp',
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-pro'
            ]
            
            for model_name in model_names:
                try:
                    self.client = genai.GenerativeModel(model_name)
                    self.model_name = model_name
                    st.success(f"✅ Connected to {model_name}")
                    return
                except Exception:
                    continue
            
            st.error("❌ Could not connect to any Gemini model")
            self.client = None
            
        except Exception as e:
            st.error(f"❌ Error initializing Gemini: {e}")
            self.client = None
    
    def analyze_gap(self, isarp_code: str, isarp_text: str, manual_texts: List[str]) -> Dict:
        """Perform comprehensive gap analysis using Gemini AI"""
        if not self.client:
            return self._fallback_analysis(isarp_code)
        
        combined_manuals = "\n\n---\n\n".join(manual_texts[:3])
        
        prompt = f"""You are an expert IOSA auditor. Analyze this requirement:

ISARP: {isarp_code}
Requirement: {isarp_text}

Documentation: {combined_manuals[:3000]}

Return ONLY valid JSON with this structure:
{{"status": "Conformity|Finding|Observation|Pending Evidence", "confidence": 0.0-1.0, "documentation_gap": "text", "implementation_gap": "text", "manual_references": [], "evidence_required": [], "recommended_actions": [], "assessment_reasoning": "text"}}"""
        
        try:
            response = self.client.generate_content(prompt)
            result = self._parse_gemini_response(response.text, isarp_code)
            return result
        except Exception as e:
            st.error(f"⚠️ AI Analysis Error for {isarp_code}: {e}")
            return self._fallback_analysis(isarp_code)
    
    def _parse_gemini_response(self, response_text: str, isarp_code: str) -> Dict:
        """Parse Gemini's JSON response"""
        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                result = json.loads(json_text)
                result['isarp_code'] = isarp_code
                result['analysis_date'] = datetime.now().isoformat()
                result['ai_powered'] = True
                return result
        except Exception as e:
            st.warning(f"⚠️ Parse error for {isarp_code}: {e}")
        
        return self._fallback_analysis(isarp_code)
    
    def _fallback_analysis(self, isarp_code: str) -> Dict:
        """Fallback when AI unavailable"""
        return {
            'isarp_code': isarp_code,
            'status': Config.STATUS_NOT_ASSESSED,
            'confidence': 0.0,
            'documentation_gap': 'AI analysis unavailable - manual review required',
            'implementation_gap': 'Requires manual assessment',
            'manual_references': [],
            'evidence_required': ['Manual Review Required'],
            'recommended_actions': ['Conduct manual compliance review'],
            'assessment_reasoning': 'Automated analysis unavailable',
            'ai_powered': False
        }
    
    def check_ipm_1_1_1(self, manual_texts: List[str]) -> Dict:
        """IPM Section 1.1.1 compliance check"""
        if not self.client:
            return {'error': 'AI unavailable'}
        
        combined = "\n\n".join(manual_texts)
        
        prompt = f"""Analyze this documentation for IOSA IPM 1.1.1 compliance.

Documentation: {combined[:5000]}

Return JSON:
{{"has_documented_policy": true/false, "has_resource_provision": true/false, "policy_clarity": "HIGH/MEDIUM/LOW", "resource_specificity": "HIGH/MEDIUM/LOW", "policy_excerpts": [], "resource_excerpts": [], "gaps": [], "recommendations": [], "compliant": true/false}}"""
        
        try:
            response = self.client.generate_content(prompt)
            cleaned = response.text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            elif cleaned.startswith('```'):
                cleaned = cleaned[3:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            st.error(f"IPM 1.1.1 Analysis Error: {e}")
        
        return {'error': 'Analysis failed'}

# ============================================================================
# PDF PROCESSING ENGINE
# ============================================================================

class PDFProcessor:
    """Advanced PDF text extraction and ISARP parsing"""
    
    @staticmethod
    def extract_text(file_path: Path) -> str:
        """Extract text from PDF with error handling"""
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            st.error(f"PDF extraction error: {e}")
            return ""
    
    @staticmethod
    def parse_isarps(text: str, filename: str) -> List[Dict]:
        """Parse ISARPs from IOSA Standards Manual"""
        isarps = []
        pattern = r'\b([A-Z]{3})\s+(\d+\.\d+\.\d+)\b'
        matches = list(re.finditer(pattern, text))
        
        for i, match in enumerate(matches):
            category = match.group(1)
            number = match.group(2)
            code = f"{category} {number}"
            
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = start_pos + 800
            
            requirement_text = text[start_pos:end_pos].strip()
            lines = requirement_text.split('\n')
            title = lines[0].strip() if lines else "Untitled"
            
            is_mandatory = any(keyword in requirement_text.lower() 
                             for keyword in Config.MANDATORY_KEYWORDS)
            
            isarps.append({
                'code': code,
                'category': category,
                'number': number,
                'title': title,
                'requirement_text': requirement_text[:500],
                'is_mandatory': is_mandatory,
                'source_file': filename,
                'page_estimate': text[:match.start()].count('\f') + 1,
                'status': Config.STATUS_NOT_ASSESSED
            })
        
        return isarps
    
    @staticmethod
    def classify_manual(filename: str, text_sample: str) -> str:
        """Classify manual type based on filename and content"""
        filename_upper = filename.upper()
        
        classifications = {
            'FOM': ['FLIGHT OPERATIONS', 'FOM', 'FLIGHT OPS'],
            'COM': ['COMPANY OPERATIONS', 'COM'],
            'AMM': ['AIRCRAFT MAINTENANCE', 'AMM', 'MAINTENANCE'],
            'GMM': ['GROUND', 'GROUND HANDLING', 'RAMP'],
            'SMS': ['SAFETY MANAGEMENT', 'SMS'],
            'SECURITY': ['SECURITY'],
            'DGM': ['DANGEROUS GOODS', 'HAZMAT']
        }
        
        for manual_type, keywords in classifications.items():
            if any(kw in filename_upper for kw in keywords):
                return manual_type
        
        text_upper = text_sample[:2000].upper()
        for manual_type, keywords in classifications.items():
            if any(kw in text_upper for kw in keywords):
                return manual_type
        
        return 'GENERAL'

# ============================================================================
# SESSION STATE MANAGEMENT
# ============================================================================

def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'api_key': '',
        'api_configured': False,
        'ism_files': [],
        'manual_files': [],
        'evidence_files': {},
        'isarps': [],
        'analysis_results': [],
        'ipm_result': None,
        'analyzer': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ============================================================================
# STATISTICS & METRICS
# ============================================================================

def get_statistics() -> Dict:
    """Calculate comprehensive statistics"""
    total = len(st.session_state.isarps)
    analyzed = len(st.session_state.analysis_results)
    
    if analyzed == 0:
        return {
            'total_isarps': total,
            'analyzed_isarps': 0,
            'conformity_count': 0,
            'findings_count': 0,
            'observations_count': 0,
            'pending_evidence_count': 0,
            'conformity_rate': 0,
            'compliance_score': 0
        }
    
    statuses = [r['status'] for r in st.session_state.analysis_results]
    
    conformity = statuses.count(Config.STATUS_CONFORMITY)
    findings = statuses.count(Config.STATUS_FINDING)
    observations = statuses.count(Config.STATUS_OBSERVATION)
    pending = statuses.count(Config.STATUS_PENDING_EVIDENCE)
    
    compliance_score = ((conformity * 1.0 + pending * 0.7 + observations * 0.5) / analyzed) * 100
    
    return {
        'total_isarps': total,
        'analyzed_isarps': analyzed,
        'conformity_count': conformity,
        'findings_count': findings,
        'observations_count': observations,
        'pending_evidence_count': pending,
        'conformity_rate': (conformity / analyzed) * 100,
        'compliance_score': compliance_score
    }

# ============================================================================
# STREAMLIT UI CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Sial-Compliance-Pro | IOSA Gap Analysis",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main-header {
    font-size: 2.8rem;
    font-weight: 700;
    color: #1f4788;
    text-align: center;
    margin-bottom: 1rem;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}
.subtitle {
    text-align: center;
    color: #666;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}
.metric-card {
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 5px solid #1f4788;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.status-badge {
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
    display: inline-block;
}
.status-conformity { background: #d4edda; color: #155724; }
.status-finding { background: #f8d7da; color: #721c24; }
.status-observation { background: #fff3cd; color: #856404; }
.status-pending { background: #d1ecf1; color: #0c5460; }
.info-box {
    background: #e7f3ff;
    border-left: 4px solid #1f4788;
    padding: 1rem;
    border-radius: 5px;
    margin: 1rem 0;
}
.success-box {
    background: #d4edda;
    border-left: 4px solid #28a745;
    padding: 1rem;
    border-radius: 5px;
    margin: 1rem 0;
}
.warning-box {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 1rem;
    border-radius: 5px;
    margin: 1rem 0;
}
.ai-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 0.3rem 0.6rem;
    border-radius: 15px;
    font-size: 0.75rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# API SETUP PAGE
# ============================================================================

def show_api_setup():
    """API configuration page"""
    st.markdown("## 🔑 API Configuration")
    
    st.markdown("""
    <div class="info-box">
    <h4>Google Gemini API Required</h4>
    <p>This application uses Google's Gemini AI for gap analysis.</p>
    <p><strong>Getting your API key:</strong></p>
    <ol>
        <li>Visit <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a></li>
        <li>Click "Get API Key" or "Create API Key"</li>
        <li>Copy your API key</li>
        <li>Paste it below</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)
    
    api_key = st.text_input(
        "Enter your Google Gemini API Key",
        type="password",
        placeholder="AIza..."
    )
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("✅ Configure API", type="primary"):
            if api_key and len(api_key) > 20:
                try:
                    analyzer = GeminiAnalyzer(api_key)
                    if analyzer.client:
                        st.session_state.api_key = api_key
                        st.session_state.analyzer = analyzer
                        st.session_state.api_configured = True
                        st.success("✅ API configured successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to initialize API")
                except Exception as e:
                    st.error(f"❌ API Error: {e}")
            else:
                st.error("❌ Invalid API key format")

# ============================================================================
# DASHBOARD PAGE
# ============================================================================

def show_dashboard():
    """Main dashboard with analytics"""
    st.header("📊 Compliance Dashboard")
    
    stats = get_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total ISARPs", stats['total_isarps'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Analyzed", stats['analyzed_isarps'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Conformity", stats['conformity_count'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Compliance Score", f"{stats['compliance_score']:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    if stats['analyzed_isarps'] > 0:
        st.subheader("Recent Analysis Results")
        recent = st.session_state.analysis_results[-10:]
        for result in reversed(recent):
            with st.expander(f"{result['isarp_code']} - {result.get('title', 'N/A')[:50]}..."):
                st.markdown(f"**Status:** {result['status']}")
                st.markdown(f"**Gap:** {result['documentation_gap']}")
    else:
        st.info("📤 Upload IOSA Standards Manual and airline manuals to begin analysis")

# ============================================================================
# DOCUMENT MANAGEMENT PAGE
# ============================================================================

def show_documents():
    """Document upload and management"""
    st.header("📄 Document Management")
    
    tab1, tab2 = st.tabs(["📘 IOSA Standards Manual (ISM)", "📚 Airline Manuals"])
    
    with tab1:
        st.subheader("Upload IOSA Standards Manual")
        ism_file = st.file_uploader("Select ISM PDF", type=['pdf'], key="ism_upload")
        
        if ism_file:
            if st.button("🔄 Process ISM Document", type="primary"):
                with st.spinner("🔍 Extracting ISARP requirements..."):
                    file_path = Config.ISM_DIR / ism_file.name
                    with open(file_path, 'wb') as f:
                        f.write(ism_file.getvalue())
                    
                    text = PDFProcessor.extract_text(file_path)
                    if text:
                        isarps = PDFProcessor.parse_isarps(text, ism_file.name)
                        if isarps:
                            st.session_state.isarps = isarps
                            st.session_state.ism_files.append({
                                'filename': ism_file.name,
                                'upload_date': datetime.now().isoformat(),
                                'isarp_count': len(isarps)
                            })
                            st.success(f"✅ Extracted **{len(isarps)} ISARPs**")
    
    with tab2:
        st.subheader("Upload Airline Manuals")
        manual_files = st.file_uploader(
            "Select Manual PDFs",
            type=['pdf'],
            accept_multiple_files=True,
            key="manuals_upload"
        )
        
        if manual_files:
            if st.button("🔄 Process Manuals", type="primary"):
                for manual_file in manual_files:
                    file_path = Config.MANUALS_DIR / manual_file.name
                    with open(file_path, 'wb') as f:
                        f.write(manual_file.getvalue())
                    
                    text = PDFProcessor.extract_text(file_path)
                    if text:
                        manual_type = PDFProcessor.classify_manual(manual_file.name, text)
                        st.session_state.manual_files.append({
                            'filename': manual_file.name,
                            'type': manual_type,
                            'text': text,
                            'upload_date': datetime.now().isoformat(),
                            'char_count': len(text)
                        })
                st.success(f"✅ Processed **{len(manual_files)} manual(s)**")

# ============================================================================
# GAP ANALYSIS PAGE
# ============================================================================

def show_gap_analysis():
    """AI-powered gap analysis"""
    st.header("🔍 AI-Powered Gap Analysis")
    
    if not st.session_state.isarps:
        st.warning("⚠️ Please upload the IOSA Standards Manual first")
        return
    
    if not st.session_state.manual_files:
        st.warning("⚠️ Please upload airline manuals first")
        return
    
    analysis_mode = st.selectbox(
        "Analysis Scope",
        ["Quick Sample (5 ISARPs)", "By Category", "Full Analysis (All ISARPs)"]
    )
    
    category = None
    if analysis_mode == "By Category":
        category = st.selectbox(
            "Select ISARP Category",
            list(Config.ISARP_CATEGORIES.keys()),
            format_func=lambda x: f"{x} - {Config.ISARP_CATEGORIES[x]}"
        )
    
    if st.button("🚀 Run AI Gap Analysis", type="primary", use_container_width=True):
        if analysis_mode == "Quick Sample (5 ISARPs)":
            isarps_to_analyze = st.session_state.isarps[:5]
        elif analysis_mode == "By Category":
            isarps_to_analyze = [i for i in st.session_state.isarps if i['category'] == category]
        else:
            isarps_to_analyze = st.session_state.isarps
        
        manual_texts = [m['text'] for m in st.session_state.manual_files]
        total = len(isarps_to_analyze)
        
        progress_bar = st.progress(0)
        status_container = st.empty()
        results = []
        
        for idx, isarp in enumerate(isarps_to_analyze):
            status_container.info(f"🔍 Analyzing: **{isarp['code']}**...")
            
            result = st.session_state.analyzer.analyze_gap(
                isarp['code'],
                isarp['requirement_text'],
                manual_texts
            )
            
            result['title'] = isarp['title']
            result['category'] = isarp['category']
            results.append(result)
            progress_bar.progress((idx + 1) / total)
        
        st.session_state.analysis_results = results
        status_container.success(f"✅ **Analysis Complete!** Processed {total} ISARPs")
        
        stats = get_statistics()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ Conformity", stats['conformity_count'])
        col2.metric("🔴 Findings", stats['findings_count'])
        col3.metric("⚠️ Observations", stats['observations_count'])
        col4.metric("⏳ Pending Evidence", stats['pending_evidence_count'])

# ============================================================================
# IPM COMPLIANCE PAGE
# ============================================================================

def show_ipm_compliance():
    """IPM Section 1.1.1 Compliance Check"""
    st.header("📋 IPM Section 1.1.1 Compliance")
    
    if not st.session_state.manual_files:
        st.warning("⚠️ Please upload airline manuals first")
        return
    
    if st.button("🔍 Run IPM 1.1.1 Analysis", type="primary"):
        with st.spinner("🤖 AI analyzing..."):
            manual_texts = [m['text'] for m in st.session_state.manual_files]
            result = st.session_state.analyzer.check_ipm_1_1_1(manual_texts)
            st.session_state.ipm_result = result
            st.json(result)

# ============================================================================
# EVIDENCE REGISTRY PAGE
# ============================================================================

def show_evidence():
    """Evidence document management"""
    st.header("📎 Evidence Registry")
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Please run gap analysis first")
        return
    
    st.info("Evidence management module - upload proof of compliance")

# ============================================================================
# REPORTS & EXPORT PAGE
# ============================================================================

def show_reports():
    """Generate and export reports"""
    st.header("📈 Reports & Export")
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Please run gap analysis first")
        return
    
    if st.button("📊 Generate Excel Report"):
        stats = get_statistics()
        excel_data = []
        for result in st.session_state.analysis_results:
            excel_data.append({
                'ISARP Code': result['isarp_code'],
                'Status': result['status'],
                'Documentation Gap': result['documentation_gap'],
            })
        
        df = pd.DataFrame(excel_data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Gap Analysis', index=False)
        output.seek(0)
        
        st.download_button(
            label="⬇️ Download Excel Report",
            data=output,
            file_name=f"IOSA_Analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    init_session_state()
    
    st.markdown('<div class="main-header">✈️ Sial-Compliance-Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Professional IOSA/EASA Gap Analysis System</div>', unsafe_allow_html=True)
    
    if not st.session_state.api_configured:
        show_api_setup()
        return
    
    with st.sidebar:
        st.markdown("### 🛩️ Sial Aviation Solutions")
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["📊 Dashboard", "📄 Document Management", "🔍 Gap Analysis", 
             "📋 IPM Compliance", "📎 Evidence Registry", "📈 Reports & Export"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        stats = get_statistics()
        st.metric("ISARPs Loaded", stats['total_isarps'])
        st.metric("Analyses Complete", stats['analyzed_isarps'])
        
        if st.button("🔄 Reset API Key"):
            st.session_state.api_configured = False
            st.rerun()
    
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "📄 Document Management":
        show_documents()
    elif page == "🔍 Gap Analysis":
        show_gap_analysis()
    elif page == "📋 IPM Compliance":
        show_ipm_compliance()
    elif page == "📎 Evidence Registry":
        show_evidence()
    elif page == "📈 Reports & Export":
        show_reports()

if __name__ == "__main__":
    main()
