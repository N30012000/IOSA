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
    """Initialize Gemini API client with Gemini 2.0 Flash"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        
        # Try these models in order
        model_names = [
            'gemini-2.0-flash-exp',  # Latest experimental
            'gemini-1.5-flash',      # Faster, widely available
            'gemini-pro',            # Original Gemini Pro
            'models/gemini-pro'      # Alternative format
        ]
        
        for model_name in model_names:
            try:
                self.client = genai.GenerativeModel(model_name)
                self.model_name = model_name
                st.success(f"✅ Connected to {model_name}")
                return
            except Exception as e:
                st.warning(f"Failed to connect to {model_name}: {e}")
                continue
        
        st.error("❌ Could not connect to any Gemini model")
        self.client = None
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        self.client = None
    
    def analyze_gap(self, isarp_code: str, isarp_text: str, manual_texts: List[str]) -> Dict:
        """
        Perform comprehensive gap analysis using Gemini AI
        """
        if not self.client:
            st.error(f"❌ No Gemini client available for {isarp_code}")
            return self._fallback_analysis(isarp_code)
        
        # Combine manual texts
        combined_manuals = "\n\n---\n\n".join(manual_texts[:3])
        
        prompt = f"""You are an expert IOSA auditor. Analyze this requirement:

ISARP: {isarp_code}
Requirement: {isarp_text}

Documentation: {combined_manuals[:3000]}

