(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function toDgXY(value) {
        return value instanceof window.dgXY ? value : new window.dgXY(value);
    }

    function numberOr(value, fallback) {
        var num = parseFloat(value);
        return isNaN(num) ? fallback : num;
    }

    function projectMercator(x, y) {
        var maxLat = 85.05112878;
        var lon = parseFloat(x);
        var lat = Math.max(-maxLat, Math.min(maxLat, parseFloat(y)));
        var mx = lon * 20037508.34 / 180;
        var my = Math.log(Math.tan((90 + lat) * Math.PI / 360)) / (Math.PI / 180);
        my = my * 20037508.34 / 180;
        return [mx, my];
    }

    function getExtentValues(item) {
        var x1 = parseFloat(item._lt_xy.x);
        var y1 = parseFloat(item._lt_xy.y);
        var x2 = parseFloat(item._rb_xy.x);
        var y2 = parseFloat(item._rb_xy.y);
        return {
            left: Math.min(x1, x2),
            right: Math.max(x1, x2),
            top: Math.max(y1, y2),
            bottom: Math.min(y1, y2)
        };
    }

    function rotatePoint(point, center, rotate) {
        var degree = numberOr(rotate, 0);
        if (degree == 0) return point.slice();
        var rad = -degree * Math.PI / 180;
        var cos = Math.cos(rad);
        var sin = Math.sin(rad);
        var dx = point[0] - center[0];
        var dy = point[1] - center[1];
        return [
            center[0] + dx * cos - dy * sin,
            center[1] + dx * sin + dy * cos
        ];
    }

    function getImageCoordinates(item) {
        var extent = getExtentValues(item);
        var coordinates = [
            [extent.left, extent.top],
            [extent.right, extent.top],
            [extent.right, extent.bottom],
            [extent.left, extent.bottom]
        ];
        var rotate = numberOr(item._rotate, 0);
        if (rotate == 0) return coordinates;
        var center = [(extent.left + extent.right) / 2, (extent.top + extent.bottom) / 2];
        for (var i = 0; i < coordinates.length; i++) {
            coordinates[i] = rotatePoint(coordinates[i], center, rotate);
        }
        return coordinates;
    }

    function dgStaticImage(src, dgXY_lt_xy, dgXY_rb_xy, ops) {
        this._id = '';
        this._type = 'dgstaticimage';
        this._src = src == null ? null : src;
        this._lt_xy = toDgXY(dgXY_lt_xy);
        this._rb_xy = toDgXY(dgXY_rb_xy);
        this._instance = null;
        this._width = 'auto';
        this._height = 'auto';
        this._rotate = 0;
        this._opacity = 1;
        this._options = ops || {};
        if (typeof this._options == 'object') {
            if (typeof this._options.width != 'undefined') this._width = this._options.width;
            if (typeof this._options.height != 'undefined') this._height = this._options.height;
            if (typeof this._options.rotate != 'undefined') this._rotate = numberOr(this._options.rotate, 0);
            if (typeof this._options.opacity != 'undefined') this._opacity = numberOr(this._options.opacity, 1);
        }
        ns.attachItemBasics(this);
    }

    dgStaticImage.prototype._refreshData = function () {
        ns.refreshItemData(this);
        return this;
    };

    dgStaticImage.prototype._refreshStyle = function () {
        ns.refreshItemStyle(this);
        return this;
    };

    dgStaticImage.prototype._getCoordinates = function () {
        return getImageCoordinates(this);
    };

    dgStaticImage.prototype.getCenter = function () {
        var extent = getExtentValues(this);
        return new window.dgXY((extent.left + extent.right) / 2, (extent.top + extent.bottom) / 2);
    };

    dgStaticImage.prototype.getExtent = function () {
        var extent = getExtentValues(this);
        return [extent.left, extent.bottom, extent.right, extent.top];
    };

    dgStaticImage.prototype.setExtent = function (dgXY_lt_xy, dgXY_rb_xy) {
        var lt = toDgXY(dgXY_lt_xy);
        var rb = toDgXY(dgXY_rb_xy);
        this._lt_xy = new window.dgXY(Math.min(lt.x, rb.x), Math.max(lt.y, rb.y));
        this._rb_xy = new window.dgXY(Math.max(lt.x, rb.x), Math.min(lt.y, rb.y));
        return this._refreshData();
    };

    dgStaticImage.prototype.getExtentArea = function () {
        var extent = this.getExtent();
        var a = projectMercator(extent[0], extent[1]);
        var b = projectMercator(extent[2], extent[3]);
        return Math.abs((b[0] - a[0]) * (b[1] - a[1]));
    };

    dgStaticImage.prototype.getArea = function () {
        return this.getExtentArea();
    };

    dgStaticImage.prototype.setUpperZoomByBoundary = function (options) {
        this._setUpperZoomByBoundary = true;
        this._upperZoomByBoundaryOptions = options || this._upperZoomByBoundaryOptions || {};
        if (this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgStaticImage.prototype.getURL = function () {
        return this._src;
    };

    dgStaticImage.prototype.setURL = function (src) {
        this._src = src == null ? null : src;
        return this._refreshData();
    };

    dgStaticImage.prototype.getOpacity = function () {
        return this._opacity;
    };

    dgStaticImage.prototype.setOpacity = function (opacity) {
        this._opacity = numberOr(opacity, 1);
        if (this._opacity < 0) this._opacity = 0;
        if (this._opacity > 1) this._opacity = 1;
        return this._refreshStyle();
    };

    window.dgStaticImage = dgStaticImage;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgStaticImage');
})(window);
