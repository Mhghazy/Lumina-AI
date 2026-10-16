/**
 * WhatsApp Automation Module
 * Handles sending messages via WhatsApp Web Direct Send (No API)
 */

// Configuration
const WHATSAPP_CONFIG = {
    senderPhone: '+201001611579'
};

// Ensure Supabase client is available (use 'sb' to avoid conflict with global 'supabase')
const sb = window.supabase || window.supabaseClient;

/**
 * Initializes the WhatsApp module
 */
async function initWhatsAppModule() {
    console.log('📱 WhatsApp Module Initialized (Direct Mode)');
    await ensureSenderClient();
    setupUIListeners();
}

/**
 * Ensures the system sender client exists in Supabase
 */
async function ensureSenderClient() {
    const senderPhone = WHATSAPP_CONFIG.senderPhone;
    console.log('Checking sender client:', senderPhone);

    try {
        if (!sb) return; // Guard if sb is not set
        const { data, error } = await sb
            .from('clients')
            .select('*')
            .eq('phone', senderPhone);

        if (error) throw error;

        if (!data || data.length === 0) {
            console.log('Sender not found. Creating...');
            const { error: insertError } = await sb.from('clients').insert([
                {
                    name: 'System Sender',
                    phone: senderPhone,
                    company: 'System',
                    category: 'Others',
                    email: 'sender@system.com',
                    website: '',
                    registration_date: new Date().toISOString().split('T')[0]
                }
            ]);

            if (insertError) throw insertError;
            console.log('✅ System Sender created successfully.');
        } else {
            console.log('✅ System Sender already exists.');
        }
    } catch (err) {
        console.error('❌ Error ensuring sender client:', err);
    }
}

/**
 * Sets up the global event listeners for the WhatsApp UI
 */
function setupUIListeners() {
    const openBtn = document.getElementById('openWhatsAppModalBtn');
    if (openBtn) {
        openBtn.addEventListener('click', openWhatsAppModal);
    }

    const sendBtn = document.getElementById('waSendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', startBatchSend);
    }
}

/**
 * Opens the WhatsApp Modal and prepares the selected clients
 */
function openWhatsAppModal() {
    const modal = document.getElementById('whatsappModal');
    if (!modal) return;

    // Using new checkbox class
    const selectedCheckboxes = document.querySelectorAll('.client-checkbox:checked');
    let count = selectedCheckboxes.length;

    document.getElementById('waSelectedCount').textContent = count;
    modal.style.display = 'flex';
}

/**
 * Closes the WhatsApp Modal
 */
function closeWhatsAppModal() {
    const modal = document.getElementById('whatsappModal');
    if (modal) modal.style.display = 'none';
}

/**
 * Normalizes phone number to international format
 */
function normalizePhone(phone) {
    if (!phone) return null;
    let p = phone.replace(/\D/g, '');

    // Eg: 01001611579 -> 201001611579
    if (p.startsWith('01')) {
        p = '20' + p.substring(1);
    } else if (p.startsWith('1') && p.length === 10) {
        p = '20' + p;
    }

    return p;
}

/**
 * Starts the batch sending process
 */
async function startBatchSend() {
    const message = document.getElementById('waMessageInput').value;
    const mediaFile = document.getElementById('waMediaInput').files[0];
    const logArea = document.getElementById('waLogArea');
    const progressBar = document.getElementById('waProgressBar');
    const progressFill = document.getElementById('waProgressFill');

    if (!message && !mediaFile) {
        alert('Please enter a message or select a file (Image/Video/Document).');
        return;
    }

    // Gather Clients
    let targetClients = [];

    const checkboxes = Array.from(document.querySelectorAll('.client-checkbox:checked'));
    if (checkboxes.length > 0) {
        targetClients = checkboxes.map(cb => ({
            name: cb.dataset.name,
            phone: cb.dataset.phone,
            id: cb.dataset.pk
        }));
    }

    if (targetClients.length === 0) {
        alert('No clients selected!');
        return;
    }

    // Reset UI
    logArea.innerHTML = '';
    logArea.style.display = 'block';
    progressBar.style.display = 'block';
    progressFill.style.width = '0%';

    let processed = 0;

    // Process Media (Clipboard logic for images)
    let clipboardSuccess = false;

    if (mediaFile) {
        if (mediaFile.type.startsWith('image/')) {
            try {
                await navigator.clipboard.write([
                    new ClipboardItem({
                        [mediaFile.type]: mediaFile
                    })
                ]);
                clipboardSuccess = true;
                logArea.innerHTML += `<div class="log-success">📋 Image copied! Press Ctrl+V in each tab.</div>`;
            } catch (err) {
                console.warn('Clipboard write failed:', err);
                logArea.innerHTML += `<div class="log-error">⚠️ Auto-copy failed. Attach manually.</div>`;
            }
        } else {
            logArea.innerHTML += `<div class="log-info">📁 File selected. Attach manually in each tab.</div>`;
        }
    }

    logArea.innerHTML += `<div>🚀 Starting batch send for ${targetClients.length} clients...</div>`;
    logArea.innerHTML += `<div class="log-info" style="color:orange">⚠️ IMPORTANT: Please allow popups for this site if multiple tabs don't open.</div>`;

    for (const client of targetClients) {
        const phone = normalizePhone(client.phone);
        if (!phone) {
            logArea.innerHTML += `<div class="log-error">❌ ${client.name}: Invalid Phone</div>`;
            processed++;
            continue;
        }

        try {
            const fullUrl = `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
            const newWindow = window.open(fullUrl, '_blank');

            // Check for popup blocker
            if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
                logArea.innerHTML += `<div class="log-error">🚫 ${client.name}: POPUP BLOCKED</div>`;
                alert(`⚠️ Popup Blocked!\n\nThe browser blocked opening the chat for ${client.name}.\n\nPlease look for the "Popup blocked" icon in your address bar (usually top right), click it, and select "Always allow popups and redirects" for this site.\n\nThen try again.`);
                break; // Stop the batch
            }

            logArea.innerHTML += `<div class="log-info">↗️ ${client.name}: Chat Opened</div>`;

            // Delay to prevent freezing and reduce likelihood of blocking
            await new Promise(r => setTimeout(r, 1500));

        } catch (err) {
            logArea.innerHTML += `<div class="log-error">❌ ${client.name}: Error - ${err.message}</div>`;
        }

        processed++;
        const percent = (processed / targetClients.length) * 100;
        progressFill.style.width = `${percent}%`;
    }

    logArea.innerHTML += `<div>🏁 Batch Complete.</div>`;

    if (mediaFile) {
        if (clipboardSuccess) {
            alert('MAGIC FEATURE ✨\n\nImage copied to clipboard!\nPress "Ctrl + V" in each WhatsApp tab to send.');
        } else {
            alert('Note: Please manually attach the selected file in each WhatsApp tab.');
        }
    }
}

// Make accessible globally
window.initWhatsAppModule = initWhatsAppModule;
window.openWhatsAppModal = openWhatsAppModal;
window.closeWhatsAppModal = closeWhatsAppModal;
