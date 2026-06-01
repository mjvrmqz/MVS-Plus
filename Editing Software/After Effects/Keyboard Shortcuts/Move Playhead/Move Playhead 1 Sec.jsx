// Move Playhead 1 Sec.jsx
var comp = app.project.activeItem;
if (comp && comp instanceof CompItem) {
    comp.time = Math.min(comp.time + 1, comp.duration);
}
