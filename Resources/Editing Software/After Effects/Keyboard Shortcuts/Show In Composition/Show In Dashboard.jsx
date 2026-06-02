(function () {
    app.beginUndoGroup("Show Layer in Asset Dashboard");

    var proj = app.project;
    if (!proj) {
        alert("No project open.");
        return;
    }

    var activeComp = proj.activeItem;
    if (!(activeComp instanceof CompItem)) {
        alert("No active composition selected!");
        return;
    }

    if (activeComp.selectedLayers.length === 0) {
        // Nothing selected
        app.endUndoGroup();
        return;
    }

    // Only take the first selected layer
    var selectedLayer = activeComp.selectedLayers[0];
    var layerName = selectedLayer.name;

    // Find the Asset Dashboard comp
    var dashboardComp = null;
    for (var i = 1; i <= proj.numItems; i++) {
        var item = proj.item(i);
        if (item instanceof CompItem && item.name === "Asset Dashboard") {
            dashboardComp = item;
            break;
        }
    }

    if (!dashboardComp) {
        alert('No comp named "Asset Dashboard" found.');
        app.endUndoGroup();
        return;
    }

    // Find the layer with the same name
    var targetLayer = null;
    for (var l = 1; l <= dashboardComp.numLayers; l++) {
        if (dashboardComp.layer(l).name === layerName) {
            targetLayer = dashboardComp.layer(l);
            break;
        }
    }

    if (!targetLayer) {
        // No matching layer, do nothing
        app.endUndoGroup();
        return;
    }

    // Select the layer in Asset Dashboard
    dashboardComp.openInViewer(); // Make Asset Dashboard active
    // Deselect all layers first
    for (var l = 1; l <= dashboardComp.numLayers; l++) {
        dashboardComp.layer(l).selected = false;
    }
    targetLayer.selected = true;

    app.endUndoGroup();
})();