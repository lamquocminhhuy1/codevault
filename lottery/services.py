"""Business logic for the lottery app: fetching/caching draw results and
matching a ticket number against them.

Two data sources, layered (see the plan this was built from):
- sync_results(): a reliable daily batch sync from a community-maintained
  GitHub dataset. Always the source of truth for historical dates.
- fetch_live_result(): a best-effort same-day lookup against the
  provincial lottery company's own live-results endpoint, used only when
  today's result isn't in our DB yet (i.e. before the daily sync has run).
"""

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timedelta

from django.utils import timezone

from .models import LotteryResult, PrizeTier

logger = logging.getLogger("lottery")

# The 21 Southern provincial lottery companies (xổ số kiến thiết miền Nam).
# Only 2-3 of these actually draw on any given day - the dropdown lists all
# of them for simplicity; picking one that didn't draw on the chosen date
# just means "no result found for that day", same as any other miss.
SOUTHERN_STATIONS = [
    "An Giang", "Bạc Liêu", "Bến Tre", "Bình Dương", "Bình Phước",
    "Bình Thuận", "Cà Mau", "Cần Thơ", "Hậu Giang", "Hồ Chí Minh",
    "Kiên Giang", "Long An", "Sóc Trăng", "Tiền Giang", "Trà Vinh",
    "Tây Ninh", "Vĩnh Long", "Vũng Tàu", "Đà Lạt", "Đồng Nai", "Đồng Tháp",
]

GITHUB_RESULTS_URL = (
    "https://raw.githubusercontent.com/tuanseo5t-alt/xosomn-xosomt/main/data/xsmn/xsmn.json"
)

# Reverse-engineered from a public project that already calls it (the
# provincial lottery company's own live-results AJAX endpoint) - NOT
# independently verified end-to-end from this codebase's dev environment
# (outbound access to the domain was blocked there). Treat as best-effort:
# on any shape surprise _parse_live_payload gives up and returns None
# rather than guessing, so a live-lookup miss always falls back to "not
# available yet" instead of risking a wrong result.
LIVE_RESULT_URL = (
    "https://www.xosobinhduong.com.vn/get-lottery-mn"
    "?mask=getResultLoteryMn&lotdate={date}&skip=true&flagNumber=-1"
)

DEFAULT_SYNC_LOOKBACK_DAYS = 400


def check_ticket_against_result(number, result):
    """Match a ticket's printed number against one day's result.

    Standard Vietnamese lottery rule: a ticket wins the highest tier whose
    winning number equals the ticket number's own last N digits (N = that
    tier's digit length, read from the actual result rather than assumed -
    tiers get shorter going from giải đặc biệt down to giải tám). Checked
    in tier order (LotteryResult.TIER_FIELDS), so the best possible match
    wins when a short suffix would otherwise also match a lower tier.
    Returns (tier_key, matched_number) or (None, None).
    """
    number = (number or "").strip()
    if not number:
        return None, None
    for tier_key in LotteryResult.TIER_FIELDS:
        for candidate in result.numbers_for(tier_key):
            n = len(candidate)
            if n and number[-n:] == candidate:
                return tier_key, candidate
    return None, None


def apply_result_to_ticket(ticket, result):
    """Check `ticket` against `result` and stamp the outcome onto it.
    Caller is responsible for saving."""
    tier_key, matched_number = check_ticket_against_result(ticket.number, result)
    ticket.checked_at = timezone.now()
    if tier_key:
        tier = PrizeTier.objects.filter(key=tier_key).first()
        ticket.matched_tier = tier
        ticket.matched_number = matched_number
        ticket.payout_amount = tier.payout_amount if tier else 0
    else:
        ticket.matched_tier = None
        ticket.matched_number = ""
        ticket.payout_amount = 0
    return ticket


