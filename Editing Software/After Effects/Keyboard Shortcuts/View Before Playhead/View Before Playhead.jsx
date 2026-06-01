(function() {
    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) { alert("Please select a comp first!"); return; }
    var time = comp.time;
    app.beginUndoGroup("Smart Shy (Show Past + Present)");
    for (var i = 1; i <= comp.numLayers; i++) {
        var layer = comp.layer(i);
        if (!(layer instanceof CameraLayer) && !(layer instanceof LightLayer)) {
            if (layer.inPoint > time && !(time >= layer.inPoint && time <= layer.outPoint)) layer.shy = true;
            else layer.shy = false;
        }
    }
    comp.hideShyLayers = true;
    app.endUndoGroup();
})();
