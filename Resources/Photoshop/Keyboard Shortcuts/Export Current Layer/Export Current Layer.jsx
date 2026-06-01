#target photoshop

function main() {

    if (app.documents.length === 0) {
        alert("No document open.");
        return;
    }

    var originalDoc = app.activeDocument;
    var layer = originalDoc.activeLayer;

    if (!layer || layer.isBackgroundLayer) {
        alert("Select a non-background layer.");
        return;
    }

    var topFolder = Folder.selectDialog("Select the top folder to scan");
    if (!topFolder) {
        alert("No folder selected.");
        return;
    }

    function findMatchingFolder(baseFolder, targetName) {
        var folders = baseFolder.getFiles(function(f) {
            return f instanceof Folder;
        });

        for (var i = 0; i < folders.length; i++) {

            if (folders[i].name === targetName) {
                return folders[i];
            }

            var result = findMatchingFolder(folders[i], targetName);
            if (result) return result;
        }

        return null;
    }

    var exportFolder = findMatchingFolder(topFolder, layer.name);

    if (!exportFolder) {
        exportFolder = new Folder(topFolder.fsName + "/" + layer.name);
        exportFolder.create();
    }

    // Create temp document
    var tempDoc = app.documents.add(
        originalDoc.width,
        originalDoc.height,
        originalDoc.resolution,
        "tempExport",
        NewDocumentMode.RGB,
        DocumentFill.TRANSPARENT
    );

    // IMPORTANT: switch back to original document
    app.activeDocument = originalDoc;

    // Duplicate into temp
    layer.duplicate(tempDoc, ElementPlacement.PLACEATBEGINNING);

    // Switch to temp doc to trim + export
    app.activeDocument = tempDoc;
    tempDoc.trim(TrimType.TRANSPARENT);

    var exportFile = new File(exportFolder.fsName + "/" + layer.name + ".png");

    var options = new ExportOptionsSaveForWeb();
    options.format = SaveDocumentType.PNG;
    options.PNG8 = false;
    options.transparency = true;
    options.quality = 100;

    tempDoc.exportDocument(exportFile, ExportType.SAVEFORWEB, options);
    tempDoc.close(SaveOptions.DONOTSAVECHANGES);

    app.activeDocument = originalDoc;

    alert("Export complete to: " + exportFolder.fsName);
}

main();