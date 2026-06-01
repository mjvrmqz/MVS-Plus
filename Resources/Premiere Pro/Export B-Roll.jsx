(function () {
    var proj = app.project;
    var seq = proj.activeSequence;
    if (!seq) return;

    var track = seq.videoTracks[0]; // V1
    if (!track || track.clips.numItems === 0) return;

    for (var i = 0; i < track.clips.numItems; i++) {
        var clip = track.clips[i];

        var newSeq = proj.createNewSequenceFromClips(
            clip.name,
            [clip.projectItem],
            seq.videoTracks[0]
        );

        if (!newSeq) continue;

        newSeq.setInPoint(clip.start.seconds, 0);
        newSeq.setOutPoint(clip.end.seconds, 0);
    }
})();