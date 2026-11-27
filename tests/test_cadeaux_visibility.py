import unittest
from types import SimpleNamespace

from app.routers.cadeaux import _cadeau_visible_pour_membre


def user(user_id):
    return SimpleNamespace(id=user_id)


class CadeauVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.creator = user(1)
        self.santa = user(2)
        self.member = user(3)
        self.family = SimpleNamespace(
            id=10,
            creator_id=self.creator.id,
            pere_noel_id=self.santa.id,
        )

    def test_creator_sees_only_gifts_for_santa(self):
        santa_gift = SimpleNamespace(
            beneficiaires=[self.santa],
            beneficiaire_profil=None,
        )
        other_gift = SimpleNamespace(
            beneficiaires=[self.member],
            beneficiaire_profil=None,
        )

        self.assertTrue(_cadeau_visible_pour_membre(santa_gift, self.family, self.creator))
        self.assertFalse(_cadeau_visible_pour_membre(other_gift, self.family, self.creator))

    def test_santa_does_not_see_own_gifts(self):
        own_gift = SimpleNamespace(
            beneficiaires=[self.santa],
            beneficiaire_profil=None,
        )
        other_gift = SimpleNamespace(
            beneficiaires=[self.member],
            beneficiaire_profil=None,
        )

        self.assertFalse(_cadeau_visible_pour_membre(own_gift, self.family, self.santa))
        self.assertTrue(_cadeau_visible_pour_membre(other_gift, self.family, self.santa))

    def test_profile_managed_by_santa_is_treated_as_santa_beneficiary(self):
        profile = SimpleNamespace(responsables=[self.santa])
        profile_gift = SimpleNamespace(
            beneficiaires=[],
            beneficiaire_profil=profile,
        )

        self.assertTrue(_cadeau_visible_pour_membre(profile_gift, self.family, self.creator))
        self.assertFalse(_cadeau_visible_pour_membre(profile_gift, self.family, self.santa))

    def test_regular_member_sees_family_gifts(self):
        gift = SimpleNamespace(beneficiaires=[], beneficiaire_profil=None)
        self.assertTrue(_cadeau_visible_pour_membre(gift, self.family, self.member))


if __name__ == "__main__":
    unittest.main()
