-- LaHotte: rattacher les contributions aux bénéficiaires sans perdre l'origine cadeau.
-- À exécuter uniquement après validation et sauvegarde de la base.

ALTER TABLE public.contributions
  ADD COLUMN IF NOT EXISTS beneficiaire_user_id integer NULL
    REFERENCES public.users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS beneficiaire_profil_id integer NULL
    REFERENCES public.beneficiaires(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS famille_id integer NULL
    REFERENCES public.familles(id) ON DELETE CASCADE;

-- Vérifier les données historiques avant toute attribution : ne jamais choisir
-- arbitrairement une famille ou un bénéficiaire si l'ancien cadeau en avait plusieurs.
DO $
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.contributions c
    LEFT JOIN public.cadeau_familles cf ON cf.cadeau_id = c.cadeau_id
    WHERE c.famille_id IS NULL
    GROUP BY c.id
    HAVING COUNT(cf.famille_id) <> 1
  ) THEN
    RAISE EXCEPTION 'Migration interrompue : une contribution historique est liée à un cadeau sans exactement une famille.';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM public.contributions c
    JOIN public.cadeaux g ON g.id = c.cadeau_id
    LEFT JOIN public.cadeau_beneficiaires cb ON cb.cadeau_id = g.id
    WHERE c.beneficiaire_user_id IS NULL
      AND c.beneficiaire_profil_id IS NULL
    GROUP BY c.id, g.id, g.beneficiaire_profil_id
    HAVING (g.beneficiaire_profil_id IS NOT NULL AND COUNT(cb.user_id) > 0)
        OR (g.beneficiaire_profil_id IS NULL AND COUNT(cb.user_id) > 1)
  ) THEN
    RAISE EXCEPTION 'Migration interrompue : un cadeau historique possède plusieurs bénéficiaires. Corriger son destinataire avant la migration.';
  END IF;
END $;

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

-- Les anciennes contributions sont rattachées à l'unique famille du cadeau.
UPDATE public.contributions AS c
SET famille_id = cf.famille_id
FROM public.cadeau_familles AS cf
WHERE c.cadeau_id = cf.cadeau_id
  AND c.famille_id IS NULL;

-- Échouer explicitement plutôt que déployer avec des contributions sans famille
-- ou ambiguës : aucune donnée n'est supprimée.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.contributions WHERE famille_id IS NULL
  ) THEN
    RAISE EXCEPTION 'Migration interrompue : certaines contributions historiques ne peuvent pas être rattachées à une famille. Vérifier cadeau_familles avant de continuer.';
  END IF;
END $$;

ALTER TABLE public.contributions ALTER COLUMN famille_id SET NOT NULL;

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
CREATE INDEX IF NOT EXISTS ix_contributions_famille_id
  ON public.contributions (famille_id);
