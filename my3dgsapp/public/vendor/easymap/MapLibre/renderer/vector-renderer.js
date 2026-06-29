(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    ns.vectorRenderer = ns.vectorRenderer || {
        version: 'ml1.0.1',
        owner: 'Easymap MapLibre runtime'
    };

    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('renderer/vector-renderer');
})(window);
