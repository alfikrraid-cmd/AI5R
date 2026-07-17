CREATE TABLE IF NOT EXISTS public.mapping_profile (
    mapping_profile_id TEXT PRIMARY KEY NOT NULL,
    profile_name TEXT NOT NULL,
    workbook_type TEXT NOT NULL,
    customer TEXT,
    description TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT mapping_profile_workbook_type_check
        CHECK (workbook_type IN (
            'PUMP_MASTER', 'MECHANICAL_SEAL_MASTER', 'SEAL_STOCK', 'SEAL_INTERCHANGE',
            'PUMP_COMPATIBILITY', 'INSTALLATION_HISTORY', 'MAINTENANCE_HISTORY',
            'ENGINEER_MASTER', 'CUSTOMER_MASTER', 'VENDOR_MASTER', 'BILL_OF_MATERIAL'
        ))
);
