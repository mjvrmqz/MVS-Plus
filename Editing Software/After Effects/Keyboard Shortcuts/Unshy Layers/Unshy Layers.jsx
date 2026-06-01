/*
    Unshy All Layers
    Unhides every layer in the active comp and disables shy visibility.
*/

(function() {
    var comp = app.project.activeItem;
    if (!(comp && comp instanceof CompItem)) {
        alert("Please select a comp first!");
        return;
    }

    app.beginUndoGroup("Unshy All Layers");

    for (var i = 1; i <= comp.numLayers; i++) {
        comp.layer(i).shy = false;
    }

    // Make sure shy layers are visible again
    comp.hideShyLayers = false;

    app.endUndoGroup();
})();