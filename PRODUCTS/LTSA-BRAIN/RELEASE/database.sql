-- Auto Generated

CREATE TABLE IF NOT EXISTS ltsa_customers (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_pumps (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_seals (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_seal_stocks (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_seal_pump_compatibilitys (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_seal_interchange_compatibilitys (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_seal_engineering_documents (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_knowledge_source_registrys (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_workbooks (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_worksheets (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_worksheet_tables (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_mapping_profiles (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_column_mappings (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_acquisition_jobs (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_pdf_documents (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_pdf_metadatas (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_document_classifications (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_pdf_acquisition_jobs (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_engineering_medias (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_media_metadatas (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_media_classifications (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_media_acquisition_jobs (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_assets (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_soot_blowers (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_work_orders (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_maintenance_historys (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_dashboards (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_ai_assistants (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_inspections (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_maintenances (
    id SERIAL PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS ltsa_organizations (
    id SERIAL PRIMARY KEY
);
