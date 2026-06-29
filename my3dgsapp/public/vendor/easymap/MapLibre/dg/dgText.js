(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function toDgXY(value) {
        return value instanceof window.dgXY ? value : new window.dgXY(value);
    }

    function dgText(xy, label, color, fontSize) {
        xy = toDgXY(xy);
        this._id = '';
        this._type = 'text';
        this._label = label == null ? '' : String(label);
        this._fontSize = ns.toNumber(fontSize, 10);
        this._rotate = 0;
        this._x = xy.x;
        this._y = xy.y;
        this._textColor = color || 'rgba(255,0,0,1)';
        this._textOuterColor = 'rgba(255,255,255,0.5)';
        this._ptRadius = 0;
        this._lineWidth = 0;
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
        ns.attachItemBasics(this);
    }

    dgText.prototype._refreshData = function () {
        ns.refreshItemData(this);
        return this;
    };

    dgText.prototype._refreshStyle = function () {
        ns.refreshItemStyle(this);
        return this;
    };

    dgText.prototype.setXY = function (tmpxy) {
        tmpxy = toDgXY(tmpxy);
        this._x = tmpxy.x;
        this._y = tmpxy.y;
        return this._refreshData();
    };

    dgText.prototype.getXY = function () {
        return new window.dgXY(this._x, this._y);
    };

    dgText.prototype.getCenter = function () {
        return this.getXY();
    };

    dgText.prototype.getExtent = function () {
        return {
            lt_x: this._x,
            lt_y: this._y,
            rb_x: this._x,
            rb_y: this._y
        };
    };

    dgText.prototype.setUpperZoomByBoundary = function (options) {
        this._setUpperZoomByBoundary = true;
        this._upperZoomByBoundaryOptions = options || this._upperZoomByBoundaryOptions || {};
        if (this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgText.prototype.getTextColor = function () {
        return this._textColor;
    };

    dgText.prototype.getRotate = function () {
        return this._rotate;
    };

    dgText.prototype.setText = function (val) {
        this._label = val == null ? '' : String(val);
        return this._refreshData();
    };

    dgText.prototype.getText = function () {
        return this._label;
    };

    dgText.prototype.setRotate = function (val) {
        val = parseInt(val, 10);
        if (isNaN(val)) val = 0;
        this._rotate = val % 360;
        return this._refreshStyle();
    };

    dgText.prototype.setTextColor = function (val) {
        this._textColor = val || 'rgba(255,0,0,1)';
        return this._refreshStyle();
    };

    dgText.prototype.getFontSize = function () {
        return parseInt(this._fontSize, 10);
    };

    dgText.prototype.setFontSize = function (val) {
        this._fontSize = ns.toNumber(val, 1);
        return this._refreshStyle();
    };

    dgText.prototype.enableFlashFocus = function (obj) {
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
        var originColor = this._textColor;
        var remaining = this._flashFocusData.runTimes;
        this._flashFocusData.orinStyle = { textColor: originColor };
        this._flashFocusData.isPlaying = true;
        this._flashFocusData._cFlag = 1;
        this._flashFocusData.runInterval = setInterval(function () {
            if (this._flashFocusData._cFlag == 1) {
                this.setTextColor(this._flashFocusData.flashColor);
            }
            else {
                this.setTextColor(originColor);
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

    dgText.prototype.disableFlashFocus = function () {
        if (!this._flashFocusData.isPlaying) {
            console.log('沒在閃...');
            return this;
        }
        clearInterval(this._flashFocusData.runInterval);
        this._flashFocusData.isPlaying = false;
        if (this._flashFocusData.orinStyle != null) {
            this.setTextColor(this._flashFocusData.orinStyle.textColor);
        }
        return this;
    };

    window.dgText = dgText;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgText');
})(window);
