#target photoshop
app.activeDocument.suspendHistory("Select Subject in PT Layers", "main()");

function main() {
    var doc = app.activeDocument;

    for (var i = 0; i < doc.layerSets.length; i++) {
        var group = doc.layerSets[i];

        // Only process top-level groups whose name contains "PT"
        if (group.name.indexOf("PT") === -1) continue;

        processLayers(group);
    }
}

// Recursive function to process all layers inside a group
function processLayers(group) {
    for (var i = 0; i < group.layers.length; i++) {
        var layer = group.layers[i];

        if (layer.typename === "ArtLayer") {
            // Only process layers whose name contains "PT"
            if (layer.name.indexOf("PT") === -1) continue;

            // Skip fully transparent layers
            if (isLayerEmpty(layer)) continue;

            app.activeDocument.activeLayer = layer;
            try {
                executeAction(stringIDToTypeID("autoCutout"), undefined, DialogModes.NO);
            } catch (e) {
                continue;
            }

        } else if (layer.typename === "LayerSet") {
            // Recurse into subgroups
            processLayers(layer);
        }
    }
}

// Function to check if layer is fully transparent
function isLayerEmpty(layer) {
    var bounds = layer.bounds; // [left, top, right, bottom]
    var width = bounds[2].as("px") - bounds[0].as("px");
    var height = bounds[3].as("px") - bounds[1].as("px");

    // If layer has no width or height, it’s empty
    if (width === 0 || height === 0) return true;

    // Try to select opaque pixels
    app.activeDocument.activeLayer = layer;
    try {
        layer.transparentPixelsLocked = false; // ensure we can select
        app.activeDocument.selection.selectAll();
        app.activeDocument.selection.copy();
        app.activeDocument.selection.deselect();
        // If copy succeeded, assume it has content
        return false;
    } catch (e) {
        return true;
    }
}