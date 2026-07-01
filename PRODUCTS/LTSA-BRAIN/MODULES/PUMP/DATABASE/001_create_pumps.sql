CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS ltsa_pumps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_number VARCHAR(100) NOT NULL UNIQUE,
    area VARCHAR(100) NOT NULL,
    location VARCHAR(150),
    pump_type VARCHAR(100),
    api_plan VARCHAR(50),
    seal_type VARCHAR(150),
    status VARCHAR(50) DEFAULT 'UNKNOWN',
    manufacturer VARCHAR(150),
    model VARCHAR(150),
    drawing_ref TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ltsa_pumps_tag_number ON ltsa_pumps(tag_number);
CREATE INDEX IF NOT EXISTS idx_ltsa_pumps_area ON ltsa_pumps(area);
CREATE INDEX IF NOT EXISTS idx_ltsa_pumps_status ON ltsa_pumps(status);
