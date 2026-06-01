// Move Playhead 3 Sec.jsx
var comp = app.project.activeItem;
if (comp && comp instanceof CompItem) {
    comp.time = Math.min(comp.time + 3, comp.duration);
}
