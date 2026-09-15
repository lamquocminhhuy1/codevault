import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class LotteryResult(models.Model):
    """One southern-region station's draw result for one day.

    Populated two ways (see services.py): a daily sync from a community-
    maintained GitHub dataset (reliable, but only fresh as of the last
    scheduled sync), and an on-demand "live" lookup for today's draw that
    caches whatever it gets back into this same table.
    """

    # Order matters: also the payout-priority order used by
    # services.check_ticket_against_result (special is checked first).
    TIER_FIELDS = [
        "special", "first", "second", "third", "fourth",
        "fifth", "sixth", "seventh", "eighth",
    ]

    class Source(models.TextChoices):
        SYNC = "sync", "Daily sync"
        LIVE = "live", "Live lookup"

    draw_date = models.DateField()
    station = models.CharField(max_length=60)
    special = models.CharField(max_length=20, blank=True)
    first = models.CharField(max_length=20, blank=True)
    second = models.CharField(max_length=20, blank=True)
    third = models.CharField(max_length=60, blank=True)
    fourth = models.CharField(max_length=120, blank=True)
    fifth = models.CharField(max_length=20, blank=True)
    sixth = models.CharField(max_length=60, blank=True)
    seventh = models.CharField(max_length=20, blank=True)
    eighth = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.SYNC)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-draw_date", "station"]
        constraints = [
            models.UniqueConstraint(
                fields=["draw_date", "station"], name="unique_lottery_result_per_station_day"
            )
        ]

    def __str__(self):
        return "{0} - {1}".format(self.draw_date, self.station)

    def numbers_for(self, tier_key):
        """The tier's winning number(s) as a list - most tiers have one,
        some (third/fourth/sixth) have several, comma-separated in the
        source data."""
        raw = getattr(self, tier_key, "") or ""
        return [n.strip() for n in raw.split(",") if n.strip()]


class PrizeTier(models.Model):
    """Payout reference table, editable in Django admin.

    Defaults are best-effort (verified against public sources where
    possible - see the lottery app's data migration for notes on which
    figures are confident vs. approximate). Always double-check against
    your actual ticket or the lottery company's official cơ cấu giải
    thưởng before trusting the money math here.
    """

    key = models.CharField(max_length=10, unique=True, choices=[(k, k) for k in LotteryResult.TIER_FIELDS])
    label = models.CharField(max_length=40, help_text="e.g. Giải đặc biệt")
    payout_amount = models.BigIntegerField(
        help_text="VND paid per winning number, per 10,000đ ticket."
    )
    count_per_draw = models.PositiveSmallIntegerField(
        default=1, help_text="How many winning numbers this tier draws per station per day (display only)."
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


def default_draw_date():
    return timezone.localdate()


class Ticket(models.Model):
    """One physical ticket the user bought and (eventually) checked."""

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lottery_tickets"
    )
    number = models.CharField(max_length=6)
    station = models.CharField(max_length=60)
    draw_date = models.DateField(default=default_draw_date)
    cost = models.PositiveIntegerField(default=10000)

    # Filled in once a matching LotteryResult exists and the ticket is
    # checked - null until then, so "not checked yet" and "checked, lost"
    # are distinguishable.
    matched_tier = models.ForeignKey(
        PrizeTier, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    matched_number = models.CharField(max_length=20, blank=True)
    payout_amount = models.BigIntegerField(null=True, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-draw_date", "-created_at"]

    def __str__(self):
        return "{0} @ {1} ({2})".format(self.number, self.station, self.draw_date)

    def get_absolute_url(self):
        return reverse("lottery:ticket_detail", args=[self.uid])

    @property
    def is_checked(self):
        return self.checked_at is not None

    @property
    def is_winner(self):
        return self.matched_tier_id is not None

    @property
    def net(self):
        if self.payout_amount is None:
            return -self.cost
        return self.payout_amount - self.cost
