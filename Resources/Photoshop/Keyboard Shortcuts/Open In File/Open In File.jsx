#target photoshop

// Recursively search for a PSD file with a given name
function findPSDFile(folder, fileName) {
    var files = folder.getFiles();
    for (var i = 0; i < files.length; i++) {
        var f = files[i];
        if (f instanceof Folder) {
            var found = findPSDFile(f, fileName);
            if (found) return found;
        } else if (f instanceof File) {
            if (f.name.toLowerCase() === (fileName.toLowerCase() + ".psd")) {
                return f;
            }
        }
    }
    return null;
}

// Find the topmost artboard for a given layer
function getArtboardForLayer(layer) {
    var lastLayerSet = null;
    while (layer && layer.typename !== "Document") {
        if (layer.typename === "LayerSet") {
            lastLayerSet = layer; // remember the last LayerSet
        }
        layer = layer.parent;
    }
    return lastLayerSet; // returns the topmost LayerSet as "artboard"
}

// Main
function main() {
    if (!app.documents.length) {
        alert("No document open.");
        return;
    }

    var selLayer = app.activeDocument.activeLayer;
    var artboard = getArtboardForLayer(selLayer);

    if (!artboard) {
        alert("Could not detect an artboard from the selected layer.");
        return;
    }

    var artboardName = artboard.name;

    var folder = Folder.selectDialog("Select a folder to scan for PSDs");
    if (!folder) return;

    var foundFile = findPSDFile(folder, artboardName);

    if (foundFile) {
        app.open(foundFile);
    } else {
        var createNew = confirm("No PSD named '" + artboardName + "' found. Would you like to create a new one?");
        if (createNew) {
            app.documents.add(1920, 1080, 72, artboardName, NewDocumentMode.RGB, DocumentFill.TRANSPARENT);
        }
    }
}

main();