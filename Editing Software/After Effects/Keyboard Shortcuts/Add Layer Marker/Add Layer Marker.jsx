(function () {
    app.beginUndoGroup("Add Marker to Layer");

    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) {
        alert("No active composition selected!");
        return;
    }

    if (comp.selectedLayers.length === 0) {
        alert("No layers selected!");
        return;
    }

    // Optional: change this string for marker label
    var markerName = "Custom Marker";

    for (var i = 0; i < comp.selectedLayers.length; i++) {
        var layer = comp.selectedLayers[i];
        var markerProp = layer.property("Marker");

        if (markerProp) {
            var marker = new MarkerValue(markerName);
            markerProp.setValueAtTime(comp.time, marker); // add at current time
        }
    }

    app.endUndoGroup();
})();