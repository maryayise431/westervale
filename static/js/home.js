// ===== THEME TOGGLE =====
function getTheme() {
    try {
        const m = document.cookie.match(/(?:^|;\s*)theme=([^;]+)/);
        return m ? m[1] : (localStorage.getItem('theme') || 'dark');
    } catch (e) {
        return 'dark';
    }
}

function saveTheme(t) {
    try { localStorage.setItem('theme', t); } catch (e) {}
    document.cookie = 'theme=' + t + '; path=/; max-age=31536000; SameSite=Lax';
}

function toggleTheme() {
    const html = document.documentElement;
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';

    html.setAttribute('data-theme', next);
    saveTheme(next);
    updateThemeIcon();
}

function updateThemeIcon() {
    const icons = document.querySelectorAll('.theme-icon');
    if (!icons.length) return;
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    icons.forEach(icon => {
        icon.className = 'theme-icon ' + (isDark ? 'ri-moon-line' : 'ri-sun-line');
    });
}

const savedTheme = getTheme();
document.documentElement.setAttribute('data-theme', savedTheme);
updateThemeIcon();

setInterval(function () {
    const t = getTheme() === 'light' ? 'light' : 'dark';
    if (document.documentElement.getAttribute('data-theme') !== t) {
        document.documentElement.setAttribute('data-theme', t);
        updateThemeIcon();
    }
}, 800);

// ===== MOBILE MENU =====
function toggleMenu() {
    const links = document.getElementById('navLinks');
    const icon = document.getElementById('menuIcon');
    links.classList.toggle('active');
    icon.className = links.classList.contains('active') ? 'ri-close-line' : 'ri-menu-line';
}

// Close menu on link click
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', () => {
        document.getElementById('navLinks').classList.remove('active');
        document.getElementById('menuIcon').className = 'ri-menu-line';
    });
});

// ===== CATEGORY FILTER =====
const filterPills = document.querySelectorAll('.filter-pill');

function applyFilter(filter) {
    filterPills.forEach(p => p.classList.toggle('active', p.dataset.filter === filter));
    document.querySelectorAll('.investment-card').forEach(card => {
        const match = filter === 'all' || card.dataset.category === filter;
        card.classList.toggle('hidden', !match);
    });
}

filterPills.forEach(pill => {
    pill.addEventListener('click', () => applyFilter(pill.dataset.filter));
});
// Stocks is the default category

applyFilter('stocks');

// ===== SCROLL ANIMATIONS =====
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

// ===== BACK TO TOP =====
const backToTop = document.getElementById('backToTop');

window.addEventListener('scroll', () => {
    backToTop.classList.toggle('visible', window.pageYOffset > 300);
});

backToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// ===== PARTICLES =====
const canvas = document.getElementById('particles');
const ctx = canvas.getContext('2d');
let particles = [];
let mouse = { x: null, y: null };

function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

window.addEventListener('mousemove', (e) => {
    mouse.x = e.x;
    mouse.y = e.y;
});

class Particle {
    constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2 + 0.5;
        this.speedX = Math.random() * 0.5 - 0.25;
        this.speedY = Math.random() * 0.5 - 0.25;
        this.opacity = Math.random() * 0.5 + 0.2;
    }

    update() {
        this.x += this.speedX;
        this.y += this.speedY;

        if (this.x > canvas.width) this.x = 0;
        if (this.x < 0) this.x = canvas.width;
        if (this.y > canvas.height) this.y = 0;
        if (this.y < 0) this.y = canvas.height;

        if (mouse.x != null) {
            const dx = mouse.x - this.x;
            const dy = mouse.y - this.y;
            const distance = Math.sqrt(dx * dx + dy * dy);
            if (distance < 100) {
                const force = (100 - distance) / 100;
                this.x -= dx * force * 0.02;
                this.y -= dy * force * 0.02;
            }
        }
    }

    draw() {
        ctx.fillStyle = `rgba(137, 81, 41, ${this.opacity})`;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
    }
}

function initParticles() {
    particles = [];
    const count = Math.min(window.innerWidth / 10, 100);
    for (let i = 0; i < count; i++) {
        particles.push(new Particle());
    }
}
initParticles();

function animateParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach(p => {
        p.update();
        p.draw();
    });

    particles.forEach((a, i) => {
        particles.slice(i + 1).forEach(b => {
            const dx = a.x - b.x;
            const dy = a.y - b.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < 150) {
                ctx.strokeStyle = `rgba(137, 81, 41, ${0.1 * (1 - dist / 150)})`;
                ctx.lineWidth = 0.5;
                ctx.beginPath();
                ctx.moveTo(a.x, a.y);
                ctx.lineTo(b.x, b.y);
                ctx.stroke();
            }
        });
    });

    requestAnimationFrame(animateParticles);
}
animateParticles();

