#target photoshop

if (app.documents.length < 2) {
    alert("You need at least two open documents.");
} else {

    var srcDoc = app.activeDocument;
    var importLayer = srcDoc.activeLayer;
    var targetName = importLayer.name;

    // Recursive search
    function findLayerByName(parent, name) {
        for (var i = 0; i < parent.layers.length; i++) {
            var l = parent.layers[i];

            if (l.name === name) {
                return l;
            }

            if (l.typename === "LayerSet") {
                var found = findLayerByName(l, name);
                if (found) return found;
            }
        }
        return null;
    }

    function findLayerInGroup(group, name) {
        for (var i = 0; i < group.layers.length; i++) {
            if (group.layers[i].name === name && group.layers[i].typename !== "LayerSet") {
                return group.layers[i];
            }
        }
        return null;
    }

    var targetDoc = null;
    var targetLayerSet = null;

    // Find target doc + artboard/group
    for (var d = 0; d < app.documents.length; d++) {
        var doc = app.documents[d];
        if (doc === srcDoc) continue;

        var found = findLayerByName(doc, targetName);
        if (found) {
            targetDoc = doc;
            targetLayerSet = found;
            break;
        }
    }

    if (!targetDoc || !targetLayerSet) {
        alert("No matching artboard/layer group found for name: " + targetName);
    } else {

        // 🔑 Activate target doc FIRST
        app.activeDocument = targetDoc;

        // Find existing old layer
        var oldLayer = findLayerInGroup(targetLayerSet, targetName);

        // Switch back to source to copy
        app.activeDocument = srcDoc;

        // Duplicate into target group
        var placedLayer = importLayer.duplicate(targetLayerSet, ElementPlacement.INSIDE);

        // Switch to target doc to operate on imported layer
        app.activeDocument = targetDoc;

        // Rename
        placedLayer.name = targetName;

        // Delete old version
        if (oldLayer) {
            oldLayer.remove();
        }

        // Center inside artboard
        try {
            var ab = targetLayerSet.bounds;
            var lb = placedLayer.bounds;

            var abCx = (ab[0].as("px") + ab[2].as("px")) / 2;
            var abCy = (ab[1].as("px") + ab[3].as("px")) / 2;

            var lbCx = (lb[0].as("px") + lb[2].as("px")) / 2;
            var lbCy = (lb[1].as("px") + lb[3].as("px")) / 2;

            placedLayer.translate(abCx - lbCx, abCy - lbCy);
        } catch(e) {}

        // Close temp edit file silently
        app.activeDocument = srcDoc;
        srcDoc.close(SaveOptions.DONOTSAVECHANGES);

        // Return to original doc
        app.activeDocument = targetDoc;
    }
}