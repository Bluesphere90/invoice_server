-- Migration: Add cron_schedule table for admin-configurable collector schedule
-- This table stores the cron schedule that the system reads at runtime

CREATE TABLE IF NOT EXISTS cron_schedule (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE DEFAULT 'collector',
    cron_expression VARCHAR(100) NOT NULL DEFAULT '0 3,15,21 * * *',
    description TEXT DEFAULT 'Lịch chạy thu thập hóa đơn tự động',
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Insert default schedule
INSERT INTO cron_schedule (name, cron_expression, description)
VALUES ('collector', '0 3,15,21 * * *', 'Lịch chạy thu thập hóa đơn tự động')
ON CONFLICT (name) DO NOTHING;
