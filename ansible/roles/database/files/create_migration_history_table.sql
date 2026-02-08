-- マイグレーション履歴テーブルの作成
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    postgres_version VARCHAR(20),
    postgres_image_tag VARCHAR(50),
    postgres_base_image VARCHAR(100),
    applied_by VARCHAR(100),
    execution_time_ms INTEGER
);
CREATE INDEX IF NOT EXISTS idx_migrations_applied_at ON schema_migrations(applied_at DESC);
CREATE INDEX IF NOT EXISTS idx_migrations_postgres_version ON schema_migrations(postgres_version);
