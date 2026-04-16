-- Sial-Compliance-Pro Database Schema
-- SQLite database for storing compliance analysis results and metadata

-- ISARP Requirements table
CREATE TABLE IF NOT EXISTS isarps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    requirement_text TEXT NOT NULL,
    guidance_text TEXT,
    page_number INTEGER,
    source_file TEXT,
    evidence_required TEXT, -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Airline Manuals metadata
CREATE TABLE IF NOT EXISTS manuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    manual_type TEXT NOT NULL,
    manual_name TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pages INTEGER,
    chunks_count INTEGER,
    file_path TEXT
);

-- Gap Analysis Results
CREATE TABLE IF NOT EXISTS gap_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isarp_id INTEGER NOT NULL,
    isarp_code TEXT NOT NULL,
    conformity_status TEXT NOT NULL,
    confidence REAL,
    documentation_gap TEXT,
    implementation_gap TEXT,
    manual_references TEXT, -- JSON array
    evidence_required TEXT, -- JSON array
    recommended_actions TEXT, -- JSON array
    reasoning TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyst TEXT DEFAULT 'Claude AI',
    FOREIGN KEY (isarp_id) REFERENCES isarps(id)
);

-- Evidence Documents
CREATE TABLE IF NOT EXISTS evidence_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isarp_id INTEGER NOT NULL,
    isarp_code TEXT NOT NULL,
    filename TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    file_path TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validation_status TEXT,
    validation_result TEXT, -- JSON
    is_valid BOOLEAN,
    FOREIGN KEY (isarp_id) REFERENCES isarps(id)
);

-- Audit Trail
CREATE TABLE IF NOT EXISTS audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    description TEXT,
    user_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON
);

-- Analysis Sessions
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    isarps_analyzed INTEGER,
    conformity_count INTEGER,
    findings_count INTEGER,
    observations_count INTEGER,
    status TEXT DEFAULT 'IN_PROGRESS'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_isarps_code ON isarps(code);
CREATE INDEX IF NOT EXISTS idx_isarps_category ON isarps(category);
CREATE INDEX IF NOT EXISTS idx_gap_results_status ON gap_analysis_results(conformity_status);
CREATE INDEX IF NOT EXISTS idx_gap_results_isarp ON gap_analysis_results(isarp_code);
CREATE INDEX IF NOT EXISTS idx_evidence_isarp ON evidence_documents(isarp_code);

-- Create views for reporting
CREATE VIEW IF NOT EXISTS v_compliance_summary AS
SELECT 
    i.category,
    COUNT(*) as total_isarps,
    SUM(CASE WHEN g.conformity_status = 'Conformity' THEN 1 ELSE 0 END) as conformity_count,
    SUM(CASE WHEN g.conformity_status = 'Finding' THEN 1 ELSE 0 END) as findings_count,
    SUM(CASE WHEN g.conformity_status = 'Observation' THEN 1 ELSE 0 END) as observations_count,
    SUM(CASE WHEN g.conformity_status = 'Pending Evidence' THEN 1 ELSE 0 END) as pending_count
FROM isarps i
LEFT JOIN gap_analysis_results g ON i.id = g.isarp_id
GROUP BY i.category;

CREATE VIEW IF NOT EXISTS v_evidence_status AS
SELECT 
    i.code,
    i.title,
    i.category,
    COUNT(e.id) as evidence_count,
    SUM(CASE WHEN e.is_valid = 1 THEN 1 ELSE 0 END) as valid_evidence_count,
    g.conformity_status
FROM isarps i
LEFT JOIN evidence_documents e ON i.id = e.isarp_id
LEFT JOIN gap_analysis_results g ON i.id = g.isarp_id
GROUP BY i.id;
