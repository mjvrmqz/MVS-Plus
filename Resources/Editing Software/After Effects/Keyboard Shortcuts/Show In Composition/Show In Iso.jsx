(function () {
    app.beginUndoGroup("Show Layer in Isolation");

    var proj = app.project;
    if (!proj) {
        alert("No project open.");
        return;
    }

    var activeComp = proj.activeItem;
    if (!(activeComp instanceof CompItem) || activeComp.name !== "Asset Dashboard") {
        alert('This script only works in the "Asset Dashboard" comp.');
        return;
    }

    if (activeComp.selectedLayers.length === 0) {
        app.endUndoGroup();
        return;
    }

    // We’ll only use the first selected layer for now
    var selectedLayer = activeComp.selectedLayers[0];
    var layerName = selectedLayer.name;

    // Find all references of this layer in other comps
    var references = [];
    for (var i = 1; i <= proj.numItems; i++) {
        var comp = proj.item(i);
        if (!(comp instanceof CompItem)) continue;
        if (comp === activeComp) continue;

        for (var l = 1; l <= comp.numLayers; l++) {
            if (comp.layer(l).name === layerName) {
                references.push({ comp: comp, layer: comp.layer(l) });
            }
        }
    }

    if (references.length === 0) {
        app.endUndoGroup();
        return;
    }

    // Initialize session tracker
    if (!$.global.__SHOW_ISO_TRACKER__) {
        $.global.__SHOW_ISO_TRACKER__ = {};
    }

    if (!$.global.__SHOW_ISO_TRACKER__[layerName]) {
        $.global.__SHOW_ISO_TRACKER__[layerName] = 0;
    }

    // Get the current reference index
    var index = $.global.__SHOW_ISO_TRACKER__[layerName];

    // Safety check to loop around
    if (index >= references.length) {
        index = 0;
    }

    var target = references[index];

    // Make target comp active and select layer
    target.comp.openInViewer();
    // Deselect all layers first
    for (var l = 1; l <= target.comp.numLayers; l++) {
        target.comp.layer(l).selected = false;
    }
    target.layer.selected = true;

    // Increment the tracker for next run
    $.global.__SHOW_ISO_TRACKER__[layerName] = index + 1;

    app.endUndoGroup();
})();