// ======================================
// Auto Color Groups + Fraction Markers
// ======================================

app.beginUndoGroup("Auto Color Groups + Fractions");

var comp = app.project.activeItem;

if (!(comp && comp instanceof CompItem)) {
    alert("Select a comp first!");
} else {

    // --------------------------------------
    // CONFIG
    // --------------------------------------
    var colorCycle = [9, 10, 11, 12, 13]; // Label colors
    var startThreshold = 2; // seconds

    // --------------------------------------
    // REMOVE OLD FRACTION MARKERS
    // --------------------------------------
    var markerProp = comp.markerProperty;
    for (var i = markerProp.numKeys; i >= 1; i--) {
        var comment = markerProp.keyValue(i).comment;
        if (comment.indexOf("Fraction") === 0) {
            markerProp.removeKey(i);
        }
    }

    // --------------------------------------
    // COLLECT VALID LAYERS
    // --------------------------------------
    var layers = [];
    for (var i = 1; i <= comp.numLayers; i++) {
        var l = comp.layer(i);
        if (!(l instanceof CameraLayer) && !(l instanceof LightLayer)) {
            layers.push(l);
        }
    }

    // Sort by inPoint (earliest first)
    layers.sort(function(a, b) {
        return a.inPoint - b.inPoint;
    });

    // --------------------------------------
    // GROUPING STATE
    // --------------------------------------
    var currentGroup = [];
    var currentGroupStart = null;
    var currentGroupEnd = null;
    var colorIndex = 0;
    var fractionIndex = 1;

    // --------------------------------------
    // FINALIZE GROUP
    // --------------------------------------
    function finalizeGroup(group, groupStartTime) {
        var color = colorCycle[colorIndex % colorCycle.length];

        // Color layers
        for (var i = 0; i < group.length; i++) {
            group[i].label = color;
        }

        // Create colored marker
        var marker = new MarkerValue("Fraction " + fractionIndex);
        marker.label = color;

        comp.markerProperty.setValueAtTime(groupStartTime, marker);

        colorIndex++;
        fractionIndex++;
    }

    // --------------------------------------
    // MAIN LOOP
    // --------------------------------------
    for (var i = 0; i < layers.length; i++) {
        var layer = layers[i];

        if (currentGroup.length === 0) {
            currentGroup = [layer];
            currentGroupStart = layer.inPoint;
            currentGroupEnd = layer.outPoint;
            continue;
        }

        // Late joiner or contained logic
        if (
            (layer.inPoint - currentGroupStart <= startThreshold) ||
            (layer.inPoint >= currentGroupStart && layer.outPoint <= currentGroupEnd)
        ) {
            currentGroup.push(layer);
            currentGroupEnd = Math.max(currentGroupEnd, layer.outPoint);
        } else {
            finalizeGroup(currentGroup, currentGroupStart);

            currentGroup = [layer];
            currentGroupStart = layer.inPoint;
            currentGroupEnd = layer.outPoint;
        }
    }

    // Final group
    if (currentGroup.length > 0) {
        finalizeGroup(currentGroup, currentGroupStart);
    }
}

app.endUndoGroup();