{
    app.beginUndoGroup("Toggle Light Mode");
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) { alert("Please select an active composition."); }
    else {
        for (var i = 1; i <= comp.numLayers; i++) {
            var layer = comp.layer(i);
            if (layer.property("ADBE Effect Parade") !== null) {
                var effects = layer.property("ADBE Effect Parade");
                var darkEffect = null; var lightEffect = null;
                for (var j = 1; j <= effects.numProperties; j++) {
                    var fx = effects.property(j);
                    if (fx.name === "Dark Mode") darkEffect = fx;
                    if (fx.name === "Light Mode") lightEffect = fx;
                }
                if (darkEffect !== null && lightEffect !== null) {
                    darkEffect.enabled = false;
                    lightEffect.enabled = true;
                }
            }
        }
    }
    app.endUndoGroup();
}
