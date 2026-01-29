-- Migration: Add users, user_companies, and system_logs tables
-- For secure multi-user access via Cloudflare Tunnel

-- =====================================================
-- USERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('admin', 'accounting', 'user')),
    is_active BOOLEAN DEFAULT TRUE,
    is_locked BOOLEAN DEFAULT FALSE,
    failed_login_attempts INTEGER DEFAULT 0,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active);

-- =====================================================
-- USER_COMPANIES TABLE (Many-to-Many)
-- =====================================================
CREATE TABLE IF NOT EXISTS user_companies (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    access_level VARCHAR(20) DEFAULT 'read' CHECK (access_level IN ('read', 'write', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, company_id)
);

CREATE INDEX IF NOT EXISTS idx_user_companies_user_id ON user_companies (user_id);
CREATE INDEX IF NOT EXISTS idx_user_companies_company_id ON user_companies (company_id);

-- =====================================================
-- SYSTEM_LOGS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(10) NOT NULL,
    logger VARCHAR(100),
    message TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    request_path VARCHAR(500),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs (level);
CREATE INDEX IF NOT EXISTS idx_system_logs_logger ON system_logs (logger);

-- =====================================================
-- UPDATE TRIGGER FOR USERS
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