def get_or_fetch_result(station, draw_date):
    """The single entry point views should use: DB first, then (only for
    today) a best-effort live lookup that caches into the DB. Never
    raises; returns None when nothing is available yet."""
    result = LotteryResult.objects.filter(station=station, draw_date=draw_date).first()
    if result:
        return result
    if draw_date == timezone.localdate():
        return fetch_live_result(station, draw_date)
    return None


def fetch_live_result(station, draw_date):
    """Best-effort live lookup for today's draw. Returns None on any
    failure or unrecognized response shape - callers must treat that the
    same as "not ready yet", not as an error."""
    url = LIVE_RESULT_URL.format(date=draw_date.isoformat())
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, OSError):
        logger.info("lottery: live lookup failed for %s %s", station, draw_date)
        return None

    parsed = _parse_live_payload(payload, station)
    if not parsed:
        return None

    result, _created = LotteryResult.objects.update_or_create(
        draw_date=draw_date,
        station=station,
        defaults=dict(parsed, source=LotteryResult.Source.LIVE),
    )
    return result


def _parse_live_payload(payload, station):
    """Best-effort extraction from the live endpoint's response. Only
    trusts a couple of plausible layouts and gives up (returns None) on
    anything else - a wrong parse here would silently corrupt a result,
    which is worse than just not having one yet. Needs a real
    verification pass against the live endpoint after deploy (see
    services.py module docstring / the lottery app's plan notes)."""
    try:
        stations = payload.get("data") or payload.get("Data") or payload
        if isinstance(stations, dict):
            stations = [stations]
        for entry in stations:
            name = (entry.get("tentinh") or entry.get("name") or entry.get("station") or "").strip()
            if not name:
                continue
            if station.lower() not in name.lower() and name.lower() not in station.lower():
                continue
            return {
                "special": entry.get("giaidb") or entry.get("special") or "",
                "first": entry.get("giai1") or entry.get("first") or "",
                "second": entry.get("giai2") or entry.get("second") or "",
                "third": entry.get("giai3") or entry.get("third") or "",
                "fourth": entry.get("giai4") or entry.get("fourth") or "",
                "fifth": entry.get("giai5") or entry.get("fifth") or "",
                "sixth": entry.get("giai6") or entry.get("sixth") or "",
                "seventh": entry.get("giai7") or entry.get("seventh") or "",
                "eighth": entry.get("giai8") or entry.get("eighth") or "",
            }
    except (AttributeError, TypeError):
        return None
    return None


def sync_results(lookback_days=DEFAULT_SYNC_LOOKBACK_DAYS):
    """Pull the GitHub fallback dataset and insert any (date, station) rows
    we don't already have, limited to the last `lookback_days` days (the
    full dataset goes back to 2008 - we don't need or want 18 years of
    history synced on every run). Returns the number of rows created."""
    cutoff = timezone.localdate() - timedelta(days=lookback_days)
    with urllib.request.urlopen(GITHUB_RESULTS_URL, timeout=30) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    existing = set(
        LotteryResult.objects.filter(draw_date__gte=cutoff).values_list("draw_date", "station")
    )

    to_create = []
    seen = set()
    for row in raw:
        try:
            draw_date = datetime.strptime(row["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            continue
        if draw_date < cutoff:
            continue
        station = (row.get("station") or "").strip()
        if not station:
            continue
        key = (draw_date, station)
        if key in existing or key in seen:
            continue
        seen.add(key)
        to_create.append(
            LotteryResult(
                draw_date=draw_date,
                station=station,
                special=row.get("special", ""),
                first=row.get("first", ""),
                second=row.get("second", ""),
                third=row.get("third", ""),
                fourth=row.get("fourth", ""),
                fifth=row.get("fifth", ""),
                sixth=row.get("sixth", ""),
                seventh=row.get("seventh", ""),
                eighth=row.get("eighth", ""),
                source=LotteryResult.Source.SYNC,
            )
        )

    if to_create:
        LotteryResult.objects.bulk_create(to_create, ignore_conflicts=True)
    return len(to_create)
