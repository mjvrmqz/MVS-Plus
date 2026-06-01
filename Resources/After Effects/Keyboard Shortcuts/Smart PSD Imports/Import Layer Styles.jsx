function autoOrganizeAndUncompose() {

    app.beginUndoGroup("Auto Organize + Uncompose + Dynamic Label");

    var layersFolder = null;
    var baseName = null;

    // --------------------------------------------------
    // 1. Find folder with "Layers" in name
    // --------------------------------------------------
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);

        if (item instanceof FolderItem && item.name && item.name.indexOf("Layers") !== -1) {
            layersFolder = item;
            break;
        }
    }

    if (!layersFolder) {
        alert("No 'Layers' folder found.");
        app.endUndoGroup();
        return;
    }

    baseName = layersFolder.name.split(" ")[0];

    // --------------------------------------------------
    // 2. Detect color from name (C1, C2, etc.)
    // --------------------------------------------------
    var labelColor = 0;
    var colorMatch = layersFolder.name.match(/C(\d+)/i);

    if (colorMatch && colorMatch[1]) {
        labelColor = parseInt(colorMatch[1], 10);
        if (labelColor < 1 || labelColor > 16) labelColor = 0;
    }

    layersFolder.label = labelColor;

    // --------------------------------------------------
    // 3. Find Project/Timeline/Assets (DO NOT CREATE)
    // --------------------------------------------------
    var timelineFolder = null;
    var assetsFolder = null;

    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof FolderItem && item.name === "Timeline") {
            timelineFolder = item;
            break;
        }
    }

    if (!timelineFolder) {
        alert("Timeline folder not found.");
        app.endUndoGroup();
        return;
    }

    for (var i = 1; i <= timelineFolder.numItems; i++) {
        var subItem = timelineFolder.item(i);
        if (subItem instanceof FolderItem && subItem.name === "Assets") {
            assetsFolder = subItem;
            break;
        }
    }

    if (!assetsFolder) {
        alert("Assets folder not found inside Timeline.");
        app.endUndoGroup();
        return;
    }

    layersFolder.parentFolder = assetsFolder;

    // --------------------------------------------------
    // 4. Find main comp and rename to "Main"
    // --------------------------------------------------
    var mainComp = null;

    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);

        if (item instanceof CompItem && item.name === baseName) {
            mainComp = item;
            break;
        }
    }

    if (!mainComp) {
        alert("Main comp not found.");
        app.endUndoGroup();
        return;
    }

    mainComp.parentFolder = layersFolder;
    mainComp.name = "Main";
    mainComp.label = labelColor;

    // --------------------------------------------------
    // 5. Create subfolders per comp inside Layers folder
    // --------------------------------------------------
    for (var i = layersFolder.numItems; i >= 1; i--) {

        var item = layersFolder.item(i);

        if (item instanceof CompItem && item !== mainComp) {

            var comp = item;
            comp.label = labelColor;

            var compFolder = app.project.items.addFolder(comp.name);
            compFolder.parentFolder = layersFolder;
            compFolder.label = labelColor;

            comp.parentFolder = compFolder;

            for (var l = 1; l <= comp.numLayers; l++) {

                var layer = comp.layer(l);
                layer.label = labelColor;

                if (layer.source && layer.source instanceof FootageItem) {
                    layer.source.parentFolder = compFolder;
                    layer.source.label = labelColor;
                }
            }
        }
    }

    // --------------------------------------------------
    // 6. Recursive Uncompose inside main comp
    // --------------------------------------------------
    var changed = true;

    while (changed) {

        changed = false;

        for (var i = mainComp.numLayers; i >= 1; i--) {

            var layer = mainComp.layer(i);

            if (layer.source && layer.source instanceof CompItem) {

                changed = true;

                var precomp = layer.source;
                var insertIndex = layer.index;

                var parentPos = layer.property("Position") ? layer.property("Position").value : [0,0];
                var parentScale = layer.property("Scale") ? layer.property("Scale").value : [100,100];
                var parentRot = layer.property("Rotation") ? layer.property("Rotation").value : 0;

                for (var l = precomp.numLayers; l >= 1; l--) {

                    var innerLayer = precomp.layer(l);
                    if (!innerLayer) continue;

                    var newLayer = innerLayer.copyToComp(mainComp);
                    if (!newLayer) continue;

                    newLayer.moveBefore(mainComp.layer(insertIndex));
                    newLayer.label = labelColor;

                    if (newLayer.property("Position")) {
                        var innerPos = newLayer.property("Position").value;
                        newLayer.property("Position").setValue([
                            innerPos[0] + parentPos[0],
                            innerPos[1] + parentPos[1]
                        ]);
                    }

                    if (newLayer.property("Scale")) {
                        newLayer.property("Scale").setValue(parentScale);
                    }

                    if (newLayer.property("Rotation")) {
                        newLayer.property("Rotation").setValue(parentRot);
                    }
                }

                layer.remove();

                if (precomp.usedIn.length === 0) {
                    precomp.remove();
                }
            }
        }
    }

    // --------------------------------------------------
    // 7. RENAME Layers folder to first word (AT VERY END)
    // --------------------------------------------------
    layersFolder.name = baseName;

    app.endUndoGroup();
}

autoOrganizeAndUncompose();