(function () {
    'use strict';

    function debounce(fn, ms) {
        let timer;
        return function () {
            const ctx = this, args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () { fn.apply(ctx, args); }, ms);
        };
    }

    function setError(input, message) {
        const box = document.querySelector('[data-error-for="' + input.dataset.live + '"]');
        if (!box) return;
        if (message) {
            box.textContent = message;
            input.classList.add('input-invalid');
        } else {
            box.textContent = '';
            input.classList.remove('input-invalid');
        }
    }

    var commonPasswords = [
        'password', 'password1', '123456', '12345678', 'qwerty', 'qwerty123',
        'abc123', 'iloveyou', 'admin', 'welcome', 'letmein', '123456789',
        'password123', '1q2w3e4r', 'admin123', '123123', 'monkey', 'dragon',
        'football', 'summer2026', '1234567890', 'zaq12wsx',
    ];

    var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    function validateUsername(input) {
        const v = (input.value || '').trim();
        if (!v) return setError(input, 'Username is required.');
        if (v.length < 3) return setError(input, 'Username must be at least 3 characters.');
        if (v.length > 30) return setError(input, 'Username must be at most 30 characters.');
        if (!/^[A-Za-z0-9_.-]+$/.test(v)) return setError(input, 'Only letters, numbers, dots, underscores and dashes are allowed.');
        setError(input, '');
        return true;
    }

    function validateEmail(input, checkUnique) {
        const v = (input.value || '').trim();
        if (!v) return setError(input, 'Email address is required.');
        if (!EMAIL_RE.test(v)) return setError(input, 'Enter a valid email address.');
        if (!checkUnique) { setError(input, ''); return true; }
        fetch(input.dataset.checkUrl + '?email=' + encodeURIComponent(v))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                setError(input, data.available ? '' : data.error);
            })
            .catch(function () { });
        return true;
    }

    function validatePassword(input) {
        const v = input.value || '';
        const field = input.form ? input.form.querySelector('[data-live="username"], [data-live="email"]') : null;
        const text = ((field && field.value) || '').toLowerCase();
        if (!v) return setError(input, 'Password is required.');
        if (v.length < 8) return setError(input, 'Password must be at least 8 characters.');
        if (/^\d+$/.test(v)) return setError(input, 'Password can\'t be entirely numeric.');
        if (commonPasswords.indexOf(v.toLowerCase()) !== -1) return setError(input, 'This password is too common.');
        if (text && text.length >= 3 && v.toLowerCase().indexOf(text) !== -1) return setError(input, 'Password is too similar to your username or email.');
        setError(input, '');
        return true;
    }

    function validateConfirm(passwordInput, confirmInput) {
        if (!confirmInput.value) return setError(confirmInput, 'Please confirm your password.');
        if (confirmInput.value !== passwordInput.value) {
            return setError(confirmInput, 'The two passwords do not match.');
        }
        setError(confirmInput, '');
        return true;
    }

    var validationMap = {
        username: function (i) { return validateUsername(i); },
        email: function (i) {
            const checkUnique = !!i.dataset.checkUrl && !i.dataset.skipUnique;
            return validateEmail(i, checkUnique);
        },
        password: function (i) { return validatePassword(i); },
        confirm: function (i) {
            const p = i.form.querySelector('[data-live="password"]');
            return validateConfirm(p, i);
        },
    };

    function initAuthForm(form) {
        const live = form.querySelectorAll('[data-live]');
        live.forEach(function (input) {
            const type = input.dataset.live;
            const run = function () {
                const fn = validationMap[type];
                if (fn) fn(input);
                if (type === 'confirm') {
                    const p = form.querySelector('[data-live="password"]');
                    if (p && p.value && p.value !== input.value) setError(input, 'The two passwords do not match.');
                }
            };
            input.addEventListener('blur', run);
            input.addEventListener('input', debounce(run, type === 'email' ? 350 : 150));
            if (type === 'password') initStrengthMeter(input);
        });

        form.addEventListener('submit', function (e) {
            let firstBad = null;
            live.forEach(function (input) {
                const fn = validationMap[input.dataset.live];
                const ok = fn ? fn(input) : true;
                if (!ok && !firstBad) firstBad = input;
            });
            if (firstBad) {
                e.preventDefault();
                firstBad.focus();
            }
        });
    }

    function initStrengthMeter(input) {
        const bar = document.getElementById('strengthBar');
        if (!bar) return;
        input.addEventListener('input', function () {
            const v = input.value;
            let score = 0;
            if (v.length >= 8) score++;
            if (v.length >= 12) score++;
            if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
            if (/\d/.test(v)) score++;
            if (/[^A-Za-z0-9]/.test(v)) score++;
            const colors = ['#EF4444', '#F59E0B', '#F59E0B', '#10B981', '#10B981'];
            const pct = Math.min(100, score * 20);
            bar.style.width = pct + '%';
            bar.style.background = colors[score] || '#10B981';
        });
    }

    function initOTP(form) {
        const wrap = form.querySelector('[data-otp-wrap]');
        const hidden = document.getElementById('id_code');
        const btn = document.getElementById('verifyBtn');
        if (!wrap || !hidden) return;
        const boxes = Array.prototype.slice.call(wrap.querySelectorAll('.otp-digit'));

        boxes.forEach(function (box, i) {
            box.addEventListener('input', function () {
                box.value = box.value.replace(/[^0-9]/g, '').slice(0, 1);
                if (box.value && i < boxes.length - 1) boxes[i + 1].focus();
                sync();
            });
            box.addEventListener('keydown', function (e) {
                if (e.key === 'Backspace' && !box.value && i > 0) boxes[i - 1].focus();
            });
            box.addEventListener('paste', function (e) {
                e.preventDefault();
                const digits = (e.clipboardData.getData('text') || '').replace(/[^0-9]/g, '').slice(0, 6);
                digits.split('').forEach(function (d, j) {
                    if (boxes[j]) { boxes[j].value = d; }
                });
                if (digits.length) {
                    const next = Math.min(digits.length, 5);
                    boxes[next].focus();
                }
                sync();
            });
        });

        function sync() {
            hidden.value = boxes.map(function (b) { return b.value; }).join('');
            boxes.forEach(function (b) { b.classList.toggle('filled', !!b.value); });
            if (btn) btn.disabled = hidden.value.length !== 6;
        }
    }

    function initEmailHint() {
        // Wire AJAX check URL for email fields that want uniqueness checks.
        document.querySelectorAll('[data-live="email"]').forEach(function (input) {
            if (!input.dataset.checkUrl) {
                var form = input.closest('form');
                if (form && form.id === 'registerForm') {
                    input.dataset.checkUrl = '/check-email/';
                }
            }
        });
    }

    function initEmailPrompt() {
        const overlay = document.getElementById('emailPromptOverlay');
        if (!overlay) return;
        const input = document.getElementById('emailPromptInput');
        const error = document.getElementById('emailPromptError');
        const cancel = document.getElementById('emailPromptCancel');
        const ok = document.getElementById('emailPromptOk');
        let targetForm = null;

        function close() {
            overlay.classList.remove('open');
            document.body.style.overflow = '';
        }

        cancel.addEventListener('click', close);
        overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
        input.addEventListener('keydown', function (e) { if (e.key === 'Enter') ok.click(); });

        document.querySelectorAll('form button[type="submit"]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                const form = btn.form;
                if (!form) return;
                const emailField = form.querySelector('[data-live="email"]');
                if (emailField && !(emailField.value || '').trim()) {
                    e.preventDefault();
                    targetForm = form;
                    error.textContent = '';
                    input.value = '';
                    overlay.classList.add('open');
                    document.body.style.overflow = 'hidden';
                    setTimeout(function () { input.focus(); }, 60);
                }
            });
        });

        ok.addEventListener('click', function () {
            const v = (input.value || '').trim();
            if (!v || !EMAIL_RE.test(v)) {
                error.textContent = 'Enter a valid email address.';
                input.focus();
                return;
            }
            const form = targetForm;
            if (!form) { close(); return; }
            const emailField = form.querySelector('[data-live="email"]');
            if (emailField) emailField.value = v;
            close();
            form.requestSubmit();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initEmailHint();
        initEmailPrompt();
        var forms = document.querySelectorAll('form');
        forms.forEach(function (form) {
            if (form.id === 'registerForm') initAuthForm(form);
            if (form.id === 'loginForm' || form.id === 'forgotForm') initAuthForm(form);
            if (form.id === 'resetForm') initAuthForm(form);
            if (form.id === 'otpForm') initOTP(form);
        });
    });
})();
