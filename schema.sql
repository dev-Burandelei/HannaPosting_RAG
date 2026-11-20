
-- =========================================================
-- SOCIAL CONTENT AI
-- Modelo fÃ­sico SQLite - versÃ£o inicial 1.0
-- =========================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA busy_timeout = 5000;

-- ---------------------------------------------------------
-- 1. DOMÃNIO
-- ---------------------------------------------------------

CREATE TABLE environments (
    id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE users (
    id TEXT PRIMARY KEY NOT NULL,
    environment_id TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive')),
    created_at TEXT NOT NULL,

    UNIQUE (environment_id, id),

    FOREIGN KEY (environment_id)
        REFERENCES environments(id)
        ON DELETE RESTRICT
);

CREATE TABLE brands (
    id TEXT PRIMARY KEY NOT NULL,
    environment_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_default INTEGER NOT NULL DEFAULT 0
        CHECK (is_default IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,

    UNIQUE (environment_id, id),

    FOREIGN KEY (environment_id)
        REFERENCES environments(id)
        ON DELETE RESTRICT
);

CREATE TABLE brand_profiles (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL UNIQUE,
    target_audience TEXT,
    voice_tone TEXT,
    formality TEXT,
    preferred_length TEXT,
    emoji_policy TEXT
        CHECK (emoji_policy IS NULL OR json_valid(emoji_policy)),
    hashtag_policy TEXT
        CHECK (hashtag_policy IS NULL OR json_valid(hashtag_policy)),
    cta_guidelines TEXT,
    required_expressions TEXT
        CHECK (
            required_expressions IS NULL
            OR json_valid(required_expressions)
        ),
    forbidden_expressions TEXT
        CHECK (
            forbidden_expressions IS NULL
            OR json_valid(forbidden_expressions)
        ),
    general_guidelines TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE (brand_id, id),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT
);


CREATE TABLE brand_platform_profiles (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL,
    platform TEXT NOT NULL
        CHECK (platform IN ('instagram', 'linkedin')),
    platform_guidelines TEXT,
    preferred_formats TEXT
        CHECK (
            preferred_formats IS NULL
            OR (
                json_valid(preferred_formats)
                AND json_type(preferred_formats) = 'array'
            )
        ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE (brand_id, platform),
    UNIQUE (brand_id, id),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT
);


CREATE TABLE brand_profile_versions (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL,
    brand_profile_id TEXT NOT NULL,
    version_number INTEGER NOT NULL
        CHECK (version_number > 0),
    profile_data_json TEXT NOT NULL
        CHECK (json_valid(profile_data_json)),
    created_at TEXT NOT NULL,
    created_by TEXT,

    UNIQUE (brand_profile_id, version_number),
    UNIQUE (brand_id, id),

    FOREIGN KEY (brand_id, brand_profile_id)
        REFERENCES brand_profiles(brand_id, id)
        ON DELETE RESTRICT,

    FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE SET NULL
);

-- ---------------------------------------------------------
-- 2. CONTEÃšDO
-- ---------------------------------------------------------

CREATE TABLE content_requests (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL,
    user_id TEXT,
    brand_profile_version_id TEXT,
    profile_snapshot_json TEXT NOT NULL
    CHECK (
        json_valid(profile_snapshot_json)
        AND json_type(profile_snapshot_json) = 'object'
    ),
    operation TEXT NOT NULL
        CHECK (
            operation IN ('create', 'review', 'rewrite', 'adapt')
        ),
    briefing TEXT,
    source_text TEXT,
    platforms TEXT NOT NULL
        CHECK (json_valid(platforms)),
    research_mode TEXT NOT NULL DEFAULT 'automatic'
        CHECK (
            research_mode IN ('automatic', 'always', 'never')
        ),
    additional_instructions TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN (
        'pending',
        'processing',
        'completed',
        'failed',
        'cancelled'
    )),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE (brand_id, id),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL,

    FOREIGN KEY (brand_id, brand_profile_version_id)
        REFERENCES brand_profile_versions(brand_id, id)
        ON DELETE RESTRICT
);

CREATE TABLE posts (
    id TEXT PRIMARY KEY NOT NULL,
    request_id TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    platform TEXT NOT NULL
        CHECK (platform IN ('instagram', 'linkedin')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (
            status IN (
                'draft',
                'in_review',
                'editing',
                'discarded'
            )
        ),
    current_version_id TEXT,
    created_at TEXT NOT NULL,
updated_at TEXT NOT NULL,
discarded_at TEXT,

CHECK (
    (
        status = 'discarded'
        AND discarded_at IS NOT NULL
    )
    OR
    (
        status <> 'discarded'
        AND discarded_at IS NULL
    )
),

    UNIQUE (request_id, platform),
    UNIQUE (id, brand_id),

    FOREIGN KEY (brand_id, request_id)
        REFERENCES content_requests(brand_id, id)
        ON DELETE RESTRICT,

    -- FK circular: a versÃ£o atual precisa pertencer ao post.
    FOREIGN KEY (id, current_version_id)
        REFERENCES post_versions(post_id, id)
        ON DELETE RESTRICT
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE post_versions (
    id TEXT PRIMARY KEY NOT NULL,
    post_id TEXT NOT NULL,
    brand_id TEXT NOT NULL,
    parent_version_id TEXT,
    version_number INTEGER NOT NULL
        CHECK (version_number > 0),
    content TEXT NOT NULL,
    origin_type TEXT NOT NULL
        CHECK (
            origin_type IN (
                'generated',
                'manual_edit',
                'rewrite',
                'adapted',
                'restored'
            )
        ),
    change_description TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT,

    UNIQUE (post_id, version_number),
    UNIQUE (post_id, id),
    UNIQUE (brand_id, id),

    FOREIGN KEY (post_id, brand_id)
        REFERENCES posts(id, brand_id)
        ON DELETE RESTRICT,

    -- A versÃ£o-pai precisa pertencer ao mesmo post.
    FOREIGN KEY (post_id, parent_version_id)
        REFERENCES post_versions(post_id, id)
        ON DELETE RESTRICT,

    FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE SET NULL
);

CREATE TABLE approvals (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL,
    decision TEXT NOT NULL
        CHECK (decision IN ('approved', 'rejected')),
    comment TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY (version_id)
        REFERENCES post_versions(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (created_by)
        REFERENCES users(id)
        ON DELETE SET NULL
);

CREATE TABLE validation_runs (
    id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL,
    overall_status TEXT NOT NULL
        CHECK (
            overall_status IN ('passed', 'warning', 'failed')
        ),
    results_json TEXT NOT NULL
    CHECK (
        json_valid(results_json)
        AND json_type(results_json) = 'object'
    ),
    validator_version TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY (version_id)
        REFERENCES post_versions(id)
        ON DELETE RESTRICT
);

-- ---------------------------------------------------------
-- 3. BIBLIOTECA E RAG
-- ---------------------------------------------------------

CREATE TABLE documents (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL
        CHECK (file_size_bytes >= 0),
    content_hash TEXT NOT NULL,
    purpose TEXT NOT NULL
        CHECK (
            purpose IN ('brand_knowledge', 'writing_example')
        ),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (
            status IN (
                'active',
                'processing',
                'error',
                'deleted'
            )
        ),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,

    UNIQUE (brand_id, id),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT
);

CREATE TABLE document_processings (
    id TEXT PRIMARY KEY NOT NULL,
    document_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL
        CHECK (attempt_number > 0),
    status TEXT NOT NULL
        CHECK (
            status IN (
                'queued',
                'processing',
                'completed',
                'failed'
            )
        ),
    extracted_metadata_json TEXT
        CHECK (
            extracted_metadata_json IS NULL
            OR json_valid(extracted_metadata_json)
        ),
    error_message TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,

    UNIQUE (document_id, attempt_number),

    FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE RESTRICT
);

CREATE TABLE tags (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    is_custom INTEGER NOT NULL DEFAULT 0
        CHECK (is_custom IN (0, 1)),
    created_at TEXT NOT NULL,

    UNIQUE (brand_id, name, category),
    UNIQUE (brand_id, id),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT
);

CREATE TABLE document_tags (
    document_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    brand_id TEXT NOT NULL,

    PRIMARY KEY (document_id, tag_id),

    FOREIGN KEY (brand_id, document_id)
        REFERENCES documents(brand_id, id)
        ON DELETE RESTRICT,

    FOREIGN KEY (brand_id, tag_id)
        REFERENCES tags(brand_id, id)
        ON DELETE RESTRICT
);

CREATE TABLE post_tags (
    post_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    brand_id TEXT NOT NULL,

    PRIMARY KEY (post_id, tag_id),

    FOREIGN KEY (post_id, brand_id)
        REFERENCES posts(id, brand_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (brand_id, tag_id)
        REFERENCES tags(brand_id, id)
        ON DELETE RESTRICT
);

CREATE TABLE rag_index_records (
    id TEXT PRIMARY KEY NOT NULL,
    brand_id TEXT NOT NULL,
    document_id TEXT,
    post_version_id TEXT,
    source_type TEXT NOT NULL
        CHECK (
            source_type IN ('brand_knowledge', 'writing_example')
        ),
    collection_name TEXT NOT NULL,
    vector_ids_json TEXT NOT NULL
        CHECK (json_valid(vector_ids_json)),
    index_status TEXT NOT NULL
        CHECK (
            index_status IN (
                'pending',
                'active',
                'inactive',
                'failed',
                'deleting'
            )
        ),
    indexed_at TEXT,
    deactivated_at TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    -- Exatamente uma fonte deve ser informada.
    CHECK (
        (document_id IS NOT NULL AND post_version_id IS NULL)
        OR
        (document_id IS NULL AND post_version_id IS NOT NULL)
    ),

    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (brand_id, document_id)
        REFERENCES documents(brand_id, id)
        ON DELETE RESTRICT,

    FOREIGN KEY (brand_id, post_version_id)
        REFERENCES post_versions(brand_id, id)
        ON DELETE RESTRICT
);

-- ---------------------------------------------------------
-- 4. CONFIGURAÃ‡Ã•ES
-- ---------------------------------------------------------

CREATE TABLE provider_configs (
    id TEXT PRIMARY KEY NOT NULL,
    environment_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    operation TEXT,
    encrypted_api_key TEXT,
    parameters_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(parameters_json)),
    limits_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(limits_json)),
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE (environment_id, id),

    FOREIGN KEY (environment_id)
        REFERENCES environments(id)
        ON DELETE RESTRICT
);

-- ---------------------------------------------------------
-- 5. OPERAÃ‡Ã•ES
-- ---------------------------------------------------------


CREATE TABLE jobs (
    id TEXT PRIMARY KEY NOT NULL,
    environment_id TEXT NOT NULL,
    brand_id TEXT,
    content_request_id TEXT,
    job_type TEXT NOT NULL,
    resource_type TEXT
    CHECK (
        resource_type IS NULL
        OR resource_type IN (
            'content_request',
            'document',
            'post',
            'post_version'
        )
    ),
resource_id TEXT,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (
            status IN (
                'queued',
                'processing',
                'completed',
                'failed',
                'cancelled'
            )
        ),
    progress INTEGER NOT NULL DEFAULT 0
        CHECK (progress BETWEEN 0 AND 100),
    attempts INTEGER NOT NULL DEFAULT 0
        CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3
        CHECK (max_attempts > 0),
    worker_id TEXT,
    locked_at TEXT,
    last_heartbeat_at TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}'
        CHECK (json_valid(payload_json)),
    result_json TEXT
        CHECK (result_json IS NULL OR json_valid(result_json)),
    error_message TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    UNIQUE (environment_id, id),

    -- Uma solicitaÃ§Ã£o vinculada precisa ter uma marca.
    CHECK (
        content_request_id IS NULL
        OR brand_id IS NOT NULL
    ),

    -- As referÃªncias explÃ­cita e polimÃ³rfica
    -- devem apontar para a mesma solicitaÃ§Ã£o.
    CHECK (
        (
            content_request_id IS NULL
            AND resource_type IS NOT 'content_request'
        )
        OR
        (
            content_request_id IS NOT NULL
            AND resource_type = 'content_request'
            AND resource_id = content_request_id
        )
    ),

     -- Um recurso associado exige tipo, ID e marca.
    -- Sem recurso, tipo e ID devem ser NULL.
    CHECK (
        (
            resource_type IS NULL
            AND resource_id IS NULL
        )
        OR
        (
            resource_type IS NOT NULL
            AND resource_id IS NOT NULL
            AND brand_id IS NOT NULL
        )
    ),

    FOREIGN KEY (environment_id)
        REFERENCES environments(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (environment_id, brand_id)
        REFERENCES brands(environment_id, id)
        ON DELETE RESTRICT,

    FOREIGN KEY (brand_id, content_request_id)
        REFERENCES content_requests(brand_id, id)
        ON DELETE RESTRICT
);



CREATE TABLE usage_logs (
    id TEXT PRIMARY KEY NOT NULL,
    environment_id TEXT NOT NULL,
    provider_config_id TEXT NOT NULL,
    job_id TEXT,
    brand_id TEXT,
    operation TEXT NOT NULL,

    input_tokens INTEGER NOT NULL DEFAULT 0
        CHECK (input_tokens >= 0),

    output_tokens INTEGER NOT NULL DEFAULT 0
        CHECK (output_tokens >= 0),

    estimated_cost NUMERIC
        CHECK (estimated_cost IS NULL OR estimated_cost >= 0),

    currency TEXT
        CHECK (
            currency IS NULL
            OR length(currency) = 3
        ),

    latency_ms INTEGER
        CHECK (latency_ms IS NULL OR latency_ms >= 0),

    status TEXT NOT NULL,
    request_id TEXT,
    created_at TEXT NOT NULL,

    FOREIGN KEY (environment_id)
        REFERENCES environments(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (environment_id, provider_config_id)
        REFERENCES provider_configs(environment_id, id)
        ON DELETE RESTRICT,

    FOREIGN KEY (environment_id, job_id)
        REFERENCES jobs(environment_id, id)
        ON DELETE NO ACTION,

    FOREIGN KEY (environment_id, brand_id)
        REFERENCES brands(environment_id, id)
        ON DELETE RESTRICT
);


CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY NOT NULL,
    environment_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details_json TEXT
        CHECK (
            details_json IS NULL
            OR json_valid(details_json)
        ),
    created_at TEXT NOT NULL,

    FOREIGN KEY (environment_id)
        REFERENCES environments(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (environment_id, user_id)
        REFERENCES users(environment_id, id)
        ON DELETE NO ACTION
);

-- ---------------------------------------------------------
-- 6. ÃNDICES
-- ---------------------------------------------------------

CREATE UNIQUE INDEX uq_brands_default_per_environment
ON brands(environment_id)
WHERE is_default = 1 AND deleted_at IS NULL;

CREATE UNIQUE INDEX uq_users_email_per_environment
ON users(environment_id, email)
WHERE email IS NOT NULL;

CREATE INDEX ix_brands_environment_active
ON brands(environment_id, is_active);

CREATE INDEX ix_content_requests_brand_created
ON content_requests(brand_id, created_at);

CREATE INDEX ix_approvals_version_created
ON approvals(version_id, created_at DESC);

CREATE INDEX ix_validation_runs_version_created
ON validation_runs(version_id, created_at DESC);

CREATE INDEX ix_documents_brand_status_purpose
ON documents(brand_id, status, purpose);

CREATE INDEX ix_document_processings_document_attempt
ON document_processings(document_id, attempt_number);

CREATE INDEX ix_tags_brand_category
ON tags(brand_id, category);

CREATE INDEX ix_rag_brand_source_status
ON rag_index_records(brand_id, source_type, index_status);

CREATE INDEX ix_jobs_status_created
ON jobs(status, created_at);

CREATE INDEX ix_jobs_environment_status
ON jobs(environment_id, status);

CREATE INDEX ix_usage_brand_created
ON usage_logs(brand_id, created_at);

CREATE INDEX ix_usage_provider_created
ON usage_logs(provider_config_id, created_at);

CREATE INDEX ix_audit_environment_created
ON audit_logs(environment_id, created_at);

-- Somente um registro ativo por fonte e coleÃ§Ã£o.
CREATE UNIQUE INDEX uq_rag_active_document_collection
ON rag_index_records(brand_id, document_id, collection_name)
WHERE document_id IS NOT NULL AND index_status = 'active';

CREATE UNIQUE INDEX uq_rag_active_version_collection
ON rag_index_records(brand_id, post_version_id, collection_name)
WHERE post_version_id IS NOT NULL AND index_status = 'active';

-- RecuperaÃ§Ã£o eficiente de jobs pendentes.
CREATE INDEX ix_jobs_queue
ON jobs(created_at)
WHERE status = 'queued';

-- RecuperaÃ§Ã£o de execuÃ§Ãµes interrompidas.
CREATE INDEX ix_jobs_processing_heartbeat
ON jobs(last_heartbeat_at)
WHERE status = 'processing';

-- Ãndice para a nova referÃªncia
CREATE INDEX ix_jobs_brand_content_request
ON jobs(brand_id, content_request_id)
WHERE content_request_id IS NOT NULL;

-- ---------------------------------------------------------
-- 7. Triggers
-- ---------------------------------------------------------


CREATE TRIGGER trg_users_preserve_audit_logs
BEFORE DELETE ON users
FOR EACH ROW
BEGIN
    UPDATE audit_logs
    SET user_id = NULL
    WHERE environment_id = OLD.environment_id
      AND user_id = OLD.id;
END;


CREATE TRIGGER trg_jobs_preserve_usage_logs
BEFORE DELETE ON jobs
FOR EACH ROW
BEGIN
    UPDATE usage_logs
    SET job_id = NULL
    WHERE environment_id = OLD.environment_id
      AND job_id = OLD.id;
END;

CREATE TRIGGER trg_content_requests_snapshot_immutable
BEFORE UPDATE OF profile_snapshot_json
ON content_requests
FOR EACH ROW
WHEN OLD.profile_snapshot_json IS NOT NEW.profile_snapshot_json
BEGIN
    SELECT RAISE(
        ABORT,
        'O snapshot da solicitacao e imutavel'
    );
END;


-- ---------------------------------------------------------
-- 5. INTEGRIDADE DOS USUÃRIOS RESPONSÃVEIS
-- ---------------------------------------------------------

-- BRAND PROFILE VERSIONS: INSERT
CREATE TRIGGER trg_profile_versions_created_by_environment_insert
BEFORE INSERT ON brand_profile_versions
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM brands b
    JOIN users u
        ON u.environment_id = b.environment_id
    WHERE b.id = NEW.brand_id
      AND u.id = NEW.created_by
)
BEGIN
    SELECT RAISE(
        ABORT,
        'O usuario criador deve pertencer ao mesmo ambiente da marca'
    );
END;

-- BRAND PROFILE VERSIONS: UPDATE
CREATE TRIGGER trg_profile_versions_created_by_environment_update
BEFORE UPDATE ON brand_profile_versions
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM brands b
    JOIN users u
        ON u.environment_id = b.environment_id
    WHERE b.id = NEW.brand_id
      AND u.id = NEW.created_by
)
BEGIN
    SELECT RAISE(
        ABORT,
        'O usuario criador deve pertencer ao mesmo ambiente da marca'
    );
END;

-- POST VERSIONS: INSERT
CREATE TRIGGER trg_post_versions_created_by_environment_insert
BEFORE INSERT ON post_versions
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM posts p
    JOIN brands b
        ON b.id = p.brand_id
    JOIN users u
        ON u.environment_id = b.environment_id
    WHERE p.id = NEW.post_id
      AND p.brand_id = NEW.brand_id
      AND u.id = NEW.created_by
)
BEGIN
    SELECT RAISE(
        ABORT,
        'O usuario criador deve pertencer ao mesmo ambiente do post'
    );
END;

-- POST VERSIONS: UPDATE
CREATE TRIGGER trg_post_versions_created_by_environment_update
BEFORE UPDATE ON post_versions
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM posts p
    JOIN brands b
        ON b.id = p.brand_id
    JOIN users u
        ON u.environment_id = b.environment_id
    WHERE p.id = NEW.post_id
      AND p.brand_id = NEW.brand_id
      AND u.id = NEW.created_by
)
BEGIN
    SELECT RAISE(
        ABORT,
        'O usuario criador deve pertencer ao mesmo ambiente do post'
    );
END;

-- APPROVALS: INSERT
CREATE TRIGGER trg_approvals_created_by_environment_insert
BEFORE INSERT ON approvals
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM post_versions pv
    JOIN posts p
        ON p.id = pv.post_id
       AND p.brand_id = pv.brand_id
    JOIN brands b
        ON b.id = p.brand_id
    JOIN users u
        ON u.environment_id = b.environment_id
    WHERE pv.id = NEW.version_id
      AND u.id = NEW.created_by
)
BEGIN
    SELECT RAISE(
        ABORT,
        'O usuario responsavel deve pertencer ao mesmo ambiente do post'
    );
END;

-- APPROVALS: UPDATE
CREATE TRIGGER trg_approvals_created_by_environment_update
BEFORE UPDATE ON approvals
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM post_versions pv
    JOIN posts p
        ON p.id = pv.post_id
       AND p.brand_id = pv.brand_id
    JOIN brands b
        ON b.id = p.brand_id
    JOIN users u
        ON u.environment_id = b.environment_id
    WHERE pv.id = NEW.version_id
      AND u.id = NEW.created_by
)
BEGIN
    SELECT RAISE(
        ABORT,
        'O usuario responsavel deve pertencer ao mesmo ambiente do post'
    );
END;

