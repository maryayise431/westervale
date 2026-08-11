// ===== WESTERVALE animations.js — counters, sidebar, ambient, transitions =====

// Animated number counter
function animateCounter(el) {
    const target = parseFloat(el.dataset.target);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const duration = parseInt(el.dataset.duration || '1400', 10);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';

    if (isNaN(target)) return;

    const start = performance.now();
    const from = 0;

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = from + (target - from) * eased;
        el.textContent = prefix + value.toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }) + suffix;
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

function initCounters() {
    document.querySelectorAll('.counter').forEach(el => {
        if (el.dataset.done) return;
        el.dataset.done = '1';
        animateCounter(el);
    });
}

// Intersection observer to trigger counters when scrolled into view
const counterObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            initCountersFor(entry.target);
            counterObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.2 });

function initCountersFor(scope) {
    // The observed element may itself be a .counter (not a container).
    const isCounter = scope.classList && scope.classList.contains('counter');
    const counters = isCounter ? [scope] : scope.querySelectorAll('.counter');
    counters.forEach(el => {
        if (el.dataset.done) return;
        el.dataset.done = '1';
        animateCounter(el);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // Auto-run counters already in view
    document.querySelectorAll('.counter:not([data-done])').forEach(el => counterObserver.observe(el));
    // Safety net: animate any counter the observer missed so values are never left at 0
    window.setTimeout(() => initCounters(), 2500);
});

// ===== Sidebar =====
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('show');
}

// ===== Ambient theme =====
function getTheme() {
    try {
        const m = document.cookie.match(/(?:^|;\s*)theme=([^;]+)/);
        return m ? m[1] : (localStorage.getItem('theme') || 'dark');
    } catch (e) {
        return 'dark';
    }
}

function initAmbient() {
    const saved = getTheme();
    document.documentElement.dataset.theme = saved === 'light' ? 'light' : 'dark';
}

initAmbient();

setInterval(function () {
    const t = getTheme() === 'light' ? 'light' : 'dark';
    if (document.documentElement.getAttribute('data-theme') !== t) {
        document.documentElement.setAttribute('data-theme', t);
    }
}, 800);

// ===== Fade-in on scroll (progressive enhancement) =====
document.addEventListener('DOMContentLoaded', () => {
    const els = document.querySelectorAll('.fade-in:not(.d1):not(.d2):not(.d3):not(.d4):not(.d5)');
    if (!('IntersectionObserver' in window)) {
        els.forEach(el => el.classList.add('visible'));
        return;
    }
    const obs = new IntersectionObserver(entries => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('visible');
                obs.unobserve(e.target);
            }
        });
    }, { threshold: 0.1 });
    els.forEach(el => obs.observe(el));
});
