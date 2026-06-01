// Remove Black Screen.jsx
app.beginUndoGroup("Remove Black Screen");
var comp = app.project.activeItem;
if (comp && comp.selectedLayers.length > 0) {
    for (var i = 0; i < comp.selectedLayers.length; i++) {
        comp.selectedLayers[i].blendingMode = BlendingMode.SCREEN;
    }
} else { alert("Select at least one layer."); }
app.endUndoGroup();
