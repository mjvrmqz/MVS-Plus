// Go To Nearest Marker Back.jsx
app.beginUndoGroup("Nearest Marker Backwards");
var comp = app.project.activeItem;
if (!(comp && comp instanceof CompItem)) { alert("Select a comp first!"); }
else {
    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length === 0) { alert("Select at least one layer."); }
    else {
        var currentTime = comp.time;
        var nearestMarkerTime = null;
        for (var i = 0; i < selectedLayers.length; i++) {
            var layer = selectedLayers[i];
            var markerProp = layer.property("Marker");
            if (!markerProp) continue;
            for (var k = markerProp.numKeys; k >= 1; k--) {
                var markerTime = markerProp.keyTime(k);
                if (markerTime < currentTime) {
                    if (nearestMarkerTime === null || markerTime > nearestMarkerTime) nearestMarkerTime = markerTime;
                    break;
                }
            }
        }
        if (nearestMarkerTime !== null) comp.time = nearestMarkerTime;
    }
}
app.endUndoGroup();
