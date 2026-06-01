// Auto Rename By First Effect + Layer Name Overrides (AE-compatible)

(function () {

    app.beginUndoGroup("Auto Rename By First Effect + Layer Name Overrides");

    var comp = app.project.activeItem;

    if (!(comp instanceof CompItem)) {
        alert("Open a composition first.");
        return;
    }

    for (var i = 1; i <= comp.numLayers; i++) {

        var layer = comp.layer(i);

        if (!(layer instanceof AVLayer)) continue;

        // Remove leading/trailing whitespace in a JSX-compatible way
        var layerName = layer.name.replace(/^\s+|\s+$/g, '');

        // ---------- Layer name overrides ----------
        if (layerName.toLowerCase().indexOf("default") !== -1) {
            layer.name = "Camera";
            continue; // skip further renaming
        } 
        else if (layerName.toLowerCase().indexOf("shape") !== -1) {
            layer.name = "Shape";
            continue; // skip further renaming
        }

        // ---------- Adjustment layer first effect rename ----------
        if (layerName.toLowerCase().indexOf("adjustment") !== -1) {
            var effects = layer.property("ADBE Effect Parade");
            if (!effects || effects.numProperties === 0) continue;

            var firstEffect = effects.property(1);
            if (!firstEffect) continue;

            var newName = firstEffect.name || firstEffect.matchName;
            if (!newName) continue;

            layer.name = newName;
        }

    }

    app.endUndoGroup();

})();