// ===== SMOOTH SCROLL FOR ANCHOR LINKS =====
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// ===== CARD BUTTON INTERACTIONS =====
document.querySelectorAll('.card-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const original = this.innerHTML;
        this.innerHTML = '<i class="ri-loader-4-line"></i> Loading...';
        this.style.opacity = '0.7';

        setTimeout(() => {
            this.innerHTML = '<i class="ri-verified-badge-line"></i> Coming Soon';
                    this.style.background = 'var(--primary)';
            this.style.color = 'white';
            this.style.borderColor = 'transparent';

            setTimeout(() => {
                this.innerHTML = original;
                this.style.background = '';
                this.style.color = '';
                this.style.borderColor = '';
                this.style.opacity = '1';
            }, 2000);
        }, 800);
    });
});

// ===== NEWSLETTER FORM =====
const newsletterForm = document.getElementById('newsletterForm');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const btn = this.querySelector('button');
        btn.innerHTML = '<i class="ri-check-line"></i> Subscribed!';
        setTimeout(() => {
            btn.innerHTML = '<i class="ri-send-plane-line"></i> Subscribe';
        }, 2500);
        this.reset();
    });
}

// ===== CONTACT FORM =====
const contactForm = document.getElementById('contactForm');
if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const btn = this.querySelector('button');
        btn.innerHTML = '<i class="ri-check-line"></i> Message Sent!';
        setTimeout(() => {
            btn.innerHTML = 'Send Message <i class="ri-send-plane-line"></i>';
        }, 2500);
        this.reset();
    });
}

// ===== SCROLL PROGRESS + NAVBAR SHRINK =====
const scrollProgress = document.getElementById('scrollProgress');
const navbar = document.querySelector('.navbar');

window.addEventListener('scroll', () => {
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const scrolled = docHeight > 0 ? (window.pageYOffset / docHeight) * 100 : 0;
    scrollProgress.style.width = scrolled + '%';
    navbar.classList.toggle('scrolled', window.pageYOffset > 40);
}, { passive: true });

// ===== STAGGERED REVEAL =====
document.querySelectorAll('.reveal-stagger').forEach(group => {
    const items = group.querySelectorAll('.fade-in');
    items.forEach((el, i) => {
        el.style.transitionDelay = `${i * 90}ms`;
    });
});

// Cards reveal with a slight cascade even when not inside .reveal-stagger
document.querySelectorAll('.investments-grid, .about-grid, .contact-info-cards').forEach(grid => {
    const cards = grid.querySelectorAll('.fade-in');
    cards.forEach((el, i) => {
        el.style.transitionDelay = `${(i % 4) * 90}ms`;
    });
});

// ===== 3D TILT ON INVESTMENT CARDS =====
document.querySelectorAll('.investment-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card.style.transform = `perspective(900px) rotateX(${-y * 6}deg) rotateY(${x * 6}deg) translateY(-4px)`;
    });
    card.addEventListener('mouseleave', () => {
        card.style.transform = '';
    });
});

// ===== ANIMATED COUNTERS =====
function animateCounter(el) {
    const target = parseFloat(el.dataset.counter);
    const duration = 1600;
    const start = performance.now();
    el.textContent = '0';

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(tick);
        else el.textContent = target;
    }
    requestAnimationFrame(tick);
}

const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            animateCounter(entry.target);
            counterObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.6 });

document.querySelectorAll('[data-counter]').forEach(el => counterObserver.observe(el));

// ===== ORB PARALLAX =====
const orbs = document.querySelectorAll('.orb');

window.addEventListener('mousemove', (e) => {
    const nx = (e.clientX / window.innerWidth) - 0.5;
    const ny = (e.clientY / window.innerHeight) - 0.5;

    orbs.forEach((orb, i) => {
        const depth = (i + 1) * 20;
        orb.style.transform = `translate(${nx * depth}px, ${ny * depth}px)`;
    });
}, { passive: true });

// ===== HERO TITLE GLOW =====
const heroTitle = document.querySelector('.hero h1');
if (heroTitle) {
    setInterval(() => {
        heroTitle.classList.remove('glow-pulse');
        void heroTitle.offsetWidth;
        heroTitle.classList.add('glow-pulse');
    }, 6000);
}
