// Smart Relink — Relinks or deletes missing footage by scanning a chosen folder
(function RelinkOrDeleteMissing() {
    app.beginUndoGroup("Relink or Delete Missing");
    var searchRoot = Folder.selectDialog("Select root folder to scan");
    if (!searchRoot) { alert("No folder selected."); return; }
    function findFileRecursive(folder, targetName, targetSize) {
        var entries = folder.getFiles();
        for (var i = 0; i < entries.length; i++) {
            var entry = entries[i];
            if (entry instanceof File) {
                if (entry.name.toLowerCase() === targetName.toLowerCase()) {
                    if (targetSize === -1 || entry.length === targetSize) return entry;
                }
            } else if (entry instanceof Folder) {
                var result = findFileRecursive(entry, targetName, targetSize);
                if (result) return result;
            }
        }
        return null;
    }
    var relinked = []; var deleted = []; var checked = 0;
    for (var i = app.project.numItems; i >= 1; i--) {
        var item = app.project.item(i);
        if (item instanceof FootageItem && item.mainSource instanceof FileSource && item.footageMissing === true) {
            checked++;
            var originalSize = -1;
            try { originalSize = item.mainSource.file.length; } catch(e) {}
            var foundFile = findFileRecursive(searchRoot, item.name, originalSize);
            if (foundFile) { item.replace(foundFile); relinked.push(item.name); }
            else { deleted.push(item.name); item.remove(); }
        }
    }
    alert("Checked: " + checked + "\nRelinked: " + relinked.length + "\nDeleted: " + deleted.length);
    app.endUndoGroup();
})();
