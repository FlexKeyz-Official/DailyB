// Main JavaScript file for Cron Job Manager

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Setup form validation
    setupFormValidation();
    
    // Setup auto-refresh for dashboard
    setupAutoRefresh();
    
    // Setup confirmation dialogs
    setupConfirmationDialogs();
    
    // Setup cron expression helpers
    setupCronHelpers();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Real-time cron expression validation
    const cronInput = document.getElementById('cron_expression');
    if (cronInput) {
        cronInput.addEventListener('input', function() {
            validateCronExpression(this);
        });
    }
    
    // URL validation
    const urlInput = document.getElementById('url');
    if (urlInput) {
        urlInput.addEventListener('input', function() {
            validateUrl(this);
        });
    }
}

/**
 * Validate cron expression
 */
function validateCronExpression(input) {
    const value = input.value.trim();
    const parts = value.split(' ');
    
    if (parts.length !== 5) {
        setInputError(input, 'Cron expression must have exactly 5 parts');
        return false;
    }
    
    // Basic validation for each part
    const patterns = [
        /^(\*|[0-5]?[0-9]|(\*\/[0-9]+)|([0-5]?[0-9]-[0-5]?[0-9])|([0-5]?[0-9](,[0-5]?[0-9])*))$/, // minute
        /^(\*|[01]?[0-9]|2[0-3]|(\*\/[0-9]+)|([01]?[0-9]-[01]?[0-9]|2[0-3])|([01]?[0-9]|2[0-3])(,[01]?[0-9]|2[0-3])*)$/, // hour
        /^(\*|[01]?[0-9]|2[0-9]|3[01]|(\*\/[0-9]+)|([01]?[0-9]-[01]?[0-9]|2[0-9]|3[01])|([01]?[0-9]|2[0-9]|3[01])(,[01]?[0-9]|2[0-9]|3[01])*)$/, // day
        /^(\*|[01]?[0-9]|1[0-2]|(\*\/[0-9]+)|([01]?[0-9]-[01]?[0-9]|1[0-2])|([01]?[0-9]|1[0-2])(,[01]?[0-9]|1[0-2])*)$/, // month
        /^(\*|[0-6]|(\*\/[0-9]+)|([0-6]-[0-6])|([0-6](,[0-6])*))$/ // day of week
    ];
    
    let isValid = true;
    for (let i = 0; i < 5; i++) {
        if (!patterns[i].test(parts[i])) {
            isValid = false;
            break;
        }
    }
    
    if (isValid) {
        setInputSuccess(input);
        return true;
    } else {
        setInputError(input, 'Invalid cron expression format');
        return false;
    }
}

/**
 * Validate URL
 */
function validateUrl(input) {
    const value = input.value.trim();
    
    if (!value) {
        clearInputValidation(input);
        return;
    }
    
    try {
        new URL(value);
        if (value.startsWith('http://') || value.startsWith('https://')) {
            setInputSuccess(input);
            return true;
        } else {
            setInputError(input, 'URL must start with http:// or https://');
            return false;
        }
    } catch (e) {
        setInputError(input, 'Please enter a valid URL');
        return false;
    }
}

/**
 * Set input error state
 */
function setInputError(input, message) {
    input.classList.remove('is-valid');
    input.classList.add('is-invalid');
    
    let feedback = input.parentNode.querySelector('.invalid-feedback');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        input.parentNode.appendChild(feedback);
    }
    feedback.textContent = message;
}

/**
 * Set input success state
 */
function setInputSuccess(input) {
    input.classList.remove('is-invalid');
    input.classList.add('is-valid');
    
    const feedback = input.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

/**
 * Clear input validation state
 */
function clearInputValidation(input) {
    input.classList.remove('is-valid', 'is-invalid');
    
    const feedback = input.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.remove();
    }
}

/**
 * Setup auto-refresh for dashboard
 */
function setupAutoRefresh() {
    // Only auto-refresh on the dashboard page
    if (window.location.pathname === '/' || window.location.pathname === '/index') {
        // Refresh every 60 seconds
        setTimeout(function() {
            // Only refresh if no modals are open
            const openModals = document.querySelectorAll('.modal.show');
            if (openModals.length === 0) {
                window.location.reload();
            }
        }, 60000);
    }
}

/**
 * Setup confirmation dialogs
 */
function setupConfirmationDialogs() {
    // Add confirmation to delete buttons
    document.querySelectorAll('a[href*="/delete_job/"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this job? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
    
    // Add confirmation to toggle buttons
    document.querySelectorAll('a[href*="/toggle_job/"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            const isActivating = link.querySelector('i').classList.contains('bi-play');
            const action = isActivating ? 'activate' : 'deactivate';
            if (!confirm(`Are you sure you want to ${action} this job?`)) {
                e.preventDefault();
            }
        });
    });
    
    // Add confirmation to run now buttons
    document.querySelectorAll('a[href*="/run_job/"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            if (!confirm('Run this job now?')) {
                e.preventDefault();
            }
        });
    });
    
    // Add confirmation to clear history button
    document.querySelectorAll('a[href*="/clear_history"]').forEach(function(link) {
        link.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to clear all history? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Setup cron expression helpers
 */
function setupCronHelpers() {
    // Cron preset buttons
    document.querySelectorAll('.cron-preset').forEach(function(button) {
        button.addEventListener('click', function() {
            const cronInput = document.getElementById('cron_expression');
            if (cronInput) {
                cronInput.value = this.dataset.cron;
                validateCronExpression(cronInput);
            }
        });
    });
    
    // Show/hide payload section based on HTTP method
    const methodSelect = document.getElementById('method');
    const payloadSection = document.getElementById('payloadSection');
    
    if (methodSelect && payloadSection) {
        function togglePayloadSection() {
            const method = methodSelect.value;
            if (['POST', 'PUT', 'PATCH'].includes(method)) {
                payloadSection.style.display = 'block';
            } else {
                payloadSection.style.display = 'none';
            }
        }
        
        methodSelect.addEventListener('change', togglePayloadSection);
        togglePayloadSection(); // Initial check
    }
}

/**
 * Show loading state for buttons
 */
function showButtonLoading(button, text = 'Loading...') {
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${text}`;
}

/**
 * Hide loading state for buttons
 */
function hideButtonLoading(button, originalText) {
    button.disabled = false;
    button.innerHTML = originalText;
}

/**
 * Display toast notification
 */
function showToast(message, type = 'info') {
    // Create toast element
    const toastHtml = `
        <div class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2 text-${type === 'error' ? 'danger' : type}"></i>
                <strong class="me-auto">Notification</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showToast('Copied to clipboard!', 'success');
    }).catch(function(err) {
        console.error('Failed to copy text: ', err);
        showToast('Failed to copy to clipboard', 'error');
    });
}

// Export functions for global use
window.CronJobManager = {
    showToast,
    copyToClipboard,
    formatDate,
    validateCronExpression,
    validateUrl
};
