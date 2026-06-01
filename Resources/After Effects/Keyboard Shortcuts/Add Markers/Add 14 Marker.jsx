// Color Selected Keyframes - Color 14.jsx
// Adds a marker at every selected keyframe using color 14

(function () {
    app.beginUndoGroup("Color Selected Keyframes - Color 14");

    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) {
        alert("Select a composition first.");
        return;
    }

    var layers = comp.selectedLayers;
    if (layers.length === 0) {
        alert("Select at least one layer with selected keyframes.");
        return;
    }

    var color = 14; // AE label color 14

    for (var i = 0; i < layers.length; i++) {
        var layer = layers[i];

        function processProperty(prop) {
            if (prop.propertyType === PropertyType.PROPERTY && prop.numKeys > 0) {
                for (var k = 1; k <= prop.numKeys; k++) {
                    if (prop.keySelected(k)) {
                        var t = prop.keyTime(k);
                        var markerProp = layer.property("Marker");
                        var marker = new MarkerValue(""); // empty comment
                        marker.label = color;
                        markerProp.setValueAtTime(t, marker);
                    }
                }
            } else if (prop.numProperties > 0) {
                for (var p = 1; p <= prop.numProperties; p++) {
                    processProperty(prop.property(p));
                }
            }
        }

        processProperty(layer);
    }

    app.endUndoGroup();
})();