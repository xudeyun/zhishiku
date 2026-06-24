-- ===========================================
-- 在 Supabase SQL Editor 中运行此脚本
-- ===========================================

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 模块表（种子数据）
CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    description TEXT,
    sort_order INT DEFAULT 0
);

INSERT INTO modules (id, name, icon, description, sort_order) VALUES
    ('accounting', '核算', '📊', '会计核算相关知识', 1),
    ('tax', '税务', '🧾', '税务法规与实务知识', 2),
    ('other', '其他', '📁', '其他综合知识', 3)
ON CONFLICT (id) DO NOTHING;

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    module_id TEXT NOT NULL REFERENCES modules(id),
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    title TEXT,
    status TEXT DEFAULT 'processing',
    file_content TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 知识表
CREATE TABLE IF NOT EXISTS knowledge (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    module_id TEXT NOT NULL REFERENCES modules(id),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 分块表（含向量）
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    module_id TEXT NOT NULL REFERENCES modules(id),
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    page_number INT,
    section_title TEXT,
    sheet_name TEXT,
    row_number INT,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 向量索引
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_chunks_module ON chunks(module_id);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_type, source_id);

-- 对话表
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    module_id TEXT NOT NULL REFERENCES modules(id),
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    citations JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 关闭 RLS（个人使用，后续可按需开启）
ALTER TABLE modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all" ON modules;
DROP POLICY IF EXISTS "Allow all" ON documents;
DROP POLICY IF EXISTS "Allow all" ON knowledge;
DROP POLICY IF EXISTS "Allow all" ON chunks;
DROP POLICY IF EXISTS "Allow all" ON conversations;
DROP POLICY IF EXISTS "Allow all" ON messages;

CREATE POLICY "Allow all" ON modules FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON knowledge FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON chunks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON messages FOR ALL USING (true) WITH CHECK (true);
