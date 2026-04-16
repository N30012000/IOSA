"""
Sial-Compliance-Pro - Main Streamlit Application
Aviation Regulatory Compliance Gap Analysis Tool
"""

import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys
import os

# Fix import paths - add parent directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Now import with correct paths
try:
    from app.config import settings, ConformityStatus, EvidenceType, ISARPParser
    from app.gap_analyzer import GapAnalysisEngine, quick_gap_analysis
    from app.vectorizer import VectorStore
except ImportError:
    # Alternative import for different directory structures
    from config import settings, ConformityStatus, EvidenceType, ISARPParser
    from gap_analyzer import GapAnalysisEngine, quick_gap_analysis
    from vectorizer import VectorStore


# Page configuration
st.set_page_config(
    page_title="Sial-Compliance-Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    .status-conformity {
        background-color: #d4edda;
        color: #155724;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .status-finding {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
    .status-observation {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'engine' not in st.session_state:
    st.session_state.engine = GapAnalysisEngine()
if 'ism_loaded' not in st.session_state:
    st.session_state.ism_loaded = False
if 'manuals_loaded' not in st.session_state:
    st.session_state.manuals_loaded = []
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False


def main():
    # Header
    st.markdown('<div class="main-header">✈️ Sial-Compliance-Pro</div>', 
                unsafe_allow_html=True)
    st.markdown("**IOSA/EASA Regulatory Gap Analysis System**")
    st.markdown("---")
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🛩️ Sial Aviation")
        st.markdown("### Navigation")
        
        page = st.radio(
            "Select Module",
            ["🏠 Dashboard", 
             "📄 Document Ingestion", 
             "🔍 Gap Analysis", 
             "📊 Evidence Management",
             "📈 Reports & Export"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### System Status")
        stats = st.session_state.engine.get_statistics()
        st.metric("ISARPs Loaded", stats['total_isarps'])
        st.metric("Manuals Loaded", len(st.session_state.manuals_loaded))
        st.metric("Analyses Complete", stats['analyzed_isarps'])
    
    # Route to selected page
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "📄 Document Ingestion":
        show_document_ingestion()
    elif page == "🔍 Gap Analysis":
        show_gap_analysis()
    elif page == "📊 Evidence Management":
        show_evidence_management()
    elif page == "📈 Reports & Export":
        show_reports()


def show_dashboard():
    """Dashboard overview"""
    st.header("📊 System Dashboard")
    
    stats = st.session_state.engine.get_statistics()
    
    # Metrics row
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
        st.metric("Conformity", stats['conformity_count'], 
                 delta=f"{stats['conformity_count']/max(stats['analyzed_isarps'], 1)*100:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Findings", stats['findings_count'],
                 delta=f"{stats['findings_count']/max(stats['analyzed_isarps'], 1)*100:.1f}%",
                 delta_color="inverse")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Status breakdown
    if stats['analyzed_isarps'] > 0:
        st.subheader("Compliance Status Breakdown")
        
        status_data = {
            'Status': ['Conformity', 'Findings', 'Observations', 'Pending Evidence'],
            'Count': [
                stats['conformity_count'],
                stats['findings_count'],
                stats['observations_count'],
                stats['pending_evidence_count']
            ]
        }
        
        df_status = pd.DataFrame(status_data)
        st.bar_chart(df_status.set_index('Status'))
        
        # Recent findings
        st.subheader("Recent Findings")
        if st.session_state.engine.gap_results:
            findings = [r for r in st.session_state.engine.gap_results 
                       if r.get('status') == ConformityStatus.FINDING]
            
            if findings:
                for finding in findings[:5]:
                    with st.expander(f"🔴 {finding.get('isarp_code', 'N/A')} - {finding.get('isarp_title', '')}"):
                        st.write(f"**Documentation Gap:** {finding.get('documentation_gap', 'N/A')}")
                        st.write(f"**Recommended Actions:**")
                        for action in finding.get('recommended_actions', []):
                            st.write(f"- {action}")
            else:
                st.success("No findings identified! ✅")
    else:
        st.info("👆 Upload documents and run analysis to see results")


def show_document_ingestion():
    """Document ingestion interface"""
    st.header("📄 Document Ingestion")
    
    tab1, tab2 = st.tabs(["IOSA Standards Manual", "Airline Manuals"])
    
    with tab1:
        st.subheader("Upload IOSA Standards Manual (ISM)")
        st.markdown("Upload the official IATA IOSA Standards Manual PDF containing all ISARPs.")
        
        ism_file = st.file_uploader(
            "Select ISM PDF", 
            type=['pdf'],
            key="ism_upload"
        )
        
        if ism_file and st.button("Process ISM", key="process_ism"):
            with st.spinner("Extracting ISARPs and creating vector embeddings..."):
                # Save uploaded file
                ism_path = settings.ism_dir / ism_file.name
                with open(ism_path, 'wb') as f:
                    f.write(ism_file.read())
                
                # Ingest
                try:
                    count = st.session_state.engine.ingest_ism_manual(ism_path)
                    st.session_state.ism_loaded = True
                    st.success(f"✅ Successfully loaded {count} ISARPs from ISM")
                except Exception as e:
                    st.error(f"❌ Error processing ISM: {e}")
        
        if st.session_state.ism_loaded:
            st.info(f"✅ ISM loaded with {len(st.session_state.engine.isarps)} ISARPs")
    
    with tab2:
        st.subheader("Upload Airline Internal Manuals")
        st.markdown("Upload your airline's operational manuals (FOM, COM, AMM, etc.)")
        
        manual_files = st.file_uploader(
            "Select Manual PDFs (can upload multiple)",
            type=['pdf'],
            accept_multiple_files=True,
            key="manuals_upload"
        )
        
        if manual_files and st.button("Process Manuals", key="process_manuals"):
            with st.spinner(f"Processing {len(manual_files)} manual(s)..."):
                for manual_file in manual_files:
                    # Save file
                    manual_path = settings.manuals_dir / manual_file.name
                    with open(manual_path, 'wb') as f:
                        f.write(manual_file.read())
                    
                    # Ingest
                    try:
                        manual_type = st.session_state.engine.ingest_airline_manual(manual_path)
                        st.session_state.manuals_loaded.append({
                            'filename': manual_file.name,
                            'type': manual_type,
                            'upload_date': datetime.now()
                        })
                        st.success(f"✅ Loaded {manual_file.name} ({manual_type})")
                    except Exception as e:
                        st.error(f"❌ Error processing {manual_file.name}: {e}")
        
        # Show loaded manuals
        if st.session_state.manuals_loaded:
            st.markdown("### Loaded Manuals")
            df_manuals = pd.DataFrame(st.session_state.manuals_loaded)
            st.dataframe(df_manuals, use_container_width=True)


def show_gap_analysis():
    """Gap analysis interface"""
    st.header("🔍 Gap Analysis")
    
    if not st.session_state.ism_loaded:
        st.warning("⚠️ Please upload and process the ISM first")
        return
    
    if not st.session_state.manuals_loaded:
        st.warning("⚠️ Please upload and process airline manuals first")
        return
    
    # Analysis options
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_mode = st.radio(
            "Analysis Scope",
            ["All ISARPs", "By Category", "Specific ISARPs"]
        )
    
    with col2:
        if analysis_mode == "By Category":
            category = st.selectbox(
                "Select Category",
                list(settings.isarp_categories.keys())
            )
        elif analysis_mode == "Specific ISARPs":
            isarp_codes_input = st.text_area(
                "Enter ISARP codes (one per line)",
                placeholder="ORG 1.1.1\nFLT 2.3.5\nMNT 1.2.3"
            )
    
    # IPM Section 1.1.1 Check
    st.markdown("---")
    st.subheader("📋 IPM Section 1.1.1 Compliance Check")
    st.markdown("Check for documented policies and resource provision")
    
    if st.button("Run IPM 1.1.1 Check"):
        with st.spinner("Analyzing policies and resource provisions..."):
            result = st.session_state.engine.check_ipm_1_1_1_compliance()
            
            if 'error' not in result:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Has Documented Policy", 
                             "Yes ✅" if result.get('has_documented_policy') else "No ❌")
                with col_b:
                    st.metric("Has Resource Provision",
                             "Yes ✅" if result.get('has_resource_provision') else "No ❌")
                
                if result.get('gaps'):
                    st.warning("**Gaps Identified:**")
                    for gap in result['gaps']:
                        st.write(f"- {gap}")
                
                if result.get('recommendations'):
                    st.info("**Recommendations:**")
                    for rec in result['recommendations']:
                        st.write(f"- {rec}")
    
    st.markdown("---")
    
    # Run analysis
    if st.button("🚀 Run Gap Analysis", type="primary"):
        with st.spinner("Running comprehensive gap analysis..."):
            try:
                if analysis_mode == "All ISARPs":
                    results = st.session_state.engine.run_gap_analysis()
                elif analysis_mode == "By Category":
                    results = st.session_state.engine.run_gap_analysis(category=category)
                else:
                    codes = [line.strip() for line in isarp_codes_input.split('\n') if line.strip()]
                    results = st.session_state.engine.run_gap_analysis(isarp_codes=codes)
                
                st.session_state.analysis_complete = True
                st.success(f"✅ Analysis complete! Analyzed {len(results)} ISARPs")
                
                # Show summary
                st.markdown("### Analysis Summary")
                stats = st.session_state.engine.get_statistics()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Conformity", stats['conformity_count'])
                col2.metric("Findings", stats['findings_count'])
                col3.metric("Observations", stats['observations_count'])
                col4.metric("Pending Evidence", stats['pending_evidence_count'])
                
            except Exception as e:
                st.error(f"❌ Error during analysis: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # Display results
    if st.session_state.analysis_complete and st.session_state.engine.gap_results:
        st.markdown("---")
        st.subheader("📋 Analysis Results")
        
        # Filter options
        status_filter = st.multiselect(
            "Filter by Status",
            ConformityStatus.all_statuses(),
            default=ConformityStatus.all_statuses()
        )
        
        # Create results dataframe
        results_data = []
        for result in st.session_state.engine.gap_results:
            if result.get('status') in status_filter:
                results_data.append({
                    'ISARP Code': result.get('isarp_code', 'N/A'),
                    'Title': result.get('isarp_title', ''),
                    'Status': result.get('status', 'N/A'),
                    'Confidence': f"{result.get('confidence', 0)*100:.0f}%",
                    'Documentation Gap': result.get('documentation_gap', '')[:100] + '...'
                })
        
        df_results = pd.DataFrame(results_data)
        st.dataframe(df_results, use_container_width=True)
        
        # Detailed view
        st.markdown("### Detailed Findings")
        for result in st.session_state.engine.gap_results:
            if result.get('status') in status_filter:
                status = result.get('status', 'N/A')
                status_emoji = {
                    ConformityStatus.CONFORMITY: "✅",
                    ConformityStatus.FINDING: "🔴",
                    ConformityStatus.OBSERVATION: "⚠️",
                    ConformityStatus.PENDING_EVIDENCE: "⏳"
                }.get(status, "❓")
                
                with st.expander(f"{status_emoji} {result.get('isarp_code', 'N/A')} - {result.get('isarp_title', '')}"):
                    col_left, col_right = st.columns([2, 1])
                    
                    with col_left:
                        st.markdown(f"**Status:** {status}")
                        st.markdown(f"**Confidence:** {result.get('confidence', 0)*100:.0f}%")
                        
                        if result.get('documentation_gap'):
                            st.markdown("**Documentation Gap:**")
                            st.write(result['documentation_gap'])
                        
                        if result.get('implementation_gap'):
                            st.markdown("**Implementation Gap:**")
                            st.write(result['implementation_gap'])
                    
                    with col_right:
                        if result.get('manual_references'):
                            st.markdown("**Manual References:**")
                            for ref in result['manual_references']:
                                st.write(f"- {ref}")
                        
                        if result.get('evidence_required'):
                            st.markdown("**Evidence Required:**")
                            for ev in result['evidence_required']:
                                st.write(f"- {ev}")
                    
                    if result.get('recommended_actions'):
                        st.markdown("**Recommended Actions:**")
                        for action in result['recommended_actions']:
                            st.write(f"- {action}")


def show_evidence_management():
    """Evidence management interface"""
    st.header("📊 Evidence Management")
    st.markdown("Upload and link implementation evidence to ISARPs (IPM 6.7.1 & 1.7.1)")
    
    if not st.session_state.analysis_complete:
        st.warning("⚠️ Please run gap analysis first")
        return
    
    # Select ISARP
    pending_isarps = [
        r.get('isarp_code') for r in st.session_state.engine.gap_results
        if r.get('status') in [ConformityStatus.PENDING_EVIDENCE, ConformityStatus.OBSERVATION]
    ]
    
    if not pending_isarps:
        st.success("✅ No ISARPs pending evidence!")
        return
    
    selected_isarp = st.selectbox(
        "Select ISARP requiring evidence",
        pending_isarps
    )
    
    # Evidence type
    evidence_type = st.selectbox(
        "Evidence Type",
        EvidenceType.all_types()
    )
    
    # Upload evidence
    evidence_file = st.file_uploader(
        "Upload Evidence Document (PDF)",
        type=['pdf'],
        key="evidence_upload"
    )
    
    if evidence_file and st.button("Submit Evidence"):
        with st.spinner("Validating evidence document..."):
            # Save file
            evidence_path = settings.evidence_dir / evidence_file.name
            with open(evidence_path, 'wb') as f:
                f.write(evidence_file.read())
            
            # Add evidence
            try:
                validation = st.session_state.engine.add_evidence_document(
                    selected_isarp, evidence_path, evidence_type
                )
                
                if validation.get('is_valid_evidence'):
                    st.success(f"✅ Evidence validated and linked to {selected_isarp}")
                    st.json(validation)
                else:
                    st.warning("⚠️ Evidence may not fully prove implementation")
                    st.json(validation)
            except Exception as e:
                st.error(f"❌ Error processing evidence: {e}")
    
    # Show evidence registry
    st.markdown("---")
    st.subheader("Evidence Registry")
    
    if st.session_state.engine.evidence_links:
        for isarp_code, evidence_list in st.session_state.engine.evidence_links.items():
            with st.expander(f"📎 {isarp_code} ({len(evidence_list)} document(s))"):
                for ev in evidence_list:
                    st.markdown(f"**{ev['filename']}**")
                    st.write(f"Type: {ev['evidence_type']}")
                    st.write(f"Uploaded: {ev['upload_date']}")
                    if ev.get('validation'):
                        st.write(f"Quality: {ev['validation'].get('evidence_quality', 'N/A')}")


def show_reports():
    """Reports and export interface"""
    st.header("📈 Reports & Export")
    
    if not st.session_state.analysis_complete:
        st.warning("⚠️ Please run gap analysis first")
        return
    
    # Executive summary
    st.subheader("Executive Summary")
    if st.button("Generate Executive Summary"):
        with st.spinner("Generating summary using Claude AI..."):
            summary = st.session_state.engine.generate_executive_summary()
            st.markdown(summary)
    
    st.markdown("---")
    
    # Download reports
    st.subheader("Download Reports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Generate Excel Report"):
            with st.spinner("Creating Excel report..."):
                report_path = settings.outputs_dir / f"gap_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                df = st.session_state.engine.generate_compliance_report(report_path)
                
                with open(report_path, 'rb') as f:
                    st.download_button(
                        "Download Excel Report",
                        f,
                        file_name=report_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    
    with col2:
        if st.button("📦 Export Full Audit Package"):
            with st.spinner("Preparing audit package..."):
                output_dir = settings.outputs_dir / f"audit_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                files = st.session_state.engine.export_audit_package(output_dir)
                st.success(f"✅ Audit package created at {output_dir}")
                st.json({k: str(v) for k, v in files.items()})


if __name__ == "__main__":
    main()
