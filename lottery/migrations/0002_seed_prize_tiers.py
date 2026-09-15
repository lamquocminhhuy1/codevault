from django.db import migrations

# Best-effort payout table (VND, per winning number, per 10,000đ ticket).
# "special" (2,000,000,000đ) is the one figure checked with real
# confidence during research; the rest are the commonly-published
# standard Southern-lottery figures but could NOT be independently
# verified against an authoritative source in this session (several
# official prize-structure pages were unreachable from the dev sandbox).
# Editable any time in Django admin - verify against your actual ticket
# or the lottery company's own cơ cấu giải thưởng before trusting this.
DEFAULT_TIERS = [
    ("special", "Giải đặc biệt", 2_000_000_000, 1, 0),
    ("first", "Giải nhất", 30_000_000, 1, 1),
    ("second", "Giải nhì", 15_000_000, 1, 2),
    ("third", "Giải ba", 10_000_000, 2, 3),
    ("fourth", "Giải tư", 3_000_000, 7, 4),
    ("fifth", "Giải năm", 1_000_000, 1, 5),
    ("sixth", "Giải sáu", 400_000, 3, 6),
    ("seventh", "Giải bảy", 200_000, 1, 7),
    ("eighth", "Giải tám", 100_000, 1, 8),
]


def seed_tiers(apps, schema_editor):
    PrizeTier = apps.get_model("lottery", "PrizeTier")
    for key, label, payout_amount, count_per_draw, order in DEFAULT_TIERS:
        PrizeTier.objects.update_or_create(
            key=key,
            defaults=dict(
                label=label,
                payout_amount=payout_amount,
                count_per_draw=count_per_draw,
                order=order,
            ),
        )


def remove_tiers(apps, schema_editor):
    PrizeTier = apps.get_model("lottery", "PrizeTier")
    PrizeTier.objects.filter(key__in=[t[0] for t in DEFAULT_TIERS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("lottery", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_tiers, remove_tiers),
    ]
