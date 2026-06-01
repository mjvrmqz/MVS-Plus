// camera_info_chapters.jsx
(function () {
    var seq = app.project.activeSequence;
    if (!seq) {
        alert("No active sequence.");
        return;
    }

    var chapterMarkers = [];
    var clips = [];

    // Collect clips and Chapter Markers
    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            var clip = track.clips[c];
            var start = clip.start.seconds;
            var end = start + clip.duration.seconds;

            if (clip.name === "Chapter Marker") {
                chapterMarkers.push({
                    start: start,
                    end: end
                });
            } else {
                clips.push({
                    name: clip.name,
                    start: start,
                    end: end
                });
            }
        }
    }

    if (chapterMarkers.length === 0) {
        alert("No Chapter Marker clips found.");
        return;
    }

    // Sort Chapter Markers and Clips by start time
    chapterMarkers.sort(function(a,b){ return a.start - b.start; });
    clips.sort(function(a,b){ return a.start - b.start; });

    // Assign clips to chapters
    var chapters = [];
    for (var i = 0; i < chapterMarkers.length; i++) {
        chapters[i] = [];
    }

    for (var k = 0; k < clips.length; k++) {
        var clip = clips[k];
        // assign to the first chapter whose start is before the clip
        for (var c = 0; c < chapterMarkers.length; c++) {
            if (clip.start >= chapterMarkers[c].start) {
                chapters[c].push(clip);
            }
        }
    }

    // Build overview counts
    var movementCounts = {};
    for (var i = 0; i < clips.length; i++) {
        var name = clips[i].name;
        if (!movementCounts[name]) movementCounts[name] = 0;
        movementCounts[name]++;
    }

    // Prepare output text
    var outputText = "Camera Builder Sheet Movements Metadata\n\n";
    outputText += "Total Movements: " + clips.length + "\n\n";

    for (var c = 0; c < chapters.length; c++) {
        outputText += "Chapter " + (c + 1) + "\n";
        for (var m = 0; m < chapters[c].length; m++) {
            var clip = chapters[c][m];
            outputText += clip.name + ": " + clip.start.toFixed(2) + "s → " + clip.end.toFixed(2) + "s\n";
        }
        outputText += "\n";
    }

    // Write to file
    var file = new File("/Users/mjvrmqz/Downloads/camera_movements.txt");
    file.encoding = "UTF-8";
    file.open("w");
    file.write(outputText);
    file.close();

    // Alert with simple overview
    var overview = "Camera Builder Sheet Movements Metadata\n\nTotal Movements: " + clips.length + "\n\n";
    for (var key in movementCounts) {
        overview += key + ": " + movementCounts[key] + "\n";
    }
    alert(overview);

})();