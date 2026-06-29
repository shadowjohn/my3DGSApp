(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};
    ns.nextId = ns.nextId || 1;

    ns.makeId = function (prefix) {
        var id = prefix + '-' + ns.nextId;
        ns.nextId++;
        return id;
    };

    ns.toNumber = function (value, fallback) {
        var num = parseFloat(value);
        return isNaN(num) ? fallback : num;
    };

    ns.attachItemBasics = function (item) {
        item._id = item._id || ns.makeId(item._type || 'dgitem');
        item._easymap = null;
        item._visible = true;
        item._featureClick = null;
        item._zIndex = item._zIndex || 0;
        item.onclick = null;
        item.onFeatureSelect = null;
        item.setVisible = function (visible) {
            this._visible = visible !== false;
            if (this._easymap != null && typeof this._easymap._setItemVisible == 'function') {
                this._easymap._setItemVisible(this, this._visible);
            }
            return this;
        };
        item.getVisible = function () {
            return this._visible !== false;
        };
        item.show = function () {
            return this.setVisible(true);
        };
        item.hide = function () {
            return this.setVisible(false);
        };
        item.setFeatureClick = function (callback) {
            this._featureClick = callback;
            return this;
        };
        item.remove = function () {
            if (this._easymap != null && typeof this._easymap.removeItem == 'function') {
                this._easymap.removeItem(this);
            }
            return this;
        };
        item.getZIndex = function () {
            return this._zIndex || 0;
        };
        item.setZIndex = function (zIndex) {
            this._zIndex = parseInt(zIndex, 10);
            if (isNaN(this._zIndex)) this._zIndex = 0;
            if (this._easymap != null && typeof this._easymap.setItemZIndex == 'function') {
                this._easymap.setItemZIndex(this, this._zIndex);
            }
            return this;
        };
        return item;
    };

    ns.initClusterDefaults = function (item) {
        item._isCluster = item._isCluster === true;
        item._clusterDistance = Array.isArray(item._clusterDistance) ? item._clusterDistance : [40, 20];
        item._minClusterSize = parseInt(item._minClusterSize, 10);
        if (isNaN(item._minClusterSize) || item._minClusterSize < 2) item._minClusterSize = 2;
        item._clusterMaxZoom = parseInt(item._clusterMaxZoom, 10);
        if (isNaN(item._clusterMaxZoom) || item._clusterMaxZoom < 0) item._clusterMaxZoom = 17;
        item._isClusterClickZoomToBBOX = item._isClusterClickZoomToBBOX !== false;
        return item;
    };

    ns.refreshItemLayers = function (item) {
        if (item != null && item._easymap != null && typeof item._easymap._reloadItem == 'function') {
            item._easymap._reloadItem(item);
        }
    };

    ns.setItemCluster = function (item, value) {
        if (typeof value != 'boolean') {
            console.log('只接受 true or false ，如: setCluster(true); ');
            return item;
        }
        item._isCluster = value;
        ns.refreshItemLayers(item);
        return item;
    };

    ns.getItemCluster = function (item) {
        return item._isCluster === true;
    };

    ns.setItemClusterDistance = function (item, value) {
        if (!Array.isArray(value)) {
            console.log('設定群聚間距，如 item.setClusterDistance([40, 20]);');
            return item;
        }
        item._clusterDistance = [
            Math.max(1, parseInt(value[0], 10) || 40),
            Math.max(0, parseInt(value[1], 10) || 0)
        ];
        ns.refreshItemLayers(item);
        return item;
    };

    ns.getItemClusterDistance = function (item) {
        return Array.isArray(item._clusterDistance) ? item._clusterDistance.slice() : [40, 20];
    };

    ns.setItemMinClusterSize = function (item, value) {
        var size = parseInt(value, 10);
        item._minClusterSize = isNaN(size) || size < 2 ? 2 : size;
        ns.refreshItemLayers(item);
        return item;
    };

    ns.getItemMinClusterSize = function (item) {
        var size = parseInt(item._minClusterSize, 10);
        return isNaN(size) || size < 2 ? 2 : size;
    };

    ns.setItemClusterClickZoomToBBOX = function (item, value) {
        if (typeof value != 'boolean') {
            console.log('只接受 true or false ，如: setClusterClickZoomToBBOX(true); ');
            return item;
        }
        item._isClusterClickZoomToBBOX = value;
        return item;
    };

    ns.getItemClusterClickZoomToBBOX = function (item) {
        return item._isClusterClickZoomToBBOX !== false;
    };

    ns.setItemExtrusion = function (item, value) {
        item._styleState = item._styleState || {};
        if (typeof value == 'boolean') {
            item._styleState.extrusionEnabled = value;
        }
        else if (value != null && typeof value == 'object') {
            if (value.enabled != null) item._styleState.extrusionEnabled = value.enabled !== false;
            if (value.height != null) item._styleState.extrusionHeight = ns.toNumber(value.height, 60);
            if (value.base != null) item._styleState.extrusionBase = ns.toNumber(value.base, 0);
            if (value.opacity != null) item._styleState.extrusionOpacity = ns.toNumber(value.opacity, 0.58);
            if (value.color != null) item._styleState.extrusionColor = value.color;
        }
        else {
            item._styleState.extrusionEnabled = true;
        }
        if (ns.refreshItemStyle != null) ns.refreshItemStyle(item);
        return item;
    };

    ns.setItemExtrusionHeight = function (item, value) {
        item._styleState = item._styleState || {};
        item._styleState.extrusionHeight = ns.toNumber(value, 60);
        if (item._styleState.extrusionEnabled == null) item._styleState.extrusionEnabled = true;
        if (ns.refreshItemStyle != null) ns.refreshItemStyle(item);
        return item;
    };

    ns.setItemExtrusionBase = function (item, value) {
        item._styleState = item._styleState || {};
        item._styleState.extrusionBase = ns.toNumber(value, 0);
        if (item._styleState.extrusionEnabled == null) item._styleState.extrusionEnabled = true;
        if (ns.refreshItemStyle != null) ns.refreshItemStyle(item);
        return item;
    };

    ns.setItemExtrusionColor = function (item, value) {
        item._styleState = item._styleState || {};
        item._styleState.extrusionColor = value;
        if (item._styleState.extrusionEnabled == null) item._styleState.extrusionEnabled = true;
        if (ns.refreshItemStyle != null) ns.refreshItemStyle(item);
        return item;
    };

    ns.setItemExtrusionOpacity = function (item, value) {
        item._styleState = item._styleState || {};
        item._styleState.extrusionOpacity = ns.toNumber(value, 0.58);
        if (item._styleState.extrusionEnabled == null) item._styleState.extrusionEnabled = true;
        if (ns.refreshItemStyle != null) ns.refreshItemStyle(item);
        return item;
    };

    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('core/utils');
})(window);
