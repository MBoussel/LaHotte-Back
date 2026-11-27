-- LaHotte: rattacher les contributions aux bénéficiaires sans perdre l'origine cadeau.
-- À exécuter uniquement après validation et sauvegarde de la base.
ALTER TABLE public.contributions
  ADD COLUMN IF NOT EXISTS beneficiaire_user_id integer NULL
    REFERENCES public.users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS beneficiaire_profil_id integer NULL
    REFERENCES public.beneficiaires(id) ON DELETE SET NULL;

-- Les contributions historiques d'un cadeau sont attribuées à son profil,
-- à son bénéficiaire utilisateur unique, ou au propriétaire de la liste.
UPDATE public.contributions AS c
SET beneficiaire_profil_id = g.beneficiaire_profil_id
FROM public.cadeaux AS g
WHERE c.cadeau_id = g.id
  AND g.beneficiaire_profil_id IS NOT NULL
  AND c.beneficiaire_profil_id IS NULL
  AND c.beneficiaire_user_id IS NULL;

UPDATE public.contributions AS c
SET beneficiaire_user_id = COALESCE(
  (SELECT cb.user_id
   FROM public.cadeau_beneficiaires AS cb
   WHERE cb.cadeau_id = g.id
   LIMIT 1),
  g.owner_id
)
FROM public.cadeaux AS g
WHERE c.cadeau_id = g.id
  AND g.beneficiaire_profil_id IS NULL
  AND c.beneficiaire_profil_id IS NULL
  AND c.beneficiaire_user_id IS NULL;

-- Le cadeau source devient facultatif pour les contributions faites directement
-- depuis la cagnotte globale. Les anciennes références restent conservées.
ALTER TABLE public.contributions ALTER COLUMN cadeau_id DROP NOT NULL;
ALTER TABLE public.contributions
  DROP CONSTRAINT IF EXISTS contributions_cadeau_id_fkey;
ALTER TABLE public.contributions
  ADD CONSTRAINT contributions_cadeau_id_fkey
  FOREIGN KEY (cadeau_id) REFERENCES public.cadeaux(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_contributions_beneficiaire_user_id
  ON public.contributions (beneficiaire_user_id);
CREATE INDEX IF NOT EXISTS ix_contributions_beneficiaire_profil_id
  ON public.contributions (beneficiaire_profil_id);
