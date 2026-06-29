(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function toDgXY(value) {
        return value instanceof window.dgXY ? value : new window.dgXY(value);
    }

    function sameXY(a, b) {
        if (a == null || b == null) return false;
        return parseFloat(a.x) == parseFloat(b.x) && parseFloat(a.y) == parseFloat(b.y);
    }

    function closeRing(points) {
        if (points.length == 0) return points;
        if (!sameXY(points[0], points[points.length - 1])) {
            points.push(new window.dgXY(points[0].x, points[0].y));
        }
        return points;
    }

    function syncXYArrays(item) {
        closeRing(item._xys);
        item._xs = [];
        item._ys = [];
        for (var i = 0; i < item._xys.length; i++) {
            item._xs.push(item._xys[i].x);
            item._ys.push(item._xys[i].y);
        }
        item._pcount = item._xys.length;
        item.xys = item._xys;
        item.xs = item._xs;
        item.ys = item._ys;
        item.pcount = item._pcount;
        item.attributes = item._attributes;
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

    function dgPolygon(xys, ss, fs, sw) {
        this._id = '';
        this._type = 'polygon';
        this._xys = [];
        if (Array.isArray(xys)) {
            for (var i = 0; i < xys.length; i++) {
                this._xys.push(toDgXY(xys[i]));
            }
        }
        this._attributes = {};
        this._strokeStyle = ss || 'rgba(0,0,255,1)';
        this._fillStyle = fs || 'rgba(0,0,255,0.25)';
        this._lineWidth = ns.toNumber(sw, 2);
        this._dash = {
            lineDash: null,
            lineCap: 'round'
        };
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

    dgPolygon.prototype._refreshData = function () {
        ns.refreshItemData(this);
        return this;
    };

    dgPolygon.prototype._refreshStyle = function () {
        ns.refreshItemStyle(this);
        return this;
    };

    dgPolygon.prototype._setXYS = function () {
        syncXYArrays(this);
        return this;
    };

    dgPolygon.prototype.getBuffer = function () {
        return this.buffer;
    };

    dgPolygon.prototype.setBuffer = function (meter) {
        if (this._instance == null) {
            console.log('map.addItem 後才能 setBuffer');
            return this;
        }
        if (this._easymap == null || typeof this._easymap.dgToBufferDg != 'function') {
            console.log('MapLibre dgPolygon 尚未支援 setBuffer');
            return this;
        }
        if (this.bufferObj != null) this._easymap.removeItem(this.bufferObj);
        this.buffer = meter;
        this.bufferObj = this._easymap.dgToBufferDg(this, meter);
        this._easymap.addItem(this.bufferObj);
        return this;
    };

    dgPolygon.prototype.removeBuffer = function () {
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

    dgPolygon.prototype.enableFlashFocus = function (obj) {
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
        var originStroke = this._strokeStyle;
        var originFill = this._fillStyle;
        var remaining = this._flashFocusData.runTimes;
        this._flashFocusData.orinStyle = { strokeColor: originStroke, fillColor: originFill };
        this._flashFocusData.isPlaying = true;
        this._flashFocusData._cFlag = 1;
        this._flashFocusData.runInterval = setInterval(function () {
            if (this._flashFocusData._cFlag == 1) {
                this.setStrokeColor(this._flashFocusData.flashColor);
                this.setFillColor(this._flashFocusData.flashColor);
            }
            else {
                this.setStrokeColor(originStroke);
                this.setFillColor(originFill);
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

    dgPolygon.prototype.disableFlashFocus = function () {
        if (!this._flashFocusData.isPlaying) {
            console.log('沒在閃...');
            return this;
        }
        clearInterval(this._flashFocusData.runInterval);
        this._flashFocusData.isPlaying = false;
        if (this._flashFocusData.orinStyle != null) {
            this.setStrokeColor(this._flashFocusData.orinStyle.strokeColor);
            this.setFillColor(this._flashFocusData.orinStyle.fillColor);
        }
        return this;
    };

    dgPolygon.prototype.enableDashed = function (lineDash) {
        this._dash = this._dash || {};
        this._dash.lineDash = Array.isArray(lineDash) ? lineDash.slice() : [4, 8];
        return this._refreshStyle();
    };

    dgPolygon.prototype.disableDashed = function () {
        this._dash = this._dash || {};
        this._dash.lineDash = null;
        return this._refreshStyle();
    };

    dgPolygon.prototype.getCenter = function () {
        if (this._xys.length == 0) return new window.dgXY(0, 0);
        var x = 0;
        var y = 0;
        for (var i = 0; i < this._xys.length; i++) {
            x += parseFloat(this._xys[i].x);
            y += parseFloat(this._xys[i].y);
        }
        return new window.dgXY(x / this._xys.length, y / this._xys.length);
    };

    dgPolygon.prototype.getExtent = function () {
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

    dgPolygon.prototype.getExtentArea = function () {
        var extent = this.getExtent();
        var a = projectMercator(extent[0], extent[1]);
        var b = projectMercator(extent[2], extent[3]);
        return Math.abs((b[0] - a[0]) * (b[1] - a[1]));
    };

    dgPolygon.prototype.getArea = function () {
        var area = 0;
        if (this._xys.length < 4) return 0;
        for (var i = 0; i < this._xys.length - 1; i++) {
            var a = projectMercator(this._xys[i].x, this._xys[i].y);
            var b = projectMercator(this._xys[i + 1].x, this._xys[i + 1].y);
            area += a[0] * b[1] - b[0] * a[1];
        }
        return Math.abs(area / 2);
    };

    dgPolygon.prototype.setUpperZoomByBoundary = function (options) {
        this._setUpperZoomByBoundary = true;
        this._upperZoomByBoundaryOptions = options || this._upperZoomByBoundaryOptions || {};
        if (this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgPolygon.prototype.getVertexCount = function () {
        return Math.max(0, this._xys.length - 1);
    };

    dgPolygon.prototype.getVertex = function (iidx) {
        iidx = parseInt(iidx, 10);
        if (isNaN(iidx)) return null;
        return this._xys[iidx - 1] || null;
    };

    dgPolygon.prototype.addVertex = function (ixy) {
        if (this._xys.length > 0 && sameXY(this._xys[0], this._xys[this._xys.length - 1])) {
            this._xys.pop();
        }
        this._xys.push(toDgXY(ixy));
        syncXYArrays(this);
        return this._refreshData();
    };

    dgPolygon.prototype.addAttributes = function (objects) {
        objects = objects || {};
        for (var key in objects) {
            if (Object.prototype.hasOwnProperty.call(objects, key)) this._attributes[key] = objects[key];
        }
        this.attributes = this._attributes;
        return this._refreshData();
    };

    dgPolygon.prototype.getStrokeWidth = function () {
        return this._lineWidth;
    };

    dgPolygon.prototype.setStrokeWidth = function (val) {
        this._lineWidth = ns.toNumber(val, 1);
        return this._refreshStyle();
    };

    dgPolygon.prototype.getStrokeColor = function () {
        return this._strokeStyle;
    };

    dgPolygon.prototype.setStrokeColor = function (val) {
        this._strokeStyle = val || 'rgba(0,0,255,1)';
        return this._refreshStyle();
    };

    dgPolygon.prototype.getFillColor = function () {
        return this._fillStyle;
    };

    dgPolygon.prototype.setFillColor = function (val) {
        this._fillStyle = val || 'rgba(0,0,255,0.25)';
        return this._refreshStyle();
    };

    dgPolygon.prototype.setRotate = function (r, obj) {
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
            var extent = this.getExtent();
            anchor = [(extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2];
        }
        var ax = parseFloat(anchor[0]);
        var ay = parseFloat(anchor[1]);
        if (isNaN(ax) || isNaN(ay)) {
            console.log('setRotate anchor 不正確');
            return this;
        }
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

    window.dgPolygon = dgPolygon;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgPolygon');
})(window);
