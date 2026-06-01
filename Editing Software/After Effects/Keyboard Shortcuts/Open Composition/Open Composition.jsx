// Open selected precomp layer in timeline (fixed version)
(function () {
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) {
        alert("Select a composition first.");
        return;
    }

    var sel = comp.selectedLayers;
    if (sel.length === 0) {
        alert("Select a precomp layer.");
        return;
    }

    var layer = sel[0];
    if (layer.source && layer.source instanceof CompItem) {
        app.beginUndoGroup("Open Precomp in Timeline");

        // Simulate double-clicking the layer (open it in timeline)
        layer.source.openInViewer();

        app.endUndoGroup();
    } else {
        alert("Selected layer is not a precomp.");
    }
})();