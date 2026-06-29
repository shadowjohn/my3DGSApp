(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    ns.sourceRenderer = ns.sourceRenderer || {
        version: 'ml1.0.1',
        owner: 'Easymap MapLibre runtime'
    };

    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('renderer/source-renderer');
})(window);
