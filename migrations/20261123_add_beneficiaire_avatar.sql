-- Ajoute la photo facultative aux profils bénéficiaires sans compte.
-- Migration non destructive : aucune donnée existante n'est supprimée.
ALTER TABLE public.beneficiaires
ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);
