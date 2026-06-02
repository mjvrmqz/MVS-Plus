(function ResetQuickParent() {
    var PREF_SECTION = "QuickParent";
    var PREF_KEY = "skipConfirm";

    if (app.settings.haveSetting(PREF_SECTION, PREF_KEY)) {
        app.settings.saveSetting(PREF_SECTION, PREF_KEY, "false");
        alert("QuickParent confirmation dialog has been reset.");
    } else {
        alert("Nothing to reset — confirmation was already enabled.");
    }
})();