// Auto Rename By First Effect + Layer Name Overrides
(function () {
    app.beginUndoGroup("Auto Rename By First Effect");
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) { alert("Open a composition first."); return; }
    for (var i = 1; i <= comp.numLayers; i++) {
        var layer = comp.layer(i);
        if (!(layer instanceof AVLayer)) continue;
        var layerName = layer.name.replace(/^\s+|\s+$/g, '');
        if (layerName.toLowerCase().indexOf("default") !== -1) { layer.name = "Camera"; continue; }
        else if (layerName.toLowerCase().indexOf("shape") !== -1) { layer.name = "Shape"; continue; }
        if (layerName.toLowerCase().indexOf("adjustment") !== -1) {
            var effects = layer.property("ADBE Effect Parade");
            if (!effects || effects.numProperties === 0) continue;
            var firstEffect = effects.property(1);
            if (!firstEffect) continue;
            layer.name = firstEffect.name || firstEffect.matchName;
        }
    }
    app.endUndoGroup();
})();
