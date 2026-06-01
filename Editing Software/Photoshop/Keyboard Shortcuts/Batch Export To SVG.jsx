var doc = app.activeDocument;

// Create new temp document with same size
var tempDoc = app.documents.add(
    doc.width,
    doc.height,
    doc.resolution,
    "Vector_Export",
    doc.mode
);

// Loop through layers
for (var i = 0; i < doc.layers.length; i++) {
    var layer = doc.layers[i];

    if (layer.kind == LayerKind.SOLIDFILL) {
        layer.duplicate(tempDoc, ElementPlacement.PLACEATBEGINNING);
    }
}

// If no vectors found
if (tempDoc.layers.length == 0) {
    alert("No vector shape layers found.");
} else {

    var svgOptions = new ExportOptionsSVG();
    svgOptions.embedRasterImages = false;
    svgOptions.fontSubsetting = SVGFontSubsetting.None;
    svgOptions.documentEncoding = SVGDocumentEncoding.UTF8;

    var file = File("~/Desktop/vector_only_export.svg");
    tempDoc.exportDocument(file, ExportType.SVG, svgOptions);
}

// Close temp doc without saving
tempDoc.close(SaveOptions.DONOTSAVECHANGES);