// Select Layer Above.jsx
// Selects the layer above the currently selected layer in After Effects

(function selectLayerAbove() {
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) {
        alert("Please select a composition first.");
        return;
    }

    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length !== 1) {
        alert("Please select exactly one layer.");
        return;
    }

    var currentLayer = selectedLayers[0];
    var indexAbove = currentLayer.index - 1;

    if (indexAbove < 1) {
        alert("There is no layer above the selected layer.");
        return;
    }

    app.beginUndoGroup("Select Layer Above");

    // Deselect all layers first
    for (var i = 1; i <= comp.numLayers; i++) {
        comp.layer(i).selected = false;
    }

    // Select the layer above
    comp.layer(indexAbove).selected = true;

    app.endUndoGroup();
})();