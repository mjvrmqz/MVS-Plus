app.beginUndoGroup("Null Camera Sequence Builder");

// ===========================
// HARD-CODED MOVEMENTS (REPLACED BY APPENDER)
// ===========================
var movementSequence = [
    "Move Right","Move Left","Ken Burns","Move Up","Zoom Out","Move Down"
];

// ===========================
// CHAPTER DATA (SEQUENTIAL CONSUMPTION)
// ===========================
var chapterData = {
    "Chapter 1": 3,
    "Chapter 2": 2,
    "Chapter 3": 3
};

// ===========================
var keyframeGap = 2.2;
var overlap = 1.1;
var startTime = 0;

// Strong but valid easing
var easeOut = new KeyframeEase(0, 73);
var easeIn  = new KeyframeEase(0, 73);

// Movement pointer (handles chapter slicing)
var movementIndex = 0;

// ===========================
for (var compName in chapterData) {

    var comp = null;
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === compName) {
            comp = it;
            break;
        }
    }
    if (!comp) continue;

    var needed = chapterData[compName];

    // Collect existing nulls bottom → top
    var nulls = [];
    for (var l = 1; l <= comp.numLayers; l++) {
        if (comp.layer(l).nullLayer) nulls.push(comp.layer(l));
    }
    nulls.sort(function(a,b){ return b.index - a.index; });

    // Trim extras
    while (nulls.length > needed) {
        nulls.pop().remove();
    }

    // Add missing
    while (nulls.length < needed) {
        var n = comp.layers.addNull();
        n.threeDLayer = true;
        if (nulls.length > 0) n.parent = nulls[nulls.length - 1];
        nulls.push(n);
    }

    // Apply movements
    for (var j = 0; j < nulls.length; j++) {

        var layer = nulls[j];

        // LOOP MOVEMENTS IF OUT OF BOUNDS
        var movement = movementSequence[movementIndex % movementSequence.length];
        movementIndex++;
        layer.name = movement;

        // Layer inpoint starts 1 second before first keyframe
        var tStart = startTime + j * (keyframeGap - overlap);
        var tEnd   = tStart + keyframeGap;
        layer.inPoint = Math.max(tStart - 1, 0);
        layer.outPoint = tEnd;

        var pos = layer.property("Position");

        // GET CURRENT POSITION FOR RELATIVE MOVEMENT
        var base = pos.value; // starting point
        var startVal = base.slice(); // clone array
        var endVal = base.slice();

        // Relative offsets instead of absolute positions
        switch (movement) {
            case "Zoom In":    endVal[2] += 330; break;
            case "Zoom Out":   endVal[2] -= 330; break;
            case "Move Left":  endVal[0] -= 249; break;
            case "Move Right": endVal[0] += 249; break;
            case "Move Up":    endVal[1] -= 228; break;
            case "Move Down":  endVal[1] += 360; break;
        }

        var k1 = pos.addKey(tStart);
        var k2 = pos.addKey(tEnd);

        pos.setValueAtKey(k1, startVal);
        pos.setValueAtKey(k2, endVal);

        // Spatial properties require array length = 1
        pos.setTemporalEaseAtKey(k1, [easeOut], [easeOut]);
        pos.setTemporalEaseAtKey(k2, [easeIn],  [easeIn]);

        pos.setInterpolationTypeAtKey(k1, KeyframeInterpolationType.BEZIER);
        pos.setInterpolationTypeAtKey(k2, KeyframeInterpolationType.BEZIER);
    }
}

app.endUndoGroup();