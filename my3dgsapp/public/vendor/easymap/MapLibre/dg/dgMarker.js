(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function dgMarker(dgxy, icon, drag) {
        this._type = 'dgmarker';
        this._dgxy = dgxy instanceof window.dgXY ? dgxy : new window.dgXY(dgxy);
        this._dgicon = icon instanceof window.dgIcon ? icon : null;
        this._htmlstr = typeof icon == 'string' ? icon : '';
        this._icontype = this._dgicon != null ? 'dgicon' : 'string';
        this._drag = drag === true;
        this._instance = null;
        this._properties = {};
        this._scale = null;
        this._opacity = null;
        this._rotate = null;
        this._anchor = [0.5, 1];
        this._text = '';
        this._textStyle = {};
        this.content = '';
        ns.attachItemBasics(this);
        this.ondragstart = null;
        this.ondragend = null;
        this.ondblclick = null;
        this.onmouseover = null;
        this.onmouseout = null;
        this.mousedown = null;
        this.mouseup = null;
        this.dragfeatures = [];
    }

    dgMarker.prototype.getXY = function () {
        return this._dgxy;
    };

    dgMarker.prototype.getAnchor = function () {
        return this._anchor || [0.5, 1];
    };

    dgMarker.prototype.setAnchor = function (anchor) {
        this._anchor = Array.isArray(anchor) ? anchor.slice() : anchor;
        ns.refreshItemStyle(this);
        return this;
    };

    dgMarker.prototype.getScale = function () {
        return this._scale != null ? this._scale : (this._dgicon != null ? this._dgicon._scale : 1);
    };

    dgMarker.prototype.setScale = function (scale) {
        this._scale = ns.toNumber(scale, 1);
        if (this._dgicon != null) this._dgicon._scale = this._scale;
        ns.refreshItemStyle(this);
        return this;
    };

    dgMarker.prototype.getOpacity = function () {
        return this._opacity != null ? this._opacity : (this._dgicon != null ? this._dgicon._opacity : 1);
    };

    dgMarker.prototype.setOpacity = function (opacity) {
        this._opacity = ns.toNumber(opacity, 1);
        if (this._dgicon != null) this._dgicon._opacity = this._opacity;
        ns.refreshItemStyle(this);
        return this;
    };

    dgMarker.prototype.getRotation = function () {
        return this._rotate != null ? this._rotate : (this._dgicon != null ? this._dgicon._rotate : 0);
    };

    dgMarker.prototype.setRotation = function (rotation) {
        this._rotate = ns.toNumber(rotation, 0);
        if (this._dgicon != null) this._dgicon._rotate = this._rotate;
        ns.refreshItemStyle(this);
        return this;
    };

    dgMarker.prototype.getIcon = function () {
        return this._dgicon != null ? this._dgicon._src : null;
    };

    dgMarker.prototype.setIcon = function (src) {
        if (this._dgicon == null) this._dgicon = new window.dgIcon(src, 32, 32);
        this._dgicon._src = src || '';
        this._icontype = 'dgicon';
        this._htmlstr = '';
        ns.refreshItemStyle(this);
        return this;
    };

    dgMarker.prototype.getText = function () {
        return this._text || '';
    };

    dgMarker.prototype.setText = function (text, style) {
        return this._setText(text, style);
    };

    dgMarker.prototype.setLabel = function (text, style) {
        return this._setText(text, style);
    };

    dgMarker.prototype._setText = function (text, style) {
        this._text = text == null ? '' : String(text);
        this._textStyle = style || this._textStyle || {};
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgMarker.prototype.setXY = function (dgxy) {
        this._dgxy = dgxy instanceof window.dgXY ? dgxy : new window.dgXY(dgxy);
        if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
            this._easymap._updateItemData(this);
        }
        return this;
    };

    dgMarker.prototype.setProperties = function (properties) {
        this._properties = properties || {};
        if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
            this._easymap._updateItemData(this);
        }
        return this;
    };

    dgMarker.prototype.setContent = function (content) {
        if (content != null && typeof content == 'object') {
            var tmp = window.document != null ? window.document.createElement('div') : null;
            if (tmp != null && typeof tmp.appendChild == 'function') {
                tmp.appendChild(content);
                this.content = tmp.innerHTML || '';
            }
            else {
                this.content = String(content);
            }
        }
        else {
            this.content = content == null ? '' : String(content);
        }
        this.onclick = function () {
            if (this._easymap != null && typeof this._easymap._openInfoWindow == 'function') {
                this._easymap._openInfoWindow(this.getXY(), '', this.content, { marker: this });
            }
        }.bind(this);
        return this;
    };

    dgMarker.prototype.openInfoWindow = function (content, width, height) {
        if (this._easymap != null && typeof this._easymap.openInfoWindow == 'function') {
            this._easymap.openInfoWindow(this.getXY(), content, width, height, { marker: this });
        }
        return this;
    };

    window.dgMarker = dgMarker;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgMarker');
})(window);
