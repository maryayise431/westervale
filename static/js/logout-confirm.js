// ===== LOGOUT CONFIRMATION MODAL =====
function openLogoutModal() {
    const overlay = document.getElementById('logoutModal');
    if (overlay) {
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
}

function closeLogoutModal() {
    const overlay = document.getElementById('logoutModal');
    if (overlay) {
        overlay.classList.remove('open');
        document.body.style.overflow = '';
    }
}

document.addEventListener('click', (e) => {
    const overlay = document.getElementById('logoutModal');
    if (!overlay) return;
    if (e.target === overlay) closeLogoutModal();
    if (e.key === 'Escape') closeLogoutModal();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLogoutModal();
});
