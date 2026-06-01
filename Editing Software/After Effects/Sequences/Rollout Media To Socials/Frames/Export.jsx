// ==========================
// Read frame paths for number extraction
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
    if (line) framePaths.push(line);
}
tmpFile.close();

if (framePaths.length === 0) {
    alert("No frame paths provided.");
    throw new Error("No frame paths");
}

// Extract 5-digit number from first frame file
var fileName = framePaths[0].split("/").pop();
var match = fileName.match(/\d{5}/);
if (!match) {
    alert("Could not find 5-digit number in file name: " + fileName);
    throw new Error("Number missing");
}
var number = match[0];

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
// Find "Frames" marker
// ==========================
var markerName = "Frames";
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
comp.workAreaDuration = 60; // seconds

// ==========================
// Set output path
// ==========================
var outputFolder = "/Users/mjvrmqz/Downloads/Video Editing Assets/Tweets/Frame Sequence";
var outputFile = outputFolder + "/Video " + number + ".mov";

// ==========================
// Add to render queue and render automatically
// ==========================
var rqItem = app.project.renderQueue.items.add(comp);
rqItem.outputModule(1).file = new File(outputFile);
rqItem.outputModule(1).applyTemplate("Lossless"); // ensure a valid render template

app.activate(); // make AE frontmost
app.project.renderQueue.render(); // starts rendering

// ==========================
// Delete Processor files
// ==========================
try {
    for (var i = 0; i < framePaths.length; i++) {
        var f = new File(framePaths[i]);
        if (f.exists) f.remove();
    }
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
            if (item.file && framePaths.indexOf(item.file.fsName) !== -1) {
                item.remove(); // remove from AE project
            }
        }
    }
} catch (e) {
    alert("Failed to remove footage from AE project:\n" + e.toString());
}