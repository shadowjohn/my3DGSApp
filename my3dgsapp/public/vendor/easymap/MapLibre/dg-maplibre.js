(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};
    var required = [
        'dgXY',
        'dgText',
        'dgPoint',
        'dgPolyline',
        'dgPolygon',
        'dgCurve',
        'dgStaticImage',
        'dgIcon',
        'dgMarker',
        'dgGStyle',
        'dgWKT',
        'dgGeoJson',
        'dgKML',
        'dgGML',
        'dgSource',
        'dg3D'
    ];
    var missing = [];
    for (var i = 0; i < required.length; i++) {
        if (typeof window[required[i]] != 'function') {
            missing.push(required[i]);
        }
    }
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg-maplibre');
    ns.bootstrap = ns.bootstrap || {};
    ns.bootstrap.modulesLoaded = ns.modulesLoaded.slice();
    ns.bootstrap.missing = missing;
    ns.bootstrap.ready = missing.length == 0;
})(window);
