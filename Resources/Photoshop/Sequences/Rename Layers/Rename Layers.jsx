#target photoshop

app.activeDocument.suspendHistory("Show Layer Hierarchy", "main()");

function main() {
    var doc = app.activeDocument;
    var output = "";

    // Recursive function to walk layers
    function listLayers(layers, indent) {
        for (var i = 0; i < layers.length; i++) {
            var layer = layers[i];
            var prefix = "";
            for (var j = 0; j < indent; j++) prefix += "  "; // 2 spaces per depth

            if (layer.typename === "ArtLayer") {
                output += prefix + layer.name + " (Layer, index=" + layer.itemIndex + ")\n";
            } else if (layer.typename === "LayerSet") {
                output += prefix + layer.name + " (Group, index=" + layer.itemIndex + ")\n";
                listLayers(layer.layers, indent + 1); // recursively list child layers
            }
        }
    }

    listLayers(doc.layers, 0);

    // Show result in an alert
    alert(output);
}

main();