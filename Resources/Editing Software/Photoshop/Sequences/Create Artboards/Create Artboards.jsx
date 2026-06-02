#target photoshop
app.activeDocument.suspendHistory("Duplicate Template Layer for Assets (No Double, Clustered Horizontally)", "main()");

function main() {
    var doc = app.activeDocument;

    var file = File.openDialog("Select asset list file");
    if (!file || !file.exists) return;

    file.encoding = "UTF8";
    if (!file.open("r")) return;

    var content = file.read();
    file.close();
    if (!content) return;

    var lines = content.split(/\r?\n/);

    // Find Template
    var template = null;
    for (var i = 0; i < doc.layerSets.length; i++) {
        if (doc.layerSets[i].name === "Template") {
            template = doc.layerSets[i];
            break;
        }
    }
    if (!template) { alert("No layer or artboard named 'Template' found!"); return; }

    // Color map
    var colorMap = { "BG": 3, "IC": 1, "PT": 5 };

    // Build asset list (ignore BR)
    var assets = [];
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].replace(/^\s+|\s+$/g, '');
        if (!line || line.indexOf(':') !== -1) continue;

        var name = line.split(/\s/)[0];
        if (!name || name.indexOf("BR") !== -1) continue;

        assets.push(name);
    }

    // Measure template
    var b = template.bounds;
    var width  = Math.max(b[2].as("px") - b[0].as("px"), 1000);
    var height = Math.max(b[3].as("px") - b[1].as("px"), 1000);

    var spacingX = width + 3000;
    var spacingY = height + 1500;
    var perRow = 4;
    var clusterGap = 10000; // initial big gap, will adjust dynamically

    // Separate assets by type
    var typeAssets = { "BG": [], "IC": [], "PT": [] };
    for (var i = 0; i < assets.length; i++) {
        var n = assets[i];
        if (n.indexOf("BG") !== -1) typeAssets["BG"].push(n);
        else if (n.indexOf("IC") !== -1) typeAssets["IC"].push(n);
        else if (n.indexOf("PT") !== -1) typeAssets["PT"].push(n);
    }

    var typeOrder = ["BG", "IC", "PT"];
    var clusterOffsetX = 0;

    // Duplicate and position by type clusters
    for (var t = 0; t < typeOrder.length; t++) {
        var type = typeOrder[t];
        var arr = typeAssets[type];

        // Sort assets by chapter & index
        arr.sort(function(a, b) {
            var pa = a.match(/^C(\d+)(BG|IC|PT)(\d+)$/);
            var pb = b.match(/^C(\d+)(BG|IC|PT)(\d+)$/);
            if (!pa || !pb) return 0;
            var chA = parseInt(pa[1],10), chB = parseInt(pb[1],10);
            var idxA = parseInt(pa[3],10), idxB = parseInt(pb[3],10);
            if (chA !== chB) return chA - chB;
            return idxA - idxB;
        });

        // Duplicate each
        for (var i = 0; i < arr.length; i++) {
            var name = arr[i];
            var copy = template.duplicate(doc, ElementPlacement.PLACEATEND);
            copy.name = name;

            var row = Math.floor(i / perRow);
            var col = i % perRow;

            copy.translate(
                clusterOffsetX + col * spacingX - b[0].as("px"),
                row * spacingY - b[1].as("px")
            );

            copy.color = colorMap[type];
        }

        // Update clusterOffsetX dynamically based on how wide this cluster is
        var clusterCols = Math.min(perRow, arr.length);
        clusterOffsetX += clusterCols * spacingX + clusterGap;
    }

    // ---------- LAYER PANEL ORDER (no BR) ----------
    var layers = [];
    for (var i = 0; i < doc.layerSets.length; i++) {
        var n = doc.layerSets[i].name;
        if (n !== "Template" && n.indexOf("BR") === -1) layers.push(doc.layerSets[i]);
    }

    layers.sort(function(a, b) {
        var pa = a.name.match(/^C(\d+)(BG|IC|PT)(\d+)$/);
        var pb = b.name.match(/^C(\d+)(BG|IC|PT)(\d+)$/);
        if (!pa || !pb) return 0;

        var typeA = pa[2], typeB = pb[2];
        if (typeOrder.indexOf(typeA) !== typeOrder.indexOf(typeB)) return typeOrder.indexOf(typeA) - typeOrder.indexOf(typeB);

        var chA = parseInt(pa[1],10), chB = parseInt(pb[1],10);
        if (chA !== chB) return chA - chB;

        var idxA = parseInt(pa[3],10), idxB = parseInt(pb[3],10);
        return idxA - idxB;
    });

    for (var i = layers.length - 1; i >= 0; i--) layers[i].move(doc, ElementPlacement.PLACEATBEGINNING);
}