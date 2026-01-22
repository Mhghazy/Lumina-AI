/**
 * Email Sender Module
 * Handles sending emails via the Lumina Python Backend
 */

const EMAIL_CONFIG = {
    backendUrl: (window.BACKEND_API_URL || 'http://localhost:5000') + '/api/send-email'
};

function setupEmailListeners() {
    const openBtn = document.getElementById('openEmailModalBtn');
    if (openBtn) {
        openBtn.addEventListener('click', openEmailModal);
    }

    // Checkbox listener for updating counters if needed
    // (Similar to WhatsApp, we can rely on reading checked boes when opening)
}

function openEmailModal() {
    const modal = document.getElementById('emailModal');
    if (!modal) return;

    const selectedCheckboxes = document.querySelectorAll('.client-checkbox:checked');
    const count = selectedCheckboxes.length;

    document.getElementById('emailSelectedCount').textContent = count;
    modal.style.display = 'flex';
}

function closeEmailModal() {
    const modal = document.getElementById('emailModal');
    if (modal) modal.style.display = 'none';
}

async function sendBatchEmail() {
    const subject = document.getElementById('emailSubject').value;
    const body = document.getElementById('emailBody').value;
    const fileInput = document.getElementById('emailAttachments');
    const statusDiv = document.getElementById('emailStatus');

    if (!subject || !body) {
        alert('Please enter a subject and body.');
        return;
    }

    const selectedCheckboxes = document.querySelectorAll('.client-checkbox:checked');
    if (selectedCheckboxes.length === 0) {
        alert('No clients selected.');
        return;
    }

    // Prepare Recipients
    const recipients = Array.from(selectedCheckboxes).map(cb => ({
        email: cb.dataset.email || '', // Ensure dataset.email exists in creating the table
        name: cb.dataset.name
    })).filter(r => r.email && r.email.includes('@')); // Basic validation

    if (recipients.length === 0) {
        alert('Selected clients do not have valid email addresses.');
        return;
    }

    // UI Updates
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `<div style="color:blue">⏳ Sending to ${recipients.length} recipients...</div>`;
    document.getElementById('emailSendBtn').disabled = true;

    try {
        const formData = new FormData();
        formData.append('subject', subject);
        formData.append('body', body);
        formData.append('recipients', JSON.stringify(recipients));

        // Attach files
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('attachments', fileInput.files[i]);
        }

        const response = await fetch(EMAIL_CONFIG.backendUrl, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            statusDiv.innerHTML = `<div style="color:green">✅ ${result.message}</div>`;
            setTimeout(() => {
                closeEmailModal();
                statusDiv.style.display = 'none';
                document.getElementById('emailSendBtn').disabled = false;
            }, 3000);
        } else {
            throw new Error(result.error || 'Unknown Error');
        }

    } catch (err) {
        console.error(err);
        statusDiv.innerHTML = `<div style="color:red">❌ Error: ${err.message}</div>`;
        document.getElementById('emailSendBtn').disabled = false;

        if (err.message.includes('SMTP Password')) {
            alert('CONFIGURATION ERROR:\nThe backend is missing the SMTP Password.\nPlease check the project .env file and add SMTP_PASSWORD=...');
        }
    }
}

// Expose globally
window.openEmailModal = openEmailModal;
window.closeEmailModal = closeEmailModal;
window.sendBatchEmail = sendBatchEmail;
window.setupEmailListeners = setupEmailListeners;

document.addEventListener('DOMContentLoaded', setupEmailListeners);
