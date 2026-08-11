// ===== WESTERVALE dashboard.js — chart bootstrapping =====

document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart === 'undefined') return;

    // Growth line chart
    const growth = document.getElementById('growthChart');
    if (growth) {
        const labels = JSON.parse(growth.dataset.labels || '[]');
        const values = JSON.parse(growth.dataset.values || '[]');
        createGrowthChart('growthChart', labels, values);
    }

    // Deposits vs withdrawals bar chart
    const bar = document.getElementById('flowChart');
    if (bar) {
        const labels = JSON.parse(bar.dataset.labels || '[]');
        const deposits = JSON.parse(bar.dataset.deposits || '[]');
        const withdrawals = JSON.parse(bar.dataset.withdrawals || '[]');
        createBarChart('flowChart', labels, deposits, withdrawals);
    }

    // Allocation doughnut
    const doughnut = document.getElementById('allocationChart');
    if (doughnut) {
        const labels = JSON.parse(doughnut.dataset.labels || '[]');
        const values = JSON.parse(doughnut.dataset.values || '[]');
        const center = doughnut.dataset.center
            ? JSON.parse(doughnut.dataset.center)
            : null;
        createDoughnutChart('allocationChart', labels, values, center);
    }
});
