(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function dgSource(type, options) {
        options = options || {};
        this._id = options.name || '';
        this._type = 'dgsource';
        this._sourceType = type || 'raster';
        this._layerType = this._sourceType;
        this._options = options;
        this.options = options;
        this._instance = null;
        this._events = [];
        if (options.getUrl != null) this._getUrl = options.getUrl;
        if (Array.isArray(this._options.url) == true) {
            for (var i = 0; i < this._options.url.length; i++) {
                this._options.url[i] = String(this._options.url[i]).replace(/\$/g, '');
            }
        }
        else if (this._options.url != null) {
            this._options.url = String(this._options.url).replace(/\$/g, '');
        }
        ns.attachItemBasics(this);
    }

    window.dgSource = dgSource;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgSource');
})(window);
