import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import LotteryResult, PrizeTier, Ticket
from .services import apply_result_to_ticket, check_ticket_against_result, sync_results


def make_result(**kwargs):
    defaults = dict(
        draw_date=date(2026, 9, 14),
        station="Đồng Tháp",
        special="803330",
        first="12345",
        second="67890",
        third="40150, 86548",
        fourth="08559, 80928, 12321, 06726, 52837, 33295, 41127",
        fifth="2577",
        sixth="1763, 3031, 1443",
        seventh="737",
        eighth="85",
    )
    defaults.update(kwargs)
    return LotteryResult.objects.create(**defaults)


class MatchingTests(TestCase):
    def setUp(self):
        self.result = make_result()

    def test_full_special_match(self):
        tier, number = check_ticket_against_result("803330", self.result)
        self.assertEqual(tier, "special")
        self.assertEqual(number, "803330")

    def test_eighth_tier_suffix_match(self):
        tier, number = check_ticket_against_result("9985", self.result)
        self.assertEqual(tier, "eighth")
        self.assertEqual(number, "85")

    def test_multi_number_tier_match(self):
        tier, number = check_ticket_against_result("086548", self.result)
        self.assertEqual(tier, "third")
        self.assertEqual(number, "86548")

    def test_no_match_returns_none(self):
        tier, number = check_ticket_against_result("000000", self.result)
        self.assertIsNone(tier)
        self.assertIsNone(number)

    def test_best_tier_wins_when_multiple_could_match(self):
        # A ticket ending in the full special number also trivially ends in
        # the special's own suffix at every shorter length, but must only
        # ever be credited with the single best (special) tier.
        tier, _ = check_ticket_against_result(self.result.special, self.result)
        self.assertEqual(tier, "special")


class ApplyResultTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("player", password="secret123")
        self.result = make_result()
        for key, label, amount in [("eighth", "Giải tám", 100000), ("special", "Giải đặc biệt", 2000000000)]:
            PrizeTier.objects.update_or_create(key=key, defaults={"label": label, "payout_amount": amount})

    def test_apply_result_winner(self):
        ticket = Ticket.objects.create(owner=self.user, number="9985", station="Đồng Tháp", draw_date=self.result.draw_date, cost=10000)
        apply_result_to_ticket(ticket, self.result)
        ticket.save()
        self.assertTrue(ticket.is_winner)
        self.assertEqual(ticket.payout_amount, 100000)
        self.assertEqual(ticket.net, 90000)
        self.assertIsNotNone(ticket.checked_at)

    def test_apply_result_loser(self):
        ticket = Ticket.objects.create(owner=self.user, number="000000", station="Đồng Tháp", draw_date=self.result.draw_date, cost=10000)
        apply_result_to_ticket(ticket, self.result)
        ticket.save()
        self.assertFalse(ticket.is_winner)
        self.assertEqual(ticket.payout_amount, 0)
        self.assertEqual(ticket.net, -10000)


class SyncTests(TestCase):
    def _mock_response(self, payload):
        class FakeResp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *a):
                return False

            def read(self_inner):
                return json.dumps(payload).encode("utf-8")

        return FakeResp()

    def test_sync_creates_rows(self):
        payload = [
            {
                "date": "2026-09-14",
                "station": "Đồng Tháp",
                "special": "803330",
                "first": "",
                "second": "",
                "third": "",
                "fourth": "",
                "fifth": "",
                "sixth": "",
                "seventh": "",
                "eighth": "85",
            }
        ]
        with patch("lottery.services.urllib.request.urlopen", return_value=self._mock_response(payload)):
            created = sync_results(lookback_days=400)
        self.assertEqual(created, 1)
        self.assertEqual(LotteryResult.objects.count(), 1)

    def test_sync_is_idempotent(self):
        payload = [
            {
                "date": "2026-09-14",
                "station": "Đồng Tháp",
                "special": "803330",
                "eighth": "85",
            }
        ]
        with patch("lottery.services.urllib.request.urlopen", return_value=self._mock_response(payload)):
            sync_results(lookback_days=400)
            second_created = sync_results(lookback_days=400)
        self.assertEqual(second_created, 0)
        self.assertEqual(LotteryResult.objects.count(), 1)


class AuthFlowTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("lottery:signup"),
            {"username": "newplayer", "password1": "Sup3rSecret!!", "password2": "Sup3rSecret!!"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newplayer").exists())
        # session is authenticated - dashboard (not landing) renders now
        home = self.client.get(reverse("lottery:home"))
        self.assertContains(home, "newplayer")

    def test_check_requires_login_redirects_to_lottery_login_not_vault(self):
        response = self.client.get(reverse("lottery:check"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/xoso/login/", response.url)


class TicketFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("player", password="secret123")
        self.client.login(username="player", password="secret123")
        make_result()
        for key, label, amount in [("eighth", "Giải tám", 100000)]:
            PrizeTier.objects.update_or_create(key=key, defaults={"label": label, "payout_amount": amount})

    def test_check_post_creates_ticket_and_wins(self):
        response = self.client.post(
            reverse("lottery:check"),
            {"number": "9985", "station": "Đồng Tháp", "draw_date": "2026-09-14", "cost": 10000},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["is_winner"])
        self.assertEqual(data["payout_amount"], 100000)
        self.assertEqual(Ticket.objects.filter(owner=self.user).count(), 1)

    def test_check_post_missing_result_still_saves_ticket_unchecked(self):
        response = self.client.post(
            reverse("lottery:check"),
            {"number": "123456", "station": "An Giang", "draw_date": "2026-09-14", "cost": 10000},
        )
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertFalse(data["checked"])
        ticket = Ticket.objects.get(owner=self.user)
        self.assertFalse(ticket.is_checked)

    def test_future_draw_date_rejected(self):
        response = self.client.post(
            reverse("lottery:check"),
            {"number": "123456", "station": "An Giang", "draw_date": "2099-01-01", "cost": 10000},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])


class VaultIsolationTests(TestCase):
    """A public lottery user must never see or affect the private vault
    app's data - regression guard for the shared-project decision."""

    def test_lottery_user_sees_empty_vault_project_list(self):
        User.objects.create_user("lotteryonly", password="secret123")
        self.client.login(username="lotteryonly", password="secret123")
        response = self.client.get(reverse("project_list"))
        self.assertEqual(response.status_code, 200)
        # No projects belong to this user - the (private) vault owner's
        # projects must not appear.
        self.assertEqual(list(response.context["projects"]), [])

    def test_tickets_scoped_per_owner(self):
        alice = User.objects.create_user("alice", password="secret123")
        bob = User.objects.create_user("bob", password="secret123")
        Ticket.objects.create(owner=alice, number="111111", station="An Giang", draw_date=date(2026, 9, 14))
        self.client.login(username="bob", password="secret123")
        response = self.client.get(reverse("lottery:ticket_list"))
        self.assertEqual(list(response.context["tickets"]), [])
