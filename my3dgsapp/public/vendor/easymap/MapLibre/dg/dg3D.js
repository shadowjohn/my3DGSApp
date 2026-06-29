(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function dg3D(layerType, data, options) {
        this._type = 'dg3d';
        this._layerType = layerType;
        this._url = data;
        this._data = data;
        this._options = options || {};
        this._instance = null;
        ns.attachItemBasics(this);
    }

    window.dg3D = dg3D;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dg3D');
})(window);
