/*
    Smart Shy (Show Past + Present)
    Shows all layers that start before or are touching the playhead,
    hides only those that begin after the playhead.
*/

(function() {
    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) {
        alert("Please select a comp first!");
        return;
    }

    var time = comp.time;

    app.beginUndoGroup("Smart Shy (Show Past + Present)");

    for (var i = 1; i <= comp.numLayers; i++) {
        var layer = comp.layer(i);

        if (!(layer instanceof CameraLayer) && !(layer instanceof LightLayer)) {
            var inPt = layer.inPoint;
            var outPt = layer.outPoint;

            // Hide only layers that start *after* the playhead,
            // unless they are touching it.
            if (inPt > time && !(time >= inPt && time <= outPt)) {
                layer.shy = true;
            } else {
                layer.shy = false;
            }
        }
    }

    comp.hideShyLayers = true;

    app.endUndoGroup();
})();