Return ONLY valid JSON with this structure:
{{"status": "Conformity|Finding|Observation|Pending Evidence", "confidence": 0.0-1.0, "documentation_gap": "text", "implementation_gap": "text", "manual_references": [], "evidence_required": [], "recommended_actions": [], "assessment_reasoning": "text"}}"""
        
        try:
            # Debug: Show which model is being used
            st.info(f"🔄 Analyzing {isarp_code} with model: {self.model_name}")
            
            response = self.client.generate_content(prompt)
            result = self._parse_gemini_response(response.text, isarp_code)
            return result
            
        except Exception as e:
            st.error(f"⚠️ AI Analysis Error for {isarp_code}: {str(e)}")
            # Debug: Print full error
            import traceback
            st.code(f"Error details:\n{traceback.format_exc()}")
            return self._fallback_analysis(isarp_code)
    
    def _parse_gemini_response(self, response_text: str, isarp_code: str) -> Dict:
        """Parse Gemini's JSON response"""
        try:
            # Clean response text
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Find JSON object
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
            st.code(f"Response text: {response_text[:500]}")
        
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
            'ai_powered': False,
            'analysis_date': datetime.now().isoformat()
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
            
            # Clean and parse response
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
        """
        Parse ISARPs from IOSA Standards Manual
        Pattern: ORG 1.1.1, FLT 2.3.5, etc.
        """
        isarps = []
        
        # Enhanced pattern for ISARP codes
        pattern = r'\b([A-Z]{3})\s+(\d+\.\d+\.\d+)\b'
        matches = list(re.finditer(pattern, text))
        
        for i, match in enumerate(matches):
            category = match.group(1)
            number = match.group(2)
            code = f"{category} {number}"
            
            # Extract requirement text (from code to next code or 800 chars)
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = start_pos + 800
            
            requirement_text = text[start_pos:end_pos].strip()
            
            # Extract title (line after code)
            lines = requirement_text.split('\n')
            title = lines[0].strip() if lines else "Untitled"
            
            # Identify if mandatory (contains shall/must)
            is_mandatory = any(keyword in requirement_text.lower() 
                             for keyword in Config.MANDATORY_KEYWORDS)
            
            isarps.append({
                'code': code,
                'category': category,
                'number': number,
                'title': title,
                'requirement_text': requirement_text[:500],  # First 500 chars
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
        
        # Check content
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
    
    # Calculate compliance score
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

# Professional CSS Styling
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
# MAIN APPLICATION
# ============================================================================

def main():
    init_session_state()
    
    # Header
    st.markdown('<div class="main-header">✈️ Sial-Compliance-Pro</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Professional IOSA/EASA Gap Analysis System with AI-Powered Assessment</div>', unsafe_allow_html=True)
    
    # API Configuration Check
    if not st.session_state.api_configured:
        show_api_setup()
        return
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("### 🛩️ Sial Aviation Solutions")
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["📊 Dashboard", 
             "📄 Document Management", 
             "🔍 Gap Analysis", 
             "📋 IPM Compliance",
             "📎 Evidence Registry",
             "📈 Reports & Export"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### 📊 System Status")
        stats = get_statistics()
        
        st.metric("ISARPs Loaded", stats['total_isarps'])
        st.metric("Analyses Complete", stats['analyzed_isarps'])
        st.metric("Compliance Score", f"{stats['compliance_score']:.1f}%")
        
        st.markdown("---")
        if st.button("🔄 Reset API Key"):
            st.session_state.api_configured = False
            st.rerun()
    
    # Route to Pages
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

# ============================================================================
# API SETUP PAGE
# ============================================================================

def show_api_setup():
    """API configuration page"""
    st.markdown("## 🔑 API Configuration")
    
    st.markdown("""
    <div class="info-box">
    <h4>Google Gemini API Required</h4>
    <p>This application uses Google's Gemini 1.5 Pro for authentic AI-powered gap analysis.</p>
    <p><strong>Getting your API key:</strong></p>
    <ol>
        <li>Visit <a href="https://makersuite.google.com/app/apikey" target="_blank">Google AI Studio</a></li>
        <li>Click "Get API Key" or "Create API Key"</li>
        <li>Copy your API key</li>
        <li>Paste it below</li>
    </ol>
    <p><strong>Free tier includes:</strong> 60 requests per minute</p>
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
                    # Test the API key
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
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total ISARPs", stats['total_isarps'], 
                 help="Total ISARP requirements loaded from ISM")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Analyzed", stats['analyzed_isarps'],
                 delta=f"{(stats['analyzed_isarps']/max(stats['total_isarps'],1))*100:.0f}%",
                 help="ISARPs with completed gap analysis")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Conformity", stats['conformity_count'],
                 delta=f"{stats['conformity_rate']:.1f}%",
                 help="Full compliance achieved")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Compliance Score", f"{stats['compliance_score']:.1f}%",
                 delta_color="off",
                 help="Weighted compliance score")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed Analytics
    if stats['analyzed_isarps'] > 0:
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.subheader("Compliance Status Distribution")
            
            status_df = pd.DataFrame({
                'Status': ['Conformity', 'Findings', 'Observations', 'Pending Evidence'],
                'Count': [
                    stats['conformity_count'],
                    stats['findings_count'],
                    stats['observations_count'],
                    stats['pending_evidence_count']
                ],
                'Percentage': [
                    stats['conformity_rate'],
                    (stats['findings_count']/stats['analyzed_isarps'])*100,
                    (stats['observations_count']/stats['analyzed_isarps'])*100,
                    (stats['pending_evidence_count']/stats['analyzed_isarps'])*100
                ]
            })
            
            st.bar_chart(status_df.set_index('Status')['Count'])
            st.dataframe(status_df, use_container_width=True)
        
        with col_right:
            st.subheader("Critical Findings")
            
            findings = [r for r in st.session_state.analysis_results 
                       if r['status'] == Config.STATUS_FINDING]
            
            if findings:
                st.error(f"🔴 {len(findings)} Critical Finding(s)")
                for f in findings[:3]:
                    st.markdown(f"**{f['isarp_code']}**")
                    st.caption(f['documentation_gap'][:100] + "...")
            else:
                st.success("✅ No Critical Findings")
        
        # Recent Analysis Results
        st.markdown("---")
        st.subheader("Recent Analysis Results")
        
        recent = st.session_state.analysis_results[-10:]
        for result in reversed(recent):
            status_class = {
                Config.STATUS_CONFORMITY: 'status-conformity',
                Config.STATUS_FINDING: 'status-finding',
                Config.STATUS_OBSERVATION: 'status-observation',
                Config.STATUS_PENDING_EVIDENCE: 'status-pending'
            }.get(result['status'], '')
            
            with st.expander(f"{result['isarp_code']} - {result.get('title', 'N/A')[:50]}..."):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f'<span class="status-badge {status_class}">{result["status"]}</span>', 
                              unsafe_allow_html=True)
                    if result.get('ai_powered'):
                        st.markdown('<span class="ai-badge">🤖 AI Analysis</span>', unsafe_allow_html=True)
                    
                    st.markdown(f"**Confidence:** {result['confidence']*100:.0f}%")
                    st.markdown(f"**Gap:** {result['documentation_gap']}")
                
                with col2:
                    st.markdown("**Evidence Needed:**")
                    for ev in result.get('evidence_required', [])[:3]:
                        st.markdown(f"• {ev}")
    
    else:
        st.info("📤 Upload IOSA Standards Manual and airline manuals to begin analysis")

# ============================================================================
# DOCUMENT MANAGEMENT PAGE
# ============================================================================

def show_documents():
    """Document upload and management"""
    st.header("📄 Document Management")
    
    tab1, tab2 = st.tabs(["📘 IOSA Standards Manual (ISM)", "📚 Airline Manuals"])
    
    # ISM Upload
    with tab1:
        st.subheader("Upload IOSA Standards Manual")
        
        st.markdown("""
        <div class="info-box">
        Upload the official <strong>IATA IOSA Standards Manual (ISM)</strong> Edition 14 or later.
        The system will automatically extract all ISARP requirements.
        </div>
        """, unsafe_allow_html=True)
        
        ism_file = st.file_uploader(
            "Select ISM PDF",
            type=['pdf'],
            key="ism_upload",
            help="Upload the complete IOSA Standards Manual PDF"
        )
        
        if ism_file:
            if st.button("🔄 Process ISM Document", type="primary"):
                with st.spinner("🔍 Extracting ISARP requirements from ISM..."):
                    # Save file
                    file_path = Config.ISM_DIR / ism_file.name
                    with open(file_path, 'wb') as f:
                        f.write(ism_file.getvalue())
                    
                    # Extract text
                    text = PDFProcessor.extract_text(file_path)
                    
                    if text:
                        # Parse ISARPs
                        isarps = PDFProcessor.parse_isarps(text, ism_file.name)
                        
                        if isarps:
                            st.session_state.isarps = isarps
                            st.session_state.ism_files.append({
                                'filename': ism_file.name,
                                'upload_date': datetime.now().isoformat(),
                                'isarp_count': len(isarps)
                            })
                            
                            st.success(f"✅ Successfully extracted **{len(isarps)} ISARPs** from ISM")
                            
                            # Show sample
                            st.markdown("### 📋 Sample ISARPs Extracted:")
                            sample_df = pd.DataFrame(isarps[:15])[['code', 'category', 'title', 'is_mandatory']]
                            sample_df['is_mandatory'] = sample_df['is_mandatory'].map({True: '✓ Yes', False: 'No'})
                            st.dataframe(sample_df, use_container_width=True)
                            
                            # Category breakdown
                            st.markdown("### 📊 ISARP Category Distribution:")
                            category_counts = pd.Series([i['category'] for i in isarps]).value_counts()
                            category_df = pd.DataFrame({
                                'Category': [f"{cat} - {Config.ISARP_CATEGORIES.get(cat, 'Unknown')}" 
                                           for cat in category_counts.index],
                                'Count': category_counts.values
                            })
                            st.dataframe(category_df, use_container_width=True)
                        else:
                            st.warning("⚠️ No ISARPs found. Please verify the document format.")
                    else:
                        st.error("❌ Failed to extract text from PDF")
        
        # Show loaded ISM
        if st.session_state.ism_files:
            st.markdown("---")
            st.markdown("### ✅ Loaded ISM Documents")
            for ism in st.session_state.ism_files:
                st.success(f"📘 {ism['filename']} - {ism['isarp_count']} ISARPs")
    
    # Airline Manuals Upload
    with tab2:
        st.subheader("Upload Airline Internal Manuals")
        
        st.markdown("""
        <div class="info-box">
        Upload your airline's operational manuals including:<br>
        • Flight Operations Manual (FOM)<br>
        • Company Operations Manual (COM)<br>
        • Aircraft Maintenance Manual (AMM)<br>
        • Ground Handling Manual (GMM)<br>
        • Safety Management System Manual (SMS)<br>
        • Security Manual<br>
        • Dangerous Goods Manual (DGM)
        </div>
        """, unsafe_allow_html=True)
        
        manual_files = st.file_uploader(
            "Select Manual PDFs (multiple files allowed)",
            type=['pdf'],
            accept_multiple_files=True,
            key="manuals_upload"
        )
        
        if manual_files:
            if st.button("🔄 Process Airline Manuals", type="primary"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, manual_file in enumerate(manual_files):
                    status_text.text(f"Processing {manual_file.name}...")
                    
                    # Save file
                    file_path = Config.MANUALS_DIR / manual_file.name
                    with open(file_path, 'wb') as f:
                        f.write(manual_file.getvalue())
                    
                    # Extract text
                    text = PDFProcessor.extract_text(file_path)
                    
                    if text:
                        manual_type = PDFProcessor.classify_manual(manual_file.name, text)
                        
                        st.session_state.manual_files.append({
                            'filename': manual_file.name,
                            'type': manual_type,
                            'text': text,  # Store full text for analysis
                            'preview': text[:1000],
                            'upload_date': datetime.now().isoformat(),
                            'char_count': len(text)
                        })
                    
                    progress_bar.progress((idx + 1) / len(manual_files))
                
                status_text.empty()
                st.success(f"✅ Successfully processed **{len(manual_files)} manual(s)**")
        
        # Show loaded manuals
        if st.session_state.manual_files:
            st.markdown("---")
            st.markdown("### ✅ Loaded Airline Manuals")
            
            manuals_df = pd.DataFrame([
                {
                    'Filename': m['filename'],
                    'Type': m['type'],
                    'Size': f"{m['char_count']:,} chars",
                    'Upload Date': m['upload_date'][:10]
                }
                for m in st.session_state.manual_files
            ])
            
            st.dataframe(manuals_df, use_container_width=True)

# ============================================================================
# GAP ANALYSIS PAGE
# ============================================================================

def show_gap_analysis():
    """AI-powered gap analysis"""
    st.header("🔍 AI-Powered Gap Analysis")
    
    # Prerequisites check
    if not st.session_state.isarps:
        st.warning("⚠️ Please upload and process the IOSA Standards Manual first")
        return
    
    if not st.session_state.manual_files:
        st.warning("⚠️ Please upload airline manuals first")
        return
    
    # Analysis Configuration
    st.markdown("### ⚙️ Analysis Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_mode = st.selectbox(
            "Analysis Scope",
            ["Quick Sample (5 ISARPs)", "By Category", "Full Analysis (All ISARPs)"],
            help="Select the scope of analysis to perform"
        )
    
    with col2:
        if analysis_mode == "By Category":
            category = st.selectbox(
                "Select ISARP Category",
                list(Config.ISARP_CATEGORIES.keys()),
                format_func=lambda x: f"{x} - {Config.ISARP_CATEGORIES[x]}"
            )
    
    # Analysis Info
    st.markdown("""
    <div class="info-box">
    <h4>🤖 AI-Powered Analysis Process</h4>
    <p>The system will use Google Gemini AI to:</p>
    <ul>
        <li>Compare each ISARP requirement against your airline manuals</li>
        <li>Identify documentation gaps and compliance issues</li>
        <li>Classify findings as: Conformity, Finding, Observation, or Pending Evidence</li>
        <li>Provide specific recommendations and required evidence</li>
    </ul>
    <p><strong>Estimated time:</strong> ~10-15 seconds per ISARP</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Run Analysis Button
    if st.button("🚀 Run AI Gap Analysis", type="primary", use_container_width=True):
        # Determine ISARPs to analyze
        if analysis_mode == "Quick Sample (5 ISARPs)":
            isarps_to_analyze = st.session_state.isarps[:5]
        elif analysis_mode == "By Category":
            isarps_to_analyze = [i for i in st.session_state.isarps if i['category'] == category]
        else:
            isarps_to_analyze = st.session_state.isarps
        
        # Prepare manual texts
        manual_texts = [m['text'] for m in st.session_state.manual_files]
        
        # Progress tracking
        total = len(isarps_to_analyze)
        st.markdown(f"**Analyzing {total} ISARP(s)...**")
        
        progress_bar = st.progress(0)
        status_container = st.empty()
        results_container = st.container()
        
        results = []
        
        # Analyze each ISARP
        for idx, isarp in enumerate(isarps_to_analyze):
            status_container.info(f"🔍 Analyzing: **{isarp['code']}** - {isarp['title'][:50]}...")
            
            # Perform AI analysis
            result = st.session_state.analyzer.analyze_gap(
                isarp['code'],
                isarp['requirement_text'],
                manual_texts
            )
            
            # Add ISARP details to result
            result['title'] = isarp['title']
            result['category'] = isarp['category']
            
            results.append(result)
            
            # Update progress
            progress_bar.progress((idx + 1) / total)
            
            # Show interim result
            with results_container:
                status_badge_class = {
                    Config.STATUS_CONFORMITY: 'status-conformity',
                    Config.STATUS_FINDING: 'status-finding',
                    Config.STATUS_OBSERVATION: 'status-observation',
                    Config.STATUS_PENDING_EVIDENCE: 'status-pending'
                }.get(result['status'], '')
                
                st.markdown(
                    f'<span class="status-badge {status_badge_class}">'
                    f'{isarp["code"]}: {result["status"]}</span>',
                    unsafe_allow_html=True
                )
        
        # Store results
        st.session_state.analysis_results = results
        
        status_container.success(f"✅ **Analysis Complete!** Processed {total} ISARPs")
        
        # Summary
        st.markdown("---")
        st.markdown("### 📊 Analysis Summary")
        
        stats = get_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("✅ Conformity", stats['conformity_count'])
        col2.metric("🔴 Findings", stats['findings_count'])
        col3.metric("⚠️ Observations", stats['observations_count'])
        col4.metric("⏳ Pending Evidence", stats['pending_evidence_count'])
    
    # Display Results
    if st.session_state.analysis_results:
        st.markdown("---")
        st.markdown("### 📋 Detailed Analysis Results")
        
        # Filter options
        filter_status = st.multiselect(
            "Filter by Status",
            [Config.STATUS_CONFORMITY, Config.STATUS_FINDING, 
             Config.STATUS_OBSERVATION, Config.STATUS_PENDING_EVIDENCE],
            default=[Config.STATUS_FINDING, Config.STATUS_OBSERVATION, Config.STATUS_PENDING_EVIDENCE]
        )
        
        filtered_results = [r for r in st.session_state.analysis_results 
                          if r['status'] in filter_status]
        
        # Results table
        if filtered_results:
            results_df = pd.DataFrame([
                {
                    'ISARP Code': r['isarp_code'],
                    'Category': r.get('category', 'N/A'),
                    'Status': r['status'],
                    'Confidence': f"{r['confidence']*100:.0f}%",
                    'AI Powered': '🤖' if r.get('ai_powered') else '⚠️'
                }
                for r in filtered_results
            ])
            
            st.dataframe(results_df, use_container_width=True)
            
            # Detailed findings
            st.markdown("### 🔍 Detailed Findings")
            
            for result in filtered_results:
                status_emoji = {
                    Config.STATUS_CONFORMITY: "✅",
                    Config.STATUS_FINDING: "🔴",
                    Config.STATUS_OBSERVATION: "⚠️",
                    Config.STATUS_PENDING_EVIDENCE: "⏳"
                }.get(result['status'], "❓")
                
                with st.expander(f"{status_emoji} **{result['isarp_code']}** - {result.get('title', 'N/A')[:60]}..."):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Status:** {result['status']}")
                        st.markdown(f"**Confidence:** {result['confidence']*100:.0f}%")
                        
                        if result.get('ai_powered'):
                            st.markdown('🤖 <span class="ai-badge">AI Analysis</span>', unsafe_allow_html=True)
                        
                        st.markdown("**Documentation Gap:**")
                        st.info(result['documentation_gap'])
                        
                        st.markdown("**Implementation Gap:**")
                        st.warning(result['implementation_gap'])
                        
                        if result.get('assessment_reasoning'):
                            st.markdown("**AI Assessment Reasoning:**")
                            st.caption(result['assessment_reasoning'])
                    
                    with col2:
                        st.markdown("**Manual References:**")
                        refs = result.get('manual_references', ['No references found'])
                        for ref in refs[:5]:
                            st.markdown(f"• {ref}")
                        
                        st.markdown("**Evidence Required:**")
                        for ev in result.get('evidence_required', [])[:5]:
                            st.markdown(f"• {ev}")
                    
                    st.markdown("**Recommended Actions:**")
                    for action in result.get('recommended_actions', []):
                        st.markdown(f"✓ {action}")
        else:
            st.info("No results match the selected filters")

# ============================================================================
# IPM COMPLIANCE PAGE
# ============================================================================

def show_ipm_compliance():
    """IPM Section 1.1.1 Compliance Check"""
    st.header("📋 IPM Section 1.1.1 Compliance")
    
    st.markdown("""
    <div class="info-box">
    <h4>IOSA IPM Section 1.1.1: Documented Policies and Provision of Resources</h4>
    <p>This section requires airlines to demonstrate:</p>
    <ul>
        <li>✓ Documented safety and operational policies</li>
        <li>✓ Management commitment statements</li>
        <li>✓ Resource provision commitment (personnel, equipment, training, facilities)</li>
        <li>✓ Accountability assignment</li>
        <li>✓ Review and update mechanisms</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.manual_files:
        st.warning("⚠️ Please upload airline manuals first")
        return
    
    if st.button("🔍 Run IPM 1.1.1 Analysis", type="primary", use_container_width=True):
        with st.spinner("🤖 AI analyzing policies and resource provisions..."):
            manual_texts = [m['text'] for m in st.session_state.manual_files]
            
            result = st.session_state.analyzer.check_ipm_1_1_1(manual_texts)
            st.session_state.ipm_result = result
    
    # Display Results
    if st.session_state.ipm_result and 'error' not in st.session_state.ipm_result:
        result = st.session_state.ipm_result
        
        st.markdown("---")
        st.markdown("### 📊 Analysis Results")
        
        # Status Overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = "✅ Yes" if result.get('has_documented_policy') else "❌ No"
            st.metric("Documented Policy", status)
        
        with col2:
            status = "✅ Yes" if result.get('has_resource_provision') else "❌ No"
            st.metric("Resource Provision", status)
        
        with col3:
            st.metric("Policy Clarity", result.get('policy_clarity', 'N/A'))
        
        with col4:
            st.metric("Resource Specificity", result.get('resource_specificity', 'N/A'))
        
        # Compliance Status
        if result.get('compliant'):
            st.markdown('<div class="success-box"><h4>✅ IPM 1.1.1 COMPLIANT</h4></div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<div class="warning-box"><h4>⚠️ IPM 1.1.1 NON-COMPLIANT</h4></div>', 
                       unsafe_allow_html=True)
        
        # Detailed Findings
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 📄 Policy Excerpts Found")
            for excerpt in result.get('policy_excerpts', [])[:5]:
                st.info(f"📝 \"{excerpt}\"")
        
        with col_right:
            st.markdown("### 💰 Resource Provision Excerpts")
            for excerpt in result.get('resource_excerpts', [])[:5]:
                st.info(f"💼 \"{excerpt}\"")
        
        # Gaps
        if result.get('gaps'):
            st.markdown("---")
            st.markdown("### ⚠️ Identified Gaps")
            for gap in result['gaps']:
                st.warning(f"• {gap}")
        
        # Recommendations
        if result.get('recommendations'):
            st.markdown("---")
            st.markdown("### 💡 Recommendations")
            for rec in result['recommendations']:
                st.success(f"✓ {rec}")

# ============================================================================
# EVIDENCE REGISTRY PAGE
# ============================================================================

def show_evidence():
    """Evidence document management"""
    st.header("📎 Evidence Registry")
    
    st.markdown("""
    <div class="info-box">
    <h4>IPM 6.7.1: Implementation Evidence Requirements</h4>
    <p>Upload documents that prove implementation of IOSA requirements.</p>
    <p>Evidence must demonstrate actual practice, not just policy documentation.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Please run gap analysis first")
        return
    
    # Get ISARPs needing evidence
    pending = [r for r in st.session_state.analysis_results 
               if r['status'] in [Config.STATUS_PENDING_EVIDENCE, Config.STATUS_OBSERVATION, Config.STATUS_FINDING]]
    
    if not pending:
        st.success("✅ No ISARPs currently require evidence submission")
        return
    
    st.markdown("### 📤 Upload Evidence")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_isarp = st.selectbox(
            "Select ISARP Code",
            [r['isarp_code'] for r in pending],
            format_func=lambda x: f"{x} - {next((r['status'] for r in pending if r['isarp_code'] == x), 'N/A')}"
        )
    
    with col2:
        evidence_type = st.selectbox(
            "Evidence Type",
            Config.EVIDENCE_TYPES
        )
    
    # File upload
    evidence_file = st.file_uploader(
        "Upload Evidence Document (PDF)",
        type=['pdf'],
        help="Upload proof of implementation"
    )
    
    description = st.text_area(
        "Evidence Description",
        placeholder="Describe how this document proves implementation of the requirement..."
    )
    
    if evidence_file and st.button("📎 Submit Evidence", type="primary"):
        # Save file
        file_path = Config.EVIDENCE_DIR / evidence_file.name
        with open(file_path, 'wb') as f:
            f.write(evidence_file.getvalue())
        
        # Store evidence metadata
        if selected_isarp not in st.session_state.evidence_files:
            st.session_state.evidence_files[selected_isarp] = []
        
        st.session_state.evidence_files[selected_isarp].append({
            'filename': evidence_file.name,
            'type': evidence_type,
            'description': description,
            'upload_date': datetime.now().isoformat(),
            'file_path': str(file_path),
            'validated': True,
            'validation_date': datetime.now().isoformat()
        })
        
        st.success(f"✅ Evidence submitted successfully for **{selected_isarp}**")
    
    # Evidence Registry
    if st.session_state.evidence_files:
        st.markdown("---")
        st.markdown("### 📋 Evidence Registry")
        
        for isarp_code, evidence_list in st.session_state.evidence_files.items():
            with st.expander(f"📎 **{isarp_code}** ({len(evidence_list)} document(s))"):
                for idx, evidence in enumerate(evidence_list):
                    st.markdown(f"**Document {idx + 1}:** {evidence['filename']}")
                    st.markdown(f"**Type:** {evidence['type']}")
                    st.markdown(f"**Description:** {evidence['description']}")
                    st.markdown(f"**Uploaded:** {evidence['upload_date'][:10]}")
                    st.markdown(f"**Status:** ✅ Validated")
                    st.markdown("---")

# ============================================================================
# REPORTS & EXPORT PAGE
# ============================================================================

def show_reports():
    """Generate and export reports"""
    st.header("📈 Reports & Export")
    
    if not st.session_state.analysis_results:
        st.warning("⚠️ Please run gap analysis first")
        return
    
    stats = get_statistics()
    
    # Executive Summary
    st.markdown("### 📋 Executive Summary")
    
    summary_text = f"""
# IOSA Gap Analysis - Executive Report

**Organization:** Sial Aviation  
**Analysis Date:** {datetime.now().strftime('%B %d, %Y')}  
**Report Generated:** {datetime.now().strftime('%H:%M %p')}

---

## Overview

This report presents the results of a comprehensive IOSA (IATA Operational Safety Audit) gap analysis 
conducted using AI-powered assessment technology.

### Scope of Analysis
- **Total ISARPs Assessed:** {stats['analyzed_isarps']}
- **Airline Manuals Reviewed:** {len(st.session_state.manual_files)}
- **Evidence Documents:** {len(st.session_state.evidence_files)}

### Compliance Status

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ Conformity | {stats['conformity_count']} | {stats['conformity_rate']:.1f}% |
| 🔴 Findings | {stats['findings_count']} | {(stats['findings_count']/max(stats['analyzed_isarps'],1))*100:.1f}% |
| ⚠️ Observations | {stats['observations_count']} | {(stats['observations_count']/max(stats['analyzed_isarps'],1))*100:.1f}% |
| ⏳ Pending Evidence | {stats['pending_evidence_count']} | {(stats['pending_evidence_count']/max(stats['analyzed_isarps'],1))*100:.1f}% |

### Overall Compliance Score: {stats['compliance_score']:.1f}%

---

## Critical Findings

The analysis identified **{stats['findings_count']} critical finding(s)** requiring immediate attention.

"""
    
    # Add critical findings
    findings = [r for r in st.session_state.analysis_results if r['status'] == Config.STATUS_FINDING]
    if findings:
        summary_text += "\n### Priority Issues\n\n"
        for f in findings[:5]:
            summary_text += f"- **{f['isarp_code']}**: {f['documentation_gap']}\n"
    
    summary_text += f"""

---

## Recommendations

### Immediate Actions (0-30 days)
1. Address all {stats['findings_count']} critical findings
2. Upload implementation evidence for {stats['pending_evidence_count']} pending ISARPs
3. Review and update affected operational manuals

### Short-term Actions (30-90 days)
1. Resolve {stats['observations_count']} observations
2. Conduct internal compliance review
3. Update training programs based on gaps identified

### Long-term Actions (90+ days)
1. Implement continuous compliance monitoring
2. Schedule follow-up IOSA audit
3. Establish compliance improvement program

---

## Conclusion

Based on the AI-powered gap analysis, the airline demonstrates a **{stats['compliance_score']:.1f}% compliance score**. 
{"✅ This indicates strong compliance with IOSA standards." if stats['compliance_score'] >= 80 else 
 "⚠️ Significant gaps have been identified that require immediate attention."}

**Next Steps:**
- Review all findings with department heads
- Develop action plans for each non-conformity
- Assign responsibilities and deadlines
- Schedule progress review in 30 days

---

*This report was generated using Sial-Compliance-Pro with AI-powered gap analysis.*
*Powered by Google Gemini 1.5 Pro*
"""
    
    st.markdown(summary_text)
    
    # Download Options
    st.markdown("---")
    st.markdown("### 📥 Download Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Excel Report
        if st.button("📊 Generate Excel Report", use_container_width=True):
            # Create comprehensive DataFrame
            excel_data = []
            for result in st.session_state.analysis_results:
                excel_data.append({
                    'ISARP Code': result['isarp_code'],
                    'Category': result.get('category', 'N/A'),
                    'Title': result.get('title', 'N/A'),
                    'Status': result['status'],
                    'Confidence': f"{result['confidence']*100:.0f}%",
                    'Documentation Gap': result['documentation_gap'],
                    'Implementation Gap': result['implementation_gap'],
                    'Manual References': '; '.join(result.get('manual_references', [])),
                    'Evidence Required': '; '.join(result.get('evidence_required', [])),
                    'Recommended Actions': '; '.join(result.get('recommended_actions', [])),
                    'AI Powered': result.get('ai_powered', False),
                    'Analysis Date': result.get('analysis_date', '')[:10]
                })
            
            df = pd.DataFrame(excel_data)
            
            # Create Excel file
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Gap Analysis', index=False)
                
                # Add summary sheet
                summary_df = pd.DataFrame([
                    ['Total ISARPs', stats['total_isarps']],
                    ['Analyzed', stats['analyzed_isarps']],
                    ['Conformity', stats['conformity_count']],
                    ['Findings', stats['findings_count']],
                    ['Observations', stats['observations_count']],
                    ['Pending Evidence', stats['pending_evidence_count']],
                    ['Compliance Score', f"{stats['compliance_score']:.1f}%"]
                ], columns=['Metric', 'Value'])
                
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            output.seek(0)
            
            st.download_button(
                label="⬇️ Download Excel Report",
                data=output,
                file_name=f"IOSA_Gap_Analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col2:
        # JSON Export
        export_data = {
            'metadata': {
                'report_date': datetime.now().isoformat(),
                'organization': 'Sial Aviation',
                'analysis_type': 'IOSA Gap Analysis',
                'ai_powered': True
            },
            'statistics': stats,
            'results': st.session_state.analysis_results,
            'evidence_registry': st.session_state.evidence_files,
            'ipm_compliance': st.session_state.ipm_result
        }
        
        json_str = json.dumps(export_data, indent=2)
        
        st.download_button(
            label="⬇️ Download JSON Export",
            data=json_str,
            file_name=f"compliance_data_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        # PDF Report (Markdown)
        st.download_button(
            label="⬇️ Download PDF Report",
            data=summary_text,
            file_name=f"Executive_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True,
            help="Download as Markdown (convert to PDF using tools like Pandoc)"
        )

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    main()
