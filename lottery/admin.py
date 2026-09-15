from django.contrib import admin

from .models import LotteryResult, PrizeTier, Ticket


@admin.register(LotteryResult)
class LotteryResultAdmin(admin.ModelAdmin):
    list_display = ("draw_date", "station", "special", "source", "fetched_at")
    list_filter = ("source", "station")
    date_hierarchy = "draw_date"
    search_fields = ("station",)


@admin.register(PrizeTier)
class PrizeTierAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "payout_amount", "count_per_draw", "order")
    ordering = ("order",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("number", "station", "draw_date", "owner", "cost", "matched_tier", "payout_amount", "checked_at")
    list_filter = ("station", "matched_tier")
    search_fields = ("number", "owner__username")
    date_hierarchy = "draw_date"
