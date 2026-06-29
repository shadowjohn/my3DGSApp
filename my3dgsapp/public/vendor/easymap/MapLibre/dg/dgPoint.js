(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function toDgXY(value) {
        return value instanceof window.dgXY ? value : new window.dgXY(value);
    }

    function dgPoint(xy, color, radius) {
        xy = toDgXY(xy);
        this._id = '';
        this._type = 'point';
        this._label = '.';
        this._x = xy.x;
        this._y = xy.y;
        this._strokeStyle = color || 'rgba(0,0,255,1)';
        this._fillStyle = color || 'rgba(0,0,255,1)';
        this._ptRadius = ns.toNumber(radius, 6);
        this._lineWidth = ns.toNumber(radius, 6);
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
        ns.attachItemBasics(this);
    }

    dgPoint.prototype._refreshData = function () {
        ns.refreshItemData(this);
        return this;
    };

    dgPoint.prototype._refreshStyle = function () {
        ns.refreshItemStyle(this);
        return this;
    };

    dgPoint.prototype.getBuffer = function () {
        return this.buffer;
    };

    dgPoint.prototype.setBuffer = function (meter) {
        if (this._instance == null) {
            console.log('map.addItem 後才能 setBuffer');
            return this;
        }
        if (this._easymap == null || typeof this._easymap.dgToBufferDg != 'function') {
            console.log('MapLibre dgPoint 尚未支援 setBuffer');
            return this;
        }
        if (this.bufferObj != null) this._easymap.removeItem(this.bufferObj);
        this.buffer = meter;
        this.bufferObj = this._easymap.dgToBufferDg(this, meter);
        this._easymap.addItem(this.bufferObj);
        return this;
    };

    dgPoint.prototype.removeBuffer = function () {
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

    dgPoint.prototype.enableFlashFocus = function (obj) {
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
        var originColor = this._fillStyle;
        var remaining = this._flashFocusData.runTimes;
        this._flashFocusData.orinStyle = { fillColor: originColor };
        this._flashFocusData.isPlaying = true;
        this._flashFocusData._cFlag = 1;
        this._flashFocusData.runInterval = setInterval(function () {
            if (this._flashFocusData._cFlag == 1) {
                this.setFillColor(this._flashFocusData.flashColor);
            }
            else {
                this.setFillColor(originColor);
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

    dgPoint.prototype.disableFlashFocus = function () {
        if (!this._flashFocusData.isPlaying) {
            console.log('沒在閃...');
            return this;
        }
        clearInterval(this._flashFocusData.runInterval);
        this._flashFocusData.isPlaying = false;
        if (this._flashFocusData.orinStyle != null) {
            this.setFillColor(this._flashFocusData.orinStyle.fillColor);
        }
        return this;
    };

    dgPoint.prototype.setLabel = function (label) {
        this._label = label == null ? '' : String(label);
        return this._refreshData();
    };

    dgPoint.prototype.getLabel = function () {
        return this._label;
    };

    dgPoint.prototype.setXY = function (tmpxy) {
        tmpxy = toDgXY(tmpxy);
        this._x = tmpxy.x;
        this._y = tmpxy.y;
        return this._refreshData();
    };

    dgPoint.prototype.getCenter = function () {
        return new window.dgXY(this._x, this._y);
    };

    dgPoint.prototype.getExtent = function () {
        return [this._x, this._y, this._x, this._y];
    };

    dgPoint.prototype.getExtentArea = function () {
        return 0;
    };

    dgPoint.prototype.setUpperZoomByBoundary = function (options) {
        this._setUpperZoomByBoundary = true;
        this._upperZoomByBoundaryOptions = options || this._upperZoomByBoundaryOptions || {};
        if (this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgPoint.prototype.getXY = function () {
        return new window.dgXY(this._x, this._y);
    };

    dgPoint.prototype.getFillColor = function () {
        return this._fillStyle;
    };

    dgPoint.prototype.setFillColor = function (val) {
        this._fillStyle = val || 'rgba(0,0,255,1)';
        return this._refreshStyle();
    };

    dgPoint.prototype.getStrokeWidth = function () {
        return this._lineWidth;
    };

    dgPoint.prototype.setStrokeWidth = function (val) {
        this._lineWidth = ns.toNumber(val, 1);
        this._ptRadius = this._lineWidth;
        return this._refreshStyle();
    };

    window.dgPoint = dgPoint;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgPoint');
})(window);
