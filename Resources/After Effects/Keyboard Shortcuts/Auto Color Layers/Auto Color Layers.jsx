// Auto Color Layers.jsx
// Sets all layer label colors to the majority label color in the comp

(function () {

    app.beginUndoGroup("Auto Color Layers");

    var comp = app.project.activeItem;

    if (!(comp instanceof CompItem)) {
        alert("Open a composition first.");
        return;
    }

    var labelCount = {};
    var majorityLabel = null;
    var maxCount = 0;

    // Count labels
    for (var i = 1; i <= comp.numLayers; i++) {

        var layer = comp.layer(i);
        var label = layer.label;

        if (!labelCount[label]) {
            labelCount[label] = 1;
        } else {
            labelCount[label]++;
        }

        if (labelCount[label] > maxCount) {
            maxCount = labelCount[label];
            majorityLabel = label;
        }
    }

    if (majorityLabel === null) {
        alert("No layers found.");
        return;
    }

    // Apply majority label to all layers
    for (var j = 1; j <= comp.numLayers; j++) {
        comp.layer(j).label = majorityLabel;
    }

    app.endUndoGroup();

})();