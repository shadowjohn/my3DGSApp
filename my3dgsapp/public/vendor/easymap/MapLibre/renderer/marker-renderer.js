(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    ns.markerRenderer = ns.markerRenderer || {
        version: 'ml1.0.1',
        owner: 'Easymap MapLibre runtime'
    };

    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('renderer/marker-renderer');
})(window);
