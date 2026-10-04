// Shared app-level behaviour for Profit Optimizer pages.

function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

function setBusy(element, busy) {
    var el = typeof element === 'string' ? document.querySelector(element) : element;
    if (!el) return;
    if (busy) {
        el.classList.add('is-loading');
        el.setAttribute('aria-busy', 'true');
        el.disabled = true;
    } else {
        el.classList.remove('is-loading');
        el.removeAttribute('aria-busy');
        el.disabled = false;
    }
}

function _triggerButton(options) {
    if (options && options.button) {
        var el = options.button;
        return typeof el === 'string' ? document.querySelector(el) : el;
    }
    var active = document.activeElement;
    if (active && active.tagName === 'BUTTON') {
        return active;
    }
    return null;
}

function csrfFetch(url, options) {
    options = options || {};
    var method = (options.method || 'GET').toUpperCase();
    if (method === 'GET' || method === 'HEAD' || method === 'OPTIONS') {
        return fetch(url, options);
    }
    var token = getCsrfToken();
    if (token) {
        var headers = new Headers(options.headers || {});
        if (!headers.has('X-CSRFToken')) {
            headers.set('X-CSRFToken', token);
        }
        options.headers = headers;
    }
    var busyBtn = _triggerButton(options);
    setBusy(busyBtn, true);
    return fetch(url, options)
        .then(function (response) {
            setBusy(busyBtn, false);
            return response;
        })
        .catch(function (error) {
            setBusy(busyBtn, false);
            throw error;
        });
}

function _labelOf(input) {
    var lbl = input.getAttribute('data-label');
    if (lbl) return lbl;
    var raw = input.getAttribute('name') || input.id || 'This field';
    return raw.replace(/[_-]+/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
}

function validationMessage(input) {
    var value = input.value.trim();
    if (input.hasAttribute('required') && !value) {
        return input.getAttribute('data-error-required') || _labelOf(input) + ' is required';
    }
    if (input.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        return input.getAttribute('data-error-email') || 'Please enter a valid email address';
    }
    if (input.hasAttribute('min') && value !== '' && !isNaN(parseFloat(value)) && parseFloat(value) < parseFloat(input.min)) {
        return input.getAttribute('data-error-min') || _labelOf(input) + ' must be at least ' + input.min;
    }
    if (input.hasAttribute('max') && value !== '' && !isNaN(parseFloat(value)) && parseFloat(value) > parseFloat(input.max)) {
        return input.getAttribute('data-error-max') || _labelOf(input) + ' must be at most ' + input.max;
    }
    var same = input.getAttribute('data-same');
    if (same) {
        var other = document.querySelector('[name="' + same + '"]');
        if (other && input.value !== other.value) {
            return input.getAttribute('data-error-same') || 'Values do not match';
        }
    }
    return '';
}

function validateForm(form) {
    var fields = form.querySelectorAll('input, select, textarea');
    var firstBad = null;
    var hasError = false;
    fields.forEach(function (field) {
        if (field.disabled || field.type === 'hidden' || field.type === 'submit' ||
            field.type === 'button' || field.type === 'reset') {
            return;
        }
        var wrap = field.closest('.form-group') || field.parentElement;
        var feedback = wrap ? wrap.querySelector('.invalid-feedback') : null;
        var message = validationMessage(field);
        if (message) {
            hasError = true;
            field.classList.add('is-invalid');
            field.setAttribute('aria-invalid', 'true');
            if (feedback) {
                feedback.textContent = message;
            } else if (wrap) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = message;
                feedback.setAttribute('role', 'alert');
                wrap.appendChild(feedback);
            }
            if (!firstBad) {
                firstBad = field;
            }
        } else if (field.classList.contains('is-invalid')) {
            field.classList.remove('is-invalid');
            field.removeAttribute('aria-invalid');
            if (feedback) {
                feedback.remove();
            }
        }
    });
    if (firstBad) {
        firstBad.focus();
    }
    return !hasError;
}

function initFormValidation() {
    document.querySelectorAll('form[data-validate]').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!validateForm(form)) {
                event.preventDefault();
            }
        });
        form.addEventListener('input', function () {
            if (form.querySelector('.is-invalid')) {
                validateForm(form);
            }
        });
        form.addEventListener('change', function () {
            if (form.querySelector('.is-invalid')) {
                validateForm(form);
            }
        });
    });
}

