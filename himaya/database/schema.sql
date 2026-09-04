-- ============================================================================
-- Himaya SQLite schema  (single local file: himaya.db)
-- Schema version is tracked with PRAGMA user_version (see db.py migrations).
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
-- Orders: COD sales. date = creation date (YYYY-MM-DD).
-- shipped_at / delivered_at are set when the status changes, used by the
-- dashboard "shipments today" counters.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id    INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    product        TEXT NOT NULL,
    price          REAL NOT NULL DEFAULT 0,
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
-- Used by the Time-Waster Tracker to compute conversion rates.
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
-- Fake screenshots: hashes of analysed BaridiMob receipts.
-- image_hash = perceptual hash (dHash) for near-duplicate detection,
-- details    = JSON dump of the full analysis (reasons, verdict, ocr data).
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
