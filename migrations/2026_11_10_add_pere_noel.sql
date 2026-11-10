-- LaHotte: ajout du rôle Père Noël
ALTER TABLE familles
ADD COLUMN IF NOT EXISTS pere_noel_id INTEGER NULL
REFERENCES users(id) ON DELETE SET NULL;
