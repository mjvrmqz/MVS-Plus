function precompKeepSlot() {
    app.beginUndoGroup("Precomp Keep Slot");
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) return;

    var selected = comp.selectedLayers;
    if (selected.length === 0) return;

    // Collect indices
    var indices = [];
    var earliestIn = selected[0].inPoint;
    var latestOut = selected[0].outPoint;

    for (var i = 0; i < selected.length; i++) {
        indices.push(selected[i].index);
        if (selected[i].inPoint < earliestIn) earliestIn = selected[i].inPoint;
        if (selected[i].outPoint > latestOut) latestOut = selected[i].outPoint;
    }

    var duration = latestOut - earliestIn;
    var topIndex = indices[0];
    for (var i = 1; i < indices.length; i++) {
        if (indices[i] < topIndex) topIndex = indices[i];
    }

    var newName = comp.name + " #1";

    // Precompose all selected
    var newComp = comp.layers.precompose(indices, newName, true);
    newComp.duration = duration;
    newComp.displayStartTime = 0;

    // Keep precomp in same slot
    var precompLayer = comp.layer(topIndex);
    precompLayer.startTime = earliestIn;
    precompLayer.inPoint = earliestIn;
    precompLayer.outPoint = latestOut;

    app.endUndoGroup();
}
precompKeepSlot();