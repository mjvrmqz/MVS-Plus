// Select Layer Above.jsx
(function selectLayerAbove() {
    var comp = app.project.activeItem;
    if (!(comp instanceof CompItem)) { alert("Please select a composition first."); return; }
    var selectedLayers = comp.selectedLayers;
    if (selectedLayers.length !== 1) { alert("Please select exactly one layer."); return; }
    var indexAbove = selectedLayers[0].index - 1;
    if (indexAbove < 1) { alert("There is no layer above the selected layer."); return; }
    app.beginUndoGroup("Select Layer Above");
    for (var i = 1; i <= comp.numLayers; i++) comp.layer(i).selected = false;
    comp.layer(indexAbove).selected = true;
    app.endUndoGroup();
})();
