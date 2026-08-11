// ===== AUTH AMBIENT: gold particles + orb parallax =====
(function() {
    const canvas = document.getElementById('authParticles');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let particles = [];
    let mouse = { x: null, y: null };

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    window.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });

    function spawn() {
        particles = [];
        const count = Math.min(Math.floor(window.innerWidth / 14), 80);
        for (let i = 0; i < count; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                size: Math.random() * 1.8 + 0.4,
                speedX: (Math.random() - 0.5) * 0.4,
                speedY: (Math.random() - 0.5) * 0.4,
                opacity: Math.random() * 0.5 + 0.15
            });
        }
    }
    spawn();
    window.addEventListener('resize', spawn);

    function frame() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        particles.forEach(p => {
            p.x += p.speedX;
            p.y += p.speedY;
            if (p.x < -20) p.x = canvas.width + 20;
            if (p.x > canvas.width + 20) p.x = -20;
            if (p.y < -20) p.y = canvas.height + 20;
            if (p.y > canvas.height + 20) p.y = -20;

            if (mouse.x != null) {
                const dx = mouse.x - p.x;
                const dy = mouse.y - p.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    const force = (120 - dist) / 120;
                    p.x -= dx * force * 0.03;
                    p.y -= dy * force * 0.03;
                }
            }

            ctx.fillStyle = `rgba(212, 165, 116, ${p.opacity})`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        });

        requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);

    // Orb parallax
    const orbs = document.querySelectorAll('.auth-orb');
    window.addEventListener('mousemove', (e) => {
        const nx = (e.clientX / window.innerWidth) - 0.5;
        const ny = (e.clientY / window.innerHeight) - 0.5;
        orbs.forEach((orb, i) => {
            const depth = (i + 1) * 18;
            orb.style.transform = `translate(${nx * depth}px, ${ny * depth}px)`;
        });
    }, { passive: true });
})();
