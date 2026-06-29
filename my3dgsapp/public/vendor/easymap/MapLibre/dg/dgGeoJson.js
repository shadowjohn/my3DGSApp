(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function emptyFeatureCollection() {
        return { type: 'FeatureCollection', features: [] };
    }

    function isGeoJsonObject(data) {
        if (data == null || typeof data != 'object') return false;
        if (data.type == 'FeatureCollection' || data.type == 'Feature') return true;
        if (data.type != null && data.coordinates != null) return true;
        if (data.type == 'GeometryCollection' && Array.isArray(data.geometries)) return true;
        return false;
    }

    function isJsonText(data) {
        return typeof data == 'string' && /^[\s\r\n]*[\{\[]/.test(data);
    }

    function parseJsonText(data) {
        if (!isJsonText(data)) return null;
        try {
            return JSON.parse(data);
        } catch (ignore) {
            return null;
        }
    }

    function normalizeInput(data) {
        if (isGeoJsonObject(data)) return data;
        var parsed = parseJsonText(data);
        return isGeoJsonObject(parsed) ? parsed : null;
    }

    function loadText(url, success, failure) {
        var xhr = null;
        if (window != null && typeof window.XMLHttpRequest == 'function') xhr = new window.XMLHttpRequest();
        else if (typeof XMLHttpRequest == 'function') xhr = new XMLHttpRequest();
        if (xhr == null) {
            if (typeof failure == 'function') failure(new Error('XMLHttpRequest is unavailable'));
            return null;
        }
        xhr.onload = function () {
            if (!xhr.status || (xhr.status >= 200 && xhr.status < 300)) {
                if (typeof success == 'function') success(xhr.responseText, xhr);
                return;
            }
            if (typeof failure == 'function') failure(new Error('GeoJSON load failed: ' + xhr.status), xhr);
        };
        xhr.onerror = function (event) {
            if (typeof failure == 'function') failure(event, xhr);
        };
        xhr.open('GET', url, true);
        xhr.send(null);
        return xhr;
    }

    function dgGeoJson(data, srs, callback) {
        this._type = 'dggeojson';
        this._easymapClass = 'dggeojson';
        this._url = data;
        this._geojson = normalizeInput(data);
        this._dataSRS = srs || 'EPSG:4326';
        this._callback = typeof callback == 'function' ? callback : null;
        this._options = callback && typeof callback == 'object' ? callback : {};
        this._styleState = {};
        this._featureStyles = {};
        this._iconScale = 1;
        this._styleProxy = null;
        this._instance = null;
        this._setUpperZoomByBoundary = false;
        this._upperZoomByBoundaryOptions = null;
        this._xhr = null;
        this._isLoaded = this._geojson != null;
        this._callbackCalled = false;
        ns.initClusterDefaults(this);
        ns.attachItemBasics(this);
    }

    dgGeoJson.prototype._notifyLoaded = function () {
        if (this._callbackCalled === true) return this;
        this._callbackCalled = true;
        if (typeof this._callback == 'function') this._callback.call(this, this);
        return this;
    };

    dgGeoJson.prototype._load = function (success, failure) {
        var self = this;
        if (this._geojson != null) {
            this._isLoaded = true;
            if (typeof success == 'function') success(this);
            return null;
        }
        var parsed = normalizeInput(this._url);
        if (parsed != null) {
            this._geojson = parsed;
            this._isLoaded = true;
            if (typeof success == 'function') success(this);
            return null;
        }
        if (typeof this._url != 'string' || this._url == '') {
            this._geojson = emptyFeatureCollection();
            this._isLoaded = true;
            if (typeof success == 'function') success(this);
            return null;
        }
        this._xhr = loadText(this._url, function (text) {
            var loaded = normalizeInput(text);
            if (loaded == null) {
                if (typeof failure == 'function') failure(new Error('GeoJSON parse failed'), self._xhr);
                return;
            }
            self._url = text;
            self._geojson = loaded;
            self._isLoaded = true;
            if (typeof success == 'function') success(self);
        }, failure);
        return this._xhr;
    };

    dgGeoJson.prototype.setData = function (data) {
        this._url = data;
        this._geojson = normalizeInput(data);
        this._isLoaded = this._geojson != null;
        this._callbackCalled = false;
        if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
            this._easymap._updateItemData(this);
        }
        return this;
    };

    dgGeoJson.prototype.getData = function () {
        return this._geojson || this._url;
    };

    dgGeoJson.prototype.toGeoJSON = function () {
        if (this._geojson != null) return this._geojson;
        var parsed = normalizeInput(this._url);
        if (parsed != null) {
            this._geojson = parsed;
            this._isLoaded = true;
            return this._geojson;
        }
        return emptyFeatureCollection();
    };

    dgGeoJson.prototype.getStyle = function () {
        if (this._styleProxy == null) this._styleProxy = ns.createWktStyleProxy(this);
        return this._styleProxy;
    };

    dgGeoJson.prototype.setOpacity = function (opacity) {
        this._styleState.strokeOpacity = ns.toNumber(opacity, 1);
        this._styleState.fillOpacity = ns.toNumber(opacity, 1);
        this._styleState.pointOpacity = ns.toNumber(opacity, 1);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.setStrokeColor = function (color) {
        var parsed = ns.parseColor(color, color);
        this._styleState.strokeColor = parsed.color;
        if (parsed.opacity != null) this._styleState.strokeOpacity = parsed.opacity;
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.setFillColor = function (color) {
        var parsed = ns.parseColor(color, color);
        this._styleState.fillColor = parsed.color;
        if (parsed.opacity != null) this._styleState.fillOpacity = parsed.opacity;
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.setStrokeWidth = function (width) {
        this._styleState.strokeWidth = ns.toNumber(width, 1);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.enableDashed = function (lineDash) {
        return this.setLineDash(lineDash);
    };

    dgGeoJson.prototype.setLineDash = function (lineDash) {
        if (!Array.isArray(lineDash)) return this;
        this._styleState.lineDash = lineDash.slice();
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.setLineCap = function (lineCap) {
        if (['round', 'square', 'butt'].indexOf(lineCap) == -1) return this;
        this._styleState.lineCap = lineCap;
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.setIcon = function (dataIndex, options) {
        if (typeof options != 'object' || options == null) return this;
        var style = this._featureStyles[dataIndex] || {};
        if (options.pic != null) style.pic = options.pic;
        if (options.scale != null) style.scale = ns.toNumber(options.scale, 1);
        if (options.rotate != null) style.rotate = ns.toNumber(options.rotate, 0);
        if (options.rotation != null) style.rotate = ns.toNumber(options.rotation, 0);
        if (options.postion != null) style.anchor = options.postion;
        if (options.position != null) style.anchor = options.position;
        if (options.anchor != null) style.anchor = options.anchor;
        this._featureStyles[dataIndex] = style;
        if (options['auto-refresh'] !== false) {
            ns.refreshItemData(this);
            ns.refreshItemStyle(this);
        }
        return this;
    };

    dgGeoJson.prototype.setIconScale = function (value) {
        this._iconScale = ns.toNumber(value, this._iconScale);
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.getIconScale = function () {
        return this._iconScale;
    };

    dgGeoJson.prototype.refresh = function () {
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGeoJson.prototype.setCluster = function (value) {
        return ns.setItemCluster(this, value);
    };

    dgGeoJson.prototype.getCluster = function () {
        return ns.getItemCluster(this);
    };

    dgGeoJson.prototype.setClusterDistance = function (value) {
        return ns.setItemClusterDistance(this, value);
    };

    dgGeoJson.prototype.getClusterDistance = function () {
        return ns.getItemClusterDistance(this);
    };

    dgGeoJson.prototype.setMinClusterSize = function (value) {
        return ns.setItemMinClusterSize(this, value);
    };

    dgGeoJson.prototype.getMinClusterSize = function () {
        return ns.getItemMinClusterSize(this);
    };

    dgGeoJson.prototype.setClusterClickZoomToBBOX = function (value) {
        return ns.setItemClusterClickZoomToBBOX(this, value);
    };

    dgGeoJson.prototype.getClusterClickZoomToBBOX = function () {
        return ns.getItemClusterClickZoomToBBOX(this);
    };

    dgGeoJson.prototype.setUpperZoomByBoundary = function (value, options) {
        this._setUpperZoomByBoundary = value !== false;
        this._upperZoomByBoundaryOptions = options || null;
        if (this._setUpperZoomByBoundary === true && this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgGeoJson.prototype.setExtrusion = function (value) {
        return ns.setItemExtrusion(this, value);
    };

    dgGeoJson.prototype.setExtrusionHeight = function (value) {
        return ns.setItemExtrusionHeight(this, value);
    };

    dgGeoJson.prototype.setExtrusionBase = function (value) {
        return ns.setItemExtrusionBase(this, value);
    };

    dgGeoJson.prototype.setExtrusionColor = function (value) {
        return ns.setItemExtrusionColor(this, value);
    };

    dgGeoJson.prototype.setExtrusionOpacity = function (value) {
        return ns.setItemExtrusionOpacity(this, value);
    };

    window.dgGeoJson = dgGeoJson;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgGeoJson');
})(window);
