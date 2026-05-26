-- SQL Schema for VodaCash SMS Monitor Licensing and Subscription System
-- Copy and run this script in your Supabase SQL Editor.

-- Enable Row Level Security (optional, or configure public access policies)
-- For demonstration/easy access, you can disable RLS or add public policies.

-- Create table: coupons
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    discount_percent REAL CHECK (discount_percent >= 0 AND discount_percent <= 100) DEFAULT 0,
    trial_days INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    max_uses INT DEFAULT 1,
    uses_count INT DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Create table: license_keys
CREATE TABLE IF NOT EXISTS license_keys (
    key TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    client_phone TEXT,
    type TEXT CHECK (type IN ('TRIAL', 'MONTHLY', 'YEARLY')) DEFAULT 'MONTHLY',
    status TEXT CHECK (status IN ('ACTIVE', 'EXPIRED', 'SUSPENDED')) DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    mac_address TEXT,
    coupon_used TEXT REFERENCES coupons(code) ON DELETE SET NULL
);

-- Create table: admin_settings
CREATE TABLE IF NOT EXISTS admin_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Insert some default coupons
INSERT INTO coupons (code, discount_percent, trial_days, is_active, max_uses, uses_count, expires_at)
VALUES 
('WELCOME50', 50.0, 0, TRUE, 100, 0, timezone('utc'::text, now() + interval '1 year')),
('FREE3TRIAL', 0.0, 3, TRUE, 1000, 0, timezone('utc'::text, now() + interval '1 year')),
('SUPER90', 90.0, 0, TRUE, 10, 0, timezone('utc'::text, now() + interval '1 year'))
ON CONFLICT (code) DO NOTHING;

-- Insert default admin settings
INSERT INTO admin_settings (key, value)
VALUES 
('trial_duration_days', '3'),
('allow_self_trial', 'true'),
('admin_password', 'admin123')
ON CONFLICT (key) DO NOTHING;
