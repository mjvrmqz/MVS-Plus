(function () {
    app.beginUndoGroup("Asset Dashboard → Isolated Effects Sync");

    if (!app.project) {
        alert("No project open.");
        return;
    }

    var globalComp = null;

    // 1. Find the Asset Dashboard comp
    for (var i = 1; i <= app.project.numItems; i++) {
        var item = app.project.item(i);
        if (item instanceof CompItem && item.name === "Asset Dashboard") {
            globalComp = item;
            break;
        }
    }

    if (!globalComp) {
        alert('No comp named "Asset Dashboard" found.');
        return;
    }

    // Helper: copy property values + keyframes
    function copyProperty(srcProp, dstProp) {
        if (srcProp.numKeys > 0) {
            for (var k = 1; k <= srcProp.numKeys; k++) {
                dstProp.setValueAtTime(
                    srcProp.keyTime(k),
                    srcProp.keyValue(k)
                );
            }
        } else {
            try {
                dstProp.setValue(srcProp.value);
            } catch (e) {}
        }
    }

    // Helper: copy one effect
    function copyEffect(srcEffect, dstLayer) {
        var dstEffect = dstLayer.property("ADBE Effect Parade")
            .addProperty(srcEffect.matchName);

        if (!dstEffect) return;

        for (var p = 1; p <= srcEffect.numProperties; p++) {
            var srcProp = srcEffect.property(p);
            var dstProp = dstEffect.property(p);

            if (srcProp && dstProp && srcProp.propertyType === PropertyType.PROPERTY) {
                copyProperty(srcProp, dstProp);
            }
        }
    }

    // 2. Loop Asset Dashboard layers
    for (var g = 1; g <= globalComp.numLayers; g++) {
        var globalLayer = globalComp.layer(g);
        var layerName = globalLayer.name;
        var globalEffects = globalLayer.property("ADBE Effect Parade");

        if (!globalEffects || globalEffects.numProperties === 0) continue;

        // 3. Scan all other comps
        for (var j = 1; j <= app.project.numItems; j++) {
            var comp = app.project.item(j);
            if (!(comp instanceof CompItem)) continue;
            if (comp === globalComp) continue;

            for (var l = 1; l <= comp.numLayers; l++) {
                var targetLayer = comp.layer(l);
                if (targetLayer.name !== layerName) continue;

                var targetEffects = targetLayer.property("ADBE Effect Parade");

                // 4. Remove existing effects
                while (targetEffects.numProperties > 0) {
                    targetEffects.property(1).remove();
                }

                // 5. Apply Asset Dashboard effects
                for (var e = 1; e <= globalEffects.numProperties; e++) {
                    copyEffect(globalEffects.property(e), targetLayer);
                }
            }
        }
    }

    app.endUndoGroup();
})();