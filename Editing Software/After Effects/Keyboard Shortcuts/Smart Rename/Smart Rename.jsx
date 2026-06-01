// Smart Rename — Renames selected layer source to match layer name (or vice versa)
(function () {
    app.beginUndoGroup("Smart Rename");
    var comp = app.project.activeItem;
    if (comp instanceof CompItem) {
        if (comp.selectedLayers.length === 0) { alert("No layers selected."); }
        else {
            for (var i = 0; i < comp.selectedLayers.length; i++) {
                var layer = comp.selectedLayers[i];
                if (!(layer instanceof AVLayer) || !layer.source) continue;
                layer.source.name = layer.name;
            }
        }
    }
    app.endUndoGroup();
})();
