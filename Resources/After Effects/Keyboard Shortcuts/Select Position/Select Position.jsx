// SelectPositionProperty_Fixed.jsx
var comp = app.project.activeItem;

if (comp && comp instanceof CompItem && comp.selectedLayers.length > 0) {
    var layer = comp.selectedLayers[0];

    // Deselect all properties manually
    for (var i = 1; i <= layer.numProperties; i++) {
        try { layer.property(i).selected = false; } catch(e) {}
    }

    // Select the Position property
    var posProp = layer.property("ADBE Transform Group").property("ADBE Position");
    if (posProp) {
        posProp.selected = true;
    }
} else {
    alert("No layer selected or no active composition.");
}