function initLucide() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function initTopNav() {
    var hamburger = document.getElementById('navHamburger');
    var panel = document.getElementById('navPanel');
    var userToggle = document.getElementById('navUserToggle');
    var userMenu = document.getElementById('navUserMenu');

    function closeNav() {
        if (panel) {
            panel.classList.remove('open');
            if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
        }
        if (userMenu) {
            userMenu.classList.remove('open');
            if (userToggle) userToggle.setAttribute('aria-expanded', 'false');
        }
    }

    if (hamburger && panel) {
        hamburger.addEventListener('click', function (e) {
            e.stopPropagation();
            var open = panel.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (userMenu) {
                userMenu.classList.remove('open');
                if (userToggle) userToggle.setAttribute('aria-expanded', 'false');
            }
        });
        panel.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', closeNav);
        });
    }

    if (userToggle && userMenu) {
        userToggle.addEventListener('click', function (e) {
            e.stopPropagation();
            var open = userMenu.classList.toggle('open');
            userToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (panel) {
                panel.classList.remove('open');
                if (hamburger) hamburger.setAttribute('aria-expanded', 'false');
            }
        });
        userMenu.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', closeNav);
        });
    }

    document.addEventListener('click', function (e) {
        if (!userMenu) return;
        if (!userMenu.contains(e.target) && !(userToggle && userToggle.contains(e.target))) {
            closeNav();
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeNav();
    });
}

function setThemeLabel(isDark) {
    var toggle = document.getElementById('themeToggle');
    if (!toggle) return;
    toggle.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    var label = toggle.querySelector('span');
    if (label && !label.querySelector('i')) {
        label.textContent = isDark ? 'Light mode' : 'Dark mode';
    }
}

function initThemeToggle() {
    var toggle = document.getElementById('themeToggle');

    if (toggle) {
        setThemeLabel(document.documentElement.getAttribute('data-theme') === 'dark');

        toggle.addEventListener('click', function () {
            var root = document.documentElement;
            var isDark = root.getAttribute('data-theme') === 'dark';

            if (isDark) {
                root.removeAttribute('data-theme');
            } else {
                root.setAttribute('data-theme', 'dark');
            }

            try {
                localStorage.setItem('profit-theme', isDark ? 'light' : 'dark');
            } catch (e) {}

            setThemeLabel(!isDark);

            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        });
    }
}

function showToast(message, type) {
    type = type || 'info';
    var container = document.getElementById('toastContainer');
    if (!container) return;

    var icons = { success: 'check-circle', error: 'x-circle', warning: 'alert-triangle', info: 'info' };
    var toast = document.createElement('div');
    toast.className = 'toast ' + type;
    // Failures and warnings interrupt; confirmations wait their turn. A toast
    // that only lands in the polite queue can be missed entirely, which is
    // exactly the case where the operator most needs to read it.
    if (type === 'error' || type === 'warning') {
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
    } else {
        toast.setAttribute('role', 'status');
    }

    toast.append(Object.assign(document.createElement('i'), { 'data-lucide': icons[type] || 'info' }));

    var label = document.createElement('span');
    label.textContent = message;
    toast.appendChild(label);

    var close = document.createElement('button');
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss notification');
    close.innerHTML = '&times;';
    toast.appendChild(close);

    container.appendChild(toast);

    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    var dismiss = function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    };
    var timer = setTimeout(dismiss, type === 'error' ? 8000 : 4000);
    close.addEventListener('click', function () {
        clearTimeout(timer);
        dismiss();
    });
}

// Native confirm() is a browser dialog in a product that has its own visual
// world; it reads as an interruption from somewhere else. This is the same
// plate as every other dialog, so a destructive action looks like the product.
window.confirmAction = function (message, options) {
    options = options || {};
    return new Promise(function (resolve) {
        var dialog = document.createElement('div');
        dialog.className = 'modal modal-confirm';
        dialog.innerHTML =
            '<div class="modal-content modal-content-confirm">' +
            '<div class="modal-header">' +
            '<h2 class="modal-title"></h2>' +
            '<button type="button" class="close" aria-label="Close dialog">&times;</button>' +
            '</div>' +
            '<div class="modal-body"><p class="confirm-message"></p></div>' +
            '<div class="modal-footer">' +
            '<button type="button" class="btn btn-secondary confirm-cancel"></button>' +
            '<button type="button" class="btn btn-danger confirm-accept"></button>' +
            '</div></div>';

        var title = dialog.querySelector('.modal-title');
        var body = dialog.querySelector('.confirm-message');
        var cancel = dialog.querySelector('.confirm-cancel');
        var accept = dialog.querySelector('.confirm-accept');

        title.textContent = options.title || 'Are you sure?';
        body.textContent = message;
        cancel.textContent = options.cancelLabel || 'Cancel';
        accept.textContent = options.confirmLabel || 'Delete';

        var opener = document.activeElement;
        function done(result) {
            dialog.remove();
            document.body.style.overflow = 'auto';
            if (opener && document.contains(opener)) opener.focus();
            resolve(result);
        }

        cancel.addEventListener('click', function () { done(false); });
        accept.addEventListener('click', function () { done(true); });
        dialog.querySelector('.close').addEventListener('click', function () { done(false); });
        dialog.addEventListener('mousedown', function (event) {
            if (event.target === dialog) done(false);
        });
        dialog.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                event.stopPropagation();
                done(false);
            }
        });

        document.body.appendChild(dialog);
        document.body.style.overflow = 'hidden';
        accept.focus();
    });
};

