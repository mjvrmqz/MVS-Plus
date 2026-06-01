#target photoshop
app.activeDocument.suspendHistory("Import Latest Asset", "main()");

function main() {
    var doc = app.activeDocument;

    // Replace this with the hardcoded path (from your appender)
    // It can safely include spaces, parentheses, quotes, etc.
    var shortcutFilePath = "/Users/mjvrmqz/Downloads/Video Editing Assets/Niches/YouTube Documentary/Projects/Project 59673/Puppet/C5PT03.jpg";

    if (!shortcutFilePath || shortcutFilePath === "") {
        alert("No file path provided!");
        return;
    }

    // Ensure path is safe for File object
    var file = new File(shortcutFilePath);
    if (!file.exists) {
        alert("File does not exist: " + shortcutFilePath);
        return;
    }

    // Extract file name without extension
    var fileName = file.name.replace(/\.[^\.]+$/, '');
    var targetArtboard = null;

    // Find artboard with the same name as file
    for (var i = 0; i < doc.layerSets.length; i++) {
        if (doc.layerSets[i].name === fileName) {
            targetArtboard = doc.layerSets[i];
            break;
        }
    }

    if (!targetArtboard) {
        alert("No artboard named '" + fileName + "' found!");
        return;
    }

    // Place file safely
    var placedLayer = placeFile(file);

    // Move the placed layer inside the target artboard
    placedLayer.move(targetArtboard, ElementPlacement.INSIDE);
}

function placeFile(file) {
    var idPlc = charIDToTypeID("Plc ");
    var desc = new ActionDescriptor();
    desc.putPath(charIDToTypeID("null"), new File(file.fsName));
    desc.putEnumerated(charIDToTypeID("FTcs"), charIDToTypeID("QCSt"), charIDToTypeID("Qcsa"));
    executeAction(idPlc, desc, DialogModes.NO);
    return app.activeDocument.activeLayer;
}