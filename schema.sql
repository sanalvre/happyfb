CREATE TABLE IF NOT EXISTS ads (
  ad_id TEXT PRIMARY KEY,
  competitor TEXT NOT NULL,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL,
  status TEXT NOT NULL,
  creative_body TEXT,
  creative_title TEXT,
  cta_text TEXT,
  snapshot_url TEXT,
  platforms TEXT,
  start_date DATE,
  end_date DATE,
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ads_competitor ON ads(competitor);
CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status);
CREATE INDEX IF NOT EXISTS idx_ads_last_seen ON ads(last_seen);

CREATE VIRTUAL TABLE IF NOT EXISTS ads_fts USING fts5(
  creative_body, creative_title, cta_text,
  content='ads', content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS ads_ai AFTER INSERT ON ads BEGIN
  INSERT INTO ads_fts(rowid, creative_body, creative_title, cta_text)
  VALUES (new.rowid, new.creative_body, new.creative_title, new.cta_text);
END;

CREATE TRIGGER IF NOT EXISTS ads_ad AFTER DELETE ON ads BEGIN
  INSERT INTO ads_fts(ads_fts, rowid, creative_body, creative_title, cta_text)
  VALUES ('delete', old.rowid, old.creative_body, old.creative_title, old.cta_text);
END;

CREATE TRIGGER IF NOT EXISTS ads_au AFTER UPDATE ON ads BEGIN
  INSERT INTO ads_fts(ads_fts, rowid, creative_body, creative_title, cta_text)
  VALUES ('delete', old.rowid, old.creative_body, old.creative_title, old.cta_text);
  INSERT INTO ads_fts(rowid, creative_body, creative_title, cta_text)
  VALUES (new.rowid, new.creative_body, new.creative_title, new.cta_text);
END;

CREATE TABLE IF NOT EXISTS weekly_snapshots (
  week_of DATE NOT NULL,
  competitor TEXT NOT NULL,
  active_count INTEGER,
  new_count INTEGER,
  ended_count INTEGER,
  themes_json TEXT,
  shift_summary TEXT,
  threat_score INTEGER,
  headline TEXT,
  PRIMARY KEY (week_of, competitor)
);

CREATE TABLE IF NOT EXISTS contractors (
  page_id TEXT PRIMARY KEY,
  page_name TEXT NOT NULL,
  trade TEXT NOT NULL,
  first_seen DATE NOT NULL,
  last_seen DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'new',
  website TEXT,
  phone TEXT,
  email TEXT,
  city TEXT,
  state TEXT,
  ad_count INTEGER DEFAULT 0,
  relevance_score INTEGER,
  serves_multifamily BOOLEAN,
  company_size_signal TEXT,
  sample_ad_text TEXT,
  notes TEXT,
  raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_contractors_trade ON contractors(trade);
CREATE INDEX IF NOT EXISTS idx_contractors_status ON contractors(status);

CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  status TEXT,
  competitors_processed INTEGER,
  competitors_failed INTEGER,
  contractors_found INTEGER,
  error_log TEXT
);
