"""
Configuration Management for Sial-Compliance-Pro
Handles environment variables, paths, and application settings
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration settings"""
    
    # API Keys - BaseSettings automatically detects ANTHROPIC_API_KEY from env
    anthropic_api_key: str = ""
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = Path(__file__).parent.parent / "data"
    ism_dir: Path = Path(__file__).parent.parent / "data" / "ism"
    manuals_dir: Path = Path(__file__).parent.parent / "data" / "manuals"
    evidence_dir: Path = Path(__file__).parent.parent / "data" / "evidence"
    vector_db_path: Path = Path(__file__).parent.parent / "data" / "vector_db"
    database_path: Path = Path(__file__).parent.parent / "database" / "compliance.db"
    outputs_dir: Path = Path(__file__).parent.parent / "outputs" / "reports"
    
    # Vector Database Settings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_db_type: str = "chromadb" 
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    
    # LLM Settings
    claude_model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4000
    temperature: float = 0.1
    
    # Gap Analysis Settings
    conformity_threshold: float = 0.85
    finding_keywords: list = [
        "shall", "must", "required", "mandatory", 
        "minimum", "ensure", "establish"
    ]
    
    isarp_categories: dict = {
        "ORG": "Organization and Management",
        "FLT": "Flight Operations",
        "OPS": "Operational Control",
        "MNT": "Maintenance",
        "GRH": "Ground Handling",
        "CGO": "Cargo",
        "SEC": "Security",
        "DSP": "Dangerous Goods"
    }
    
    ipm_sections: dict = {
        "1.1.1": "Documented Policies and Resource Provision",
        "6.7.1": "Implementation Evidence Requirements",
        "1.7.1": "Digital Audit Software Standards"
    }
    
    # Modern V2 Config syntax
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [
            self.data_dir, self.ism_dir, self.manuals_dir,
            self.evidence_dir, self.vector_db_path,
            self.outputs_dir, self.database_path.parent
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

# Global settings instance initialized and directories created safely outside the class
settings = Settings()
settings.create_directories()

class ISARPParser:
    """Helper class for parsing ISARP codes"""
    @staticmethod
    def parse_code(code: str) -> dict:
        parts = code.strip().split()
        if len(parts) != 2:
            raise ValueError(f"Invalid ISARP code format: {code}")
        
        category = parts[0]
        numbers = parts[1].split('.')
        if len(numbers) != 3:
            raise ValueError(f"Invalid ISARP numbering: {parts[1]}")
            
        return {
            "category": category,
            "section": int(numbers[0]),
            "subsection": int(numbers[1]),
            "item": int(numbers[2]),
            "full_code": code,
            "category_name": settings.isarp_categories.get(category, "Unknown")
        }
    
    @staticmethod
    def is_valid_code(code: str) -> bool:
        try:
            ISARPParser.parse_code(code)
            return True
        except ValueError:
            return False

class ConformityStatus:
    """Conformity status constants"""
    CONFORMITY = "Conformity"
    FINDING = "Finding"
    OBSERVATION = "Observation"
    PENDING_EVIDENCE = "Pending Evidence"
    NOT_ASSESSED = "Not Assessed"
    
    @classmethod
    def all_statuses(cls) -> list:
        return [cls.CONFORMITY, cls.FINDING, cls.OBSERVATION, cls.PENDING_EVIDENCE, cls.NOT_ASSESSED]

class EvidenceType:
    """Types of implementation evidence"""
    POLICY_DOCUMENT = "Policy Document"
    PROCEDURE = "Standard Operating Procedure"
    TRAINING_RECORD = "Training Record"
    MAINTENANCE_LOG = "Maintenance Log"
    FLIGHT_RECORD = "Flight Record"
    AUDIT_REPORT = "Audit Report"
    MEETING_MINUTES = "Meeting Minutes"
    RESOURCE_ALLOCATION = "Resource Allocation Document"
    
    @classmethod
    def all_types(cls) -> list:
        return [
            cls.POLICY_DOCUMENT, cls.PROCEDURE, cls.TRAINING_RECORD,
            cls.MAINTENANCE_LOG, cls.FLIGHT_RECORD, cls.AUDIT_REPORT,
            cls.MEETING_MINUTES, cls.RESOURCE_ALLOCATION
        ]
