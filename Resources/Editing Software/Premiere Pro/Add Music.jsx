/**
 * Add Music.jsx
 * Imports multiple audio files into Premiere Pro
 * Creates chapter bins and song sub-bins, renames clips C#MC##
 * Adds all clips to timeline without overwriting by stacking tracks
 * and sequencing chapters horizontally.
 */

(function () {

    if (!app.project) {
        alert("No project open.");
        return;
    }

    var sequence = app.project.activeSequence;
    if (!sequence) {
        alert("No active sequence open.");
        return;
    }

    // Python replaces these
    var inputPaths = ["/Users/mjvrmqz/Personal/MVS Studios Assets/Sound/Epidemic Sound/Music Collection/Anna's Log","/Users/mjvrmqz/Personal/MVS Studios Assets/Sound/Epidemic Sound/Music Collection/Balissi","/Users/mjvrmqz/Personal/MVS Studios Assets/Sound/Epidemic Sound/Music Collection/An Abyss Of Sadness","/Users/mjvrmqz/Personal/MVS Studios Assets/Sound/Epidemic Sound/Music Collection/Between Moments"];
    var inputIDs = ["C3MC01","C4MC01","C5MC01","C6MC01"];

    if (!inputPaths || inputPaths.length === 0) {
        alert("No file paths provided.");
        return;
    }

    var importedCount = 0;
    var chapterBins = {};
    var globalTime = 0; // horizontal timeline cursor

    for (var i = 0; i < inputPaths.length; i++) {

        var folderPath = inputPaths[i];
        var id = inputIDs[i];
        var chapterNumber = id.match(/C(\d+)MC/)[1];

        if (!chapterBins[chapterNumber]) {
            chapterBins[chapterNumber] = app.project.rootItem.createBin("C" + chapterNumber);
        }
        var chapterBin = chapterBins[chapterNumber];

        var songBin = chapterBin.createBin(id);

        var folder = new Folder(folderPath);
        if (!folder.exists) { $.writeln("Folder missing: " + folderPath); continue; }

        var files = folder.getFiles();
        var maxClipDuration = 0;

        for (var j = 0; j < files.length; j++) {
            var file = files[j];
            if (file instanceof File) {
                var result = app.project.importFiles([file.fsName], 1, songBin, 0);
                if (result && result.length > 0) {
                    importedCount++;
                    var importedItem = result[0];
                    importedItem.name = id;

                    // Determine track index for vertical stacking
                    var trackIndex = 0;
                    for (var t = 0; t < sequence.audioTracks.numTracks; t++) {
                        if (!sequence.audioTracks[t].overwriteClip) { trackIndex = t; break; }
                        trackIndex++;
                    }
                    while (sequence.audioTracks.numTracks <= trackIndex) {
                        sequence.audioTracks.addTrack();
                    }

                    // Add clip to timeline
                    sequence.audioTracks[trackIndex].overwriteClip(importedItem, globalTime);

                    if (importedItem.getMediaDuration() > maxClipDuration) {
                        maxClipDuration = importedItem.getMediaDuration();
                    }

                } else {
                    $.writeln("Failed to import: " + file.name);
                }
            }
        }

        globalTime += maxClipDuration;
    }

    alert("Import complete. Files imported and added to timeline: " + importedCount);

})();