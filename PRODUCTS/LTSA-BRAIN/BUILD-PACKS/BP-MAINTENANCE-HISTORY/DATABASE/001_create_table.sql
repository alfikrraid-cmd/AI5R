-- maintenance_history.asset_code / asset_type mirrors the same documented,
-- intentional polymorphic reference used by work_order (see
-- BP-WORK-ORDER/DATABASE/001_create_table.sql) -- not a foreign key, for the
-- same reason. work_order_code is likewise not FK-enforced, to keep this
-- table independently queryable even if a work order record is absent
-- (e.g. maintenance performed without a formal work order).
CREATE TABLE IF NOT EXISTS public.maintenance_history (
    maintenance_record_code TEXT PRIMARY KEY NOT NULL,
    work_order_code TEXT,
    asset_code TEXT,
    asset_type TEXT,
    action_taken TEXT NOT NULL,
    performed_by TEXT,
    performed_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
