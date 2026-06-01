// Add Chapters.jsx
// Creates chapter markers on the active sequence

(function() {
    var seq = app.project.activeSequence;
    if (!seq) { alert("No active sequence found."); return; }

    var markers = seq.markers;
    if (!markers) { alert("Could not access markers."); return; }

    // Optional: clear existing markers
    var m = markers.getFirstMarker();
    while (m) {
        var next = markers.getNextMarker(m);
        markers.deleteMarker(m);
        m = next;
    }

    // ================================// CHAPTER MARKERS START
    var m1 = markers.createMarker(0.0);
    m1.end = 33.56666666666667;
    m1.name = "Chapter 1: The New Reality of Editing";

    var m2 = markers.createMarker(33.56666666666667);
    m2.end = 92.13333333333334;
    m2.name = "Chapter 2: Authority and Solution";
// CHAPTER MARKERS END// ================================

    alert("Chapter markers successfully created.");
})();