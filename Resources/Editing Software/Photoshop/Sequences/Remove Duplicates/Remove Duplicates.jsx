#target photoshop
app.activeDocument.suspendHistory("Organize Artboards by Name", "main()");

function main() {
    var doc = app.activeDocument;
    var groups = [];

    // Regex: C<number><TYPE><number>
    var re = /^C(\d+)([A-Z]+)(\d+)$/;

    // Collect top-level groups
    for (var i = 0; i < doc.layerSets.length; i++) {
        var ls = doc.layerSets[i];
        if (ls.parent !== doc) continue;

        var m = ls.name.match(re);
        if (!m) continue;

        groups.push({
            layer: ls,
            chapter: parseInt(m[1], 10),
            type: m[2],
            index: parseInt(m[3], 10)
        });
    }

    // Preserve first-seen type order (PT, BG, IC, etc)
    var typeOrder = [];
    for (var i = 0; i < groups.length; i++) {
        if (typeOrder.indexOf(groups[i].type) === -1) {
            typeOrder.push(groups[i].type);
        }
    }

    // Sort
    groups.sort(function(a, b) {
        var ta = typeOrder.indexOf(a.type);
        var tb = typeOrder.indexOf(b.type);
        if (ta !== tb) return ta - tb;
        if (a.chapter !== b.chapter) return a.chapter - b.chapter;
        return a.index - b.index;
    });

    // Move in correct order (bottom → top)
    for (var i = groups.length - 1; i >= 0; i--) {
        groups[i].layer.move(doc, ElementPlacement.PLACEATBEGINNING);
    }
}