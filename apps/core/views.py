from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

ERROR_PREVIEW_TEMPLATES = {
    '400': '400.html',
    '403': '403.html',
    '404': '404.html',
    '500': '500.html',
    '503': '503.html',
    '504': '504.html',
}


def service_unavailable(request):
    return render(request, '503.html', status=503)


def gateway_timeout(request):
    return render(request, '504.html', status=504)


def error_preview(request, code):
    """DEBUG-only route to preview the custom error pages."""
    if code not in ERROR_PREVIEW_TEMPLATES:
        raise Http404
    return render(request, ERROR_PREVIEW_TEMPLATES[code], {
        'request_path': f'/preview/{code}/',
    }, status=int(code))


def homepage(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return render(request, 'home.html')


def page(request, name):
    templates = {
        'about': 'pages/about.html',
        'services': 'pages/services.html',
        'how_it_works': 'pages/how_it_works.html',
        'investments': 'pages/investments.html',
        'privacy_policy': 'pages/privacy_policy.html',
        'terms_of_service': 'pages/terms_of_service.html',
        'risk_disclosure': 'pages/risk_disclosure.html',
    }
    if name not in templates:
        raise Http404
    return render(request, templates[name])


ASSETS = {
    'cryptocurrency': {
        'name': 'Cryptocurrency',
        'icon': 'ri-bit-coin-line',
        'tagline': 'Digital stocks with deep liquidity and global adoption.',
        'description': (
            'Holdings in cryptocurrency offer exposure to a fast-growing digital economy. '
            'We combine secure custody, disciplined cost-averaging, and transparent reporting '
            'so you can participate in this stock class on your own terms.'
        ),
        'strategies': [
            {'icon': 'ri-bit-coin-line', 'title': 'Bitcoin Core', 'text': 'A long-standing digital asset with deep liquidity and global adoption. Suitable for investors comfortable with price volatility.'},
            {'icon': 'ri-coin-line', 'title': 'Ethereum Ecosystem', 'text': 'Smart contract platforms support decentralized applications and programmable value.'},
            {'icon': 'ri-currency-line', 'title': 'Altcoin Index', 'text': 'Diversified exposure across several established tokens, rebalanced on a regular schedule.'},
        ],
        'facts': [
            ('Secure cold storage custody', 'Assets held offline with multi-signature protection.'),
            ('Cost-averaging strategies', 'Steady accumulation reduces the impact of volatility.'),
            ('Transparent fee structure', 'Every charge disclosed up front, no hidden costs.'),
        ],
        'risk': 'Cryptocurrency markets are highly volatile. Cryptocurrencies can lose significant value rapidly and are subject to regulatory change.',
    },
    'forex': {
        'name': 'Forex',
        'icon': 'ri-money-dollar-circle-line',
        'tagline': 'The world\u2019s most liquid market, managed with discipline.',
        'description': (
            'Foreign exchange offers round-the-clock trading across the world\u2019s major currencies. '
            'Our strategies combine transparent execution with strict risk management, giving you '
            'curated access to this deep and liquid market.'
        ),
        'strategies': [
            {'icon': 'ri-money-dollar-circle-line', 'title': 'Major Pairs', 'text': 'The most traded currency pairs, known for tight spreads and deep liquidity.'},
            {'icon': 'ri-money-yen-circle-line', 'title': 'Emerging Market FX', 'text': 'Higher-volatility pairs considered only by experienced investors under enhanced monitoring.'},
            {'icon': 'ri-flashlight-line', 'title': 'Systematic FX Strategies', 'text': 'Rules-based models with fully disclosed logic, automatic stop-losses, and regular reporting.'},
        ],
        'facts': [
            ('24/5 market access', 'Currencies trade nearly around the clock across global sessions.'),
            ('Automatic stop-losses', 'Positions protected with predefined exit levels.'),
            ('Regular reporting', 'Clear, periodic summaries of every open position.'),
        ],
        'risk': 'Forex trading carries a high level of risk due to leverage. You can lose more than your initial capital.',
    },
    'gold_metals': {
        'name': 'Gold & Metals',
        'icon': 'ri-vip-diamond-line',
        'tagline': 'A traditional store of value for long-term holdings.',
        'description': (
            'Precious metals have protected wealth for centuries. From allocated physical bullion '
            'to gold mining equities, we offer a range of ways to add this defensive stock class '
            'to your holdings.'
        ),
        'strategies': [
            {'icon': 'ri-vip-diamond-line', 'title': 'Physical Bullion', 'text': 'Allocated gold stored in audited vaults with the option of physical delivery.'},
            {'icon': 'ri-gem-line', 'title': 'Gold Mining Equities', 'text': 'Companies in precious metals extraction, selected through fundamental research.'},
            {'icon': 'ri-coin-line', 'title': 'Digitally Tracked Gold', 'text': 'Gold-backed instruments combining metal exposure with modern settlement.'},
        ],
        'facts': [
            ('Allocated ownership', 'Your bullion is individually identified and held in your name.'),
            ('Third-party audits', 'Independent verification of stored metal on a regular basis.'),
            ('Delivery on request', 'Take physical delivery of your allocated holdings.'),
        ],
        'risk': 'Gold prices fluctuate with market conditions. Mining equities can underperform the underlying metal.',
    },
    'real_estate': {
        'name': 'Real Estate',
        'icon': 'ri-building-2-line',
        'tagline': 'Property exposure built for every budget.',
        'description': (
            'Real estate can deliver income and long-term appreciation. Our vehicles open the door '
            'to commercial, fractional, and development property with professional management '
            'and transparent terms.'
        ),
        'strategies': [
            {'icon': 'ri-building-2-line', 'title': 'Commercial Real Estate', 'text': 'Income-focused exposure to office, retail, and industrial properties.'},
            {'icon': 'ri-home-heart-line', 'title': 'Fractional Property', 'text': 'Invest in shares of individual properties with a lower entry threshold.'},
            {'icon': 'ri-building-4-line', 'title': 'Development Projects', 'text': 'Pre-construction and renovation opportunities with defined exit plans.'},
        ],
        'facts': [
            ('Professional management', 'Every property is managed by experienced operators.'),
            ('Diversified properties', 'Portfolios spread across geographies and use types.'),
            ('Transparent terms', 'Fees, timelines, and exit plans disclosed up front.'),
        ],
        'risk': 'Real estate is relatively illiquid. Development projects involve longer time horizons and higher risk.',
    },
    'stocks': {
        'name': 'Stocks',
        'icon': 'ri-funds-line',
        'tagline': 'Own great companies for long-term growth.',
        'description': (
            'Equity holdings give you ownership in companies that build lasting value. '
            'From blue-chip anchors like Berkshire Hathaway to dividend growers and '
            'high-growth equities, our stock strategies pair fundamental research '
            'with patient capital.'
        ),
        'strategies': [
            {'icon': 'ri-funds-line', 'title': 'Berkshire Hathaway', 'text': 'An anchor stock in a proven conglomerate. A cornerstone holding for long-term growth, dividends, and capital preservation.'},
            {'icon': 'ri-line-chart-line', 'title': 'Dividend Growers', 'text': 'Companies with a proven record of steadily rising dividends. A defensive income core for long-term holdings.'},
            {'icon': 'ri-rocket-line', 'title': 'Growth Stocks', 'text': 'High-growth companies across technology, consumer, and industrial sectors. Greater upside potential with higher volatility.'},
        ],
        'facts': [
            ('Blue-chip anchor', 'A cornerstone holding in a proven global conglomerate.'),
            ('Dividend income', 'Long-term income from a diversified operating base.'),
            ('Capital preservation', 'A defensive profile suited to long-term holdings.'),
        ],
        'risk': 'Stock prices fluctuate with market conditions. Growth stocks are more volatile, and dividend growers can lag when rates rise.',
    },
}


ASSET_URLS = {
    'cryptocurrency': 'crypto_page',
    'forex': 'forex_page',
    'gold_metals': 'gold_page',
    'real_estate': 'real_estate_page',
    'stocks': 'stocks_page',
}


def asset_page(request, slug):
    if slug not in ASSETS:
        raise Http404
    asset = dict(ASSETS[slug], slug=slug)
    assets = [
        dict(ASSETS[key], slug=key, url=reverse(ASSET_URLS[key]))
        for key in ASSETS
    ]
    return render(request, 'pages/asset.html', {
        'asset': asset,
        'assets': assets,
    })
