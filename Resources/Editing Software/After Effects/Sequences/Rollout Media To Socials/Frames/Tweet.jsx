// ==========================
// Read frame paths from temp file
// ==========================
var tmpFile = File("/tmp/ae_frame_paths.txt");
if (!tmpFile.exists) {
    alert("Missing input paths file: " + tmpFile.fsName);
    throw new Error("Missing input paths");
}

tmpFile.open("r");
var framePaths = [];
while (!tmpFile.eof) {
    var line = tmpFile.readln();
    line = line.replace(/^\s+|\s+$/g, ""); // trim
    if (line.length > 0) framePaths.push(line);
}
tmpFile.close();

// Validate
if (framePaths.length !== 4) {
    alert("Expected 4 frame paths, got " + framePaths.length);
    throw new Error("Invalid input paths");
}

// ==========================
// Import footage function (silent unless error)
// ==========================
function importFootage(filePath) {
    var f = new File(filePath);
    if (!f.exists) {
        alert("File does not exist: " + filePath);
        return null;
    }

    try {
        var importOpts = new ImportOptions(f);
        importOpts.importAs = ImportAsType.FOOTAGE;
        return app.project.importFile(importOpts);
    } catch (e) {
        alert("Failed to import file: " + filePath + "\nError: " + e.toString());
        return null;
    }
}

// ==========================
// Get target comp
// ==========================
var targetCompName = "Editing Tweets";
var comp = null;

for (var i = 1; i <= app.project.numItems; i++) {
    if (app.project.item(i) instanceof CompItem &&
        app.project.item(i).name === targetCompName) {

        comp = app.project.item(i);
        break;
    }
}

if (!comp) {
    alert("Composition '" + targetCompName + "' not found.");
    throw new Error("Comp not found");
}

// ==========================
// Layer finder
// ===========================
function getLayerByName(comp, name) {
    for (var i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === name) return comp.layer(i);
    }
    return null;
}

// ==========================
// Apply footage to Frame layers
// ===========================
for (var i = 0; i < 4; i++) {
    var templateLayerName = "Frame " + (i + 1);
    var templateLayer = getLayerByName(comp, templateLayerName);
    if (!templateLayer) continue;

    var footage = importFootage(framePaths[i]);
    if (!footage) continue;

    var newLayer = comp.layers.add(footage);
    newLayer.moveAfter(templateLayer);
    newLayer.trackMatteType = TrackMatteType.ALPHA;
    templateLayer.enabled = false;

    // Fit scale/position
    var tScale = templateLayer.property("Scale").value;
    var tPos   = templateLayer.property("Position").value;
    var scaleX = (templateLayer.width  / newLayer.width)  * (tScale[0] / 100) * 100;
    var scaleY = (templateLayer.height / newLayer.height) * (tScale[1] / 100) * 100;

    newLayer.property("Scale").setValue([scaleX, scaleY]);
    newLayer.property("Position").setValue(tPos);

    // Match timeline duration of template
    newLayer.startTime = templateLayer.inPoint;
    newLayer.outPoint  = templateLayer.outPoint;
}

// ==========================
// Fully silent — no alerts on completion
// ==========================