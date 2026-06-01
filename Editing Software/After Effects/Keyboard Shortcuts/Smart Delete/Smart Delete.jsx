// ==============================================
// Smart Delete
// Deletes selected layer(s) and removes their
// source from the project bin.
// ==============================================

app.beginUndoGroup("Smart Delete");

var SETTINGS_SECTION = "NativeKit";
var SETTINGS_KEY = "SmartDeleteSkipConfirm";

function shouldShowConfirm() {
    try {
        return app.settings.getSetting(SETTINGS_SECTION, SETTINGS_KEY) !== "true";
    } catch (e) {
        return true;
    }
}

function deleteLayers(comp) {
    var selectedLayers = comp.selectedLayers;

    for (var i = selectedLayers.length - 1; i >= 0; i--) {
        var layer = selectedLayers[i];
        var source = layer.source;

        // Remove layer from comp
        layer.remove();

        // Remove source item from project bin if no longer used
        if (source && (source instanceof FootageItem || source instanceof CompItem)) {
            var stillUsed = false;

            // Check all comps in the project for any remaining references
            for (var j = 1; j <= app.project.numItems; j++) {
                var item = app.project.item(j);
                if (item instanceof CompItem) {
                    for (var k = 1; k <= item.numLayers; k++) {
                        if (item.layer(k).source === source) {
                            stillUsed = true;
                            break;
                        }
                    }
                }
                if (stillUsed) break;
            }

            // Safe to remove — nothing else is using it
            if (!stillUsed) {
                source.remove();
            }
        }
    }
}

// Check for active comp first
var comp = app.project.activeItem;
if (!comp || !(comp instanceof CompItem)) {
    alert("Please select layers in a composition.");
    app.endUndoGroup();
} else if (comp.selectedLayers.length === 0) {
    // Check for selected layers
    alert("No layers selected.");
    app.endUndoGroup();
} else if (shouldShowConfirm()) {
    // Build dialog
    var dialog = new Window("dialog", "Smart Delete");
    dialog.orientation = "column";
    dialog.alignChildren = "left";

    var msg = dialog.add("statictext", undefined,
        "This will delete the selected layer from the current composition and the project panel. Are you sure you want to continue?",
        {multiline: true});
    msg.preferredSize.width = 400;

    var checkbox = dialog.add("checkbox", undefined, "Never show again");

    var btnGroup = dialog.add("group");
    btnGroup.orientation = "row";
    var yesBtn = btnGroup.add("button", undefined, "Yes");
    var noBtn = btnGroup.add("button", undefined, "No");

    yesBtn.onClick = function () {
        if (checkbox.value) {
            app.settings.saveSetting(SETTINGS_SECTION, SETTINGS_KEY, "true");
        }
        dialog.close(1);
    };

    noBtn.onClick = function () {
        dialog.close(0);
    };

    var result = dialog.show();
    if (result === 1) {
        deleteLayers(comp);
    }
} else {
    deleteLayers(comp);
}

app.endUndoGroup();