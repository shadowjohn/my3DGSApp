(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function stripTags(text) {
        return String(text || '')
            .replace(/<!\[CDATA\[/g, '')
            .replace(/\]\]>/g, '')
            .replace(/<[^>]+>/g, '')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&apos;/g, "'")
            .replace(/&amp;/g, '&')
            .trim();
    }

    function localName(name) {
        name = String(name || '');
        var index = name.indexOf(':');
        if (index >= 0) name = name.substring(index + 1);
        return name.toLowerCase();
    }

    function escapeRegExp(text) {
        return String(text || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function parseAttributes(tagText) {
        var attrs = {};
        String(tagText || '').replace(/([\w:.-]+)\s*=\s*("([^"]*)"|'([^']*)')/g, function (_, name, quoted, doubleValue, singleValue) {
            attrs[localName(name)] = doubleValue != null ? doubleValue : singleValue;
            return _;
        });
        return attrs;
    }

    function firstOpenTagAttributes(block, tagName) {
        var pattern = new RegExp('<(?:[\\w.-]+:)?' + escapeRegExp(tagName) + '\\b([^>]*)>');
        var match = String(block || '').match(pattern);
        return match == null ? {} : parseAttributes(match[1]);
    }

    function extractBlocks(text, tagName) {
        var blocks = [];
        var pattern = new RegExp('<(?:[\\w.-]+:)?' + escapeRegExp(tagName) + '\\b[^>]*>[\\s\\S]*?<\\/(?:[\\w.-]+:)?' + escapeRegExp(tagName) + '>', 'g');
        var match = null;
        text = String(text || '');
        while ((match = pattern.exec(text)) != null) {
            blocks.push(match[0]);
        }
        return blocks;
    }

    function firstText(block, tagName) {
        var pattern = new RegExp('<(?:[\\w.-]+:)?' + escapeRegExp(tagName) + '\\b[^>]*>([\\s\\S]*?)<\\/(?:[\\w.-]+:)?' + escapeRegExp(tagName) + '>');
        var match = String(block || '').match(pattern);
        return match == null ? '' : stripTags(match[1]);
    }

    function isXmlText(value) {
        return typeof value == 'string' && /^\s*</.test(value);
    }

    function normalizeDataSrs(srs) {
        srs = String(srs || 'EPSG:4326').toUpperCase().replace(/\s+/g, '');
        srs = srs.replace(/YXZ$/i, '').replace(/YX$/i, '');
        return srs || 'EPSG:4326';
    }

    function isYxSrs(srs) {
        return /YX/i.test(String(srs || ''));
    }

    function inferCoordinateOptions(rawSrs, block) {
        var attrs = {};
        var openTags = String(block || '').match(/<[^!?][^>]*>/g) || [];
        for (var i = 0; i < openTags.length; i++) {
            attrs = parseAttributes(openTags[i]);
            if (attrs.srsname != null || attrs.srsdimension != null) break;
        }
        var srs = rawSrs || attrs.srsname || 'EPSG:4326';
        var dimension = parseInt(attrs.srsdimension, 10);
        if (isNaN(dimension) || dimension < 2) {
            dimension = /YXZ/i.test(String(srs)) ? 3 : 2;
        }
        return {
            rawSrs: srs,
            dataSrs: normalizeDataSrs(srs),
            yx: isYxSrs(srs),
            dimension: dimension
        };
    }

    function tupleToCoordinate(values, options) {
        if (!Array.isArray(values) || values.length < 2) return null;
        var x = options.yx === true ? parseFloat(values[1]) : parseFloat(values[0]);
        var y = options.yx === true ? parseFloat(values[0]) : parseFloat(values[1]);
        if (isNaN(x) || isNaN(y)) return null;
        return [x, y];
    }

    function parseNumberList(text) {
        var matches = String(text || '').match(/[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?/g);
        if (matches == null) return [];
        var nums = [];
        for (var i = 0; i < matches.length; i++) {
            var value = parseFloat(matches[i]);
            if (!isNaN(value)) nums.push(value);
        }
        return nums;
    }

    function parseDelimitedCoordinates(text, options) {
        var rows = String(text || '').trim().split(/\s+/);
        var coordinates = [];
        for (var i = 0; i < rows.length; i++) {
            if (rows[i] == '') continue;
            var parts = rows[i].split(',');
            if (parts.length < 2) {
                parts = parseNumberList(rows[i]);
            }
            var coordinate = tupleToCoordinate(parts, options);
            if (coordinate != null) coordinates.push(coordinate);
        }
        return coordinates;
    }

    function parseFlatCoordinates(text, options) {
        var nums = parseNumberList(text);
        var dimension = parseInt(options.dimension, 10);
        if (isNaN(dimension) || dimension < 2) dimension = 2;
        if (nums.length % dimension != 0 && nums.length % 2 == 0) dimension = 2;
        var coordinates = [];
        for (var i = 0; i <= nums.length - dimension; i += dimension) {
            var coordinate = tupleToCoordinate(nums.slice(i, i + dimension), options);
            if (coordinate != null) coordinates.push(coordinate);
        }
        return coordinates;
    }

    function parseCoordBlocks(block, options) {
        var coordBlocks = extractBlocks(block, 'coord');
        var coordinates = [];
        for (var i = 0; i < coordBlocks.length; i++) {
            var x = firstText(coordBlocks[i], 'X');
            var y = firstText(coordBlocks[i], 'Y');
            var coordinate = tupleToCoordinate([x, y], options);
            if (coordinate != null) coordinates.push(coordinate);
        }
        return coordinates;
    }

    function parseCoordinateBlock(block, rawSrs) {
        var options = inferCoordinateOptions(rawSrs, block);
        var text = firstText(block, 'coordinates');
        if (text != '') return parseDelimitedCoordinates(text, options);
        text = firstText(block, 'posList');
        if (text != '') return parseFlatCoordinates(text, options);
        text = firstText(block, 'pos');
        if (text != '') return parseFlatCoordinates(text, options);
        return parseCoordBlocks(block, options);
    }

    function closeRing(ring) {
        if (!Array.isArray(ring) || ring.length == 0) return ring;
        var first = ring[0];
        var last = ring[ring.length - 1];
        if (first[0] != last[0] || first[1] != last[1]) {
            ring = ring.slice();
            ring.push([first[0], first[1]]);
        }
        return ring;
    }

    function parsePoint(block, rawSrs) {
        var coordinates = parseCoordinateBlock(block, rawSrs);
        if (coordinates.length == 0) return null;
        return { type: 'Point', coordinates: coordinates[0] };
    }

    function parseLineString(block, rawSrs) {
        var coordinates = parseCoordinateBlock(block, rawSrs);
        if (coordinates.length == 0) return null;
        return { type: 'LineString', coordinates: coordinates };
    }

    function parsePolygon(block, rawSrs) {
        var ringBlocks = extractBlocks(block, 'LinearRing');
        var rings = [];
        if (ringBlocks.length == 0) {
            var coordinates = parseCoordinateBlock(block, rawSrs);
            if (coordinates.length > 0) rings.push(closeRing(coordinates));
        }
        for (var i = 0; i < ringBlocks.length; i++) {
            var ring = parseCoordinateBlock(ringBlocks[i], rawSrs);
            if (ring.length > 0) rings.push(closeRing(ring));
        }
        if (rings.length == 0) return null;
        return { type: 'Polygon', coordinates: rings };
    }

    function parseMultiPoint(block, rawSrs) {
        var pointBlocks = extractBlocks(block, 'Point');
        var coordinates = [];
        for (var i = 0; i < pointBlocks.length; i++) {
            var point = parsePoint(pointBlocks[i], rawSrs);
            if (point != null) coordinates.push(point.coordinates);
        }
        return coordinates.length == 0 ? null : { type: 'MultiPoint', coordinates: coordinates };
    }

    function parseMultiLineString(block, rawSrs) {
        var lineBlocks = extractBlocks(block, 'LineString');
        var coordinates = [];
        for (var i = 0; i < lineBlocks.length; i++) {
            var line = parseLineString(lineBlocks[i], rawSrs);
            if (line != null) coordinates.push(line.coordinates);
        }
        return coordinates.length == 0 ? null : { type: 'MultiLineString', coordinates: coordinates };
    }

    function parseMultiPolygon(block, rawSrs) {
        var polygonBlocks = extractBlocks(block, 'Polygon');
        var coordinates = [];
        for (var i = 0; i < polygonBlocks.length; i++) {
            var polygon = parsePolygon(polygonBlocks[i], rawSrs);
            if (polygon != null) coordinates.push(polygon.coordinates);
        }
        return coordinates.length == 0 ? null : { type: 'MultiPolygon', coordinates: coordinates };
    }

    function findGeometry(block, rawSrs) {
        var parsers = [
            { tag: 'MultiSurface', fn: parseMultiPolygon },
            { tag: 'MultiPolygon', fn: parseMultiPolygon },
            { tag: 'MultiLineString', fn: parseMultiLineString },
            { tag: 'MultiCurve', fn: parseMultiLineString },
            { tag: 'MultiPoint', fn: parseMultiPoint },
            { tag: 'Polygon', fn: parsePolygon },
            { tag: 'Surface', fn: parsePolygon },
            { tag: 'LineString', fn: parseLineString },
            { tag: 'Curve', fn: parseLineString },
            { tag: 'Point', fn: parsePoint }
        ];
        for (var i = 0; i < parsers.length; i++) {
            var geometryBlocks = extractBlocks(block, parsers[i].tag);
            if (geometryBlocks.length == 0) continue;
            var geometry = parsers[i].fn(geometryBlocks[0], rawSrs);
            if (geometry != null) return { geometry: geometry, block: geometryBlocks[0] };
        }
        return null;
    }

    function extractFeatureBlocks(text) {
        var blocks = extractBlocks(text, 'featureMember');
        if (blocks.length == 0) blocks = extractBlocks(text, 'featureMembers');
        if (blocks.length == 0) blocks = [String(text || '')];
        return blocks;
    }

    function extractProperties(featureBlock, geometryBlock) {
        var text = String(featureBlock || '');
        if (geometryBlock != null) text = text.replace(geometryBlock, '');
        var properties = {};
        var skip = {
            boundedby: true,
            envelope: true,
            geometryproperty: true,
            point: true,
            multipoint: true,
            linestring: true,
            multilinestring: true,
            multicurve: true,
            polygon: true,
            multipolygon: true,
            multisurface: true,
            surface: true,
            linearring: true,
            coordinates: true,
            pos: true,
            poslist: true,
            coord: true,
            x: true,
            y: true,
            z: true
        };
        text.replace(/<([\w:.-]+)\b[^>]*>([^<>]*)<\/\1>/g, function (_, tagName, value) {
            var key = localName(tagName);
            if (skip[key] === true) return _;
            var clean = stripTags(value);
            if (clean !== '') properties[key] = clean;
            return _;
        });
        return properties;
    }

    function parseGmlToGeoJSON(gml, rawSrs) {
        var text = String(gml || '');
        var features = [];
        var blocks = extractFeatureBlocks(text);
        for (var i = 0; i < blocks.length; i++) {
            var found = findGeometry(blocks[i], rawSrs);
            if (found == null || found.geometry == null) continue;
            var properties = extractProperties(blocks[i], found.block);
            properties.data_index = features.length;
            properties._easymapClass = 'dggml';
            if (properties.label == null || properties.label === '') {
                properties.label = properties.name || properties.title || properties.id || '';
            }
            features.push({
                type: 'Feature',
                properties: properties,
                geometry: found.geometry
            });
        }
        return { type: 'FeatureCollection', features: features };
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
            if (typeof failure == 'function') failure(new Error('GML load failed: ' + xhr.status), xhr);
        };
        xhr.onerror = function (event) {
            if (typeof failure == 'function') failure(event, xhr);
        };
        xhr.open('GET', url, true);
        xhr.send(null);
        return xhr;
    }

    function dgGML(data, srs, callback, options) {
        this._type = 'dggml';
        this._easymapClass = 'dggml';
        this._url = data || '';
        this._gml = isXmlText(data) ? data : null;
        this._geojson = null;
        this._rawDataSRS = typeof srs == 'string' ? srs : 'EPSG:4326';
        this._dataSRS = normalizeDataSrs(this._rawDataSRS);
        this._callback = typeof callback == 'function' ? callback : (typeof srs == 'function' ? srs : null);
        this._options = options || (callback && typeof callback == 'object' ? callback : {});
        this._gml_version = 'GML';
        this._gml_hasZ = /Z/i.test(this._rawDataSRS);
        this._styleState = {};
        this._featureStyles = {};
        this._iconScale = 1;
        this._styleProxy = null;
        this._instance = null;
        this._setUpperZoomByBoundary = false;
        this._upperZoomByBoundaryOptions = null;
        this._xhr = null;
        this._isLoaded = this._gml != null;
        this._callbackCalled = false;
        ns.initClusterDefaults(this);
        ns.attachItemBasics(this);
    }

    dgGML.prototype._parse = function () {
        this._geojson = parseGmlToGeoJSON(this._gml || '', this._rawDataSRS);
        this._isLoaded = true;
        return this._geojson;
    };

    dgGML.prototype._notifyLoaded = function () {
        if (this._callbackCalled === true) return this;
        this._callbackCalled = true;
        if (typeof this._callback == 'function') this._callback.call(this, this);
        return this;
    };

    dgGML.prototype._load = function (success, failure) {
        var self = this;
        if (this._gml != null || isXmlText(this._url)) {
            if (this._gml == null) this._gml = this._url;
            this._parse();
            if (typeof success == 'function') success(this);
            return null;
        }
        if (typeof this._url != 'string' || this._url == '') {
            this._parse();
            if (typeof success == 'function') success(this);
            return null;
        }
        this._xhr = loadText(this._url, function (text) {
            self._gml = text || '';
            self._parse();
            if (typeof success == 'function') success(self);
        }, failure);
        return this._xhr;
    };

    dgGML.prototype.setData = function (data) {
        this._url = data || '';
        this._gml = isXmlText(data) ? data : null;
        this._geojson = null;
        this._isLoaded = this._gml != null;
        this._callbackCalled = false;
        if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
            this._easymap._updateItemData(this);
        }
        return this;
    };

    dgGML.prototype.getData = function () {
        return this._gml || this._url;
    };

    dgGML.prototype.toGeoJSON = function () {
        if (this._geojson != null) return this._geojson;
        if (this._gml != null || isXmlText(this._url)) {
            if (this._gml == null) this._gml = this._url;
            return this._parse();
        }
        return { type: 'FeatureCollection', features: [] };
    };

    dgGML.prototype.getStyle = function () {
        if (this._styleProxy == null) this._styleProxy = ns.createWktStyleProxy(this);
        return this._styleProxy;
    };

    dgGML.prototype.setOpacity = function (opacity) {
        this._styleState.strokeOpacity = ns.toNumber(opacity, 1);
        this._styleState.fillOpacity = ns.toNumber(opacity, 1);
        this._styleState.pointOpacity = ns.toNumber(opacity, 1);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGML.prototype.setCluster = function (value) {
        return ns.setItemCluster(this, value);
    };

    dgGML.prototype.getCluster = function () {
        return ns.getItemCluster(this);
    };

    dgGML.prototype.setClusterDistance = function (value) {
        return ns.setItemClusterDistance(this, value);
    };

    dgGML.prototype.getClusterDistance = function () {
        return ns.getItemClusterDistance(this);
    };

    dgGML.prototype.setMinClusterSize = function (value) {
        return ns.setItemMinClusterSize(this, value);
    };

    dgGML.prototype.getMinClusterSize = function () {
        return ns.getItemMinClusterSize(this);
    };

    dgGML.prototype.setClusterClickZoomToBBOX = function (value) {
        return ns.setItemClusterClickZoomToBBOX(this, value);
    };

    dgGML.prototype.getClusterClickZoomToBBOX = function () {
        return ns.getItemClusterClickZoomToBBOX(this);
    };

    dgGML.prototype.setUpperZoomByBoundary = function (value, options) {
        this._setUpperZoomByBoundary = value !== false;
        this._upperZoomByBoundaryOptions = options || null;
        if (this._setUpperZoomByBoundary === true && this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgGML.prototype.setIcon = function (dataIndex, options) {
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

    dgGML.prototype.setIconScale = function (value) {
        this._iconScale = ns.toNumber(value, this._iconScale);
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGML.prototype.getIconScale = function () {
        return this._iconScale;
    };

    dgGML.prototype.refresh = function () {
        ns.refreshItemData(this);
        ns.refreshItemStyle(this);
        return this;
    };

    dgGML.prototype.setExtrusion = function (value) {
        return ns.setItemExtrusion(this, value);
    };

    dgGML.prototype.setExtrusionHeight = function (value) {
        return ns.setItemExtrusionHeight(this, value);
    };

    dgGML.prototype.setExtrusionBase = function (value) {
        return ns.setItemExtrusionBase(this, value);
    };

    dgGML.prototype.setExtrusionColor = function (value) {
        return ns.setItemExtrusionColor(this, value);
    };

    dgGML.prototype.setExtrusionOpacity = function (value) {
        return ns.setItemExtrusionOpacity(this, value);
    };

    ns.parseGmlToGeoJSON = parseGmlToGeoJSON;
    window.dgGML = dgGML;
    window.dgGml = dgGML;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgGML');
})(window);
