from apps.investments.models import InvestmentPlan

PERIODIC_PLANS = [
    {
        'name': '1X Weekly Plan', 'category': 'periodic', 'min_amount': 100,
        'duration_days': 182, 'duration_label': '26 Weeks', 'roi_percent': 200.00,
        'description': 'Contribute $100 every week for 26 weeks. Total invested '
                       '$2,600 grows to $7,800 at a 200% ROI.',
        'features': ['Contribute $100/week for 26 weeks', 'Total invested $2,600',
                     'Ending value $7,800 (200% ROI)', 'Weekly compounding available'],
    },
    {
        'name': '2X Weekly Plan', 'category': 'periodic', 'min_amount': 250,
        'duration_days': 175, 'duration_label': '25 Weeks', 'roi_percent': 200.00,
        'description': 'Contribute $250 every week for 25 weeks. Total invested '
                       '$6,250 grows to $18,750 at a 200% ROI.',
        'features': ['Contribute $250/week for 25 weeks', 'Total invested $6,250',
                     'Ending value $18,750 (200% ROI)', 'Weekly compounding available'],
    },
    {
        'name': 'Monthly Plan', 'category': 'periodic', 'min_amount': 500,
        'duration_days': 180, 'duration_label': '6 Months', 'roi_percent': 200.00,
        'description': 'Contribute $500 every month for 6 months. Total invested '
                       '$3,000 grows to $9,000 at a 200% ROI.',
        'features': ['Contribute $500/month for 6 months', 'Total invested $3,000',
                     'Ending value $9,000 (200% ROI)', 'Monthly compounding available'],
    },
]


def _flex(name, start, days, roi):
    earnings = round(start * roi / 100)
    ending = start + earnings
    return {
        'name': name, 'category': 'flexible', 'min_amount': start,
        'duration_days': days, 'duration_label': f'{days} Days', 'roi_percent': roi,
        'description': f'Start with ${start:,} and earn {roi}% over {days} days. '
                       f'Earnings of ${earnings:,} bring your ending return to ${ending:,}.',
        'features': [f'${earnings:,} earnings ({roi}% ROI)',
                     f'Ending return ${ending:,}', 'Compounding interest',
                     'Withdraw profits anytime', 'Capital guaranteed'],
    }


FLEXIBLE_PLANS = [
    _flex('Basic', 300, 6, 460),
    _flex('Starter', 500, 7, 487),
    _flex('Bronze', 1000, 8, 525),
    _flex('Silver', 3000, 10, 585),
    _flex('Gold', 5000, 11, 612),
    _flex('Ruby', 8000, 12, 638),
    _flex('Emerald', 10000, 13, 650),
    _flex('Sapphire', 15000, 14, 672),
    _flex('Diamond', 20000, 15, 688),
    _flex('Titanium', 30000, 17, 710),
    _flex('Obsidian', 40000, 18, 725),
    _flex('Platinum', 30000, 19, 1295),
    _flex('Rose Gold', 60000, 20, 747),
    _flex('White Gold', 70000, 21, 756),
    _flex('Meteor', 80000, 22, 763),
    _flex('Galaxy', 90000, 23, 769),
    _flex('Cosmic', 100000, 24, 775),
    _flex('Ultra', 200000, 26, 813),
    _flex('Supreme', 500000, 28, 862),
    _flex('Legendary', 1000000, 30, 900),
]


def seed():
    """Create or refresh the holding plan catalog. Idempotent and safe to re-run."""
    created = 0
    seed_keys = set()
    for data in PERIODIC_PLANS + FLEXIBLE_PLANS:
        defaults = dict(data)
        defaults['category'] = data.get('category', 'flexible')
        seed_keys.add((data['name'], data.get('category', 'flexible')))
        _, was_created = InvestmentPlan.objects.update_or_create(
            name=defaults['name'], category=defaults['category'], defaults=defaults
        )
        created += 1 if was_created else 0

    removed = 0
    for plan in InvestmentPlan.objects.filter(category__in=['periodic', 'flexible']):
        if (plan.name, plan.category) in seed_keys:
            continue
        if plan.user_investments.exists():
            if plan.is_active:
                plan.is_active = False
                plan.save(update_fields=['is_active'])
                removed += 1
        else:
            plan.delete()
            removed += 1

    return created, removed
