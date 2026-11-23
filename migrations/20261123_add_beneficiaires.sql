-- Profils bénéficiaires sans compte utilisateur
-- À exécuter une seule fois dans Supabase SQL Editor avant le déploiement du backend.

CREATE TABLE IF NOT EXISTS beneficiaires (
    id SERIAL PRIMARY KEY,
    famille_id INTEGER NOT NULL REFERENCES familles(id) ON DELETE CASCADE,
    nom VARCHAR(100) NOT NULL,
    created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_beneficiaires_famille_id ON beneficiaires(famille_id);

CREATE TABLE IF NOT EXISTS beneficiaire_responsables (
    beneficiaire_id INTEGER NOT NULL REFERENCES beneficiaires(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (beneficiaire_id, user_id)
);

ALTER TABLE cadeaux
    ADD COLUMN IF NOT EXISTS beneficiaire_profil_id INTEGER
    REFERENCES beneficiaires(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_cadeaux_beneficiaire_profil_id
    ON cadeaux(beneficiaire_profil_id);
