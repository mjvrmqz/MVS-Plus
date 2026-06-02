// ==========================
// Read Before/After paths
// ==========================
var tmpFile = File("/tmp/ae_before_after_paths.txt");
if (!tmpFile.exists) {
    alert("Missing input paths file: " + tmpFile.fsName);
    throw new Error("Missing input paths");
}

tmpFile.open("r");
var beforePath = tmpFile.readln();
var afterPath  = tmpFile.readln();
tmpFile.close();

// Validate
if (!beforePath || !afterPath) {
    alert("Paths not provided in temp file.");
    throw new Error("Invalid paths");
}

// ==========================
// Import footage function (handles spaces correctly)
// ==========================
function importFootage(filePath) {
    var f = new File(filePath); // do not add extra quotes
    if (!f.exists) {
        alert("File does not exist: " + filePath);
        return null;
    }

    try {
        var importOpts = new ImportOptions(f);
        importOpts.importAs = ImportAsType.FOOTAGE;
        return app.project.importFile(importOpts); // silent import
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
    if (app.project.item(i) instanceof CompItem && app.project.item(i).name === targetCompName) {
        comp = app.project.item(i);
        break;
    }
}

if (!comp) {
    alert("Composition '" + targetCompName + "' not found.");
    throw new Error("Comp not found");
}

// ==========================
// Get reference layers for duration
// ==========================
function getLayerByName(comp, name) {
    for (var i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === name) return comp.layer(i);
    }
    return null;
}

var beforeTemplate = getLayerByName(comp, "Before");
var afterTemplate  = getLayerByName(comp, "After");

if (!beforeTemplate || !afterTemplate) {
    alert("Template layers 'Before' or 'After' not found.");
    throw new Error("Template layers missing");
}

// Duration from start of "Before" to end of "After"
var startTime = beforeTemplate.inPoint;
var endTime   = afterTemplate.outPoint;

// ==========================
// Import before/after footage
// ==========================
var beforeFootage = importFootage(beforePath);
var afterFootage  = importFootage(afterPath);

// ==========================
// Add footage with track matte
// ==========================
function addWithTrackMatte(comp, templateLayerName, footage) {
    if (!footage) return;

    var templateLayer = getLayerByName(comp, templateLayerName);
    if (!templateLayer) return;

    var newLayer = comp.layers.add(footage);
    newLayer.moveAfter(templateLayer);
    newLayer.trackMatteType = TrackMatteType.ALPHA;
    templateLayer.enabled = false;

    // Fit scale/position
    var tScale = templateLayer.property("Scale").value;
    var tPos   = templateLayer.property("Position").value;
    var scaleX = (templateLayer.width / newLayer.width) * (tScale[0] / 100) * 100;
    var scaleY = (templateLayer.height / newLayer.height) * (tScale[1] / 100) * 100;
    newLayer.property("Scale").setValue([scaleX, scaleY]);
    newLayer.property("Position").setValue(tPos);

    // Match duration from Before template to After template
    newLayer.startTime = startTime;
    newLayer.outPoint = endTime;
}

// ==========================
// Apply before/after layers
// ==========================
addWithTrackMatte(comp, "Before", beforeFootage);
addWithTrackMatte(comp, "After", afterFootage);

// ==========================
// Fully silent — no completion alert
// ==========================