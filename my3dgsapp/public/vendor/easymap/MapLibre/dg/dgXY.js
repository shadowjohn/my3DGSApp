(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function dgXY(x, y, z) {
        if (Array.isArray(x)) {
            z = x[2];
            y = x[1];
            x = x[0];
        }
        this.x = ns.toNumber(x, 0);
        this.y = ns.toNumber(y, 0);
        this.z = ns.toNumber(z, 0);
        this.xy = [this.x, this.y];
        this.yx = [this.y, this.x];
        this.lon = this.x;
        this.lat = this.y;
    }

    dgXY.prototype.toArray = function () {
        return [this.x, this.y];
    };

    window.dgXY = dgXY;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgXY');
})(window);
