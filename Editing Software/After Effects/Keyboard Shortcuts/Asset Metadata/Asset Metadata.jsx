// Asset Metadata.jsx — Shows parent comps and usage count for selected layers or project items
(function() {
    app.beginUndoGroup("Asset Metadata");
    function arrayContains(arr, obj) { for (var i = 0; i < arr.length; i++) { if (arr[i] === obj) return true; } return false; }
    var sourcesToCheck = [];
    var comp = app.project.activeItem;
    if (comp instanceof CompItem) {
        var selectedLayers = comp.selectedLayers;
        for (var i = 0; i < selectedLayers.length; i++) {
            var layer = selectedLayers[i];
            if (layer instanceof AVLayer && layer.source) sourcesToCheck.push(layer.source);
        }
    }
    var selectedItems = app.project.selection;
    for (var j = 0; j < selectedItems.length; j++) {
        var item = selectedItems[j];
        if (item instanceof CompItem || item instanceof FootageItem) sourcesToCheck.push(item);
    }
    if (sourcesToCheck.length === 0) { alert("Select at least one layer or project item."); app.endUndoGroup(); return; }
    function findParentChapters(source, visitedComps) {
        visitedComps = visitedComps || [];
        var chapters = []; var usageCount = 0;
        for (var i = 1; i <= app.project.numItems; i++) {
            var projItem = app.project.item(i);
            if (!(projItem instanceof CompItem)) continue;
            if (arrayContains(visitedComps, projItem)) continue;
            for (var l = 1; l <= projItem.numLayers; l++) {
                var lyr = projItem.layer(l);
                if (!(lyr instanceof AVLayer) || !lyr.source || lyr.source !== source) continue;
                usageCount++; visitedComps.push(projItem);
                if (/^Chapter\s/i.test(projItem.name) && !arrayContains(chapters, projItem.name)) chapters.push(projItem.name);
                var parentResult = findParentChapters(projItem, visitedComps);
                usageCount += parentResult.usageCount;
                for (var c = 0; c < parentResult.chapters.length; c++) { if (!arrayContains(chapters, parentResult.chapters[c])) chapters.push(parentResult.chapters[c]); }
            }
        }
        return { chapters: chapters, usageCount: usageCount };
    }
    var alertText = "";
    for (var s = 0; s < sourcesToCheck.length; s++) {
        var src = sourcesToCheck[s]; var result = findParentChapters(src);
        alertText += "Asset: " + src.name + "\n";
        alertText += "Included in: " + (result.chapters.length ? result.chapters.join(", ") : "None") + "\n";
        alertText += "Times Used: " + result.usageCount + "\n\n";
    }
    if (alertText) alert(alertText, "Asset Metadata"); else alert("No usage found.", "Asset Metadata");
    app.endUndoGroup();
})();
