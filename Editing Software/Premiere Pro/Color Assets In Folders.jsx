var project = app.project;

// Color label numbers: Premiere uses 0–15
var templateColor = 14; // 15th color (0-indexed)
var projectColor = 4;   // 5th color (0-indexed)

// Recursive function to apply color to folder contents
function setFolderColor(folderItem, color) {
    for (var i = 0; i < folderItem.children.numItems; i++) {
        var item = folderItem.children[i];

        if (item.type === ProjectItemType.BIN) {
            // If folder, recurse
            setFolderColor(item, color);
        } else {
            // Set the color label on the item
            item.setColorLabel(color);
        }
    }
}

// Loop through top-level items
for (var i = 0; i < project.rootItem.children.numItems; i++) {
    var item = project.rootItem.children[i];

    if (item.type === ProjectItemType.BIN) {
        var name = item.name.toLowerCase();

        if (name.indexOf("template") !== -1) {
            setFolderColor(item, templateColor);
        } else if (name.indexOf("project") !== -1) {
            setFolderColor(item, projectColor);
        }
    }
}