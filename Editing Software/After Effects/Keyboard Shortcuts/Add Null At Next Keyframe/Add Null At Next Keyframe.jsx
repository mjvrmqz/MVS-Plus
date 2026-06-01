(function() {
    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) { alert("Select a comp first!"); return; }
    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length === 0) { alert("Select at least one null layer."); return; }
    app.beginUndoGroup("Add Null Before Second Keyframe");
    for (var i = 0; i < selectedLayers.length; i++) {
        var layer = selectedLayers[i];
        if (!layer.nullLayer) continue;
        var props = [layer.transform.position, layer.transform.rotation, layer.transform.scale];
        var secondKeyTime = null;
        for (var p = 0; p < props.length; p++) {
            var prop = props[p];
            if (prop && prop.numKeys >= 2) {
                var time = prop.keyTime(2) - 1;
                if (time < 0) time = 0;
                if (secondKeyTime === null || time < secondKeyTime) secondKeyTime = time;
            }
        }
        if (secondKeyTime !== null) {
            var newNull = comp.layers.addNull();
            newNull.name = "Pre-Second Key Null";
            newNull.label = layer.label;
            newNull.moveBefore(layer);
            newNull.inPoint = secondKeyTime;
            try { layer.parent = newNull; } catch(e) {}
        }
    }
    app.endUndoGroup();
})();
