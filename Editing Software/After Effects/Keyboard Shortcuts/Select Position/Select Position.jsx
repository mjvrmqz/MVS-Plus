// Select Position Property
var comp = app.project.activeItem;
if (comp && comp instanceof CompItem && comp.selectedLayers.length > 0) {
    var layer = comp.selectedLayers[0];
    for (var i = 1; i <= layer.numProperties; i++) { try { layer.property(i).selected = false; } catch(e) {} }
    var posProp = layer.property("ADBE Transform Group").property("ADBE Position");
    if (posProp) posProp.selected = true;
} else { alert("No layer selected or no active composition."); }
