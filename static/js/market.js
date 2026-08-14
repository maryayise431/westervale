// ===== WESTERVALE market.js — live market dashboard =====
(function () {
    'use strict';

    var $ = function (id) { return document.getElementById(id); };
    var els = {
        updated: $('lmUpdated'),
        content: $('lmContent'),
        loading: $('lmLoading'),
        error: $('lmError'),
        retry: $('lmRetryBtn'),
        refresh: $('lmRefreshBtn'),
        price: $('lmPrice'),
        change: $('lmChange'),
        rangeInfo: $('lmRange'),
        logo: $('lmLogo'),
        cname: $('lmCompanyName'),
        exch: $('lmExchange'),
        facts: $('lmFacts'),
        stats: $('lmStats'),
        dividends: $('lmDividends'),
        chart: $('lmChart'),
        note: $('lmChartNote'),
        symbols: $('lmSymbols'),
        tf: $('lmTf'),
    };

    var state = { symbol: null, range: '1D', chart: null, items: {}, loaded: false, timer: null };
    var REFRESH_MS = 120000; // two minutes — matches the server-side cache TTL

    function fmtNum(n, d) {
        if (n === null || n === undefined || isNaN(n)) return '–';
        return Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
    }

    function fmtUsd(n, d) {
        if (n === null || n === undefined || isNaN(n)) return '–';
        return '$' + Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
    }

    function fmtPct(n) {
        if (n === null || n === undefined || isNaN(n)) return '–';
        return (n > 0 ? '+' : '') + Number(n).toFixed(2) + '%';
    }

    function fmtBig(n) {
        if (n === null || n === undefined || isNaN(n)) return '–';
        n = Number(n);
        if (n >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T';
        if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
        if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
        return '$' + Number(n).toLocaleString();
    }

    function setVisible(elm, on) { if (elm) elm.hidden = !on; }

    function fetchJSON(url) {
        return fetch(url).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    function hexA(hex, a) {
        var h = (hex || '#10B981').replace('#', '');
        if (h.length === 3) h = h.split('').map(function (c) { return c + c; }).join('');
        var r = parseInt(h.slice(0, 2), 16);
        var g = parseInt(h.slice(2, 4), 16);
        var b = parseInt(h.slice(4, 6), 16);
        return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
    }

    function timeLabel(ts, range) {
        var d = new Date(ts * 1000);
        var pad = function (v) { return (v < 10 ? '0' : '') + v; };
        var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        var days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        if (range === '1D') return pad(d.getHours()) + ':' + pad(d.getMinutes());
        if (range === '1W') return days[d.getDay()] + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
        if (range === '1Y') return months[d.getMonth()] + ' ' + d.getDate() + ", '" + String(d.getFullYear()).slice(2);
        return months[d.getMonth()] + ' ' + d.getDate();
    }

    function row(label, value) {
        var d = document.createElement('div');
        d.className = 'lm-fact';
        var l = document.createElement('span');
        l.className = 'lm-fact-label';
        l.textContent = label;
        var v = document.createElement('span');
        v.className = 'lm-fact-value';
        v.textContent = value;
        d.appendChild(l);
        d.appendChild(v);
        return d;
    }

    function stat(label, value, cls) {
        var tile = document.createElement('div');
        tile.className = 'lm-stat' + (cls ? ' ' + cls : '');
        var l = document.createElement('span');
        l.className = 'lm-stat-label';
        l.textContent = label;
        var v = document.createElement('span');
        v.className = 'lm-stat-value';
        v.textContent = value;
        tile.appendChild(l);
        tile.appendChild(v);
        return tile;
    }

    function renderQuote(item) {
        if (!item) return;
        var q = item.quote || {};
        if (els.price) els.price.textContent = fmtUsd(q.price, 2);
        if (els.change) {
            els.change.textContent = fmtUsd(q.change, 2) + ' (' + fmtPct(q.change_pct) + ')';
            els.change.className = 'lm-change ' + (q.change >= 0 ? 'pos' : 'neg');
        }
        if (els.rangeInfo) {
            els.rangeInfo.innerHTML = 'Open ' + fmtUsd(q.open, 2) + ' · High ' + fmtUsd(q.high, 2) +
                ' · Low ' + fmtUsd(q.low, 2) + ' · Prev Close ' + fmtUsd(q.prev_close, 2);
        }
        var p = item.profile || {};
        if (els.cname) els.cname.textContent = p.name || state.symbol;
        if (els.exch) els.exch.textContent = p.exchange || '';
        if (els.logo) {
            if (p.logo) { els.logo.src = p.logo; els.logo.hidden = false; }
            else { els.logo.hidden = true; }
        }
        renderFacts(item);
        renderStats(item);
        renderDividends(item);
    }

    function renderFacts(item) {
        var p = item.profile || {};
        if (!els.facts) return;
        els.facts.innerHTML = '';
        [
            ['Industry', p.industry || '–'],
            ['Country', p.country || '–'],
            ['Exchange', p.exchange || '–'],
            ['Currency', p.currency || '–'],
            ['Website', p.website || '–'],
        ].forEach(function (f) { els.facts.appendChild(row(f[0], f[1])); });
    }

    function renderStats(item) {
        var m = item.metrics || {};
        if (!els.stats) return;
        els.stats.innerHTML = '';
        var cap = m.market_cap != null ? m.market_cap : (item.profile || {}).market_cap;
        [
            ['Market Cap', fmtBig(cap)],
            ['P/E', fmtNum(m.pe, 2)],
            ['EPS', fmtUsd(m.eps, 2)],
            ['Revenue / Share', fmtUsd(m.revenue_ps, 2)],
            ['Gross Margin', fmtPct(m.gross_margin)],
            ['Net Margin', fmtPct(m.net_margin != null ? m.net_margin : m.profit_margin)],
        ].forEach(function (s) { els.stats.appendChild(stat(s[0], s[1])); });
    }

    function renderDividends(item) {
        var m = item.metrics || {};
        if (!els.dividends) return;
        els.dividends.innerHTML = '';
        els.dividends.appendChild(stat('Dividend Yield', fmtPct(m.dividend_yield)));
        els.dividends.appendChild(stat('Dividend / Share', fmtUsd(m.dividend_ps, 4)));
    }

    function buildChart(points, range) {
        if (!els.chart || typeof Chart === 'undefined') return;
        var labels = points.map(function (p) { return timeLabel(p.t, range); });
        var closes = points.map(function (p) { return p.c; });
        var volumes = points.map(function (p) { return p.v || 0; });
        var up = closes[closes.length - 1] >= closes[0];
        var color = up ? NEXUS_COLORS.emerald : NEXUS_COLORS.red;
        var ctx = els.chart.getContext('2d');
        if (state.chart) { state.chart.destroy(); state.chart = null; }

        state.chart = new Chart(ctx, {
            data: {
                labels: labels,
                datasets: [
                    {
                        type: 'line',
                        label: 'Price',
                        data: closes,
                        borderColor: color,
                        backgroundColor: gradientFill(ctx, [hexA(color, 0.3), hexA(color, 0)]),
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        pointBackgroundColor: color,
                        pointBorderColor: '#0A0A0F',
                        pointBorderWidth: 2,
                        borderWidth: 2.5,
                        yAxisID: 'y',
                        order: 1,
                    },
                    {
                        type: 'bar',
                        label: 'Volume',
                        data: volumes,
                        backgroundColor: 'rgba(154, 163, 178, 0.25)',
                        hoverBackgroundColor: 'rgba(154, 163, 178, 0.4)',
                        borderRadius: 2,
                        barPercentage: 0.9,
                        categoryPercentage: 0.9,
                        yAxisID: 'y2',
                        order: 2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: function (items) {
                                var i = items && items[0] ? items[0].dataIndex : 0;
                                return new Date(points[i].t * 1000).toLocaleString(undefined, {
                                    month: 'short', day: 'numeric', year: 'numeric',
                                    hour: '2-digit', minute: '2-digit',
                                });
                            },
                            label: function (item) {
                                if (item.dataset.type === 'line') return 'Price: ' + fmtUsd(item.parsed.y, 2);
                                return 'Volume: ' + Number(item.parsed.y).toLocaleString();
                            },
                        },
                    },
                },
                scales: {
                    x: { grid: { color: NEXUS_COLORS.grid }, ticks: { maxTicksLimit: 8, maxRotation: 0, autoSkip: true } },
                    y: { grid: { color: NEXUS_COLORS.grid }, ticks: { callback: function (v) { return '$' + Number(v).toLocaleString(); } } },
                    y2: { position: 'right', display: false, grid: { drawOnChartArea: false } },
                },
            },
        });

        if (els.note) {
            var note = 'Intraday · 5-minute bars';
            if (range === '1W') note = 'Hourly bars';
            else if (range === '1M' || range === '3M' || range === '1Y') note = 'Daily bars';
            els.note.textContent = note;
        }
    }

    function loadCandles() {
        var url = '/dashboard/market-candles/?symbol=' + encodeURIComponent(state.symbol) + '&range=' + state.range;
        return fetchJSON(url).then(function (data) {
            if (data && data.points && data.points.length) {
                buildChart(data.points, state.range);
            } else if (els.note) {
                els.note.textContent = 'No price history available.';
            }
        }).catch(function () {
            if (els.note) els.note.textContent = 'Could not load price history.';
        });
    }

    function renderSymbol() {
        renderQuote(state.items[state.symbol]);
        loadCandles();
    }

    function loadSnapshot() {
        setVisible(els.error, false);
        if (!state.loaded) setVisible(els.loading, true);
        return fetchJSON('/dashboard/market-data/').then(function (data) {
            state.items = {};
            (data.items || []).forEach(function (it) { state.items[it.symbol] = it; });
            state.loaded = true;
            setVisible(els.loading, false);
            setVisible(els.content, true);
            if (!state.symbol && data.symbols && data.symbols.length) state.symbol = data.symbols[0];
            if (els.updated) els.updated.textContent = 'Live prices · updated ' + new Date().toLocaleTimeString();
            renderSymbol();
        }).catch(function () {
            setVisible(els.loading, false);
            if (!state.loaded) setVisible(els.error, true);
        });
    }

    function startAutoRefresh() {
        if (state.timer) clearInterval(state.timer);
        state.timer = setInterval(loadSnapshot, REFRESH_MS);
    }

    function bindEvents() {
        if (els.symbols) {
            els.symbols.querySelectorAll('.lm-sym').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    els.symbols.querySelectorAll('.lm-sym').forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');
                    state.symbol = btn.getAttribute('data-symbol');
                    renderSymbol();
                });
            });
        }
        if (els.tf) {
            els.tf.querySelectorAll('.lm-tf-btn').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    els.tf.querySelectorAll('.lm-tf-btn').forEach(function (b) { b.classList.remove('active'); });
                    btn.classList.add('active');
                    state.range = btn.getAttribute('data-range');
                    loadCandles();
                });
            });
        }
        if (els.refresh) els.refresh.addEventListener('click', loadSnapshot);
        if (els.retry) els.retry.addEventListener('click', loadSnapshot);
    }

    function init() {
        bindEvents();
        loadSnapshot();
        startAutoRefresh();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
