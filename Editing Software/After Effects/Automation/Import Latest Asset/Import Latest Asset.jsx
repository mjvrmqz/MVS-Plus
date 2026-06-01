(function () {
    if (!$.global.__IMPORT_IMAGE_FOLDER__) {
        var chosen = Folder.selectDialog("Choose image import folder");
        if (!chosen) { alert("No folder selected."); return; }
        $.global.__IMPORT_IMAGE_FOLDER__ = chosen;
    }
    var folder = $.global.__IMPORT_IMAGE_FOLDER__;
    app.beginUndoGroup("Import Latest Image and Tag Chapter");
    var files = folder.getFiles(function (f) {
        return f instanceof File && /\.(jpg|jpeg|png|webp|gif|heic)$/i.test(f.name);
    });
    if (files.length === 0) { alert("No image files found!"); app.endUndoGroup(); return; }
    files.sort(function (a, b) { return b.modified.getTime() - a.modified.getTime(); });
    var latestImage = files[0];
    var proj = app.project || app.newProject();
    function findFolderByName(parentFolder, name) {
        for (var i = 1; i <= parentFolder.numItems; i++) {
            var item = parentFolder.item(i);
            if (item instanceof FolderItem && item.name === name) return item;
        }
        return null;
    }
    var projectFolder = findFolderByName(proj.rootFolder, "Project");
    var dashboardFolder = projectFolder ? findFolderByName(projectFolder, "Dashboard") : null;
    var assetsFolder = dashboardFolder ? findFolderByName(dashboardFolder, "Assets") : null;
    if (!assetsFolder) { alert("Could not find Project/Dashboard/Assets folder!"); app.endUndoGroup(); return; }
    var importOptions = new ImportOptions(latestImage);
    var importedFile = proj.importFile(importOptions);
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) { alert("No active composition!"); app.endUndoGroup(); return; }
    importedFile.label = comp.label;
    importedFile.parentFolder = assetsFolder;
    var newLayer = comp.layers.add(importedFile);
    newLayer.label = comp.label;
    app.endUndoGroup();
})();
