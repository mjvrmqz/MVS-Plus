app.beginUndoGroup("Smart Solid");
var comp = app.project.activeItem;
if (comp && comp instanceof CompItem) {
    var color = $.colorPicker();
    if (color !== -1) {
        var r = ((color >> 16) & 255) / 255; var g = ((color >> 8) & 255) / 255; var b = (color & 255) / 255;
        var solid = comp.layers.addSolid([r, g, b], "Smart Solid", comp.width, comp.height, comp.pixelAspect, comp.duration);
        solid.startTime = comp.time;
    }
} else { alert("Select a composition first."); }
app.endUndoGroup();
