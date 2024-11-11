// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');

  // Create context menu
  chrome.contextMenus.create({
    id: 'saveToObsidian',
    title: 'Save to Obsidian',
    contexts: ['page', 'link']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'saveToObsidian') {
    const url = info.linkUrl || info.pageUrl;
    const title = tab.title;

    try {
      const response = await fetch('http://localhost:5001/api/bookmark', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url,
          title: title
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      // Show success notification without icon
      chrome.notifications.create({
        type: 'basic',
        title: 'Bookmark Saved',
        message: 'Successfully saved to Obsidian',
        iconUrl: chrome.runtime.getURL('default_icon.png')
      });

    } catch (error) {
      console.error('Error:', error);
      // Show error notification without icon
      chrome.notifications.create({
        type: 'basic',
        title: 'Error',
        message: 'Failed to save bookmark',
        iconUrl: chrome.runtime.getURL('default_icon.png')
      });
    }
  }
});

// Listen for messages from the popup or content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "processBookmark") {
        // Get the active tab
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            const activeTab = tabs[0];
            // Inject content script to get HTML
            chrome.scripting.executeScript({
                target: {tabId: activeTab.id},
                function: getPageContent
            }, (results) => {
                const htmlContent = results[0].result;
                sendToAPI(activeTab.url, htmlContent);
            });
        });
    }
    return true;
});

// Function to be injected into the page
function getPageContent() {
    return document.documentElement.outerHTML;
}

// Function to get API key from storage
async function getApiKey() {
    const result = await chrome.storage.local.get(['apiKey']);
    return result.apiKey;
}

// Function to set API key
async function setApiKey(apiKey) {
    await chrome.storage.local.set({ apiKey: apiKey });
}

// Modified sendToAPI function
async function sendToAPI(url, htmlContent) {
    const apiKey = await getApiKey();
    if (!apiKey) {
        throw new Error('API key not configured');
    }

    try {
        console.log('Sending request to API:', {
            url: url,
            htmlContentLength: htmlContent?.length
        });

        const response = await fetch('http://localhost:5001/api/bookmark', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
                'Origin': chrome.runtime.getURL('')
            },
            credentials: 'omit',
            body: JSON.stringify({
                url: url,
                html_content: htmlContent
            })
        });

        console.log('API Response status:', response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API Error:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('API Success:', result);

        chrome.runtime.sendMessage({
            action: "bookmarkProcessed",
            success: true,
            data: result
        });
    } catch (error) {
        console.error('API Call failed:', error);
        chrome.runtime.sendMessage({
            action: "bookmarkProcessed",
            success: false,
            error: error.message
        });
    }
}