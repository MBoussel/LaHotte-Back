import unittest
from types import SimpleNamespace

from app.routers.contributions import _beneficiaire_visible_pour_membre, _peut_voir_contributions


def user(user_id):
    return SimpleNamespace(id=user_id)


class ContributionVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.creator = user(1)
        self.santa = user(2)
        self.member = user(3)
        self.family = SimpleNamespace(
            id=10,
            creator_id=self.creator.id,
            pere_noel_id=self.santa.id,
        )

    def test_santa_can_see_other_members_contributions(self):
        self.assertTrue(
            _peut_voir_contributions(self.family, self.santa, self.member.id)
        )

    def test_santa_cannot_see_own_contributions(self):
        self.assertFalse(
            _peut_voir_contributions(self.family, self.santa, self.santa.id)
        )

    def test_creator_can_see_santa_contributions_only(self):
        self.assertTrue(
            _peut_voir_contributions(self.family, self.creator, self.santa.id)
        )
        self.assertFalse(
            _peut_voir_contributions(self.family, self.creator, self.member.id)
        )

    def test_regular_member_cannot_see_contributor_details(self):
        self.assertFalse(
            _peut_voir_contributions(self.family, self.member, self.creator.id)
        )

    def test_creator_can_see_profile_managed_by_santa(self):
        profile = SimpleNamespace(responsables=[self.santa])
        self.assertTrue(
            _peut_voir_contributions(
                self.family, self.creator, None, profile
            )
        )

    def test_santa_cannot_see_profile_managed_by_santa(self):
        profile = SimpleNamespace(responsables=[self.santa])
        self.assertFalse(
            _peut_voir_contributions(
                self.family, self.santa, None, profile
            )
        )

    def test_creator_can_contribute_only_to_santa_beneficiary(self):
        self.assertTrue(
            _beneficiaire_visible_pour_membre(
                self.family, self.creator, self.santa.id
            )
        )
        self.assertFalse(
            _beneficiaire_visible_pour_membre(
                self.family, self.creator, self.member.id
            )
        )

    def test_santa_cannot_contribute_to_own_beneficiary(self):
        self.assertFalse(
            _beneficiaire_visible_pour_membre(
                self.family, self.santa, self.santa.id
            )
        )
        self.assertTrue(
            _beneficiaire_visible_pour_membre(
                self.family, self.santa, self.member.id
            )
        )

    def test_regular_member_can_contribute_to_other_beneficiaries(self):
        self.assertTrue(
            _beneficiaire_visible_pour_membre(
                self.family, self.member, self.creator.id
            )
        )

    def test_creator_can_contribute_to_profile_managed_by_santa(self):
        profile = SimpleNamespace(responsables=[self.santa])
        self.assertTrue(
            _beneficiaire_visible_pour_membre(
                self.family, self.creator, None, profile
            )
        )


if __name__ == "__main__":
    unittest.main()
