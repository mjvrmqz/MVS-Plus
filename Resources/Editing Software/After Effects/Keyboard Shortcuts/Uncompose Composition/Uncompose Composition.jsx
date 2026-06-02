function unPrecompose(precompLayer) {
    if (!(precompLayer instanceof AVLayer)) {
        alert("Select a precomp layer to un-precompose.");
        return;
    }

    var parentComp = precompLayer.containingComp;
    var precomp = precompLayer.source;

    if (!(precomp instanceof CompItem)) {
        alert("Selected layer is not a precomp.");
        return;
    }

    app.beginUndoGroup("Un-Precompose");

    var startTime = precompLayer.startTime;

    // Copy each layer from the precomp to the parent comp
    for (var i = 1; i <= precomp.numLayers; i++) {
        var oldLayer = precomp.layer(i);
        var newLayer = parentComp.layers.add(oldLayer.source);

        // Move layer to correct time in parent comp
        newLayer.startTime = startTime + oldLayer.startTime;
        newLayer.inPoint = startTime + oldLayer.inPoint;
        newLayer.outPoint = startTime + oldLayer.outPoint;

        // Copy transform properties
        var props = ["position", "scale", "rotation", "opacity", "anchorPoint"];
        for (var p = 0; p < props.length; p++) {
            var prop = oldLayer.property(props[p]);
            var newProp = newLayer.property(props[p]);
            if (!prop || !newProp) continue;

            if (prop.numKeys > 0) {
                for (var k = 1; k <= prop.numKeys; k++) {
                    newProp.setValueAtTime(startTime + prop.keyTime(k), prop.keyValue(k));
                }
            } else {
                newProp.setValue(prop.value);
            }
        }

        // Copy effects safely
        var effects = oldLayer.property("ADBE Effect Parade");
        if (effects) {
            for (var e = 1; e <= effects.numProperties; e++) {
                var eff = effects.property(e);
                if (!eff) continue;

                var newEff = newLayer.property("ADBE Effect Parade").addProperty(eff.matchName);
                if (!newEff) continue;

                copyEffectProperty(eff, newEff, startTime);
            }
        }
    }

    // Remove original precomp layer
    precompLayer.remove();

    app.endUndoGroup();
}

// Recursive safe effect copy
function copyEffectProperty(sourceProp, targetProp, offsetTime) {
    if (!sourceProp || !targetProp) return;

    if (sourceProp.numProperties > 0) {
        for (var i = 1; i <= sourceProp.numProperties; i++) {
            copyEffectProperty(sourceProp.property(i), targetProp.property(i), offsetTime);
        }
    } else {
        if (sourceProp.numKeys > 0) {
            for (var k = 1; k <= sourceProp.numKeys; k++) {
                var t = sourceProp.keyTime(k);
                try {
                    targetProp.setValueAtTime(offsetTime + t, sourceProp.keyValue(k));
                } catch (err) {}
            }
        } else {
            try {
                targetProp.setValue(sourceProp.value);
            } catch (err) {}
        }
    }
}

// Run it on selected layer
var sel = app.project.activeItem.selectedLayers;
if (sel.length === 1) {
    unPrecompose(sel[0]);
} else {
    alert("Select exactly one precomp layer to un-precompose.");
}