import unittest
from types import SimpleNamespace

from app.routers.cadeaux import _cadeau_accessible_pour_membre, _cadeau_visible_pour_membre


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
            membres=[self.creator, self.santa, self.member],
        )

    def test_every_family_member_sees_every_gift(self):
        gifts = [
            SimpleNamespace(owner_id=self.creator.id, beneficiaires=[self.member], beneficiaire_profil=None),
            SimpleNamespace(owner_id=self.member.id, beneficiaires=[self.santa], beneficiaire_profil=None),
            SimpleNamespace(owner_id=self.santa.id, beneficiaires=[], beneficiaire_profil=None),
            SimpleNamespace(owner_id=self.member.id, beneficiaires=[], beneficiaire_profil=None),
        ]
        for gift in gifts:
            for member in (self.creator, self.santa, self.member):
                with self.subTest(owner=gift.owner_id, member=member.id):
                    self.assertTrue(_cadeau_visible_pour_membre(gift, self.family, member))

    def test_every_family_member_can_access_any_family_gift(self):
        gift = SimpleNamespace(
            owner_id=self.member.id,
            beneficiaires=[self.member],
            beneficiaire_profil=None,
            familles=[self.family],
        )
        for member in (self.creator, self.santa, self.member):
            with self.subTest(member=member.id):
                self.assertTrue(_cadeau_accessible_pour_membre(gift, member))

    def test_non_member_cannot_access_family_gift(self):
        outsider = user(99)
        gift = SimpleNamespace(
            owner_id=self.member.id,
            beneficiaires=[self.member],
            beneficiaire_profil=None,
            familles=[self.family],
        )
        self.assertFalse(_cadeau_accessible_pour_membre(gift, outsider))


if __name__ == "__main__":
    unittest.main()
