(function () {

    // ===== Import latest image and tag chapter (session folder) =====

    // --- SESSION-PERSISTENT FOLDER ---
    if (!$.global.__IMPORT_IMAGE_FOLDER__) {
        var chosen = Folder.selectDialog("Choose image import folder");
        if (!chosen) {
            alert("No folder selected.");
            return;
        }
        $.global.__IMPORT_IMAGE_FOLDER__ = chosen;
    }

    var folder = $.global.__IMPORT_IMAGE_FOLDER__;

    // === MAIN ===
    app.beginUndoGroup("Import Latest Image and Tag Chapter");

    // Get image files
    var files = folder.getFiles(function (f) {
        return f instanceof File && /\.(jpg|jpeg|png|webp|gif|heic)$/i.test(f.name);
    });

    if (files.length === 0) {
        alert("No image files found in selected folder!");
        app.endUndoGroup();
        return;
    }

    // Sort by modified date (newest first)
    files.sort(function (a, b) {
        return b.modified.getTime() - a.modified.getTime();
    });

    var latestImage = files[0];

    var proj = app.project || app.newProject();

    // --- Folder finder ---
    function findFolderByName(parentFolder, name) {
        for (var i = 1; i <= parentFolder.numItems; i++) {
            var item = parentFolder.item(i);
            if (item instanceof FolderItem && item.name === name) {
                return item;
            }
        }
        return null;
    }

    // --- Locate Project → Dashboard → Assets ---
    var projectFolder = findFolderByName(proj.rootFolder, "Project");
    var dashboardFolder = projectFolder ? findFolderByName(projectFolder, "Dashboard") : null;
    var assetsFolder = dashboardFolder ? findFolderByName(dashboardFolder, "Assets") : null;

    if (!assetsFolder) {
        alert("Could not find Project/Dashboard/Assets folder structure in project!");
        app.endUndoGroup();
        return;
    }

    // --- Import ---
    var importOptions = new ImportOptions(latestImage);
    var importedFile = proj.importFile(importOptions);

    // --- Active comp required ---
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) {
        alert("No active composition selected!");
        app.endUndoGroup();
        return;
    }

    // Match label colors
    importedFile.label = comp.label;
    importedFile.parentFolder = assetsFolder;

    // Add as layer
    var newLayer = comp.layers.add(importedFile);
    newLayer.label = comp.label;

    // --- Tag Chapter ---
    function tagChapter() {
        try {
            if (newLayer && newLayer.source) {
                var fileName = newLayer.source.name.toUpperCase();
                var match = fileName.match(/C([1-5])/);

                if (match) {
                    var chapterNum = parseInt(match[1], 10);

                    // Add marker at time 0
                    var markerProp = newLayer.property("Marker");
                    if (markerProp) {
                        var marker = new MarkerValue("Chapter " + chapterNum);
                        markerProp.setValueAtTime(0, marker);
                    }

                    // Rename layer
                    newLayer.name = "[C" + chapterNum + "] " + newLayer.name;
                }
                return;
            }
        } catch (e) {}

        // Retry until layer is ready
        app.scheduleTask(tagChapter, 50, false);
    }

    tagChapter();

    app.endUndoGroup();

})();