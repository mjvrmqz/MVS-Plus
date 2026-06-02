// Select All Keyframes on Selected Layers.jsx

(function () {
    app.beginUndoGroup("Select All Keyframes");

    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) {
        alert("Select a composition first.");
        return;
    }

    var layers = comp.selectedLayers;
    if (layers.length === 0) {
        alert("Select at least one layer.");
        return;
    }

    function selectKeysRecursive(prop) {
        if (prop.propertyType === PropertyType.PROPERTY) {
            if (prop.numKeys > 0) {
                for (var k = 1; k <= prop.numKeys; k++) {
                    prop.setSelectedAtKey(k, true);
                }
            }
        } else {
            for (var i = 1; i <= prop.numProperties; i++) {
                selectKeysRecursive(prop.property(i));
            }
        }
    }

    for (var i = 0; i < layers.length; i++) {
        var layer = layers[i];
        selectKeysRecursive(layer);
    }

    app.endUndoGroup();
})();