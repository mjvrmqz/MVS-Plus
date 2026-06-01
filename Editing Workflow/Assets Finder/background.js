// Sleep helper
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// Helper to create a tab and return its ID
function createTab(url, windowId = null) {
    return new Promise(resolve => {
        chrome.tabs.create({ url, windowId }, tab => resolve(tab.id));
    });
}

// Helper to group a single tab (return groupId)
function groupTab(tabId) {
    return new Promise(resolve => {
        chrome.tabs.group({ tabIds: tabId }, groupId => resolve(groupId));
    });
}

// Helper to set a tab's title (affects window title)
function setTabTitle(tabId, title) {
    chrome.scripting.executeScript({
        target: { tabId },
        func: (newTitle) => { document.title = newTitle; },
        args: [title]
    });
}

// Main function
async function createTabGroups() {
    // Create a new window
    let win = await new Promise(resolve => {
        chrome.windows.create({ focused: true }, w => resolve(w));
    });
    const windowId = win.id;

    // Groups configuration
    const groups = [
        { title: "Puppet", baseQuery: "puppet", tabs: 10, color: "purple" },
        { title: "Icon", baseQuery: "icon", tabs: 10, color: "orange" },
        { title: "Background", baseQuery: "background", tabs: 10, color: "green" }
    ];

    for (let g of groups) {
        // First tab in the group
        let firstUrl = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(g.baseQuery + " 0")}`;
        let firstTabId = await createTab(firstUrl, windowId);
        let groupId = await groupTab(firstTabId);

        // Set group title and color
        chrome.tabGroups.update(groupId, { title: g.title, color: g.color });

        // Set first tab title
        setTabTitle(firstTabId, `${g.title} 1`);

        // Remaining tabs
        for (let i = 1; i < g.tabs; i++) {
            let url = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(g.baseQuery + " " + i)}`;
            let tabId = await createTab(url, windowId);
            await chrome.tabs.group({ groupId: groupId, tabIds: tabId });
            setTabTitle(tabId, `${g.title} ${i+1}`);
            await sleep(250); // delay between tabs
        }

        console.log(`Group ${g.title} created`);
        await sleep(2000); // delay between groups
    }

    // Rename first tab in the window to "Asset Finder"
    setTabTitle(win.tabs[0].id, "Asset Finder");

    console.log("All tab groups created successfully!");
}

// Run when extension icon is clicked
chrome.action.onClicked.addListener(() => {
    createTabGroups();
});
