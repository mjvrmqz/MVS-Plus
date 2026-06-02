#target photoshop
app.activeDocument.suspendHistory("Create Group Hierarchy", "main()");

function main() {
    var doc = app.activeDocument;
    var groups = ["Background", "Icon", "Puppet"];

    for (var i = 0; i < groups.length; i++) {
        var groupName = groups[i];
        if (!findGroupByName(groupName)) {
            var newGroup = doc.layerSets.add();
            newGroup.name = groupName;
        }
    }
}

// Helper: find top-level group by name
function findGroupByName(name) {
    var doc = app.activeDocument;
    for (var i = 0; i < doc.layerSets.length; i++) {
        if (doc.layerSets[i].name == name) return doc.layerSets[i];
    }
    return null;
}