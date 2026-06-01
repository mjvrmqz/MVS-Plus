(function assetPlaceholder() {
    var seq = app.project.activeSequence;
    if (!seq) {
        alert("No active sequence found.");
        return;
    }

    var baseFolder = Folder("/Users/mjvrmqz/Downloads/Video Editing Assets/YouTube Documentaries/Projects/Project 59673/");
    if (!baseFolder.exists) {
        alert("Project folder does not exist!");
        return;
    }

    var layerTypes = {
        "B-Roll": "BR",
        "Background": "BG",
        "Icon": "IC",
        "Puppet": "PT"
    };

    // -----------------------------
    // Chapter markers
    // -----------------------------
    var chapterMarkers = [];
    if (seq.markers) {
        var m = seq.markers.getFirstMarker();
        while (m) {
            if (m.name && m.name.toLowerCase().indexOf("chapter") !== -1) {
                chapterMarkers.push(m.start.seconds);
            }
            m = seq.markers.getNextMarker(m);
        }
    }
    if (chapterMarkers.length === 0) chapterMarkers.push(0);
    chapterMarkers.sort(function (a, b) { return a - b; });

    function getChapter(start) {
        var chapter = 1;
        for (var i = 0; i < chapterMarkers.length; i++) {
            if (start >= chapterMarkers[i]) chapter = i + 1;
        }
        return chapter;
    }

    function pad(n) {
        return (n < 10 ? "0" : "") + n;
    }

    function createPNG(path) {
        var f = new File(path);
        if (!f.exists) {
            f.open("w");
            f.encoding = "BINARY";
            f.write("");
            f.close();
        }
    }

    function createFolder(path) {
        var f = new Folder(path);
        if (!f.exists) f.create();
    }

    // -----------------------------
    // Scan clips
    // -----------------------------
    var assetClips = [];
    var chapterCounters = {};

    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
        var track = seq.videoTracks[t];
        for (var c = 0; c < track.clips.numItems; c++) {
            var clip = track.clips[c];
            if (!layerTypes[clip.name]) continue;

            var start = clip.start.seconds;
            var end = clip.end.seconds;
            var chapter = getChapter(start);
            var code = layerTypes[clip.name];

            if (!chapterCounters[chapter]) chapterCounters[chapter] = {};
            if (!chapterCounters[chapter][code]) chapterCounters[chapter][code] = 0;
            chapterCounters[chapter][code]++;

            var order = pad(chapterCounters[chapter][code]);
            var assetID = "C" + chapter + code + order;

            // Create placeholders (NOT B-Roll)
            if (clip.name === "Background") {
                createFolder(baseFolder.fsName + "/Background/" + assetID);
            } else if (clip.name !== "B-Roll") {
                createPNG(baseFolder.fsName + "/" + clip.name + "/" + assetID + ".png");
            }

            assetClips.push({
                assetID: assetID,
                start: start,
                end: end
            });
        }
    }

    // -----------------------------
    // WRITE assets.txt (WORKING LOGIC)
    // -----------------------------
    var assetFile = File(baseFolder.fsName + "/assets.txt");

    try {
        var outputText = "Asset Placeholder Sheet Metadata\n\n";

        for (var i = 0; i < assetClips.length; i++) {
            var a = assetClips[i];

            outputText += a.assetID + "\n";

            var sm = Math.floor(a.start / 60);
            var ss = Math.floor(a.start % 60);
            var em = Math.floor(a.end / 60);
            var es = Math.floor(a.end % 60);

            outputText +=
                sm + ":" + (ss < 10 ? "0" + ss : ss) +
                "-" +
                em + ":" + (es < 10 ? "0" + es : es) +
                "\n\n";
        }

        assetFile.encoding = "UTF-8";
        if (assetFile.open("w")) {
            assetFile.write(outputText);
            assetFile.close();
            alert("assets.txt created successfully at:\n" + assetFile.fsName);
        } else {
            alert("Failed to open assets.txt for writing.");
        }

    } catch (e) {
        alert("Error creating assets.txt: " + e);
    }

})();