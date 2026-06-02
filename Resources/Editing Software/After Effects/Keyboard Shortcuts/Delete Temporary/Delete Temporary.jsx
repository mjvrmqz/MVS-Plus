// Delete Test Comps (case-insensitive, contains match)

(function () {

    app.beginUndoGroup("Delete Test Comps");

    var keywords = ["tmp", "test"];

    for (var i = app.project.numItems; i >= 1; i--) {

        var item = app.project.item(i);

        if (!(item instanceof CompItem)) continue;

        var nameLower = item.name.toLowerCase();

        for (var k = 0; k < keywords.length; k++) {

            if (nameLower.indexOf(keywords[k]) !== -1) {
                item.remove();
                break;
            }
        }
    }

    app.endUndoGroup();

})();