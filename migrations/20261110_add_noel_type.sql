ALTER TABLE familles ADD COLUMN IF NOT EXISTS noel_type VARCHAR(20) NOT NULL DEFAULT 'pere_noel';

ALTER TABLE familles ADD CONSTRAINT familles_noel_type_check CHECK (noel_type IN ('pere_noel', 'mere_noel'));