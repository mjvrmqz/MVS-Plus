var comp = app.project.activeItem;

if (!comp || !(comp instanceof CompItem)) {
    alert("Please select a comp first.");
} else {
    var layers = comp.selectedLayers;

    if (layers.length > 1) {
        app.beginUndoGroup("Reverse Layer Order");

        for (var i = layers.length - 1; i >= 0; i--) {
            layers[i].moveToBeginning();
        }

        app.endUndoGroup();
    }
}