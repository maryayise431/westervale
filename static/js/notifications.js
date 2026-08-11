// ===== WESTERVALE notifications.js — toast system =====

function showToast(message, type = 'info', title = '') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'ri-checkbox-circle-line',
        error: 'ri-error-warning-line',
        info: 'ri-information-line',
        warning: 'ri-alert-line',
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.setAttribute('role', 'status');
    toast.innerHTML = `
        <i class="${icons[type] || icons.info}"></i>
        <div>
            ${title ? `<strong>${title}</strong><br>` : ''}
            ${message}
        </div>
        <button class="toast-close" aria-label="Dismiss">&times;</button>
    `;

    container.appendChild(toast);

    const dismiss = () => {
        toast.classList.add('out');
        setTimeout(() => toast.remove(), 320);
    };

    toast.querySelector('.toast-close').addEventListener('click', dismiss);
    setTimeout(dismiss, 5200);
}

document.addEventListener('DOMContentLoaded', () => {
    // Serialize Django messages into toasts
    const dataEl = document.getElementById('djangoMessages');
    if (dataEl && dataEl.dataset.messages) {
        try {
            const messages = JSON.parse(dataEl.dataset.messages);
            messages.forEach(m => showToast(m.text, m.tags));
        } catch (e) { /* ignore malformed */ }
    }
});
