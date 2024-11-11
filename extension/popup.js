document.addEventListener('DOMContentLoaded', function() {
    const button = document.getElementById('bookmarkButton');
    const status = document.getElementById('status');

    function showStatus(message, type) {
        status.textContent = message;
        status.className = type;
        status.style.display = 'block';
    }

    function setButtonState(isProcessing) {
        button.disabled = isProcessing;
        button.innerHTML = isProcessing ?
            `<svg class="animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...` :
            `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
            </svg>
            Save to Obsidian`;
    }

    button.addEventListener('click', async function() {
        setButtonState(true);
        showStatus('Processing bookmark...', 'processing');

        try {
            chrome.runtime.sendMessage({action: "processBookmark"});
        } catch (error) {
            showStatus('Failed to process bookmark', 'error');
            setButtonState(false);
        }
    });

    // Listen for response from background script
    chrome.runtime.onMessage.addListener((message) => {
        if (message.action === "bookmarkProcessed") {
            setButtonState(false);
            if (message.success) {
                showStatus('Bookmark saved successfully!', 'success');
                setTimeout(() => window.close(), 1500);
            } else {
                showStatus(`Error: ${message.error}`, 'error');
            }
        }
    });
});