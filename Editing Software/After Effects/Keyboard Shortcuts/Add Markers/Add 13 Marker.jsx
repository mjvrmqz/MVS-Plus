(function () {
    app.beginUndoGroup("Color Selected Keyframes - Color 13");
    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) { alert("Select a composition first."); return; }
    var layers = comp.selectedLayers;
    if (layers.length === 0) { alert("Select at least one layer."); return; }
    var color = 13;
    for (var i = 0; i < layers.length; i++) {
        var layer = layers[i];
        function processProperty(prop) {
            if (prop.propertyType === PropertyType.PROPERTY && prop.numKeys > 0) {
                for (var k = 1; k <= prop.numKeys; k++) {
                    if (prop.keySelected(k)) {
                        var t = prop.keyTime(k);
                        var marker = new MarkerValue(""); marker.label = color;
                        layer.property("Marker").setValueAtTime(t, marker);
                    }
                }
            } else if (prop.numProperties > 0) {
                for (var p = 1; p <= prop.numProperties; p++) processProperty(prop.property(p));
            }
        }
        processProperty(layer);
    }
    app.endUndoGroup();
})();
