{
    function setInOutForAllLayers() {
        var comp = app.project.activeItem;
        if (!(comp instanceof CompItem)) {
            alert("Please select a composition first.");
            return;
        }

        app.beginUndoGroup("Set In/Out Points for All Layers");

        var layers = comp.layers;
        for (var i = 1; i <= layers.length; i++) {
            var layer = layers[i];

            var props = [
                layer.property("Position"),
                layer.property("Rotation"),
                layer.property("Scale"),
                layer.property("Opacity")
            ];

            var firstKF = null;
            var lastKF = null;

            for (var p = 0; p < props.length; p++) {
                var prop = props[p];
                if (prop && prop.numKeys > 0) {
                    var first = prop.keyTime(1);
                    var last = prop.keyTime(prop.numKeys);

                    if (firstKF === null || first < firstKF) firstKF = first;
                    if (lastKF === null || last > lastKF) lastKF = last;
                }
            }

            if (firstKF !== null && lastKF !== null) {
                var inTime = Math.max(0, firstKF - 1);
                var outTime = Math.min(comp.duration, lastKF + 1);

                layer.inPoint = inTime;
                layer.outPoint = outTime;
            }
        }

        app.endUndoGroup();
    }

    setInOutForAllLayers();
}