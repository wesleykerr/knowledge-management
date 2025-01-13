// Save options to chrome.storage
const saveOptions = async () => {
    const apiKey = document.getElementById('apiKey').value;
    const apiUrl = document.getElementById('apiUrl').value;
    await chrome.storage.local.set({
        apiKey: apiKey,
        apiUrl: apiUrl
    });

    // Update status to let user know options were saved
    const status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(() => {
        status.textContent = '';
    }, 2000);
};

// Restore options from chrome.storage
const restoreOptions = async () => {
    try {
        const result = await chrome.storage.local.get({
            apiKey: '',
            apiUrl: 'http://192.168.86.191:5001/api'
        });
        document.getElementById('apiKey').value = result.apiKey;
        document.getElementById('apiUrl').value = result.apiUrl;
    } catch (error) {
        console.error('Error loading options:', error);
    }
};

// Move event listeners inside DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    restoreOptions();
    document.getElementById('save').addEventListener('click', saveOptions);
});