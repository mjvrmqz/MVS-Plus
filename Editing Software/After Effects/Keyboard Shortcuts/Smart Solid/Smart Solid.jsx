app.beginUndoGroup("Smart Solid");

var comp = app.project.activeItem;

if (comp && comp instanceof CompItem) {

    // Open color picker
    var color = $.colorPicker();

    if (color !== -1) {
        // Convert hex to RGB [0–1]
        var r = ((color >> 16) & 255) / 255;
        var g = ((color >> 8) & 255) / 255;
        var b = (color & 255) / 255;

        // Create solid
        var solid = comp.layers.addSolid(
            [r, g, b],
            "Smart Solid",
            comp.width,
            comp.height,
            comp.pixelAspect,
            comp.duration
        );

        // Move to playhead
        solid.startTime = comp.time;
    }

} else {
    alert("Select a composition first.");
}

app.endUndoGroup();