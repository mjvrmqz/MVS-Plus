// ==============================================
// Smart Rename
// Renames selected layer source to match the
// layer name, or renames timeline layers to
// match their source name in the project panel.
// ==============================================

(function () {
    app.beginUndoGroup("Smart Rename");

    var SETTINGS_SECTION = "NativeKit";
    var SETTINGS_KEY_TIMELINE = "SmartRenameSkipConfirmTimeline";
    var SETTINGS_KEY_PROJECT = "SmartRenameSkipConfirmProject";

    function shouldShowConfirm(key) {
        try {
            return app.settings.getSetting(SETTINGS_SECTION, key) !== "true";
        } catch (e) {
            return true;
        }
    }

    function showConfirmDialog(message, key, onConfirm) {
        if (shouldShowConfirm(key)) {
            var dialog = new Window("dialog", "Smart Rename");
            dialog.orientation = "column";
            dialog.alignChildren = "left";

            var msg = dialog.add("statictext", undefined, message, {multiline: true});
            msg.preferredSize.width = 400;

            var checkbox = dialog.add("checkbox", undefined, "Never show again");

            var btnGroup = dialog.add("group");
            btnGroup.orientation = "row";
            var yesBtn = btnGroup.add("button", undefined, "Yes");
            var noBtn = btnGroup.add("button", undefined, "No");

            yesBtn.onClick = function () {
                if (checkbox.value) {
                    app.settings.saveSetting(SETTINGS_SECTION, key, "true");
                }
                dialog.close(1);
            };

            noBtn.onClick = function () {
                dialog.close(0);
            };

            var result = dialog.show();
            if (result === 1) {
                onConfirm();
            }
        } else {
            onConfirm();
        }
    }

    function renameFromTimeline(comp) {
        var selectedLayers = comp.selectedLayers;
        for (var i = 0; i < selectedLayers.length; i++) {
            var layer = selectedLayers[i];
            if (!(layer instanceof AVLayer)) continue;
            if (!layer.source) continue;
            // Rename the project source item to match the layer name
            layer.source.name = layer.name;
        }
    }

    function renameFromProject(selectedItems) {
        for (var j = 0; j < selectedItems.length; j++) {
            var item = selectedItems[j];
            if (!(item instanceof FootageItem || item instanceof CompItem)) continue;
            // Find all layers using this source and rename them to match the source name
            for (var k = 1; k <= app.project.numItems; k++) {
                var projItem = app.project.item(k);
                if (!(projItem instanceof CompItem)) continue;
                for (var l = 1; l <= projItem.numLayers; l++) {
                    var layer = projItem.layer(l);
                    if (!(layer instanceof AVLayer)) continue;
                    if (!layer.source) continue;
                    if (layer.source === item) {
                        // Rename the timeline layer to match the source name
                        layer.name = item.name;
                    }
                }
            }
        }
    }

    // ---------- Determine context and run ----------
    var comp = app.project.activeItem;
    var selectedItems = app.project.selection;

    if (comp instanceof CompItem) {
        if (comp.selectedLayers.length === 0) {
            alert("No layers selected.");
        } else {
            showConfirmDialog(
                "This will rename the source item in the project panel to match the selected layer name. Are you sure you want to continue?",
                SETTINGS_KEY_TIMELINE,
                function () { renameFromTimeline(comp); }
            );
        }
    } else if (selectedItems && selectedItems.length > 0) {
        showConfirmDialog(
            "This will rename the timeline layers to match the selected source name in the project panel. Are you sure you want to continue?",
            SETTINGS_KEY_PROJECT,
            function () { renameFromProject(selectedItems); }
        );
    } else {
        alert("No layers or items selected.");
    }

    app.endUndoGroup();
})();