// ===== WESTERVALE portfolio.js — live portfolio dashboard =====
(function () {
    'use strict';

    var ROOT = document.getElementById('portfolioDashboard');
    if (!ROOT) return;

    var CACHE_KEY = 'nexus_portfolio_data';
    var TS_KEY = 'nexus_portfolio_ts';
    var ENDPOINT = '/dashboard/portfolio-data/';

    var refreshSeconds = parseInt(ROOT.getAttribute('data-refresh-seconds') || '16200', 10);
    var refreshMs = Math.max(60000, refreshSeconds * 1000);

    var PALETTE = ['#D4AF37', '#10B981', '#3B82F6', '#8B5CF6', '#EF4444', '#14B8A6', '#F59E0B', '#60A5FA', '#EC4899', '#22C55E'];

    var els = {};
    [
        'Loading', 'Error', 'RetryBtn', 'Empty', 'Content', 'LastUpdated',
        'RefreshBtn', 'StaleNotice', 'Donut', 'Legend', 'HoldingsTable',
        'ViewAll', 'Sectors', 'SectorDetails', 'ViewSectors', 'Stats', 'Chart',
    ].forEach(function (key) {
        els[key] = document.getElementById('portfolio' + key);
    });

    var donutChart = null;
    var perfChart = null;
    var lastData = null;
    var hasData = false;
    var allHoldingsVisible = false;
    var sectorDetailsVisible = false;
    var MAX_ROWS = 5;

    function fmtMoney(value) {
        return '$' + Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function fmtPct(value, digits) {
        var v = Number(value);
        return v.toLocaleString(undefined, { minimumFractionDigits: digits || 1, maximumFractionDigits: digits || 1 }) + '%';
    }

    function signedMoney(value) {
        var v = Number(value);
        return (v >= 0 ? '+' : '-') + fmtMoney(Math.abs(v));
    }

    function colorFor(index) {
        return PALETTE[index % PALETTE.length];
    }

    function loadCache() {
        try {
            var raw = localStorage.getItem(CACHE_KEY);
            var ts = parseInt(localStorage.getItem(TS_KEY) || '0', 10);
            if (!raw) return null;
            return { data: JSON.parse(raw), ts: ts };
        } catch (e) {
            return null;
        }
    }

    function saveCache(data) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify(data));
            localStorage.setItem(TS_KEY, String(Date.now()));
        } catch (e) { /* private mode — ignore */ }
    }

    function isStale(ts) {
        return !ts || (Date.now() - ts) > refreshMs;
    }

    function showLoading() {
        els.Loading.hidden = false;
        els.Error.hidden = true;
        els.Empty.hidden = true;
        els.Content.hidden = true;
    }

    function showError() {
        els.Loading.hidden = true;
        els.Error.hidden = false;
        els.Empty.hidden = true;
        els.Content.hidden = true;
    }

    function showEmpty() {
        destroyCharts();
        els.Loading.hidden = true;
        els.Error.hidden = true;
        els.Empty.hidden = false;
        els.Content.hidden = true;
        els.LastUpdated.textContent = 'No portfolio data yet.';
    }

    function showStale() {
        els.StaleNotice.hidden = false;
        els.Error.hidden = true;
        els.Loading.hidden = true;
    }

    function hideStale() {
        els.StaleNotice.hidden = true;
    }

    function relativeTime(iso) {
        var then = new Date(iso).getTime();
        if (!then) return '';
        var diff = Math.max(0, Date.now() - then);
        var mins = Math.round(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return mins + 'm ago';
        var hours = Math.round(mins / 60);
        if (hours < 24) return hours + 'h ago';
        return Math.round(hours / 24) + 'd ago';
    }

    function refresh(manual) {
        if (manual) {
            els.RefreshBtn.classList.add('spinning');
        }
        if (!hasData) {
            showLoading();
        }
        fetch(ENDPOINT, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(function (res) {
                if (!res.ok) throw new Error('Bad status ' + res.status);
                return res.json();
            })
            .then(function (data) {
                lastData = data;
                hasData = true;
                saveCache(data);
                render(data);
                els.Error.hidden = true;
                els.Loading.hidden = true;
                if (data.has_holdings) hideStale();
            })
            .catch(function () {
                if (hasData) {
                    showStale();
                    els.Loading.hidden = true;
                    els.Error.hidden = true;
                } else {
                    showError();
                }
            })
            .finally(function () {
                els.RefreshBtn.classList.remove('spinning');
            });
    }

    function render(data) {
        if (!data.has_holdings) {
            showEmpty();
            return;
        }
        destroyCharts();
        els.Loading.hidden = true;
        els.Error.hidden = true;
        els.Empty.hidden = true;
        els.Content.hidden = false;

        renderDonut(data);
        renderLegend(data);
        renderTable(data);
        renderSectors(data);
        renderStats(data);
        renderChart(data);

        var time = new Date(data.generated_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
        els.LastUpdated.textContent = 'Updated ' + time + ' · ' + relativeTime(data.generated_at);
    }

    function renderDonut(data) {
        var holdings = data.holdings.slice(0, 10);
        var restValue = 0;
        if (data.holdings.length > 10) {
            restValue = data.holdings.slice(10).reduce(function (s, h) { return s + h.value; }, 0);
        }
        var labels = holdings.map(function (h) { return h.ticker; });
        var values = holdings.map(function (h) { return h.value; });
        if (restValue > 0) {
            labels.push('Other');
            values.push(restValue);
        }
        var ctx = els.Donut.getContext('2d');
        donutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: labels.map(function (_, i) { return colorFor(i); }),
                    borderColor: '#0C1018',
                    borderWidth: 3,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '66%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (item) {
                                var total = data.summary.total_value;
                                var pct = total ? (item.parsed / total * 100) : 0;
                                return ' ' + fmtMoney(item.parsed) + ' (' + pct.toFixed(1) + '%)';
                            },
                        },
                    },
                },
            },
            plugins: [{
                id: 'centerText',
                afterDraw: function (chart) {
                    var ctx2 = chart.ctx;
                    var meta = chart.getDatasetMeta(0);
                    if (!meta.data.length) return;
                    var x = meta.data.reduce(function (s, d) { return s + d.x; }, 0) / meta.data.length;
                    var y = meta.data.reduce(function (s, d) { return s + d.y; }, 0) / meta.data.length;
                    ctx2.save();
                    ctx2.textAlign = 'center';
                    ctx2.textBaseline = 'middle';
                    ctx2.fillStyle = '#F2F5F9';
                    ctx2.font = "800 20px 'Inter', sans-serif";
                    ctx2.fillText(fmtMoney(data.summary.total_value), x, y - 9);
                    ctx2.fillStyle = '#9AA3B2';
                    ctx2.font = "11px 'Inter', sans-serif";
                    ctx2.fillText('Total Value', x, y + 15);
                    ctx2.restore();
                },
            }],
        });
    }

    function renderLegend(data) {
        els.Legend.innerHTML = '';
        data.holdings.forEach(function (h, i) {
            var li = document.createElement('li');
            li.innerHTML =
                '<span class="legend-dot" style="background:' + colorFor(i) + '"></span>' +
                '<span class="legend-ticker">' + escapeHtml(h.ticker) + '</span>' +
                '<span class="legend-name">' + escapeHtml(h.name) + '</span>' +
                '<span class="legend-meta">' + fmtMoney(h.value) + '<small>' + fmtPct(h.weight) + ' of portfolio</small></span>';
            els.Legend.appendChild(li);
        });
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderTable(data) {
        var tbody = els.HoldingsTable.querySelector('tbody');
        tbody.innerHTML = '';
        data.holdings.forEach(function (h, i) {
            var tr = document.createElement('tr');
            if (i >= MAX_ROWS) tr.classList.add('hidden-row');
            var changeClass = h.day_change >= 0 ? 'amount-pos' : 'amount-neg';
            tr.innerHTML =
                '<td data-label="Ticker"><span class="mono font-bold">' + escapeHtml(h.ticker) + '</span></td>' +
                '<td data-label="Name">' + escapeHtml(h.name) + '</td>' +
                '<td data-label="Current Value">' + fmtMoney(h.value) + '</td>' +
                '<td data-label="% of Total">' + fmtPct(h.weight) + '</td>' +
                '<td data-label="Day" class="' + changeClass + '">' + signedMoney(h.day_change) + '</td>';
            tbody.appendChild(tr);
        });
        allHoldingsVisible = data.holdings.length <= MAX_ROWS;
        updateHoldingsToggle();
    }

    function updateHoldingsToggle() {
        var total = lastData ? lastData.holdings.length : 0;
        if (total <= MAX_ROWS) {
            els.ViewAll.style.display = 'none';
            return;
        }
        els.ViewAll.style.display = '';
        els.ViewAll.textContent = allHoldingsVisible ? 'Show Less' : 'View All Holdings (' + total + ')';
    }

    function toggleHoldings() {
        allHoldingsVisible = !allHoldingsVisible;
        var rows = els.HoldingsTable.querySelectorAll('tbody tr.hidden-row');
        rows.forEach(function (row) { row.classList.toggle('hidden-row', !allHoldingsVisible); });
        updateHoldingsToggle();
    }

    function renderSectors(data) {
        els.Sectors.innerHTML = '';
        data.sectors.forEach(function (s, i) {
            var row = document.createElement('div');
            row.className = 'sector-row';
            row.innerHTML =
                '<span class="sector-name" title="' + escapeHtml(s.name) + '">' + escapeHtml(s.name) + '</span>' +
                '<div class="sector-track"><div class="sector-bar" style="width:0;background:' + colorFor(i) + '"></div></div>' +
                '<span class="sector-meta">' + fmtPct(s.weight) + ' · ' + fmtMoney(s.value) + '</span>';
            els.Sectors.appendChild(row);
        });
        requestAnimationFrame(function () {
            data.sectors.forEach(function (s, i) {
                var bars = els.Sectors.querySelectorAll('.sector-bar');
                if (bars[i]) bars[i].style.width = s.weight + '%';
            });
        });
        renderSectorDetails(data);
        updateSectorsToggle();
    }

    function renderSectorDetails(data) {
        els.SectorDetails.innerHTML = '';
        data.sectors.forEach(function (s) {
            var holdings = data.holdings.filter(function (h) { return h.sector === s.name; });
            var group = document.createElement('div');
            group.className = 'sector-detail-group';
            var head = document.createElement('div');
            head.className = 'sector-detail-title';
            head.textContent = s.name + ' — ' + fmtPct(s.weight);
            group.appendChild(head);
            holdings.forEach(function (h) {
                var row = document.createElement('div');
                row.className = 'sector-detail-row';
                row.innerHTML = '<span>' + escapeHtml(h.name) + '</span><span>' + fmtMoney(h.value) + '</span>';
                group.appendChild(row);
            });
            els.SectorDetails.appendChild(group);
        });
    }

    function updateSectorsToggle() {
        var total = lastData ? lastData.sectors.length : 0;
        if (total === 0) {
            els.ViewSectors.style.display = 'none';
            return;
        }
        els.ViewSectors.style.display = '';
        els.ViewSectors.textContent = sectorDetailsVisible ? 'Hide Sector Details' : 'View Sector Details';
    }

    function toggleSectors() {
        sectorDetailsVisible = !sectorDetailsVisible;
        els.SectorDetails.hidden = !sectorDetailsVisible;
        updateSectorsToggle();
    }

    function animateNumber(el, target, formatter) {
        var start = 0;
        var duration = 600;
        var t0 = null;
        function step(ts) {
            if (!t0) t0 = ts;
            var progress = Math.min(1, (ts - t0) / duration);
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = formatter(start + (target - start) * eased);
            if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }

    function renderStats(data) {
        els.Stats.innerHTML = '';
        var tiles = [
            { icon: 'ri-donation-line', label: 'Dividend Yield', value: data.dividend_yield, fmt: function (v) { return fmtPct(v); }, sub: 'Estimated on current value' },
            { icon: 'ri-bank-line', label: 'Annual Dividend Income', value: data.annual_dividend_income, fmt: fmtMoney, sub: 'Projected yearly income' },
            { icon: 'ri-line-chart-line', label: 'YTD Performance', value: data.ytd_performance, fmt: function (v) { return fmtPct(v); }, sub: 'This year', signed: true },
            { icon: 'ri-bar-chart-box-line', label: 'S&amp;P 500 (YTD)', value: data.benchmark_performance, fmt: function (v) { return fmtPct(v); }, sub: 'Benchmark proxy', signed: true },
            { icon: 'ri-funds-line', label: 'Total Holdings', value: data.holding_count, fmt: function (v) { return String(Math.round(v)); }, sub: 'Active positions' },
            { icon: 'ri-stack-line', label: 'Sectors', value: data.sector_count, fmt: function (v) { return String(Math.round(v)); }, sub: 'Diversification' },
            { icon: 'ri-shield-warning-line', label: 'Concentration Risk', value: data.concentration_risk, fmt: function (v) { return v; }, sub: 'Based on largest sector' },
            { icon: 'ri-pie-chart-2-line', label: 'Amount Invested', value: data.summary.amount_invested, fmt: fmtMoney, sub: 'Across all plans' },
        ];
        tiles.forEach(function (tile) {
            var card = document.createElement('div');
            card.className = 'portfolio-stat';
            card.innerHTML = '<div class="ps-label"><i class="' + tile.icon + '"></i> ' + tile.label + '</div>' +
                '<div class="ps-value"></div>' +
                '<div class="ps-sub">' + tile.sub + '</div>';
            els.Stats.appendChild(card);
            var valueEl = card.querySelector('.ps-value');
            var isSigned = tile.signed && typeof tile.value === 'number';
            if (isSigned) valueEl.classList.add(tile.value >= 0 ? 'text-emerald' : 'text-red');
            if (typeof tile.value === 'number') {
                animateNumber(valueEl, tile.value, tile.fmt);
            } else {
                valueEl.textContent = tile.fmt(tile.value);
            }
        });
    }

    function renderChart(data) {
        var labels = data.history.labels;
        var portfolioSeries = data.history.portfolio;
        var startValue = portfolioSeries[0] || 1;
        var portfolioIndex = portfolioSeries.map(function (v) { return (v / startValue) * 100; });
        var benchmarkSeries = data.history.benchmark;
        var benchmarkIndex = benchmarkSeries.map(function (v) { return (v / startValue) * 100; });

        var ctx = els.Chart.getContext('2d');
        perfChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Portfolio',
                        data: portfolioIndex,
                        borderColor: NEXUS_COLORS.gold,
                        backgroundColor: gradientFill(ctx, ['rgba(212, 175, 55, 0.25)', 'rgba(212, 175, 55, 0)']),
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        borderWidth: 2.5,
                    },
                    {
                        label: 'S&P 500',
                        data: benchmarkIndex,
                        borderColor: NEXUS_COLORS.blue,
                        backgroundColor: 'transparent',
                        borderDash: [6, 4],
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', align: 'end', labels: { boxWidth: 10, usePointStyle: true } },
                    tooltip: { callbacks: { label: function (item) { return ' ' + item.dataset.label + ': ' + item.parsed.y.toFixed(1); } } },
                },
                scales: {
                    x: { grid: { color: NEXUS_COLORS.grid }, ticks: { maxTicksLimit: 10 } },
                    y: { grid: { color: NEXUS_COLORS.grid }, ticks: { callback: function (v) { return v.toFixed(0); } } },
                },
                interaction: { mode: 'index', intersect: false },
            },
        });
    }

    function destroyCharts() {
        if (donutChart) { donutChart.destroy(); donutChart = null; }
        if (perfChart) { perfChart.destroy(); perfChart = null; }
    }

    // Boot
    els.RefreshBtn.addEventListener('click', function () { refresh(true); });
    els.RetryBtn.addEventListener('click', function () { refresh(true); });
    els.ViewAll.addEventListener('click', toggleHoldings);
    els.ViewSectors.addEventListener('click', toggleSectors);

    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) {
            var cache = loadCache();
            if (isStale(cache ? cache.ts : 0)) refresh(false);
        }
    });
    window.addEventListener('focus', function () {
        var cache = loadCache();
        if (isStale(cache ? cache.ts : 0)) refresh(false);
    });

    var cache = loadCache();
    if (cache && cache.data) {
        hasData = true;
        lastData = cache.data;
        render(cache.data);
        if (isStale(cache.ts)) refresh(false);
    } else {
        refresh(false);
    }

    setInterval(function () {
        var c = loadCache();
        if (isStale(c ? c.ts : 0)) refresh(false);
    }, refreshMs);
})();