var FOCUSABLE = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])', 'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])'
].join(',');

function isVisible(el) {
    if (!el || !el.getClientRects().length) return false;
    return window.getComputedStyle(el).visibility !== 'hidden';
}

function openDialogs() {
    return Array.prototype.filter.call(
        document.querySelectorAll('.modal, .modal-overlay'),
        isVisible
    );
}

// A modal that lets Tab walk out of it into the page behind is not a modal.
// This keeps focus on the plate, and hands focus back to whatever opened it.
function initModalBehavior() {
    document.querySelectorAll('.modal').forEach(function (modal) {
        if (!modal.hasAttribute('role')) {
            modal.setAttribute('role', 'dialog');
        }
        modal.setAttribute('aria-modal', 'true');
        if (!modal.getAttribute('aria-label')) {
            var heading = modal.querySelector('.modal-header h2, .modal-header h3, .modal-title');
            if (heading && heading.textContent.trim()) {
                if (heading.id) {
                    modal.setAttribute('aria-labelledby', heading.id);
                } else {
                    modal.setAttribute('aria-label', heading.textContent.trim());
                }
            }
        }
    });

    // Close buttons are spans in the page markup, which is not reachable by
    // keyboard and is not announced as a control. Promote them.
    document.querySelectorAll('.modal .close, .modal .close-modal').forEach(function (el) {
        if (el.tagName !== 'BUTTON') {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = el.className;
            button.setAttribute('aria-label', 'Close dialog');
            button.innerHTML = el.innerHTML;
            el.parentNode.replaceChild(button, el);
        } else {
            el.setAttribute('type', 'button');
            if (!el.getAttribute('aria-label')) el.setAttribute('aria-label', 'Close dialog');
        }
    });

    var lastFocused = null;

    function topDialog() {
        var open = openDialogs();
        return open.length ? open[open.length - 1] : null;
    }

    function focusablesIn(dialog) {
        return Array.prototype.filter.call(dialog.querySelectorAll(FOCUSABLE), isVisible);
    }

    // Page scripts toggle display directly, so watch the tree instead of
    // patching every one of their open/close paths.
    var observer = new MutationObserver(function () {
        var open = openDialogs();
        if (open.length) {
            var dialog = open[open.length - 1];
            if (dialog !== lastFocused) {
                lastFocused = dialog;
                if (!dialog.hasAttribute('data-focus-seeded')) {
                    dialog.setAttribute('data-focus-seeded', 'true');
                    var fields = focusablesIn(dialog);
                    (fields[1] || fields[0] || dialog).focus();
                }
            }
        } else if (lastFocused) {
            var opener = lastFocused;
            lastFocused = null;
            document.querySelectorAll('[data-focus-seeded]').forEach(function (el) {
                el.removeAttribute('data-focus-seeded');
            });
            var restore = opener.__opener;
            if (restore && document.contains(restore)) {
                restore.focus();
            } else {
                var skip = document.getElementById('main');
                if (skip) skip.focus({ preventScroll: true });
            }
        }
    });
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class', 'hidden'] });

    document.addEventListener('mousedown', function (event) {
        var dialog = topDialog();
        if (!dialog) return;
        var trigger = event.target.closest('[data-modal-open], .btn, button');
        if (trigger) {
            openDialogs().forEach(function (open) { open.__opener = trigger; });
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            var dialog = topDialog();
            if (!dialog) return;
            event.stopPropagation();
            var closeBtn = dialog.querySelector('.close-modal, .close');
            if (closeBtn) {
                closeBtn.click();
            } else {
                dialog.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
            return;
        }

        if (event.key !== 'Tab') return;
        var dialog = topDialog();
        if (!dialog) return;
        var fields = focusablesIn(dialog);
        if (!fields.length) {
            event.preventDefault();
            dialog.focus();
            return;
        }
        var first = fields[0];
        var last = fields[fields.length - 1];
        if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    // Dismiss toasts (including ones created by page scripts)
    document.addEventListener('click', function (event) {
        var target = event.target;
        if (target && target.classList && target.classList.contains('toast-close')) {
            var toast = target.closest('.toast');
            if (toast) {
                toast.remove();
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    initLucide();
    initTopNav();
    initFormValidation();
    initThemeToggle();
    initModalBehavior();
});