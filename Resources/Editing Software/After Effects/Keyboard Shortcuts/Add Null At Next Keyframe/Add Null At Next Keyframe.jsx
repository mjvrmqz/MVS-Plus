/*
    Auto Null Before Second Keyframe
    - Only for selected nulls
    - Adds null 1 second before the second keyframe
    - Places it above the original layer
    - Matches the original layer’s label color
*/

(function() {
    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) {
        alert("Select a comp first!");
        return;
    }

    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length === 0) {
        alert("Select at least one null layer.");
        return;
    }

    app.beginUndoGroup("Add Null Before Second Keyframe");

    for (var i = 0; i < selectedLayers.length; i++) {
        var layer = selectedLayers[i];
        if (!layer.nullLayer) continue;

        var props = [layer.transform.position, layer.transform.rotation, layer.transform.scale];
        var secondKeyTime = null;

        // Find earliest second keyframe
        for (var p = 0; p < props.length; p++) {
            var prop = props[p];
            if (prop && prop.numKeys >= 2) {
                var time = prop.keyTime(2) - 1;
                if (time < 0) time = 0;
                if (secondKeyTime === null || time < secondKeyTime) {
                    secondKeyTime = time;
                }
            }
        }

        if (secondKeyTime !== null) {
            // Add null
            var newNull = comp.layers.addNull();
            newNull.name = "Pre-Second Key Null";

            // Match label color of original null
            newNull.label = layer.label;

            // Position null above original layer
            newNull.moveBefore(layer);

            // Set its inPoint
            newNull.inPoint = secondKeyTime;

            // Parent original null to new null
            try {
                layer.parent = newNull;
            } catch(e) {}
        }
    }

    app.endUndoGroup();
})();