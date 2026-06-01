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

// ==========================
// Extract 5-digit number from the Before file
// ==========================
var fileName = beforePath.split("/").pop(); // get just the file name
var match = fileName.match(/\d{5}/);        // match 5 digits
if (!match) {
    alert("Could not find a 5-digit number in file name: " + fileName);
    throw new Error("Number missing");
}
var number = match[0]; // e.g., "29834"

// ==========================
// Get target comp
// ==========================
var compName = "Editing Tweets";
var comp = null;
for (var i = 1; i <= app.project.numItems; i++) {
    if (app.project.item(i) instanceof CompItem && app.project.item(i).name === compName) {
        comp = app.project.item(i);
        break;
    }
}
if (!comp) {
    alert("Comp not found: " + compName);
    throw new Error("Comp missing");
}

// ==========================
// Find "Before & After" marker
// ==========================
var markerName = "Before & After";
var markerTime = null;
var markers = comp.markerProperty;
for (var i = 1; i <= markers.numKeys; i++) {
    if (markers.keyValue(i).comment === markerName) {
        markerTime = markers.keyTime(i);
        break;
    }
}
if (markerTime === null) {
    alert("Marker missing: " + markerName);
    throw new Error("Marker missing");
}

// ==========================
// Set work area: marker start → 1 min after
// ==========================
comp.workAreaStart = markerTime;
comp.workAreaDuration = 60; // 60 seconds

// ==========================
// Set output path
// ==========================
var outputFolder = "/Users/mjvrmqz/Downloads/Video Editing Assets/Tweets/Previews";
var outputFile = outputFolder + "/Video " + number + ".mov";

// ==========================
// Add to render queue and start render
// ==========================
var rqItem = app.project.renderQueue.items.add(comp);
rqItem.outputModule(1).file = new File(outputFile);
app.project.renderQueue.render(); // actually starts rendering

// ==========================
// Delete Processor files
// ==========================
try {
    var beforeFile = new File(beforePath);
    var afterFile  = new File(afterPath);

    if (beforeFile.exists) beforeFile.remove();
    if (afterFile.exists) afterFile.remove();
} catch (e) {
    alert("Failed to delete processor files:\n" + e.toString());
}

// ==========================
// Remove imported footage from AE project
// ==========================
try {
    for (var i = app.project.numItems; i >= 1; i--) {
        var item = app.project.item(i);
        if (item instanceof FootageItem) {
            if (item.file && (item.file.fsName === beforePath || item.file.fsName === afterPath)) {
                item.remove(); // removes from AE project
            }
        }
    }
} catch (e) {
    alert("Failed to remove footage from AE project:\n" + e.toString());
}