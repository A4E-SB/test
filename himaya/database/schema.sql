-- ============================================================================
-- Himaya SQLite schema  (single local file: himaya.db)
-- Schema version is tracked with PRAGMA user_version (see db.py migrations).
--   v1: customers, orders, blacklist, inquiries, fake_screenshots,
--       templates, settings
--   v2: products catalog, orders.product_id + orders.deposit,
--       detector_feedback (adaptive fake-receipt scoring)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Customers: the seller's contacts with an auto-computed trust score.
-- trust_score: 0..100, tags: comma-separated auto tags (ghost, scammer, ...)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL,               -- normalized: 0XXXXXXXXX
    wilaya      TEXT DEFAULT '',
    address     TEXT DEFAULT '',
    trust_score INTEGER NOT NULL DEFAULT 50,
    tags        TEXT DEFAULT '',             -- 'trusted,new,ghost,...'
    notes       TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);

-- ---------------------------------------------------------------------------
-- Products catalog: cost/sale price + stock. Orders link to a product;
-- real profit = sale - cost - shipping. Stock follows order statuses.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    cost_price REAL NOT NULL DEFAULT 0,
    sale_price REAL NOT NULL DEFAULT 0,
    quantity   INTEGER NOT NULL DEFAULT 0,
    low_stock  INTEGER NOT NULL DEFAULT 5,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_name ON products(name);

-- ---------------------------------------------------------------------------
-- Orders: COD sales. date = creation date (YYYY-MM-DD).
-- product_id links to the catalog (NULL = free-text product, kept for
-- backwards compatibility). deposit = acompte already received (DA);
-- the label prints the REMAINING amount to collect.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    product_id     INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product        TEXT NOT NULL,
    price          REAL NOT NULL DEFAULT 0,
    deposit        REAL NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'pending',
    delivery_method TEXT DEFAULT '',
    wilaya         TEXT DEFAULT '',
    date           TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    shipping_cost  REAL NOT NULL DEFAULT 0,
    notes          TEXT DEFAULT '',
    shipped_at     TEXT DEFAULT '',
    delivered_at   TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date    ON orders(date);
-- v1.1.4: per-wilaya stats/filters column (present since v1).
-- NOTE: idx_orders_product is created AFTER migrations in db.py — the
-- product_id column only exists once a v1 database has been upgraded.
CREATE INDEX IF NOT EXISTS idx_orders_wilaya ON orders(wilaya);

-- ---------------------------------------------------------------------------
-- Blacklist: known bad phone numbers (shared between sellers via .hma files).
-- severity: 1=suspect, 2=dangerous, 3=confirmed scammer
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blacklist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    phone         TEXT NOT NULL,
    reason        TEXT DEFAULT '',
    evidence_path TEXT DEFAULT '',
    reported_date TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    severity      INTEGER NOT NULL DEFAULT 2
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_blacklist_phone ON blacklist(phone);

-- ---------------------------------------------------------------------------
-- Inquiries: every contact that did (or did not) convert into an order.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inquiries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    date        TEXT NOT NULL DEFAULT (date('now', 'localtime')),
    platform    TEXT DEFAULT 'Messenger',
    converted   INTEGER NOT NULL DEFAULT 0,   -- 0/1
    notes       TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_inquiries_customer ON inquiries(customer_id);

-- ---------------------------------------------------------------------------
-- Fake screenshots: hashes of analysed BaridiMob receipts (also exchanged
-- in .hma v2 files so known fakes spread between sellers).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fake_screenshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    image_hash TEXT NOT NULL,
    phone      TEXT DEFAULT '',
    date       TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    details    TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_fake_hash ON fake_screenshots(image_hash);

-- ---------------------------------------------------------------------------
-- Detector feedback: the seller confirms/corrects each verdict; the local
-- scoring adapts (weights per reason drift towards what the human says).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS detector_feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    reason       TEXT NOT NULL,               -- reason code, e.g. ela_localized_edit
    user_verdict TEXT NOT NULL,               -- 'real' | 'fake'
    date         TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_feedback_reason ON detector_feedback(reason);

-- ---------------------------------------------------------------------------
-- Reply templates (Arabic / French) for common time-waster situations.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS templates (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    text_ar  TEXT DEFAULT '',
    text_fr  TEXT DEFAULT ''
);

-- ---------------------------------------------------------------------------
-- Key/value settings (language, CCP info, delivery defaults, ...).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT DEFAULT ''
);

-- v1.7.10: dashboard alert lookup. The flagged-customer scan is
-- 'tags LIKE %scammer% OR trust_score < 25' — without this index the
-- ORDER BY trust_score LIMIT 5 branch degrades to a full table scan
-- (measured 65-130ms on large catalogs on weak machines).
CREATE INDEX IF NOT EXISTS idx_customers_trust
    ON customers(trust_score);

-- v1.7.11: PARTIAL index for the flagged-customer branch of the alert
-- query. A leading-wildcard LIKE can never seek a normal index, but a
-- partial index pre-selects only the matching rows: the scan drops from
-- the whole table to a handful of entries (measured 11.5ms -> 0.006ms
-- per query on 50k rows) and it also satisfies the ORDER BY.
CREATE INDEX IF NOT EXISTS idx_customers_scammer
    ON customers(trust_score)
    WHERE (',' || tags || ',') LIKE '%,scammer,%';
