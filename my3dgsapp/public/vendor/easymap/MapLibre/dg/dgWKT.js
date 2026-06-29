(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};
    var EARTH_RADIUS = 6378137;

    function emptyFeatureCollection() {
        return { type: 'FeatureCollection', features: [] };
    }

    function getSourceGeoJson(item) {
        var record = item != null ? item._instance : null;
        var map = item != null && item._easymap != null ? item._easymap._map : null;
        if (record == null || map == null || typeof map.getSource != 'function') return null;
        var sourceIds = [];
        if (record.sourceId != null) sourceIds.push(record.sourceId);
        if (record.clusterSourceId != null) sourceIds.push(record.clusterSourceId);
        var features = [];
        for (var i = 0; i < sourceIds.length; i++) {
            var source = map.getSource(sourceIds[i]);
            var data = source != null ? source.data : null;
            if (data != null && Array.isArray(data.features)) {
                features = features.concat(data.features);
            }
        }
        return features.length > 0 ? { type: 'FeatureCollection', features: features } : null;
    }

    function getItemGeoJson(item) {
        var sourceGeoJson = getSourceGeoJson(item);
        if (sourceGeoJson != null) return sourceGeoJson;
        if (ns.parseWktToGeoJSON != null) return ns.parseWktToGeoJSON(item.getData ? item.getData() : item._url);
        if (window.EASYMAP_MAPLIBRE_PARSE_WKT != null) return window.EASYMAP_MAPLIBRE_PARSE_WKT(item.getData ? item.getData() : item._url);
        return emptyFeatureCollection();
    }

    function collectCoordinates(value, output) {
        if (!Array.isArray(value)) return;
        if (typeof value[0] == 'number' && typeof value[1] == 'number') {
            output.push([value[0], value[1]]);
            return;
        }
        for (var i = 0; i < value.length; i++) collectCoordinates(value[i], output);
    }

    function getGeoJsonCoordinates(geojson) {
        var output = [];
        var features = geojson != null && Array.isArray(geojson.features) ? geojson.features : [];
        for (var i = 0; i < features.length; i++) {
            if (features[i] != null && features[i].geometry != null) {
                collectCoordinates(features[i].geometry.coordinates, output);
            }
        }
        return output;
    }

    function getGeoJsonExtent(geojson) {
        var coordinates = getGeoJsonCoordinates(geojson);
        if (coordinates.length == 0) return null;
        var minX = Infinity;
        var minY = Infinity;
        var maxX = -Infinity;
        var maxY = -Infinity;
        for (var i = 0; i < coordinates.length; i++) {
            var x = parseFloat(coordinates[i][0]);
            var y = parseFloat(coordinates[i][1]);
            if (isNaN(x) || isNaN(y)) continue;
            if (x < minX) minX = x;
            if (y < minY) minY = y;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
        }
        if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) return null;
        return [minX, minY, maxX, maxY];
    }

    function projectMeters(coordinate, refLat) {
        var lon = parseFloat(coordinate[0]);
        var lat = parseFloat(coordinate[1]);
        return {
            x: EARTH_RADIUS * lon * Math.PI / 180 * Math.cos(refLat * Math.PI / 180),
            y: EARTH_RADIUS * lat * Math.PI / 180
        };
    }

    function distanceMeters(a, b) {
        var refLat = (parseFloat(a[1]) + parseFloat(b[1])) / 2;
        var pa = projectMeters(a, refLat);
        var pb = projectMeters(b, refLat);
        var dx = pa.x - pb.x;
        var dy = pa.y - pb.y;
        return Math.sqrt(dx * dx + dy * dy);
    }

    function ringAreaMeters(ring) {
        if (!Array.isArray(ring) || ring.length < 3) return 0;
        var refLat = 0;
        for (var i = 0; i < ring.length; i++) refLat += parseFloat(ring[i][1]) || 0;
        refLat = refLat / ring.length;
        var area = 0;
        for (var j = 0; j < ring.length; j++) {
            var p1 = projectMeters(ring[j], refLat);
            var p2 = projectMeters(ring[(j + 1) % ring.length], refLat);
            area += p1.x * p2.y - p2.x * p1.y;
        }
        return Math.abs(area) / 2;
    }

    function polygonAreaMeters(polygonCoordinates) {
        if (!Array.isArray(polygonCoordinates) || polygonCoordinates.length == 0) return 0;
        var area = ringAreaMeters(polygonCoordinates[0]);
        for (var i = 1; i < polygonCoordinates.length; i++) {
            area -= ringAreaMeters(polygonCoordinates[i]);
        }
        return Math.max(0, area);
    }

    function geometryAreaMeters(geometry) {
        if (geometry == null) return 0;
        if (geometry.type == 'Polygon') return polygonAreaMeters(geometry.coordinates);
        if (geometry.type == 'MultiPolygon' && Array.isArray(geometry.coordinates)) {
            var total = 0;
            for (var i = 0; i < geometry.coordinates.length; i++) total += polygonAreaMeters(geometry.coordinates[i]);
            return total;
        }
        return 0;
    }

    function getGeoJsonArea(geojson) {
        var features = geojson != null && Array.isArray(geojson.features) ? geojson.features : [];
        var total = 0;
        for (var i = 0; i < features.length; i++) total += geometryAreaMeters(features[i].geometry);
        return total;
    }

    function collectGeometryParts(geometry, parts) {
        if (geometry == null) return parts;
        parts = parts || { points: [], segments: [] };
        function addPoint(coordinate) {
            if (Array.isArray(coordinate) && typeof coordinate[0] == 'number' && typeof coordinate[1] == 'number') {
                parts.points.push([coordinate[0], coordinate[1]]);
            }
        }
        function addLine(coordinates, close) {
            if (!Array.isArray(coordinates)) return;
            for (var i = 0; i < coordinates.length; i++) addPoint(coordinates[i]);
            for (var j = 1; j < coordinates.length; j++) parts.segments.push([coordinates[j - 1], coordinates[j]]);
            if (close === true && coordinates.length > 2) parts.segments.push([coordinates[coordinates.length - 1], coordinates[0]]);
        }
        if (geometry.type == 'Point') addPoint(geometry.coordinates);
        else if (geometry.type == 'MultiPoint') {
            for (var p = 0; p < geometry.coordinates.length; p++) addPoint(geometry.coordinates[p]);
        }
        else if (geometry.type == 'LineString') addLine(geometry.coordinates, false);
        else if (geometry.type == 'MultiLineString') {
            for (var l = 0; l < geometry.coordinates.length; l++) addLine(geometry.coordinates[l], false);
        }
        else if (geometry.type == 'Polygon') {
            for (var r = 0; r < geometry.coordinates.length; r++) addLine(geometry.coordinates[r], true);
        }
        else if (geometry.type == 'MultiPolygon') {
            for (var m = 0; m < geometry.coordinates.length; m++) {
                for (var mr = 0; mr < geometry.coordinates[m].length; mr++) addLine(geometry.coordinates[m][mr], true);
            }
        }
        return parts;
    }

    function pointSegmentDistanceMeters(point, segment) {
        var refLat = (parseFloat(point[1]) + parseFloat(segment[0][1]) + parseFloat(segment[1][1])) / 3;
        var p = projectMeters(point, refLat);
        var a = projectMeters(segment[0], refLat);
        var b = projectMeters(segment[1], refLat);
        var dx = b.x - a.x;
        var dy = b.y - a.y;
        if (dx == 0 && dy == 0) return distanceMeters(point, segment[0]);
        var t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy);
        t = Math.max(0, Math.min(1, t));
        var x = a.x + t * dx;
        var y = a.y + t * dy;
        var px = p.x - x;
        var py = p.y - y;
        return Math.sqrt(px * px + py * py);
    }

    function geometryDistanceMeters(a, b) {
        var partsA = collectGeometryParts(a);
        var partsB = collectGeometryParts(b);
        var min = Infinity;
        for (var i = 0; i < partsA.points.length; i++) {
            for (var j = 0; j < partsB.points.length; j++) min = Math.min(min, distanceMeters(partsA.points[i], partsB.points[j]));
            for (var s = 0; s < partsB.segments.length; s++) min = Math.min(min, pointSegmentDistanceMeters(partsA.points[i], partsB.segments[s]));
        }
        for (var k = 0; k < partsB.points.length; k++) {
            for (var as = 0; as < partsA.segments.length; as++) min = Math.min(min, pointSegmentDistanceMeters(partsB.points[k], partsA.segments[as]));
        }
        return isFinite(min) ? min : Infinity;
    }

    function getRowWkt(row) {
        if (typeof row == 'string') return row;
        if (row != null && typeof row == 'object') return row.WKT || row.wkt || row.geom || row.geometry_wkt || row.GEOM || '';
        return '';
    }

    function extendObject(target, source) {
        target = target || {};
        source = source || {};
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key)) target[key] = source[key];
        }
        return target;
    }

    function dgWKT(data, srs, callback, options) {
        this._type = 'dgwkt';
        this._easymapClass = 'dgwkt';
        this._url = data;
        this._wkt = Array.isArray(data) ? data : null;
        this._dataSRS = srs || 'EPSG:4326';
        this._callback = typeof callback == 'function' ? callback : null;
        this._options = options || (callback && typeof callback == 'object' ? callback : {});
        this._styleState = {};
        this._featureStyles = {};
        this._iconScale = 0.35;
        this._styleProxy = null;
        this._instance = null;
        this._renderMode = 'vector';
        this._renderModeOptions = {};
        this._styleSetting = null;
        this._imageRows = [];
        this._imageCanvas = null;
        this._imageOverlay = null;
        this._imageEvents = [];
        this._imageRedrawTimer = null;
        this._imageHoverRow = null;
        this._imageBounds = null;
        this._imagePendingRemovals = [];
        this._imageRetireDelay = 180;
        this._activeRenderMode = null;
        this._onFeatureHover = null;
        this._onFeatureMouseOut = null;
        this._setUpperZoomByBoundary = false;
        this._upperZoomByBoundaryOptions = null;
        this._spiderDisplayMapEvent = null;
        this._spiderDisplayWKTOBJ = null;
        this._isSpiderDisplay = false;
        this._spiderDisplayZoomLevel = 15;
        this._point_positionY = 20;
        this._linestring_positionY = 0;
        this._polygon_positionY = 0;
        this.opacity = 1;
        ns.initClusterDefaults(this);
        ns.attachItemBasics(this);
    }

    dgWKT.prototype.setData = function (data) {
        this._url = data;
        this._wkt = Array.isArray(data) ? data : null;
        if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
            this._easymap._updateItemData(this);
        }
        return this;
    };

    dgWKT.prototype.getData = function () {
        return this._url;
    };

    dgWKT.prototype.toGeoJSON = function () {
        return getItemGeoJson(this);
    };

    dgWKT.prototype.getExtent = function () {
        return getGeoJsonExtent(getItemGeoJson(this));
    };

    dgWKT.prototype.getCenter = function () {
        var extent = this.getExtent();
        if (extent == null) return null;
        return new window.dgXY((extent[0] + extent[2]) / 2, (extent[1] + extent[3]) / 2);
    };

    dgWKT.prototype.getExtentArea = function () {
        var extent = this.getExtent();
        if (extent == null) return 0;
        var midX = (extent[0] + extent[2]) / 2;
        var midY = (extent[1] + extent[3]) / 2;
        return distanceMeters([extent[0], midY], [extent[2], midY]) * distanceMeters([midX, extent[1]], [midX, extent[3]]);
    };

    dgWKT.prototype.getArea = function () {
        return getGeoJsonArea(getItemGeoJson(this));
    };

    dgWKT.prototype.getType = function () {
        if (this._activeRenderMode == 'image') return 'image';
        return this._instance == null ? null : 'vector';
    };

    dgWKT.prototype.getStyle = function () {
        if (this._styleProxy == null) this._styleProxy = ns.createWktStyleProxy(this);
        return this._styleProxy;
    };

    dgWKT.prototype.setOpacity = function (opacity) {
        this.opacity = ns.toNumber(opacity, 1);
        this._styleState.strokeOpacity = this.opacity;
        this._styleState.fillOpacity = this.opacity;
        this._styleState.pointOpacity = this.opacity;
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.getOpacity = function () {
        return this.opacity == null ? 1 : this.opacity;
    };

    dgWKT.prototype.setFeatureHover = function (handler) {
        this._onFeatureHover = handler;
        return this;
    };

    dgWKT.prototype.setFeatureMouseOut = function (handler) {
        this._onFeatureMouseOut = handler;
        return this;
    };

    dgWKT.prototype.onmouseout = function (handler) {
        return this.setFeatureMouseOut(handler);
    };

    dgWKT.prototype.renderMode = function (mode, options) {
        if (mode == null) return this;
        mode = String(mode).toLowerCase();
        if (['vector', 'image', 'auto'].indexOf(mode) < 0) {
            console.log('dgWKT.renderMode 只支援 vector、image、auto');
            mode = 'vector';
        }
        this._renderMode = mode;
        this._renderModeOptions = extendObject(this._renderModeOptions || {}, options || {});

        if (this._easymap != null && this._instance != null) {
            if (this._resolveRenderMode(this._getImageSourceRows()) == 'image') {
                if (this._activeRenderMode == 'image') this._renderImageMode();
                else ns.refreshItemLayers(this);
            }
            else if (this._activeRenderMode == 'image') {
                ns.refreshItemLayers(this);
            }
        }
        return this;
    };

    dgWKT.prototype.getRenderMode = function () {
        return this._renderMode || 'vector';
    };

    dgWKT.prototype.styleSetting = function (styleSetting) {
        this._styleSetting = styleSetting || null;
        if (this._activeRenderMode == 'image') {
            this._redrawImageMode();
        }
        return this;
    };

    dgWKT.prototype._getImageSourceRows = function () {
        var data = Array.isArray(this._wkt) ? this._wkt : (Array.isArray(this._url) ? this._url : null);
        if (data != null) return data;
        if (typeof this._url == 'string') return [this._url];
        return [];
    };

    dgWKT.prototype._resolveRenderMode = function (rows) {
        var mode = this.getRenderMode();
        if (mode != 'auto') return mode;
        var options = this._renderModeOptions || {};
        var threshold = parseInt(options.threshold == null ? 800 : options.threshold, 10);
        var imageGeometryTypes = options.imageGeometryTypes || ['Polygon', 'MultiPolygon'];
        var fallback = options.fallback || 'vector';
        rows = Array.isArray(rows) ? rows : this._getImageSourceRows();
        if (!Array.isArray(rows) || rows.length < threshold) return fallback;
        for (var i = 0; i < rows.length; i++) {
            var geometryType = this._getWktGeometryType(getRowWkt(rows[i]));
            if (imageGeometryTypes.indexOf(geometryType) < 0) return fallback;
        }
        return 'image';
    };

    dgWKT.prototype._getWktGeometryType = function (wkt) {
        if (typeof wkt != 'string') return null;
        var match = wkt.replace(/^\s+|\s+$/g, '').match(/^([a-zA-Z]+)\s*/);
        if (match == null) return null;
        var type = match[1].toLowerCase();
        if (type == 'polygon') return 'Polygon';
        if (type == 'multipolygon') return 'MultiPolygon';
        if (type == 'point') return 'Point';
        if (type == 'multipoint') return 'MultiPoint';
        if (type == 'linestring') return 'LineString';
        if (type == 'multilinestring') return 'MultiLineString';
        return match[1];
    };

    dgWKT.prototype._renderImageMode = function () {
        this._destroyImageRenderer();
        return this._drawImageOverlay(true);
    };

    dgWKT.prototype._redrawImageMode = function () {
        if (this.getRenderMode() == 'vector') return false;
        var oldOverlay = this._imageOverlay;
        return this._drawImageOverlay(false, oldOverlay);
    };

    dgWKT.prototype._drawImageOverlay = function (attachEvents, retireOverlay) {
        var doc = window.document;
        if (this._easymap == null) return false;
        if (doc == null || typeof doc.createElement != 'function') {
            console.log('dgWKT image mode 需要 browser canvas');
            return false;
        }
        var rows = this._prepareImageRows(this._getImageSourceRows());
        var bounds = this._getImageRowsBounds(rows);
        if (rows.length <= 0 || bounds == null) return false;

        var size = this._getImageCanvasSize(bounds);
        var canvas = doc.createElement('canvas');
        canvas.width = size.width;
        canvas.height = size.height;
        this._drawImageRowsToCanvas(canvas, rows, bounds);

        var imgUrl = canvas.toDataURL('image/png');
        var quadWkt = this._boundsToQuadWkt(bounds);
        var overlay = null;
        if (typeof this._easymap._addDgWktImage == 'function') {
            overlay = this._easymap._addDgWktImage(this, imgUrl, quadWkt, bounds);
        }
        else if (typeof this._easymap.addGroundOverlayQuad == 'function') {
            overlay = this._easymap.addGroundOverlayQuad(imgUrl, quadWkt);
        }
        if (overlay == null || overlay.status == 'invalid') return false;

        this._imageRows = rows;
        this._imageCanvas = canvas;
        this._imageOverlay = overlay;
        this._imageBounds = bounds;
        this._instance = overlay;
        this._activeRenderMode = 'image';
        overlay._dgwkt = this;
        if (retireOverlay != null && retireOverlay !== overlay) {
            this._queueImageOverlayRemoval(retireOverlay);
        }
        if (attachEvents) this._attachImageEvents();
        return overlay;
    };

    dgWKT.prototype._destroyImageRenderer = function () {
        if (this._imageRedrawTimer != null) {
            clearTimeout(this._imageRedrawTimer);
            this._imageRedrawTimer = null;
        }
        if (this._easymap != null && typeof this._easymap.detachEvent == 'function') {
            for (var i = 0; i < this._imageEvents.length; i++) {
                this._easymap.detachEvent(this._imageEvents[i].type, this._imageEvents[i].handler);
            }
        }
        this._imageEvents = [];
        this._imageHoverRow = null;
        this._clearPendingImageRemovals(true);
        this._removeImageOverlay();
    };

    dgWKT.prototype._removeImageOverlay = function () {
        this._removeImageOverlayNow(this._imageOverlay);
        this._imageOverlay = null;
        this._imageCanvas = null;
        this._imageBounds = null;
        this._instance = null;
        this._activeRenderMode = null;
    };

    dgWKT.prototype._removeImageOverlayNow = function (overlay) {
        if (overlay == null) return;
        if (overlay._dgwktImageRemoved === true) return;
        overlay._dgwktImageRemoved = true;
        if (this._easymap != null) {
            if (typeof this._easymap._removeDgWktImage == 'function') {
                this._easymap._removeDgWktImage(overlay);
            }
            else if (typeof this._easymap.removeGroundOverlayQuad == 'function') {
                this._easymap.removeGroundOverlayQuad(overlay);
            }
        }
    };

    dgWKT.prototype._queueImageOverlayRemoval = function (overlay) {
        if (overlay == null) return;
        var options = this._renderModeOptions || {};
        var delay = parseInt(options.retireDelay == null ? this._imageRetireDelay : options.retireDelay, 10);
        if (isNaN(delay) || delay < 0) delay = this._imageRetireDelay;
        var removal = {
            overlay: overlay,
            timer: null
        };
        var retire = function () {
            var index = this._imagePendingRemovals.indexOf(removal);
            if (index >= 0) this._imagePendingRemovals.splice(index, 1);
            this._removeImageOverlayNow(overlay);
        }.bind(this);

        this._imagePendingRemovals.push(removal);
        if (delay <= 0) {
            retire();
        }
        else {
            removal.timer = setTimeout(retire, delay);
        }
    };

    dgWKT.prototype._clearPendingImageRemovals = function (removeNow) {
        var pending = this._imagePendingRemovals || [];
        this._imagePendingRemovals = [];
        for (var i = 0; i < pending.length; i++) {
            if (pending[i].timer != null) {
                clearTimeout(pending[i].timer);
                pending[i].timer = null;
            }
            if (removeNow !== false) this._removeImageOverlayNow(pending[i].overlay);
        }
    };

    dgWKT.prototype._attachImageEvents = function () {
        var options = this._renderModeOptions || {};
        if (this._easymap == null || typeof this._easymap.attachEvent != 'function') return;
        if (options.hitTest !== false) {
            var clickHandler = function (evt, dgxy) {
                this._handleImageMapClick(evt, dgxy);
            }.bind(this);
            var moveHandler = function (evt, dgxy) {
                this._handleImageMapMove(evt, dgxy);
            }.bind(this);
            this._easymap.attachEvent('click', clickHandler);
            this._easymap.attachEvent('mousemove', moveHandler);
            this._imageEvents.push({ type: 'click', handler: clickHandler });
            this._imageEvents.push({ type: 'mousemove', handler: moveHandler });
        }
        if (options.redrawOnMoveEnd || options.redrawOnZoomEnd) {
            var redrawHandler = function () {
                this._debounceImageRedraw();
            }.bind(this);
            this._easymap.attachEvent('moveend', redrawHandler);
            this._imageEvents.push({ type: 'moveend', handler: redrawHandler });
        }
    };

    dgWKT.prototype._debounceImageRedraw = function () {
        var options = this._renderModeOptions || {};
        var delay = parseInt(options.redrawDelay == null ? 250 : options.redrawDelay, 10);
        if (this._imageRedrawTimer != null) clearTimeout(this._imageRedrawTimer);
        this._imageRedrawTimer = setTimeout(function () {
            this._imageRedrawTimer = null;
            this._redrawImageMode();
        }.bind(this), delay);
    };

    dgWKT.prototype._prepareImageRows = function (rows) {
        var output = [];
        if (!Array.isArray(rows)) return output;
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            var parsed = this._parseImageWKT(getRowWkt(row));
            if (parsed == null) continue;
            var properties = {};
            if (row != null && typeof row == 'object' && !Array.isArray(row)) {
                for (var key in row) {
                    if (Object.prototype.hasOwnProperty.call(row, key)) properties[key] = row[key];
                }
            }
            properties.data_index = i;
            output.push({
                dataIndex: i,
                geometryType: parsed.geometryType,
                coordinates: parsed.coordinates,
                bounds: this._getImageGeometryBounds(parsed.coordinates),
                properties: properties,
                row: row,
                style: this._getImageRowStyle(row, parsed.geometryType)
            });
        }
        return output;
    };

    dgWKT.prototype._parseImageWKT = function (wkt) {
        if (typeof wkt != 'string') return null;
        var geometryType = this._getWktGeometryType(wkt);
        var body = wkt.replace(/^\s+|\s+$/g, '').replace(/^[a-zA-Z]+\s*/i, '').replace(/^\s+|\s+$/g, '');
        body = this._stripOuterParens(body);
        if (geometryType == 'Polygon') {
            return {
                geometryType: geometryType,
                coordinates: [this._splitWktGroups(body).map(function (ringText) {
                    return this._parseImageRing(ringText);
                }.bind(this))]
            };
        }
        if (geometryType == 'MultiPolygon') {
            return {
                geometryType: geometryType,
                coordinates: this._splitWktGroups(body).map(function (polygonText) {
                    return this._splitWktGroups(polygonText).map(function (ringText) {
                        return this._parseImageRing(ringText);
                    }.bind(this));
                }.bind(this))
            };
        }
        return null;
    };

    dgWKT.prototype._stripOuterParens = function (text) {
        text = String(text || '').replace(/^\s+|\s+$/g, '');
        if (text.charAt(0) == '(' && text.charAt(text.length - 1) == ')') {
            return text.substring(1, text.length - 1).replace(/^\s+|\s+$/g, '');
        }
        return text;
    };

    dgWKT.prototype._splitWktGroups = function (text) {
        var groups = [];
        var depth = 0;
        var start = -1;
        text = String(text || '').replace(/^\s+|\s+$/g, '');
        for (var i = 0; i < text.length; i++) {
            var ch = text.charAt(i);
            if (ch == '(') {
                if (depth == 0) start = i + 1;
                depth++;
            }
            else if (ch == ')') {
                depth--;
                if (depth == 0 && start >= 0) {
                    groups.push(text.substring(start, i).replace(/^\s+|\s+$/g, ''));
                    start = -1;
                }
            }
        }
        if (groups.length <= 0 && text.length > 0) groups.push(text);
        return groups;
    };

    dgWKT.prototype._parseImageRing = function (text) {
        var points = [];
        var coords = String(text || '').split(',');
        for (var i = 0; i < coords.length; i++) {
            var parts = coords[i].replace(/^\s+|\s+$/g, '').split(/\s+/);
            if (parts.length < 2) continue;
            var point = this._normalizeImagePoint([parseFloat(parts[0]), parseFloat(parts[1])]);
            if (!isNaN(point[0]) && !isNaN(point[1])) points.push(point);
        }
        return points;
    };

    dgWKT.prototype._normalizeImagePoint = function (point) {
        var fromSrs = this._dataSRS || 'EPSG:4326';
        if (ns.normalizeSrs != null && ns.normalizeSrs(fromSrs) != 'EPSG:4326' && typeof ns.projCoordinate == 'function') {
            return ns.projCoordinate(point, fromSrs, 'EPSG:4326');
        }
        return point;
    };

    dgWKT.prototype._getImageGeometryBounds = function (polygons) {
        var bounds = null;
        for (var i = 0; i < polygons.length; i++) {
            for (var j = 0; j < polygons[i].length; j++) {
                for (var k = 0; k < polygons[i][j].length; k++) {
                    bounds = this._extendImageBounds(bounds, polygons[i][j][k]);
                }
            }
        }
        return bounds;
    };

    dgWKT.prototype._getImageRowsBounds = function (rows) {
        var bounds = null;
        rows = rows || [];
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].bounds == null) continue;
            bounds = this._extendImageBounds(bounds, [rows[i].bounds[0], rows[i].bounds[1]]);
            bounds = this._extendImageBounds(bounds, [rows[i].bounds[2], rows[i].bounds[3]]);
        }
        return bounds;
    };

    dgWKT.prototype._extendImageBounds = function (bounds, point) {
        if (bounds == null) return [point[0], point[1], point[0], point[1]];
        bounds[0] = Math.min(bounds[0], point[0]);
        bounds[1] = Math.min(bounds[1], point[1]);
        bounds[2] = Math.max(bounds[2], point[0]);
        bounds[3] = Math.max(bounds[3], point[1]);
        return bounds;
    };

    dgWKT.prototype._getImageCanvasSize = function (bounds) {
        var options = this._renderModeOptions || {};
        var maxCanvasSize = parseInt(options.maxCanvasSize == null ? 2048 : options.maxCanvasSize, 10);
        var lonDiff = Math.max(Math.abs(bounds[2] - bounds[0]), 0.000001);
        var latDiff = Math.max(Math.abs(bounds[3] - bounds[1]), 0.000001);
        var width = maxCanvasSize;
        var height = maxCanvasSize;
        if (lonDiff >= latDiff) height = Math.max(1, Math.round(maxCanvasSize * (latDiff / lonDiff)));
        else width = Math.max(1, Math.round(maxCanvasSize * (lonDiff / latDiff)));
        return { width: width, height: height };
    };

    dgWKT.prototype._drawImageRowsToCanvas = function (canvas, rows, bounds) {
        var ctx = canvas.getContext('2d');
        if (ctx == null) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            var style = row.style || this._getImageRowStyle(row.row, row.geometryType);
            for (var p = 0; p < row.coordinates.length; p++) {
                var polygon = row.coordinates[p];
                ctx.beginPath();
                for (var r = 0; r < polygon.length; r++) {
                    var ring = polygon[r];
                    for (var j = 0; j < ring.length; j++) {
                        var xy = this._imageLonLatToPixel(ring[j][0], ring[j][1], bounds, canvas.width, canvas.height);
                        if (j == 0) ctx.moveTo(xy.x, xy.y);
                        else ctx.lineTo(xy.x, xy.y);
                    }
                    ctx.closePath();
                }
                ctx.fillStyle = style.fillColor;
                ctx.strokeStyle = style.strokeColor;
                ctx.lineWidth = style.strokeWidth;
                ctx.fill();
                if (style.strokeWidth > 0) ctx.stroke();
            }
        }
    };

    dgWKT.prototype._imageLonLatToPixel = function (lon, lat, bounds, width, height) {
        var lonDiff = Math.max(bounds[2] - bounds[0], 0.000001);
        var latDiff = Math.max(bounds[3] - bounds[1], 0.000001);
        return {
            x: ((lon - bounds[0]) / lonDiff) * width,
            y: ((bounds[3] - lat) / latDiff) * height
        };
    };

    dgWKT.prototype._boundsToQuadWkt = function (bounds) {
        // MapLibre image source 需要左上、右上、右下、左下四點。
        return 'POLYGON((' +
            bounds[0] + ' ' + bounds[3] + ',' +
            bounds[2] + ' ' + bounds[3] + ',' +
            bounds[2] + ' ' + bounds[1] + ',' +
            bounds[0] + ' ' + bounds[1] + ',' +
            bounds[0] + ' ' + bounds[3] +
            '))';
    };

    dgWKT.prototype._getImageRowStyle = function (row, geometryType) {
        var options = this._renderModeOptions || {};
        var style = {
            fillColor: 'rgba(0,0,255,0.1)',
            strokeColor: 'rgba(0,0,255,0.8)',
            strokeWidth: 1
        };
        if (typeof options.styleFunction == 'function') {
            style = extendObject(style, options.styleFunction(row, geometryType, this) || {});
        }
        var setting = this._getImageStyleSetting(row, geometryType);
        if (setting != null) {
            style.fillColor = setting['fill-color'] || setting.fillColor || setting.color || style.fillColor;
            style.strokeColor = setting['stroke-color'] || setting.strokeColor || setting.color || style.strokeColor;
            style.strokeWidth = parseFloat(setting.width || setting.strokeWidth || style.strokeWidth);
            if (setting.opacity != null) style.fillColor = this._applyImageOpacity(style.fillColor, setting.opacity);
            if (setting.fillOpacity != null) style.fillColor = this._applyImageOpacity(style.fillColor, setting.fillOpacity);
            if (setting.strokeOpacity != null) style.strokeColor = this._applyImageOpacity(style.strokeColor, setting.strokeOpacity);
        }
        if (isNaN(style.strokeWidth)) style.strokeWidth = 1;
        return style;
    };

    dgWKT.prototype._getImageStyleSetting = function (row, geometryType) {
        var options = this._renderModeOptions || {};
        var styleSetting = null;
        if (row != null && typeof row == 'object' && row.style_setting != null) styleSetting = row.style_setting;
        else if (row != null && typeof row == 'object' && row.styleSetting != null) styleSetting = row.styleSetting;
        else if (this._styleSetting != null) styleSetting = this._styleSetting;
        else if (options.styleSetting != null) styleSetting = options.styleSetting;
        if (styleSetting == null) return null;
        var kind = String(geometryType || '').toLowerCase();
        return styleSetting[kind] || styleSetting[geometryType] || styleSetting.Polygon || styleSetting.polygon || null;
    };

    dgWKT.prototype._applyImageOpacity = function (color, opacity) {
        opacity = parseFloat(opacity);
        if (isNaN(opacity) || typeof color != 'string') return color;
        if (color.indexOf('rgba') == 0) {
            return color.replace(/rgba\(([^,]+),([^,]+),([^,]+),([^)]+)\)/, function (all, r, g, b) {
                return 'rgba(' + r + ',' + g + ',' + b + ',' + opacity + ')';
            });
        }
        if (color.indexOf('rgb') == 0) {
            return color.replace(/rgb\(([^,]+),([^,]+),([^)]+)\)/, function (all, r, g, b) {
                return 'rgba(' + r + ',' + g + ',' + b + ',' + opacity + ')';
            });
        }
        return color;
    };

    dgWKT.prototype._getImageHitRow = function (lon, lat) {
        if (this._imageRows == null) return null;
        for (var i = this._imageRows.length - 1; i >= 0; i--) {
            var row = this._imageRows[i];
            if (row.bounds == null) continue;
            if (lon < row.bounds[0] || lon > row.bounds[2] || lat < row.bounds[1] || lat > row.bounds[3]) continue;
            if (this._pointInImagePolygons([lon, lat], row.coordinates)) return row;
        }
        return null;
    };

    dgWKT.prototype._pointInImagePolygons = function (point, polygons) {
        for (var i = 0; i < polygons.length; i++) {
            var polygon = polygons[i];
            if (polygon.length <= 0) continue;
            if (!this._pointInImageRing(point, polygon[0])) continue;
            var inHole = false;
            for (var j = 1; j < polygon.length; j++) {
                if (this._pointInImageRing(point, polygon[j])) {
                    inHole = true;
                    break;
                }
            }
            if (!inHole) return true;
        }
        return false;
    };

    dgWKT.prototype._pointInImageRing = function (point, ring) {
        var x = point[0];
        var y = point[1];
        var inside = false;
        for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
            var xi = ring[i][0], yi = ring[i][1];
            var xj = ring[j][0], yj = ring[j][1];
            var intersect = ((yi > y) != (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 0.000001) + xi);
            if (intersect) inside = !inside;
        }
        return inside;
    };

    dgWKT.prototype._handleImageMapClick = function (evt, dgxy) {
        var xy = this._normalizeImageEventXY(evt, dgxy);
        if (xy == null) return null;
        var row = this._getImageHitRow(xy.x, xy.y);
        if (row == null) return null;
        var feature = this._createImageFeatureLike(row);
        var result = {
            engine: 'maplibre',
            type: 'dgwkt',
            itemType: 'dgwkt',
            cluster: false,
            renderMode: 'image',
            item: this,
            feature: feature,
            features: [feature],
            properties: row.properties,
            coordinate: [xy.x, xy.y],
            originalEvent: evt
        };
        if (this._easymap != null && typeof this._easymap._dispatchItemClick == 'function') {
            this._easymap._dispatchItemClick(this, result);
        }
        else {
            this._dispatchImageFeatureFallback(row, feature, evt);
        }
        return row;
    };

    dgWKT.prototype._handleImageMapMove = function (evt, dgxy) {
        var xy = this._normalizeImageEventXY(evt, dgxy);
        if (xy == null) return null;
        var row = this._getImageHitRow(xy.x, xy.y);
        if (row == null) {
            if (this._imageHoverRow != null && typeof this._onFeatureMouseOut == 'function') {
                this._onFeatureMouseOut.apply(this._imageHoverRow.properties, [
                    this._imageHoverRow.properties,
                    this._imageHoverRow.geometryType,
                    this._imageHoverRow.coordinates,
                    this._createImageFeatureLike(this._imageHoverRow),
                    evt
                ]);
            }
            this._imageHoverRow = null;
            return null;
        }
        if (typeof this._onFeatureHover == 'function') {
            this._onFeatureHover.apply(row.properties, [
                row.properties,
                row.geometryType,
                row.coordinates,
                this._createImageFeatureLike(row),
                evt
            ]);
        }
        this._imageHoverRow = row;
        return row;
    };

    dgWKT.prototype._normalizeImageEventXY = function (evt, dgxy) {
        if (dgxy != null) {
            if (dgxy.x != null && dgxy.y != null) return { x: parseFloat(dgxy.x), y: parseFloat(dgxy.y) };
            if (Array.isArray(dgxy.xy)) return { x: parseFloat(dgxy.xy[0]), y: parseFloat(dgxy.xy[1]) };
        }
        if (evt != null && evt.lngLat != null) return { x: parseFloat(evt.lngLat.lng), y: parseFloat(evt.lngLat.lat) };
        return null;
    };

    dgWKT.prototype._createImageFeatureLike = function (row) {
        var geometryCoordinates = row.geometryType == 'Polygon' ? row.coordinates[0] : row.coordinates;
        var feature = {
            type: 'Feature',
            _easymapClass: 'dgwkt',
            _dgwkt: this,
            values_: row.properties,
            properties: row.properties,
            geometry: {
                type: row.geometryType,
                coordinates: geometryCoordinates
            },
            get: function (key) {
                return this.values_[key];
            },
            getProperties: function () {
                return this.values_;
            }
        };
        return feature;
    };

    dgWKT.prototype._dispatchImageFeatureFallback = function (row, feature, evt) {
        var callbacks = [this._featureClick, this.onFeatureSelect];
        for (var i = 0; i < callbacks.length; i++) {
            if (typeof callbacks[i] == 'function') {
                callbacks[i].apply(row.properties, [
                    row.properties,
                    row.geometryType,
                    row.coordinates,
                    feature,
                    evt,
                    [feature]
                ]);
            }
        }
    };

    dgWKT.prototype.getStrokeColor = function () {
        return this._styleState.strokeColor || this._options.strokeColor || this._options['stroke-color'];
    };

    dgWKT.prototype.setStrokeColor = function (color) {
        var parsed = ns.parseColor(color, color);
        this._styleState.strokeColor = parsed.color;
        if (parsed.opacity != null) this._styleState.strokeOpacity = parsed.opacity;
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.getFillColor = function () {
        return this._styleState.fillColor || this._options.fillColor || this._options['fill-color'];
    };

    dgWKT.prototype.setFillColor = function (color) {
        var parsed = ns.parseColor(color, color);
        this._styleState.fillColor = parsed.color;
        if (parsed.opacity != null) this._styleState.fillOpacity = parsed.opacity;
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.getStrokeWidth = function () {
        return this._styleState.strokeWidth || this._options.strokeWidth || this._options.width;
    };

    dgWKT.prototype.setStrokeWidth = function (width) {
        this._styleState.strokeWidth = ns.toNumber(width, 1);
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.enableDashed = function (lineDash) {
        return this.setLineDash(lineDash);
    };

    dgWKT.prototype.setLineDash = function (lineDash) {
        if (!Array.isArray(lineDash)) return this;
        this._styleState.lineDash = lineDash.slice();
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.setLineCap = function (lineCap) {
        if (['round', 'square', 'butt'].indexOf(lineCap) == -1) return this;
        this._styleState.lineCap = lineCap;
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.setIcon = function (dataIndex, options) {
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
        if (Array.isArray(this._wkt) && this._wkt[dataIndex] != null && typeof this._wkt[dataIndex] == 'object') {
            var row = this._wkt[dataIndex];
            if (options.pic != null) row.pic = options.pic;
            var imageStyle = null;
            if (options.scale != null || options.rotate != null || options.rotation != null || options.postion != null || options.position != null || options.anchor != null || options.opacity != null) {
                row.style_setting = row.style_setting || {};
                row.style_setting.Image = row.style_setting.Image || {};
                imageStyle = row.style_setting.Image;
            }
            if (imageStyle != null) {
                if (options.scale != null) imageStyle.scale = ns.toNumber(options.scale, 1);
                if (options.rotate != null) imageStyle.rotate = ns.toNumber(options.rotate, 0);
                if (options.rotation != null) imageStyle.rotate = ns.toNumber(options.rotation, 0);
                if (options.postion != null) imageStyle.anchor = options.postion.slice ? options.postion.slice() : options.postion;
                if (options.position != null) imageStyle.anchor = options.position.slice ? options.position.slice() : options.position;
                if (options.anchor != null) imageStyle.anchor = options.anchor.slice ? options.anchor.slice() : options.anchor;
                if (options.opacity != null) imageStyle.opacity = ns.toNumber(options.opacity, 1);
            }
        }
        if (options['auto-refresh'] !== false) {
            ns.refreshItemData(this);
            ns.refreshItemStyle(this);
        }
        return this;
    };

    dgWKT.prototype.updateWKT = function (dataIndex, wktObj, srs) {
        var index = parseInt(dataIndex, 10);
        if (isNaN(index) || index < 0 || wktObj == null || typeof wktObj != 'object') return this;
        if (!Array.isArray(this._wkt)) {
            if (Array.isArray(this._url)) {
                this._wkt = this._url;
            }
            else {
                return this;
            }
        }
        var row = this._wkt[index];
        if (row == null || typeof row != 'object' || Array.isArray(row)) {
            row = { wkt: typeof row == 'string' ? row : '' };
        }
        for (var key in wktObj) {
            if (Object.prototype.hasOwnProperty.call(wktObj, key) && key != 'auto-refresh') {
                row[key] = wktObj[key];
            }
        }
        this._wkt[index] = row;
        this._url = this._wkt;
        if (srs != null) this._dataSRS = srs;
        if (wktObj['auto-refresh'] !== false) {
            ns.refreshItemData(this);
            ns.refreshItemStyle(this);
        }
        return this;
    };

    dgWKT.prototype.setXY = function (dataIndex, dgxy) {
        var index = parseInt(dataIndex, 10);
        if (isNaN(index) || dgxy == null || isNaN(parseFloat(dgxy.x)) || isNaN(parseFloat(dgxy.y))) return this;
        if (!Array.isArray(this._wkt)) {
            if (Array.isArray(this._url)) this._wkt = this._url;
            else return this;
        }
        if (this._wkt[index] == null) return this;
        var row = this._wkt[index];
        if (typeof row != 'object' || Array.isArray(row)) row = { wkt: getRowWkt(row) };
        row.wkt = 'POINT(' + parseFloat(dgxy.x) + ' ' + parseFloat(dgxy.y) + ')';
        this._wkt[index] = row;
        this._url = this._wkt;
        ns.refreshItemData(this);
        return this;
    };

    dgWKT.prototype.setLabel = function (dataIndex, text) {
        var index = parseInt(dataIndex, 10);
        if (isNaN(index)) return this;
        if (!Array.isArray(this._wkt)) {
            if (Array.isArray(this._url)) this._wkt = this._url;
            else return this;
        }
        if (this._wkt[index] == null) return this;
        var row = this._wkt[index];
        if (typeof row != 'object' || Array.isArray(row)) row = { wkt: getRowWkt(row) };
        row.label = text;
        this._wkt[index] = row;
        this._url = this._wkt;
        ns.refreshItemData(this);
        return this;
    };

    dgWKT.prototype.getLabel = function (dataIndex) {
        var index = parseInt(dataIndex, 10);
        if (isNaN(index)) return undefined;
        var rows = Array.isArray(this._wkt) ? this._wkt : (Array.isArray(this._url) ? this._url : null);
        if (rows == null || rows[index] == null || typeof rows[index] != 'object') return undefined;
        return rows[index].label;
    };

    dgWKT.prototype.getClosestData = function (wktOrDgxy, counts) {
        var rows = Array.isArray(this._wkt) ? this._wkt : (Array.isArray(this._url) ? this._url : null);
        if (!Array.isArray(rows)) {
            console.log('此 dgWKT 尚未載入 wkt ');
            return false;
        }
        var queryWkt = wktOrDgxy;
        if (wktOrDgxy != null && wktOrDgxy.x != null && wktOrDgxy.y != null) {
            queryWkt = 'POINT(' + wktOrDgxy.x + ' ' + wktOrDgxy.y + ')';
        }
        var queryGeometry = ns.parseWktGeometry != null ? ns.parseWktGeometry(queryWkt) : null;
        if (queryGeometry == null) return [];
        var output = [];
        for (var i = 0; i < rows.length; i++) {
            var rowGeometry = ns.parseWktGeometry != null ? ns.parseWktGeometry(getRowWkt(rows[i])) : null;
            if (rowGeometry == null) continue;
            var row = rows[i];
            if (row == null || typeof row != 'object' || Array.isArray(row)) row = { wkt: getRowWkt(row) };
            row.getClosestData_index = i;
            row.getClosestData_distance = geometryDistanceMeters(queryGeometry, rowGeometry);
            output.push(row);
        }
        output.sort(function (a, b) {
            return a.getClosestData_distance - b.getClosestData_distance;
        });
        var limit = parseInt(counts, 10);
        if (!isNaN(limit)) output = output.slice(0, limit);
        return output;
    };

    dgWKT.prototype.setIconScale = function (value) {
        this._iconScale = ns.toNumber(value, this._iconScale);
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.getIconScale = function () {
        return this._iconScale;
    };

    dgWKT.prototype.refresh = function () {
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgWKT.prototype.setCluster = function (value) {
        return ns.setItemCluster(this, value);
    };

    dgWKT.prototype.getCluster = function () {
        return ns.getItemCluster(this);
    };

    dgWKT.prototype.setClusterDistance = function (value) {
        return ns.setItemClusterDistance(this, value);
    };

    dgWKT.prototype.getClusterDistance = function () {
        return ns.getItemClusterDistance(this);
    };

    dgWKT.prototype.setMinClusterSize = function (value) {
        return ns.setItemMinClusterSize(this, value);
    };

    dgWKT.prototype.getMinClusterSize = function () {
        return ns.getItemMinClusterSize(this);
    };

    dgWKT.prototype.setClusterClickZoomToBBOX = function (value) {
        return ns.setItemClusterClickZoomToBBOX(this, value);
    };

    dgWKT.prototype.getClusterClickZoomToBBOX = function () {
        return ns.getItemClusterClickZoomToBBOX(this);
    };

    dgWKT.prototype.enableSpiderDisplay = function (zoom) {
        this._isSpiderDisplay = true;
        var value = parseFloat(zoom);
        if (!isNaN(value)) this._spiderDisplayZoomLevel = value;
        if (this._easymap != null && typeof this._easymap._registerWktSpiderDisplayCleanup == 'function') {
            this._easymap._registerWktSpiderDisplayCleanup(this);
        }
        if (this._easymap != null && typeof this._easymap._clearWktSpiderDisplay == 'function') {
            this._easymap._clearWktSpiderDisplay(this);
        }
        return this;
    };

    dgWKT.prototype.disableSpiderDisplay = function () {
        this._isSpiderDisplay = false;
        if (this._easymap != null && typeof this._easymap._clearWktSpiderDisplay == 'function') {
            this._easymap._clearWktSpiderDisplay(this);
        }
        return this;
    };

    dgWKT.prototype.displaySpiderDisplay = function () {
        return this.disableSpiderDisplay();
    };

    dgWKT.prototype.setUpperZoomByBoundary = function (value, options) {
        this._setUpperZoomByBoundary = value !== false;
        this._upperZoomByBoundaryOptions = options || null;
        if (this._setUpperZoomByBoundary === true && this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgWKT.prototype.setExtrusion = function (value) {
        return ns.setItemExtrusion(this, value);
    };

    dgWKT.prototype.setExtrusionHeight = function (value) {
        return ns.setItemExtrusionHeight(this, value);
    };

    dgWKT.prototype.setExtrusionBase = function (value) {
        return ns.setItemExtrusionBase(this, value);
    };

    dgWKT.prototype.setExtrusionColor = function (value) {
        return ns.setItemExtrusionColor(this, value);
    };

    dgWKT.prototype.setExtrusionOpacity = function (value) {
        return ns.setItemExtrusionOpacity(this, value);
    };

    window.dgWKT = dgWKT;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgWKT');
})(window);
