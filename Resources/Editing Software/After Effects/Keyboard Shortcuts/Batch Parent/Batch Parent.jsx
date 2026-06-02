app.beginUndoGroup("Batch Parent");

var comp = app.project.activeItem;

if (comp && comp instanceof CompItem) {
    var selectedLayers = comp.selectedLayers;

    if (selectedLayers.length > 1) {
        // Sort layers by index (top to bottom)
        selectedLayers.sort(function(a, b) {
            return a.index - b.index;
        });

        for (var i = selectedLayers.length - 1; i > 0; i--) {
            var child = selectedLayers[i];
            var parent = selectedLayers[i - 1];
            child.parent = parent;
        }
    } else {
        alert("Select at least 2 layers.");
    }
} else {
    alert("No active comp.");
}

app.endUndoGroup();