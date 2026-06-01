// Smart Delete — Deletes selected layer(s) and removes their source from the project bin
app.beginUndoGroup("Smart Delete");
var SETTINGS_SECTION = "NativeKit"; var SETTINGS_KEY = "SmartDeleteSkipConfirm";
function shouldShowConfirm() { try { return app.settings.getSetting(SETTINGS_SECTION, SETTINGS_KEY) !== "true"; } catch(e) { return true; } }
function deleteLayers(comp) {
    var selectedLayers = comp.selectedLayers;
    for (var i = selectedLayers.length - 1; i >= 0; i--) {
        var layer = selectedLayers[i]; var source = layer.source;
        layer.remove();
        if (source && (source instanceof FootageItem || source instanceof CompItem)) {
            var stillUsed = false;
            for (var j = 1; j <= app.project.numItems; j++) {
                var item = app.project.item(j);
                if (item instanceof CompItem) {
                    for (var k = 1; k <= item.numLayers; k++) { if (item.layer(k).source === source) { stillUsed = true; break; } }
                }
                if (stillUsed) break;
            }
            if (!stillUsed) source.remove();
        }
    }
}
var comp = app.project.activeItem;
if (!comp || !(comp instanceof CompItem)) { alert("Please select layers in a composition."); app.endUndoGroup(); }
else if (comp.selectedLayers.length === 0) { alert("No layers selected."); app.endUndoGroup(); }
else { deleteLayers(comp); }
app.endUndoGroup();
