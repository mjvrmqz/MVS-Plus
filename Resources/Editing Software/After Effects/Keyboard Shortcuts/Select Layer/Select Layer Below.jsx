// Select Layer Below.jsx
// Selects the layer below the currently selected layer in After Effects

(function selectLayerBelow() {
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
    var indexBelow = currentLayer.index + 1;

    if (indexBelow > comp.numLayers) {
        alert("There is no layer below the selected layer.");
        return;
    }

    app.beginUndoGroup("Select Layer Below");

    // Deselect all layers first
    for (var i = 1; i <= comp.numLayers; i++) {
        comp.layer(i).selected = false;
    }

    // Select the layer below
    comp.layer(indexBelow).selected = true;

    app.endUndoGroup();
})();