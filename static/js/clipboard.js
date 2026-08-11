// ===== WESTERVALE clipboard.js — copy wallet address =====

function copyText(text, btn) {
    const fallback = () => {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand('copy'); } catch (e) { /* noop */ }
        document.body.removeChild(ta);
    };

    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => flash(btn)).catch(fallback);
    } else {
        fallback();
        flash(btn);
    }
}

function flash(btn) {
    if (!btn) return;
    const original = btn.innerHTML;
    btn.innerHTML = '<i class="ri-check-line"></i>';
    btn.classList.add('copied');
    btn.setAttribute('aria-label', 'Copied');
    setTimeout(() => {
        btn.innerHTML = original;
        btn.classList.remove('copied');
    }, 1800);
    showToast('Wallet address copied to clipboard.', 'success', 'Copied');
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-copy]').forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            const target = document.querySelector(btn.dataset.copyTarget);
            const text = (target && target.textContent.trim()) || btn.dataset.copyText || '';
            if (text) copyText(text, btn);
        });
    });
});
