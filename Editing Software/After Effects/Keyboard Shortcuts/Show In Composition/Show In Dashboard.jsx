// Show In Dashboard.jsx — Selects matching layer in Asset Dashboard comp
(function () {
    app.beginUndoGroup("Show Layer in Asset Dashboard");
    var activeComp = app.project.activeItem;
    if (!(activeComp instanceof CompItem)) { alert("No active composition selected!"); return; }
    if (activeComp.selectedLayers.length === 0) { app.endUndoGroup(); return; }
    var layerName = activeComp.selectedLayers[0].name;
    var dashboardComp = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === "Asset Dashboard") { dashboardComp = item; break; }
    }
    if (!dashboardComp) { alert('No comp named "Asset Dashboard" found.'); app.endUndoGroup(); return; }
    var targetLayer = null;
    for (var l = 1; l <= dashboardComp.numLayers; l++) {
        if (dashboardComp.layer(l).name === layerName) { targetLayer = dashboardComp.layer(l); break; }
    }
    if (!targetLayer) { app.endUndoGroup(); return; }
    dashboardComp.openInViewer();
    for (var l = 1; l <= dashboardComp.numLayers; l++) dashboardComp.layer(l).selected = false;
    targetLayer.selected = true;
    app.endUndoGroup();
})();
