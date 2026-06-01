// Show In Iso.jsx — Cycles through comps that reference a selected layer from Asset Dashboard
(function () {
    app.beginUndoGroup("Show Layer in Isolation");
    var activeComp = app.project.activeItem;
    if (!(activeComp instanceof CompItem) || activeComp.name !== "Asset Dashboard") { alert('Only works in "Asset Dashboard" comp.'); return; }
    if (activeComp.selectedLayers.length === 0) { app.endUndoGroup(); return; }
    var layerName = activeComp.selectedLayers[0].name;
    var references = [];
    for (var i = 1; i <= app.project.numItems; i++) {
        var comp = app.project.item(i);
        if (!(comp instanceof CompItem) || comp === activeComp) continue;
        for (var l = 1; l <= comp.numLayers; l++) {
            if (comp.layer(l).name === layerName) references.push({ comp: comp, layer: comp.layer(l) });
        }
    }
    if (references.length === 0) { app.endUndoGroup(); return; }
    if (!$.global.__SHOW_ISO_TRACKER__) $.global.__SHOW_ISO_TRACKER__ = {};
    if (!$.global.__SHOW_ISO_TRACKER__[layerName]) $.global.__SHOW_ISO_TRACKER__[layerName] = 0;
    var index = $.global.__SHOW_ISO_TRACKER__[layerName];
    if (index >= references.length) index = 0;
    var target = references[index];
    target.comp.openInViewer();
    for (var l = 1; l <= target.comp.numLayers; l++) target.comp.layer(l).selected = false;
    target.layer.selected = true;
    $.global.__SHOW_ISO_TRACKER__[layerName] = index + 1;
    app.endUndoGroup();
})();
