(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function dgIcon(src, width, height, options) {
        options = options || {};
        this._type = 'dgicon';
        this._src = src || '';
        this._width = width || 32;
        this._height = height || 32;
        this._w = this._width;
        this._h = this._height;
        this._options = options;
        this._scale = options.scale != null ? ns.toNumber(options.scale, 1) : 1;
        this._opacity = options.opacity != null ? ns.toNumber(options.opacity, 1) : 1;
        this._rotate = options.rotate != null ? ns.toNumber(options.rotate, 0) : 0;
    }

    window.dgIcon = dgIcon;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgIcon');
})(window);
