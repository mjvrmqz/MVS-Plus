// Content script: runs inside pages
document.addEventListener("click", (e) => {
    if (e.target.tagName === "IMG") {
        console.log("Image clicked:", e.target.src);

        // Send clicked image URL to background
        chrome.runtime.sendMessage({ imageUrl: e.target.src });
    }
});

// Listen for messages from background (example)
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === "highlight") {
        document.body.style.border = "5px solid red";
    }
});
