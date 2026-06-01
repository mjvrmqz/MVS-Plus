// Select Layer Below.jsx
(function selectLayerBelow() {
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) { alert("Please select a composition first."); return; }
    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length !== 1) { alert("Please select exactly one layer."); return; }
    var indexBelow = selectedLayers[0].index + 1;
    if (indexBelow > comp.numLayers) { alert("There is no layer below the selected layer."); return; }
    app.beginUndoGroup("Select Layer Below");
    for (var i = 1; i <= comp.numLayers; i++) comp.layer(i).selected = false;
    comp.layer(indexBelow).selected = true;
    app.endUndoGroup();
})();
