/*
Comp Chapters.jsx
*/

app.beginUndoGroup("Comp Chapters");

var comp = app.project.activeItem;

if (!(comp instanceof CompItem)) {
    alert("Please select an active composition.");
} else {

    var solidLayers = [];

    // Collect solid layers top → bottom
    for (var i = 1; i <= comp.numLayers; i++) {
        var lyr = comp.layer(i);
        if (lyr instanceof AVLayer && lyr.source instanceof FootageItem && lyr.source.label === 0) {
            solidLayers.push(lyr);
        }
    }

    if (solidLayers.length === 0) {
        alert("No solid layers found in this comp.");
    } else {

        // Iterate bottom → top to preserve indexes
        for (var j = solidLayers.length - 1; j >= 0; j--) {
            var layer = solidLayers[j];
            var chapterNum = j + 1;
            var chapterName = "Chapter " + chapterNum;

            // Rename + label color
            layer.name = chapterName;
            layer.label = (chapterNum % 5) + 1;

            // Store original layer info
            var originalStart = layer.startTime;
            var originalIn = layer.inPoint;
            var originalOut = layer.outPoint;
            var duration = originalOut - originalIn;

            // === STEP 1: Create new comp matching solid duration ===
            var newComp = app.project.items.addComp(
                chapterName,
                comp.width,
                comp.height,
                comp.pixelAspect,
                duration,
                comp.frameRate
            );

            // === STEP 2: Copy solid into new comp ===
            layer.copyToComp(newComp);
            if (newComp.numLayers > 0) {
                var innerLayer = newComp.layer(1);
                innerLayer.startTime = 0;
                innerLayer.inPoint = 0;
                innerLayer.outPoint = duration;
            }

            // === STEP 3: Replace original solid with new comp in place ===
            layer.replaceSource(newComp, false);

            // === STEP 4: Fix layer timing so it stays in place ===
            layer.startTime = originalStart + (originalIn - 0); // preserve original timeline position
            layer.inPoint = 0;
            layer.outPoint = duration;

            // Preserve label color
            layer.label = (chapterNum % 5) + 1;
        }
    }
}

app.endUndoGroup();