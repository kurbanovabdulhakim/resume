-- Canonical SQLite Schema for Resume Job Tracker & Document Generator
-- Single Source of Truth (SSOT) for positions.db

PRAGMA foreign_keys = ON;

-- Vacancies table: records every monitored or targeted job posting
CREATE TABLE IF NOT EXISTS vacancies (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    url TEXT,
    source TEXT DEFAULT 'hh.uz',
    tier INTEGER DEFAULT 2,
    sector TEXT DEFAULT 'Finance',
    salary_min INTEGER,
    salary_max INTEGER,
    salary_text TEXT,
    published_at TEXT,
    scraped_at TEXT,
    is_active INTEGER DEFAULT 1
);

-- Applications table: tracks application progress and interview stages
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'applied' CHECK(status IN ('applied', 'viewed', 'invited', 'interview', 'offer', 'rejected', 'declined')),
    applied_at TEXT,
    cv_variant TEXT,
    cover_letter_sent INTEGER DEFAULT 0,
    pdf_sent_in_chat INTEGER DEFAULT 0,
    notes TEXT,
    last_updated TEXT,
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE
);

-- Documents table: records generated tailored PDFs and Markdown assets
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK(doc_type IN ('cover_letter', 'cv')),
    variant_used TEXT,
    file_path TEXT NOT NULL,
    generated_at TEXT,
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(id) ON DELETE CASCADE
);

-- Indexes for lightning-fast queries and filtering
CREATE INDEX IF NOT EXISTS idx_vacancies_tier ON vacancies(tier);
CREATE INDEX IF NOT EXISTS idx_vacancies_sector ON vacancies(sector);
CREATE INDEX IF NOT EXISTS idx_vacancies_is_active ON vacancies(is_active);
CREATE INDEX IF NOT EXISTS idx_applications_vacancy_id ON applications(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_documents_vacancy_id ON documents(vacancy_id);
