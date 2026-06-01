app.beginUndoGroup("Batch Parent");
var comp = app.project.activeItem;
if (comp && comp instanceof CompItem) {
    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length > 1) {
        selectedLayers.sort(function(a, b) { return a.index - b.index; });
        for (var i = selectedLayers.length - 1; i > 0; i--) {
            selectedLayers[i].parent = selectedLayers[i - 1];
        }
    } else { alert("Select at least 2 layers."); }
} else { alert("No active comp."); }
app.endUndoGroup();
