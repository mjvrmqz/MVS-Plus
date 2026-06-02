// ======================================
// Nearest Marker Backwards
// ======================================

app.beginUndoGroup("Nearest Marker Backwards");

var comp = app.project.activeItem;

if (!(comp && comp instanceof CompItem)) {
    alert("Select a comp first!");
} else {

    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length === 0) {
        alert("Select at least one layer.");
    } else {

        // --------------------------------------
        // FIND EARLIEST IN POINT
        // --------------------------------------
        var earliestIn = selectedLayers[0].inPoint;
        for (var i = 1; i < selectedLayers.length; i++) {
            earliestIn = Math.min(earliestIn, selectedLayers[i].inPoint);
        }

        // --------------------------------------
        // FIND PREVIOUS MARKER BEFORE EARLIEST IN
        // --------------------------------------
        var markerProp = comp.markerProperty;
        var targetMarkerTime = null;

        for (var k = markerProp.numKeys; k >= 1; k--) {
            var markerTime = markerProp.keyTime(k);
            if (markerTime < earliestIn) {
                targetMarkerTime = markerTime;
                break;
            }
        }

        // --------------------------------------
        // MOVE LAYERS
        // --------------------------------------
        if (targetMarkerTime !== null) {
            var delta = targetMarkerTime - earliestIn;

            for (var j = 0; j < selectedLayers.length; j++) {
                selectedLayers[j].startTime += delta;
            }
        }
    }
}

app.endUndoGroup();