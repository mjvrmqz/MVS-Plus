// ============================
// youtube_comment_to_ae.jsx
// ============================

// Hard-coded comment
var commentText = "Comp Name: Screenshot 2026-01-05 at 2.36.07 PM | Username: @thatisabsolutelykooooge2211 | Date: 3 weeks ago | Comment: Shultz tries way too hard to be this east coast masculine alpha type. His overall tone is fake | Likes: 382";

// ----------------------------
// Utilities (ExtendScript-safe)
// ----------------------------
function trim(str) {
    return str.replace(/^\s+|\s+$/g, '');
}

function setText(layer, value) {
    if (!layer) return;
    var prop = layer.property("Source Text");
    if (!prop) return;
    var td = prop.value;
    td.text = value;
    prop.setValue(td);
}

// ----------------------------
// Parse comment blob
// ----------------------------
var parts = commentText.split('|');
for (var i = 0; i < parts.length; i++) parts[i] = trim(parts[i]);

function getVal(part, label) {
    return trim(part.replace(label, ''));
}

var compName  = getVal(parts[0], "Comp Name:");
var username  = getVal(parts[1], "Username:");
var dateText  = getVal(parts[2], "Date:");
var comment   = getVal(parts[3], "Comment:");
var likesText = getVal(parts[4], "Likes:");

// ----------------------------
// Username: 8-character cutoff
// ----------------------------
if (username.length > 8) {
    username = username.substring(0, 8);
}

// ----------------------------
// Comment: 37-char line wrapping
// ----------------------------
var lines = [];
for (var i = 0; i < comment.length; i += 37) {
    lines.push(comment.substring(i, i + 37));
}
var wrappedComment = lines.join("\r");
var lineCount = lines.length;

// ----------------------------
// Find template comp
// ----------------------------
var template = null;
for (var i = 1; i <= app.project.numItems; i++) {
    var it = app.project.item(i);
    if (it instanceof CompItem && it.name === "Isolated Comment") {
        template = it;
        break;
    }
}

// Only continue if template exists
if (template) {

    app.beginUndoGroup("YouTube Comment");

    var comp = template.duplicate();
    comp.name = compName || "New Comment Comp";

    // Label color: 13th AE label
    comp.label = 13;

    // ----------------------------
    // Move comp into Project/Dashboard/Assets
    // ----------------------------
    function findOrCreateFolder(parent, name) {
        for (var i = 1; i <= parent.numItems; i++) {
            if (parent.item(i) instanceof FolderItem && parent.item(i).name === name) {
                return parent.item(i);
            }
        }
        var f = app.project.items.addFolder(name);
        f.parentFolder = parent;
        return f;
    }

    var root = app.project.rootFolder;
    var projectFolder   = findOrCreateFolder(root, "Project");
    var dashboardFolder = findOrCreateFolder(projectFolder, "Dashboard");
    var assetsFolder    = findOrCreateFolder(dashboardFolder, "Assets");
    comp.parentFolder = assetsFolder;

    // ----------------------------
    // Set text layers
    // ----------------------------
    setText(comp.layer("Username"), username);
    setText(comp.layer("Date"), dateText);
    setText(comp.layer("Comment"), wrappedComment);
    setText(comp.layer("Likes"), likesText);

    // ----------------------------
    // Position/Scale logic based on line count
    // ----------------------------
    function setPos(layerName, x, y) {
        var l = comp.layer(layerName);
        if (!l) return;
        var p = l.property("Position");
        if (p) p.setValue([x, y]);
    }

    function setScale(layerName, x, y) {
        var l = comp.layer(layerName);
        if (!l) return;
        var s = l.property("Scale");
        if (s) s.setValue([x, y]);
    }

    if (lineCount <= 1) {
        setScale("Background", 70.7, 33.2);
        setPos("Likes", -267.5, 121.0);
        setPos("Reply Button", -44.5, 121.0);
        setPos("Thumb Graphic", -317.0, 99.5);
    }
    else if (lineCount === 2) {
        setScale("Background", 70.7, 38.2);
        setPos("Likes", -267.5, 184.0);
        setPos("Reply Button", 44.5, 184.0);
        setPos("Thumb Graphic", -317.0, 162.5);
    }
    else {
        setScale("Background", 70.7, 43.2);
        setPos("Likes", -267.5, 238.0);
        setPos("Reply Button", -44.5, 238.0);
        setPos("Thumb Graphic", -317.0, 216.5);
    }

    app.endUndoGroup();
}
// If template does not exist, nothing happens

// ============================
// End script
// ============================