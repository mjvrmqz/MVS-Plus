{
    function smpteToSeconds(tc, fps) {
        var p = tc.split(";");
        if (p.length !== 4) return 0;
        return (
            parseInt(p[0],10) * 3600 +
            parseInt(p[1],10) * 60 +
            parseInt(p[2],10) +
            parseInt(p[3],10) / fps
        );
    }

    function snap(t, fps) {
        return Math.round(t * fps) / fps;
    }

    function AutoCutAndRippleFromCSV() {

        var comp = app.project.activeItem;
        if (!(comp && comp instanceof CompItem)) {
            alert("Select a composition.");
            return;
        }

        if (comp.selectedLayers.length !== 1) {
            alert("Select exactly one layer.");
            return;
        }

        var selectedLayer = comp.selectedLayers[0];
        if (!(selectedLayer instanceof AVLayer)) {
            alert("Selected layer must be footage, audio, or precomp.");
            return;
        }

        var baseSource = selectedLayer.source;
        var fps = comp.frameRate;

        var file = File.openDialog("Select silence CSV", "*.csv");
        if (!file) return;

        file.open("r");
        var lines = file.read().split("\n");
        file.close();

        if (lines.length < 2) {
            alert("CSV empty.");
            return;
        }

        app.beginUndoGroup("Auto Cut + Ripple Silence");

        var ranges = [];
        for (var i = 1; i < lines.length; i++) {
            var row = lines[i].replace("\r","");
            if (!row) continue;
            var cols = row.split(",");
            if (cols.length < 2) continue;

            var start = snap(smpteToSeconds(cols[0], fps), fps);
            var end   = snap(smpteToSeconds(cols[1], fps), fps);
            if (start >= end) continue;
            ranges.push({start:start, end:end});
        }

        for (var r = 0; r < ranges.length; r++) {

            var start = ranges[r].start;
            var end   = ranges[r].end;

            // Find layer containing this silence
            var targetLayer = null;
            for (var i = 1; i <= comp.numLayers; i++) {
                var L = comp.layer(i);
                if (!(L instanceof AVLayer)) continue;
                if (L.source === baseSource &&
                    start < L.outPoint &&
                    end > L.inPoint) {
                    targetLayer = L;
                    break;
                }
            }

            if (!targetLayer) continue;

            var inP = targetLayer.inPoint;
            var outP = targetLayer.outPoint;

            // Clamp start/end strictly inside layer bounds
            start = Math.max(start, inP + 0.0001);
            end   = Math.min(end, outP - 0.0001);

            var silenceDuration = end - start;

            if (start >= end) continue; // skip tiny or invalid ranges

            // Edge-case safe removal/split
            if (start <= inP && end >= outP) {
                // Silence covers whole layer → remove layer
                targetLayer.remove();
            } else if (start <= inP) {
                // Silence at start → split only at end
                if (end < outP) {
                    targetLayer.splitLayer(end).startTime = end;
                    targetLayer.remove();
                }
            } else if (end >= outP) {
                // Silence at end → split only at start
                targetLayer.splitLayer(start).remove();
            } else {
                // Silence inside layer → split start then end
                var afterLayer = targetLayer.splitLayer(end);
                targetLayer.splitLayer(start).remove();
            }

            // Ripple all remaining layers
            for (var j = 1; j <= comp.numLayers; j++) {
                var rippleLayer = comp.layer(j);
                if (!(rippleLayer instanceof AVLayer)) continue;
                if (rippleLayer.source === baseSource && rippleLayer.inPoint >= end) {
                    rippleLayer.startTime -= silenceDuration;
                }
            }
        }

        app.endUndoGroup();
        alert("Silence removed and timeline fully rippled.");
    }

    AutoCutAndRippleFromCSV();
}