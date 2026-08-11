// ===== WESTERVALE charts.js — Chart.js theme helpers =====

const NEXUS_COLORS = {
    gold: '#D4AF37',
    goldLight: '#EBCE6B',
    emerald: '#10B981',
    emeraldLight: '#34D399',
    blue: '#3B82F6',
    blueLight: '#60A5FA',
    red: '#EF4444',
    text: '#9AA3B2',
    grid: 'rgba(255, 255, 255, 0.06)',
    border: 'rgba(255, 255, 255, 0.1)',
};

function nexusChartDefaults() {
    if (typeof Chart === 'undefined') return;
    Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
    Chart.defaults.color = NEXUS_COLORS.text;
    Chart.defaults.borderColor = NEXUS_COLORS.border;
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(10, 14, 22, 0.95)';
    Chart.defaults.plugins.tooltip.borderColor = 'rgba(255, 255, 255, 0.12)';
    Chart.defaults.plugins.tooltip.borderWidth = 1;
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 10;
    Chart.defaults.plugins.tooltip.titleColor = '#F2F5F9';
    Chart.defaults.plugins.tooltip.bodyColor = '#9AA3B2';
    Chart.defaults.plugins.tooltip.displayColors = true;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;
    Chart.defaults.plugins.legend.labels.padding = 16;
}

function gradientFill(ctx, colors) {
    const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight || 280);
    g.addColorStop(0, colors[0]);
    g.addColorStop(1, colors[1]);
    return g;
}

// Helper to build the growth line chart
function createGrowthChart(canvasId, labels, values) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    const ctx = canvas.getContext('2d');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Account Balance',
                data: values,
                borderColor: NEXUS_COLORS.gold,
                backgroundColor: gradientFill(ctx, ['rgba(212, 175, 55, 0.28)', 'rgba(212, 175, 55, 0)']),
                fill: true,
                tension: 0.45,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointBackgroundColor: NEXUS_COLORS.gold,
                pointBorderColor: '#0A0A0F',
                pointBorderWidth: 2,
                borderWidth: 2.5,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: { grid: { color: NEXUS_COLORS.grid }, ticks: { maxTicksLimit: 10 } },
                y: {
                    grid: { color: NEXUS_COLORS.grid },
                    ticks: { callback: v => '$' + Number(v).toLocaleString() },
                },
            },
            interaction: { mode: 'index', intersect: false },
        },
    });
}

function createBarChart(canvasId, labels, deposits, withdrawals) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    new Chart(canvas.getContext('2d'), {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Deposits',
                    data: deposits,
                    backgroundColor: 'rgba(16, 185, 129, 0.75)',
                    hoverBackgroundColor: NEXUS_COLORS.emeraldLight,
                    borderRadius: 8,
                    barPercentage: 0.7,
                    categoryPercentage: 0.6,
                },
                {
                    label: 'Withdrawals',
                    data: withdrawals,
                    backgroundColor: 'rgba(239, 68, 68, 0.65)',
                    hoverBackgroundColor: '#F87171',
                    borderRadius: 8,
                    barPercentage: 0.7,
                    categoryPercentage: 0.6,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    align: 'end',
                    labels: { boxWidth: 10 },
                },
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: NEXUS_COLORS.grid },
                    ticks: { callback: v => '$' + Number(v).toLocaleString() },
                },
            },
        },
    });
}

function createDoughnutChart(canvasId, labels, values, centerText) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;

    const palette = [NEXUS_COLORS.gold, NEXUS_COLORS.emerald, NEXUS_COLORS.blue, '#8B5CF6', NEXUS_COLORS.red, '#14B8A6'];

    new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: palette,
                borderColor: '#0C1018',
                borderWidth: 3,
                hoverOffset: 8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 10, padding: 14 },
                },
            },
        },
        plugins: [{
            id: 'centerText',
            afterDraw(chart) {
                if (!centerText) return;
                const { ctx } = chart;
                const meta = chart.getDatasetMeta(0);
                const x = meta.data.reduce((s, d) => s + d.x, 0) / meta.data.length;
                const y = meta.data.reduce((s, d) => s + d.y, 0) / meta.data.length;
                ctx.save();
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = '#F2F5F9';
                ctx.font = "800 22px 'Inter', sans-serif";
                ctx.fillText(centerText.value, x, y - 8);
                ctx.fillStyle = '#9AA3B2';
                ctx.font = "11px 'Inter', sans-serif";
                ctx.fillText(centerText.label, x, y + 16);
                ctx.restore();
            },
        }],
    });
}

nexusChartDefaults();
