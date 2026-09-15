from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import SignUpForm, TicketForm
from .models import Ticket
from .services import SOUTHERN_STATIONS, apply_result_to_ticket, get_or_fetch_result


def signup(request):
    if request.user.is_authenticated:
        return redirect("lottery:home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Chào mừng! Tài khoản đã được tạo.")
            return redirect("lottery:home")
    else:
        form = SignUpForm()
    return render(request, "lottery/signup.html", {"form": form})


def home(request):
    if not request.user.is_authenticated:
        return render(request, "lottery/landing.html")
    recent = request.user.lottery_tickets.select_related("matched_tier")[:5]
    return render(request, "lottery/dashboard.html", {"recent": recent, "totals": totals_for(request.user)})


@login_required(login_url="lottery:login")
def check(request):
    if request.method == "POST":
        form = TicketForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)

        ticket = form.save(commit=False)
        ticket.owner = request.user
        ticket.save()

        result = get_or_fetch_result(ticket.station, ticket.draw_date)
        if result:
            apply_result_to_ticket(ticket, result)
            ticket.save()

        return JsonResponse(
            {
                "ok": True,
                "ticket_uid": str(ticket.uid),
                "number": ticket.number,
                "station": ticket.station,
                "draw_date": ticket.draw_date.isoformat(),
                "cost": ticket.cost,
                "checked": ticket.is_checked,
                "is_winner": ticket.is_winner,
                "tier_label": ticket.matched_tier.label if ticket.matched_tier else None,
                "matched_number": ticket.matched_number,
                "payout_amount": ticket.payout_amount,
                "net": ticket.net,
            }
        )

    form = TicketForm(initial={"draw_date": timezone.localdate(), "cost": 10000})
    return render(request, "lottery/check.html", {"form": form, "stations": SOUTHERN_STATIONS})


@login_required(login_url="lottery:login")
def ticket_list(request):
    qs = request.user.lottery_tickets.select_related("matched_tier")
    station = request.GET.get("station") or ""
    if station:
        qs = qs.filter(station=station)
    if request.GET.get("won") == "1":
        qs = qs.filter(matched_tier__isnull=False)
    return render(
        request,
        "lottery/tickets.html",
        {"tickets": qs, "stations": SOUTHERN_STATIONS, "station": station, "won_only": request.GET.get("won") == "1"},
    )


@login_required(login_url="lottery:login")
def ticket_detail(request, uid):
    ticket = get_object_or_404(Ticket, uid=uid, owner=request.user)
    return render(request, "lottery/ticket_detail.html", {"ticket": ticket})


@login_required(login_url="lottery:login")
def stats(request):
    return render(
        request,
        "lottery/stats.html",
        {"totals": totals_for(request.user), "monthly": monthly_breakdown(request.user)},
    )


def totals_for(user):
    agg = user.lottery_tickets.aggregate(
        total_spent=Sum("cost"),
        total_payout=Sum("payout_amount"),
        ticket_count=Count("id"),
        win_count=Count("id", filter=Q(matched_tier__isnull=False)),
        checked_count=Count("id", filter=Q(checked_at__isnull=False)),
    )
    total_spent = agg["total_spent"] or 0
    total_payout = agg["total_payout"] or 0
    checked_count = agg["checked_count"] or 0
    win_count = agg["win_count"] or 0
    net = total_payout - total_spent
    return {
        "total_spent": total_spent,
        "total_payout": total_payout,
        "net": net,
        "profit_percent": (net / total_spent * 100) if total_spent else 0,
        "ticket_count": agg["ticket_count"] or 0,
        "win_count": win_count,
        "checked_count": checked_count,
        "win_rate": (win_count / checked_count * 100) if checked_count else 0,
    }


def monthly_breakdown(user):
    rows = list(
        user.lottery_tickets.annotate(month=TruncMonth("draw_date"))
        .values("month")
        .annotate(spent=Sum("cost"), payout=Sum("payout_amount"))
        .order_by("-month")
    )
    breakdown = [
        {
            "month": row["month"],
            "spent": row["spent"] or 0,
            "payout": row["payout"] or 0,
            "net": (row["payout"] or 0) - (row["spent"] or 0),
        }
        for row in rows
    ]
    max_spent = max((row["spent"] for row in breakdown), default=0)
    for row in breakdown:
        row["bar_percent"] = int(row["spent"] / max_spent * 100) if max_spent else 0
    return breakdown
