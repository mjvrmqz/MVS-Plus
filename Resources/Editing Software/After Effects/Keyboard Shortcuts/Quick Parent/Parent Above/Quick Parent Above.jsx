(function QuickParentAbove() {
    var PREF_SECTION = "QuickParentAbove";
    var PREF_KEY = "skipConfirm";

    var skipConfirm = app.settings.haveSetting(PREF_SECTION, PREF_KEY) &&
                      app.settings.getSetting(PREF_SECTION, PREF_KEY) === "true";

    function doParent() {
        app.beginUndoGroup("Quick Parent Above");
        var comp = app.project.activeItem;
        if (!(comp instanceof CompItem)) {
            alert("Please open a comp.");
            return;
        }

        var selected = comp.selectedLayers;
        if (selected.length === 0) {
            alert("Select at least one layer.");
            return;
        }

        // Find the top-most selected layer index
        var highestIndex = selected[0].index;
        for (var i = 1; i < selected.length; i++) {
            if (selected[i].index < highestIndex) {
                highestIndex = selected[i].index;
            }
        }

        var parentIndex = highestIndex - 1;
        if (parentIndex < 1) {
            alert("No layer above the selection.");
            return;
        }

        var parentLayer = comp.layer(parentIndex);

        for (var i = 0; i < selected.length; i++) {
            if (selected[i].threeDLayer) {
                parentLayer.threeDLayer = true;
            }
            selected[i].parent = parentLayer;
        }

        app.endUndoGroup();
    }

    if (skipConfirm) {
        doParent();
        return;
    }

    // Build confirmation dialog
    var dlg = new Window("dialog", "Quick Parent Above");
    dlg.orientation = "column";
    dlg.alignChildren = "fill";

    var msg = dlg.add("statictext", undefined,
        "This will parent the selected layer(s) to the layer directly above.\nDo you want to continue?",
        { multiline: true });
    msg.alignment = "center";

    var dontShow = dlg.add("checkbox", undefined, "Don't show this again");

    var btnGroup = dlg.add("group");
    btnGroup.alignment = "center";
    btnGroup.orientation = "row";

    var btnYes = btnGroup.add("button", undefined, "Yes");
    var btnNo  = btnGroup.add("button", undefined, "No");

    btnYes.onClick = function () {
        if (dontShow.value) {
            app.settings.saveSetting(PREF_SECTION, PREF_KEY, "true");
        }
        dlg.close();
        doParent();
    };

    btnNo.onClick = function () {
        dlg.close();
    };

    dlg.show();
})();