// Save options to chrome.storage
const saveOptions = async () => {
    const apiKey = document.getElementById('apiKey').value;
    await chrome.storage.local.set({ apiKey: apiKey });

    // Update status to let user know options were saved
    const status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(() => {
        status.textContent = '';
    }, 2000);
};

// Restore options from chrome.storage
const restoreOptions = async () => {
    const result = await chrome.storage.local.get(['apiKey']);
    document.getElementById('apiKey').value = result.apiKey || '';
};

document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('save').addEventListener('click', saveOptions);