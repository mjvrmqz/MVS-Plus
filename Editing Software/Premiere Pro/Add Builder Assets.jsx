var storyboardTimestamps = [
    [0,29,1,1,4,4],
    [29,72,2,2,2,2],
    [72,155,1,1,3,3],
    [155,200,1,1,3,3],
    [200,271,4,4,3,3],
    [271,314,1,1,2,2],
    [374,413,1,1,3,3],
    [413,482,1,1,2,2],
    [482,571,1,1,3,3]
];

var seq = app.project.activeSequence;

if (seq) {
    var trackBackground = seq.videoTracks[0]; // V1
    var trackBasePuppet = 1; // V2
    var trackBaseIcon = 5;   // V6

    function findProjectItemByName(name) {
        return searchBin(app.project.rootItem, name);
    }

    function searchBin(bin, name) {
        for (var i = 0; i < bin.children.numItems; i++) {
            var item = bin.children[i];
            if (item.name === name) return item;
            if (item.type === ProjectItemType.BIN) {
                var found = searchBin(item, name);
                if (found) return found;
            }
        }
        return null;
    }

    function getOrCreateTrack(index) {
        while (seq.videoTracks.numTracks <= index) {
            seq.videoTracks.addTrack();
        }
        return seq.videoTracks[index];
    }

    function clearTrackRange(track, start, end) {
        for (var i = track.clips.numItems - 1; i >= 0; i--) {
            var clip = track.clips[i];
            if ((clip.start < end) && ((clip.end) > start)) {
                clip.remove(0,1); // remove overlapping clip
            }
        }
    }

    var bgItem = findProjectItemByName("Backgrounds");
    var puppetItem = findProjectItemByName("Puppet");
    var iconItem = findProjectItemByName("Icon");

    if (bgItem && puppetItem && iconItem) {
        for (var i = 0; i < storyboardTimestamps.length; i++) {
            var entry = storyboardTimestamps[i];
            var start = entry[0];
            var end = entry[1];
            var duration = end - start;
            var puppetCount = entry[2];
            var maxPuppetLayer = entry[3];
            var iconCount = entry[4];
            var maxIconLayer = entry[5];

            // Background clip
            clearTrackRange(trackBackground, start, end);
            var bgClip = trackBackground.insertClip(bgItem, start);
            if (bgClip) bgClip.end = end;

            // Puppets
            for (var p = 0; p < puppetCount; p++) {
                var trackIndex = trackBasePuppet + (p % maxPuppetLayer);
                var track = getOrCreateTrack(trackIndex);
                clearTrackRange(track, start, end);
                var puppetClip = track.insertClip(puppetItem, start);
                if (puppetClip) puppetClip.end = end;
            }

            // Icons
            for (var c = 0; c < iconCount; c++) {
                var trackIndex = trackBaseIcon + (c % maxIconLayer);
                var track = getOrCreateTrack(trackIndex);
                clearTrackRange(track, start, end);
                var iconClip = track.insertClip(iconItem, start);
                if (iconClip) iconClip.end = end;
            }
        }
    }
}