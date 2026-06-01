app.beginUndoGroup("Move Backward 1.25s");

var comp = app.project.activeItem;
if (comp && comp instanceof CompItem) {
    comp.time -= 1.25;
}

app.endUndoGroup();