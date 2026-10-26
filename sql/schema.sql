SET ROLE pm10;
CREATE TABLE IF NOT EXISTS pipeline_run (
    run_id uuid PRIMARY KEY,
    dataset text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL CHECK (status IN ('running','succeeded','failed')),
    source_sha256 text NOT NULL,
    recipe_sha256 text NOT NULL,
    metrics jsonb,
    error text
);
CREATE TABLE IF NOT EXISTS active_dataset (
    dataset text PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES pipeline_run,
    source_sha256 text NOT NULL,
    recipe_sha256 text NOT NULL,
    result_sha256 text NOT NULL,
    row_count bigint NOT NULL CHECK (row_count > 0)
);
CREATE TABLE IF NOT EXISTS daily_feature (
    dataset text NOT NULL,
    state text NOT NULL,
    county text NOT NULL,
    site text NOT NULL,
    parameter text NOT NULL CHECK (parameter = '81102'),
    poc text NOT NULL,
    day date NOT NULL,
    n_observed integer NOT NULL CHECK (n_observed BETWEEN 1 AND 24),
    n_usable integer NOT NULL CHECK (n_usable BETWEEN 0 AND n_observed),
    n_review integer NOT NULL CHECK (n_review >= 0),
    n_negative integer NOT NULL CHECK (n_negative >= 0),
    n_flagged integer NOT NULL CHECK (n_flagged >= 0),
    n_events integer NOT NULL CHECK (n_events >= 0),
    n_methods integer NOT NULL CHECK (n_methods > 0),
    mean_observed double precision,
    mean_pm10 double precision,
    min_pm10 double precision,
    max_pm10 double precision,
    eligible boolean NOT NULL,
    run_id uuid NOT NULL REFERENCES pipeline_run,
    PRIMARY KEY (dataset,state,county,site,parameter,poc,day),
    CHECK ((n_usable = 0 AND mean_pm10 IS NULL AND min_pm10 IS NULL AND max_pm10 IS NULL)
        OR (n_usable > 0 AND min_pm10 <= mean_pm10 + 1e-9 AND mean_pm10 <= max_pm10 + 1e-9))
);
CREATE INDEX IF NOT EXISTS daily_feature_day ON daily_feature(day);
CREATE OR REPLACE VIEW model_candidates AS
 SELECT f.*, r.source_sha256, r.recipe_sha256
 FROM daily_feature f JOIN pipeline_run r USING (run_id)
 WHERE eligible;
COMMENT ON VIEW model_candidates IS 'Candidate daily inputs, not certified regulatory means or a trained model. Inspect quality counts before modeling.';
