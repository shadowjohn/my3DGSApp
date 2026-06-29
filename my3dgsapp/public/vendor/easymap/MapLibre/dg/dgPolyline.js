(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function toDgXY(value) {
        return value instanceof window.dgXY ? value : new window.dgXY(value);
    }

    function syncXYArrays(item) {
        item._xs = [];
        item._ys = [];
        for (var i = 0; i < item._xys.length; i++) {
            item._xs.push(item._xys[i].x);
            item._ys.push(item._xys[i].y);
        }
        item._pcount = item._xys.length;
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

    function dgPolyline(xys, ss, sw) {
        this._id = '';
        this._type = 'polyline';
        this._xys = [];
        if (Array.isArray(xys)) {
            for (var i = 0; i < xys.length; i++) {
                this._xys.push(toDgXY(xys[i]));
            }
        }
        this._strokeStyle = ss || 'rgba(0,0,255,1)';
        this._lineWidth = ns.toNumber(sw, 2);
        this._dash = {
            lineDash: null,
            lineCap: 'round'
        };
        this._isLinestringArrowEnabled = false;
        this._lineStringIconsrc = '';
        this._lineStringIconsrcScale = 1;
        this._instance = null;
        this._flashFocusData = {
            orinStyle: null,
            isPlaying: false,
            runTimes: 5,
            duration: 300,
            flashColor: 'rgb(255,0,0)',
            runInterval: null,
            _cFlag: 1
        };
        this.bufferObj = null;
        this.buffer = null;
        syncXYArrays(this);
        ns.attachItemBasics(this);
    }

    dgPolyline.prototype._refreshData = function () {
        ns.refreshItemData(this);
        return this;
    };

    dgPolyline.prototype._refreshStyle = function () {
        ns.refreshItemStyle(this);
        return this;
    };

    dgPolyline.prototype._setXYS = function () {
        syncXYArrays(this);
        return this;
    };

    dgPolyline.prototype.getBuffer = function () {
        return this.buffer;
    };

    dgPolyline.prototype.setBuffer = function (meter) {
        if (this._instance == null) {
            console.log('map.addItem 後才能 setBuffer');
            return this;
        }
        if (this._easymap == null || typeof this._easymap.dgToBufferDg != 'function') {
            console.log('MapLibre dgPolyline 尚未支援 setBuffer');
            return this;
        }
        if (this.bufferObj != null) this._easymap.removeItem(this.bufferObj);
        this.buffer = meter;
        this.bufferObj = this._easymap.dgToBufferDg(this, meter);
        this._easymap.addItem(this.bufferObj);
        return this;
    };

    dgPolyline.prototype.removeBuffer = function () {
        if (this._instance == null) {
            console.log('map.addItem 後才能 removeBuffer');
            return this;
        }
        if (this._easymap != null && this.bufferObj != null) {
            this._easymap.removeItem(this.bufferObj);
            this.bufferObj = null;
        }
        return this;
    };

    dgPolyline.prototype.enableFlashFocus = function (obj) {
        if (this._flashFocusData.isPlaying) {
            console.log('正在閃...');
            return this;
        }
        if (this._instance == null) {
            console.log('需 map.addItem 以後才能使用');
            return this;
        }
        obj = typeof obj == 'object' && obj != null ? obj : {};
        for (var key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) this._flashFocusData[key] = obj[key];
        }
        var originColor = this._strokeStyle;
        var remaining = this._flashFocusData.runTimes;
        this._flashFocusData.orinStyle = { strokeColor: originColor };
        this._flashFocusData.isPlaying = true;
        this._flashFocusData._cFlag = 1;
        this._flashFocusData.runInterval = setInterval(function () {
            if (this._flashFocusData._cFlag == 1) {
                this.setStrokeColor(this._flashFocusData.flashColor);
            }
            else {
                this.setStrokeColor(originColor);
                if (remaining != -1) {
                    remaining--;
                    if (remaining <= 0) {
                        this.disableFlashFocus();
                        return;
                    }
                }
            }
            this._flashFocusData._cFlag *= -1;
        }.bind(this), this._flashFocusData.duration);
        return this;
    };

    dgPolyline.prototype.disableFlashFocus = function () {
        if (!this._flashFocusData.isPlaying) {
            console.log('沒在閃...');
            return this;
        }
        clearInterval(this._flashFocusData.runInterval);
        this._flashFocusData.isPlaying = false;
        if (this._flashFocusData.orinStyle != null) {
            this.setStrokeColor(this._flashFocusData.orinStyle.strokeColor);
        }
        return this;
    };

    dgPolyline.prototype.getCenter = function () {
        if (this._xys.length == 0) return new window.dgXY(0, 0);
        var x = 0;
        var y = 0;
        for (var i = 0; i < this._xys.length; i++) {
            x += parseFloat(this._xys[i].x);
            y += parseFloat(this._xys[i].y);
        }
        return new window.dgXY(x / this._xys.length, y / this._xys.length);
    };

    dgPolyline.prototype.getExtent = function () {
        if (this._xys.length == 0) return [0, 0, 0, 0];
        var minX = parseFloat(this._xys[0].x);
        var minY = parseFloat(this._xys[0].y);
        var maxX = minX;
        var maxY = minY;
        for (var i = 1; i < this._xys.length; i++) {
            var x = parseFloat(this._xys[i].x);
            var y = parseFloat(this._xys[i].y);
            if (x < minX) minX = x;
            if (y < minY) minY = y;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
        }
        return [minX, minY, maxX, maxY];
    };

    dgPolyline.prototype.getExtentArea = function () {
        var extent = this.getExtent();
        var a = projectMercator(extent[0], extent[1]);
        var b = projectMercator(extent[2], extent[3]);
        return Math.abs((b[0] - a[0]) * (b[1] - a[1]));
    };

    dgPolyline.prototype.setUpperZoomByBoundary = function (options) {
        this._setUpperZoomByBoundary = true;
        this._upperZoomByBoundaryOptions = options || this._upperZoomByBoundaryOptions || {};
        if (this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgPolyline.prototype.getVertexCount = function () {
        return Math.max(0, this._xys.length - 2);
    };

    dgPolyline.prototype.getVertex = function (iidx) {
        iidx = parseInt(iidx, 10);
        if (isNaN(iidx)) return null;
        return this._xys[iidx - 1] || null;
    };

    dgPolyline.prototype.addVertex = function (ixy) {
        this._xys.push(toDgXY(ixy));
        syncXYArrays(this);
        return this._refreshData();
    };

    dgPolyline.prototype.getStrokeWidth = function () {
        return this._lineWidth;
    };

    dgPolyline.prototype.setStrokeWidth = function (val) {
        this._lineWidth = ns.toNumber(val, 1);
        return this._refreshStyle();
    };

    dgPolyline.prototype.getStrokeColor = function () {
        return this._strokeStyle;
    };

    dgPolyline.prototype.setStrokeColor = function (val) {
        this._strokeStyle = val || 'rgba(0,0,255,1)';
        return this._refreshStyle();
    };

    dgPolyline.prototype.enableDashed = function (lineDash) {
        this._dash = this._dash || {};
        this._dash.lineDash = Array.isArray(lineDash) ? lineDash.slice() : [4, 8];
        return this._refreshStyle();
    };

    dgPolyline.prototype.disableDashed = function () {
        this._dash = this._dash || {};
        this._dash.lineDash = null;
        return this._refreshStyle();
    };

    dgPolyline.prototype.enableLineStringArrow = function (iconsrc, op) {
        if (iconsrc == null || iconsrc == '') {
            iconsrc = 'https://openlayers.org/en/latest/examples/data/arrow.png';
        }
        var scale = this._lineStringIconsrcScale || 1;
        if (typeof op == 'number') {
            scale = op;
        }
        else if (op != null && typeof op == 'object' && op.scale != null) {
            scale = op.scale;
        }
        this._isLinestringArrowEnabled = true;
        this._lineStringIconsrc = iconsrc;
        this._lineStringIconsrcScale = ns.toNumber(scale, 1);
        if (this._easymap != null && typeof this._easymap._enablePolylineArrow == 'function') {
            this._easymap._enablePolylineArrow(this);
        }
        return this;
    };

    dgPolyline.prototype.disableLineStringArrow = function () {
        if (this._easymap != null && typeof this._easymap._removePolylineArrow == 'function') {
            this._easymap._removePolylineArrow(this);
        }
        this._isLinestringArrowEnabled = false;
        return this;
    };

    dgPolyline.prototype.setRotate = function (r, obj) {
        var degree = parseFloat(r);
        if (isNaN(degree)) {
            console.log('setRotate(r, { anchor: [x, y] })');
            return this;
        }
        obj = obj || {};
        var anchor = Array.isArray(obj.anchor) ? obj.anchor : null;
        if (anchor == null && obj.xy != null) {
            var anchorXY = toDgXY(obj.xy);
            anchor = [anchorXY.x, anchorXY.y];
        }
        if (anchor == null) {
            var center = this.getCenter();
            anchor = [center.x, center.y];
        }
        var ax = parseFloat(anchor[0]);
        var ay = parseFloat(anchor[1]);
        if (isNaN(ax) || isNaN(ay)) {
            console.log('setRotate anchor 不正確');
            return this;
        }
        // 舊版正角度是順時針，MapLibre 座標平面需反向換算。
        var rad = -degree * Math.PI / 180;
        var cos = Math.cos(rad);
        var sin = Math.sin(rad);
        for (var i = 0; i < this._xys.length; i++) {
            var dx = parseFloat(this._xys[i].x) - ax;
            var dy = parseFloat(this._xys[i].y) - ay;
            var x = ax + dx * cos - dy * sin;
            var y = ay + dx * sin + dy * cos;
            this._xys[i] = new window.dgXY(x, y);
        }
        syncXYArrays(this);
        return this._refreshData();
    };

    window.dgPolyline = dgPolyline;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgPolyline');
})(window);
