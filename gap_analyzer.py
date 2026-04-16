"""
Gap Analysis Module
Orchestrates the complete gap analysis workflow
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import datetime
from loguru import logger
import json

from app.config import settings, ConformityStatus, EvidenceType
from app.utils.pdf_parser import PDFParser, ISARPRequirement, process_ism_document, process_airline_manual
from app.utils.vectorizer import VectorStore, SemanticMatcher
from app.utils.llm_analyzer import ClaudeAnalyzer, batch_analyze_isarps


class GapAnalysisEngine:
    """Main engine for conducting gap analysis"""
    
    def __init__(self):
        self.pdf_parser = PDFParser(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        self.vector_store = VectorStore()
        self.claude_analyzer = ClaudeAnalyzer()
        self.semantic_matcher = SemanticMatcher()
        
        # Storage for analysis results
        self.isarps: List[ISARPRequirement] = []
        self.gap_results: List[Dict] = []
        self.evidence_links: Dict[str, List[Dict]] = {}  # ISARP code -> evidence docs
    
    def ingest_ism_manual(self, pdf_path: Path) -> int:
        """
        Ingest IOSA Standards Manual
        
        Returns:
            Number of ISARPs extracted
        """
        logger.info(f"Ingesting ISM from: {pdf_path}")
        
        # Extract ISARPs and chunks
        requirements, chunks = process_ism_document(pdf_path)
        self.isarps = requirements
        
        # Add to vector database
        self.vector_store.add_ism_chunks(chunks)
        
        # Also add each ISARP's requirement text separately for better search
        for isarp in requirements:
            # Create a chunk for the ISARP requirement itself
            from app.utils.pdf_parser import DocumentChunk
            isarp_chunk = DocumentChunk(
                text=f"{isarp.code}: {isarp.title}\n{isarp.requirement_text}",
                page_number=isarp.page_number,
                chunk_index=0,
                metadata={"isarp_code": isarp.code},
                source_file=isarp.source_file
            )
            self.vector_store.add_ism_chunks([isarp_chunk], isarp_code=isarp.code)
        
        logger.info(f"Successfully ingested {len(requirements)} ISARPs")
        return len(requirements)
    
    def ingest_airline_manual(self, pdf_path: Path, manual_name: Optional[str] = None) -> str:
        """
        Ingest airline internal manual
        
        Returns:
            Manual type (classified)
        """
        logger.info(f"Ingesting airline manual from: {pdf_path}")
        
        manual_name = manual_name or pdf_path.stem
        manual_type, chunks = process_airline_manual(pdf_path)
        
        # Add to vector database
        self.vector_store.add_manual_chunks(chunks, manual_type, manual_name)
        
        logger.info(f"Successfully ingested {len(chunks)} chunks from {manual_type}")
        return manual_type
    
    def ingest_multiple_manuals(self, manual_paths: List[Path]) -> Dict[str, str]:
        """
        Ingest multiple airline manuals
        
        Returns:
            Dictionary mapping filename to manual type
        """
        results = {}
        for path in manual_paths:
            try:
                manual_type = self.ingest_airline_manual(path)
                results[path.name] = manual_type
            except Exception as e:
                logger.error(f"Error ingesting {path}: {e}")
                results[path.name] = f"ERROR: {str(e)}"
        
        return results
    
    def run_gap_analysis(self, isarp_codes: Optional[List[str]] = None,
                        category: Optional[str] = None) -> List[Dict]:
        """
        Run gap analysis for specified ISARPs or all ISARPs
        
        Args:
            isarp_codes: Specific ISARP codes to analyze (e.g., ["ORG 1.1.1", "FLT 2.3.5"])
            category: Analyze all ISARPs in a category (e.g., "ORG", "FLT")
        
        Returns:
            List of gap analysis results
        """
        # Filter ISARPs to analyze
        isarps_to_analyze = self._filter_isarps(isarp_codes, category)
        
        if not isarps_to_analyze:
            logger.warning("No ISARPs to analyze")
            return []
        
        logger.info(f"Starting gap analysis for {len(isarps_to_analyze)} ISARPs")
        
        # Run batch analysis
        results = batch_analyze_isarps(
            analyzer=self.claude_analyzer,
            isarps=isarps_to_analyze,
            vector_store=self.vector_store,
            batch_size=5
        )
        
        self.gap_results.extend(results)
        
        logger.info(f"Gap analysis completed. Results: {self._summarize_results(results)}")
        return results
    
    def _filter_isarps(self, codes: Optional[List[str]], 
                      category: Optional[str]) -> List[ISARPRequirement]:
        """Filter ISARPs based on criteria"""
        if codes:
            return [isarp for isarp in self.isarps if isarp.code in codes]
        elif category:
            return [isarp for isarp in self.isarps if isarp.category == category]
        else:
            return self.isarps
    
    def _summarize_results(self, results: List[Dict]) -> Dict:
        """Summarize analysis results"""
        summary = {status: 0 for status in ConformityStatus.all_statuses()}
        
        for result in results:
            status = result.get('status', ConformityStatus.NOT_ASSESSED)
            summary[status] = summary.get(status, 0) + 1
        
        return summary
    
    def add_evidence_document(self, isarp_code: str, pdf_path: Path, 
                            evidence_type: str) -> Dict:
        """
        Add evidence document for a specific ISARP
        Following IPM 1.7.1 digital evidence requirements
        
        Args:
            isarp_code: ISARP code (e.g., "ORG 1.1.1")
            pdf_path: Path to evidence document
            evidence_type: Type of evidence (see EvidenceType class)
        
        Returns:
            Validation result
        """
        logger.info(f"Adding evidence for {isarp_code}: {pdf_path.name}")
        
        # Process evidence document
        pages = self.pdf_parser.extract_text_pymupdf(pdf_path)
        chunks = self.pdf_parser.chunk_text(pages)
        
        # Add to vector database
        self.vector_store.add_evidence_document(chunks, isarp_code, evidence_type)
        
        # Get the corresponding ISARP
        isarp = next((i for i in self.isarps if i.code == isarp_code), None)
        if not isarp:
            logger.warning(f"ISARP {isarp_code} not found")
            return {"error": f"ISARP {isarp_code} not found"}
        
        # Validate evidence using Claude
        evidence_text = "\n".join([page["text"] for page in pages[:3]])  # First 3 pages
        validation = self.claude_analyzer.validate_evidence_document(
            isarp, evidence_text, evidence_type
        )
        
        # Store evidence link
        if isarp_code not in self.evidence_links:
            self.evidence_links[isarp_code] = []
        
        self.evidence_links[isarp_code].append({
            "filename": pdf_path.name,
            "evidence_type": evidence_type,
            "upload_date": datetime.now().isoformat(),
            "validation": validation
        })
        
        # Update gap analysis result if evidence is valid
        if validation.get('is_valid_evidence'):
            self._update_conformity_status(isarp_code, validation)
        
        return validation
    
    def _update_conformity_status(self, isarp_code: str, validation: Dict):
        """Update conformity status when valid evidence is added"""
        # Find existing gap result
        for result in self.gap_results:
            if result.get('isarp_code') == isarp_code:
                if result.get('status') == ConformityStatus.PENDING_EVIDENCE:
                    if validation.get('proves_implementation'):
                        result['status'] = ConformityStatus.CONFORMITY
                        result['evidence_validated'] = True
                        logger.info(f"Updated {isarp_code} to CONFORMITY based on evidence")
                break
    
    def check_ipm_1_1_1_compliance(self) -> Dict:
        """
        Special check for IPM Section 1.1.1: Documented Policies and Resource Provision
        Typically applies to ORG category ISARPs
        """
        logger.info("Checking IPM 1.1.1 compliance")
        
        # Search for policy and resource documents in manuals
        policy_query = "policy documented management commitment resources provision"
        policy_passages = self.vector_store.search_manuals(policy_query, top_k=10)
        
        # Use Claude to assess
        assessment = self.claude_analyzer.assess_ipm_1_1_1_compliance(policy_passages)
        
        return assessment
    
    def generate_compliance_report(self, output_path: Optional[Path] = None) -> pd.DataFrame:
        """
        Generate comprehensive compliance report
        
        Returns:
            DataFrame with columns: [ISARP Code, Manual Reference, Conformity Status, Details]
        """
        logger.info("Generating compliance report")
        
        report_data = []
        
        for result in self.gap_results:
            isarp_code = result.get('isarp_code', 'UNKNOWN')
            status = result.get('status', ConformityStatus.NOT_ASSESSED)
            
            # Get manual references
            manual_refs = result.get('manual_references', [])
            manual_ref_str = '; '.join(manual_refs) if manual_refs else 'No reference found'
            
            # Get evidence status
            evidence_status = "No evidence" if isarp_code not in self.evidence_links else \
                             f"{len(self.evidence_links[isarp_code])} document(s)"
            
            report_data.append({
                'ISARP Code': isarp_code,
                'ISARP Title': result.get('isarp_title', ''),
                'Category': isarp_code.split()[0] if ' ' in isarp_code else '',
                'Conformity Status': status,
                'Confidence': f"{result.get('confidence', 0):.2%}",
                'Manual Reference': manual_ref_str,
                'Documentation Gap': result.get('documentation_gap', ''),
                'Implementation Gap': result.get('implementation_gap', ''),
                'Evidence Status': evidence_status,
                'Recommended Actions': '; '.join(result.get('recommended_actions', [])),
                'Analysis Date': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
        
        df = pd.DataFrame(report_data)
        
        # Save to Excel if path provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_excel(output_path, index=False, engine='openpyxl')
            logger.info(f"Report saved to {output_path}")
        
        return df
    
    def generate_executive_summary(self) -> str:
        """Generate executive summary using Claude"""
        if not self.gap_results:
            return "No gap analysis results available."
        
        summary = self.claude_analyzer.generate_compliance_summary(self.gap_results)
        return summary
    
    def export_audit_package(self, output_dir: Path):
        """
        Export complete audit package including:
        - Gap analysis report (Excel)
        - Evidence registry (JSON)
        - Executive summary (PDF)
        - Detailed findings (JSON)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Gap analysis report
        report_path = output_dir / f"gap_analysis_report_{timestamp}.xlsx"
        self.generate_compliance_report(report_path)
        
        # 2. Evidence registry
        evidence_path = output_dir / f"evidence_registry_{timestamp}.json"
        with open(evidence_path, 'w') as f:
            json.dump(self.evidence_links, f, indent=2)
        
        # 3. Detailed findings
        findings_path = output_dir / f"detailed_findings_{timestamp}.json"
        with open(findings_path, 'w') as f:
            json.dump(self.gap_results, f, indent=2)
        
        # 4. Executive summary
        summary_path = output_dir / f"executive_summary_{timestamp}.txt"
        summary = self.generate_executive_summary()
        with open(summary_path, 'w') as f:
            f.write(summary)
        
        logger.info(f"Audit package exported to {output_dir}")
        
        return {
            "report": report_path,
            "evidence_registry": evidence_path,
            "findings": findings_path,
            "summary": summary_path
        }
    
    def get_statistics(self) -> Dict:
        """Get current analysis statistics"""
        stats = {
            "total_isarps": len(self.isarps),
            "analyzed_isarps": len(self.gap_results),
            "conformity_count": sum(1 for r in self.gap_results 
                                   if r.get('status') == ConformityStatus.CONFORMITY),
            "findings_count": sum(1 for r in self.gap_results 
                                 if r.get('status') == ConformityStatus.FINDING),
            "observations_count": sum(1 for r in self.gap_results 
                                     if r.get('status') == ConformityStatus.OBSERVATION),
            "pending_evidence_count": sum(1 for r in self.gap_results 
                                         if r.get('status') == ConformityStatus.PENDING_EVIDENCE),
            "evidence_documents": len(self.evidence_links),
            "vector_db_stats": self.vector_store.get_collection_stats()
        }
        
        return stats


# Utility function for quick analysis
def quick_gap_analysis(ism_path: Path, manual_paths: List[Path], 
                      category: Optional[str] = None) -> Dict:
    """
    Quick gap analysis workflow
    
    Args:
        ism_path: Path to IOSA Standards Manual
        manual_paths: List of paths to airline manuals
        category: Optional category filter (e.g., "ORG")
    
    Returns:
        Dictionary with results and statistics
    """
    engine = GapAnalysisEngine()
    
    # Ingest documents
    logger.info("Ingesting ISM...")
    engine.ingest_ism_manual(ism_path)
    
    logger.info("Ingesting airline manuals...")
    engine.ingest_multiple_manuals(manual_paths)
    
    # Run analysis
    logger.info("Running gap analysis...")
    results = engine.run_gap_analysis(category=category)
    
    # Generate report
    report_df = engine.generate_compliance_report()
    
    return {
        "results": results,
        "report": report_df,
        "statistics": engine.get_statistics(),
        "engine": engine  # Return engine for further operations
    }
