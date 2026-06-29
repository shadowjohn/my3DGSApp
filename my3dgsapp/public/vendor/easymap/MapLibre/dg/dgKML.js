(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};
    var EARTH_RADIUS = 6378137;

    function stripTags(text) {
        return String(text || '')
            .replace(/<!\[CDATA\[/g, '')
            .replace(/\]\]>/g, '')
            .replace(/<[^>]+>/g, '')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&amp;/g, '&')
            .replace(/&quot;/g, '"')
            .replace(/&apos;/g, "'")
            .trim();
    }

    function firstMatch(text, pattern) {
        var match = String(text || '').match(pattern);
        return match == null ? '' : stripTags(match[1]);
    }

    function isKmlText(data) {
        return typeof data == 'string' && /^\s*</.test(data);
    }

    function emptyFeatureCollection() {
        return { type: 'FeatureCollection', features: [] };
    }

    function formatWktNumber(value) {
        var num = parseFloat(value);
        if (isNaN(num)) return null;
        return String(num);
    }

    function formatWktCoordinate(coordinate) {
        if (!Array.isArray(coordinate) || coordinate.length < 2) return null;
        var lon = formatWktNumber(coordinate[0]);
        var lat = formatWktNumber(coordinate[1]);
        return lon == null || lat == null ? null : lon + ' ' + lat;
    }

    function formatWktCoordinateList(coordinates, minimum) {
        if (!Array.isArray(coordinates) || coordinates.length < minimum) return null;
        var output = [];
        for (var i = 0; i < coordinates.length; i++) {
            var coordinate = formatWktCoordinate(coordinates[i]);
            if (coordinate != null) output.push(coordinate);
        }
        return output.length < minimum ? null : output.join(', ');
    }

    function sameCoordinate(a, b) {
        return Array.isArray(a) && Array.isArray(b) && parseFloat(a[0]) == parseFloat(b[0]) && parseFloat(a[1]) == parseFloat(b[1]);
    }

    function closeRing(coordinates) {
        if (!Array.isArray(coordinates) || coordinates.length == 0) return [];
        var ring = coordinates.slice();
        if (!sameCoordinate(ring[0], ring[ring.length - 1])) ring.push([ring[0][0], ring[0][1]]);
        return ring;
    }

    function formatWktRing(coordinates) {
        coordinates = closeRing(coordinates);
        var ring = formatWktCoordinateList(coordinates, 4);
        return ring == null ? null : '(' + ring + ')';
    }

    function geometryToWkt(geometry) {
        if (geometry == null) return '';
        if (geometry.type == 'Feature' && geometry.geometry != null) geometry = geometry.geometry;
        if (geometry.type == 'Point') {
            var point = formatWktCoordinate(geometry.coordinates);
            return point == null ? '' : 'POINT(' + point + ')';
        }
        if (geometry.type == 'MultiPoint') {
            if (!Array.isArray(geometry.coordinates)) return '';
            var points = [];
            for (var i = 0; i < geometry.coordinates.length; i++) {
                var multiPoint = formatWktCoordinate(geometry.coordinates[i]);
                if (multiPoint != null) points.push('(' + multiPoint + ')');
            }
            return points.length == 0 ? '' : 'MULTIPOINT(' + points.join(', ') + ')';
        }
        if (geometry.type == 'LineString') {
            var line = formatWktCoordinateList(geometry.coordinates, 2);
            return line == null ? '' : 'LINESTRING(' + line + ')';
        }
        if (geometry.type == 'MultiLineString') {
            if (!Array.isArray(geometry.coordinates)) return '';
            var lines = [];
            for (var j = 0; j < geometry.coordinates.length; j++) {
                var lineString = formatWktCoordinateList(geometry.coordinates[j], 2);
                if (lineString != null) lines.push('(' + lineString + ')');
            }
            return lines.length == 0 ? '' : 'MULTILINESTRING(' + lines.join(', ') + ')';
        }
        if (geometry.type == 'Polygon') {
            if (!Array.isArray(geometry.coordinates)) return '';
            var rings = [];
            for (var k = 0; k < geometry.coordinates.length; k++) {
                var ring = formatWktRing(geometry.coordinates[k]);
                if (ring != null) rings.push(ring);
            }
            return rings.length == 0 ? '' : 'POLYGON(' + rings.join(', ') + ')';
        }
        if (geometry.type == 'MultiPolygon') {
            if (!Array.isArray(geometry.coordinates)) return '';
            var polygons = [];
            for (var p = 0; p < geometry.coordinates.length; p++) {
                var polygonRings = [];
                for (var r = 0; r < geometry.coordinates[p].length; r++) {
                    var polygonRing = formatWktRing(geometry.coordinates[p][r]);
                    if (polygonRing != null) polygonRings.push(polygonRing);
                }
                if (polygonRings.length > 0) polygons.push('(' + polygonRings.join(', ') + ')');
            }
            return polygons.length == 0 ? '' : 'MULTIPOLYGON(' + polygons.join(', ') + ')';
        }
        return '';
    }

    function geoJsonToWktRows(geojson) {
        if (geojson == null) return [];
        var features = geojson.type == 'FeatureCollection' ? geojson.features : [geojson];
        if (!Array.isArray(features)) return [];
        var output = [];
        for (var i = 0; i < features.length; i++) {
            var feature = features[i];
            var geometry = feature != null && feature.type == 'Feature' ? feature.geometry : feature;
            var wkt = geometryToWkt(geometry);
            if (wkt == '') continue;
            var row = {};
            var properties = feature != null && feature.type == 'Feature' && feature.properties != null ? feature.properties : {};
            for (var key in properties) {
                if (Object.prototype.hasOwnProperty.call(properties, key)) row[key] = properties[key];
            }
            row.wkt = wkt;
            output.push(row);
        }
        return output;
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

    function getKmlWktRows(item) {
        if (Array.isArray(item._wkt)) return item._wkt;
        if (item._kml == null && isKmlText(item._url)) {
            item._kml = item._url;
            item._isLoaded = true;
        }
        if (item._kml == null) return null;
        item._wkt = geoJsonToWktRows(item.toGeoJSON());
        return item._wkt;
    }

    function getXmlAttr(text, name) {
        var pattern = new RegExp(name + "\\s*=\\s*(['\"])([\\s\\S]*?)\\1", 'i');
        var match = String(text || '').match(pattern);
        return match == null ? '' : stripTags(match[2]);
    }

    function normalizeStyleId(value) {
        return String(value || '').replace(/^\s*#/, '').trim();
    }

    function resolveKmlHref(href, baseUrl) {
        href = stripTags(href);
        if (href == '') return '';
        if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.indexOf('//') == 0 || href.charAt(0) == '/') return href;
        if (typeof baseUrl != 'string' || baseUrl == '' || isKmlText(baseUrl)) return href;
        if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(baseUrl)) return href;
        var cleanBase = baseUrl.split('#')[0].split('?')[0];
        var slashIndex = cleanBase.lastIndexOf('/');
        if (slashIndex < 0) return href;
        return cleanBase.substring(0, slashIndex + 1) + href;
    }

    function copyIconStyle(source, target) {
        target = target || {};
        if (source == null) return target;
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key) && source[key] != null && source[key] !== '') {
                target[key] = source[key];
            }
        }
        return target;
    }

    function parseIconStyleBlock(text, baseUrl) {
        var iconStyleMatch = String(text || '').match(/<IconStyle\b[^>]*>([\s\S]*?)<\/IconStyle>/i);
        if (iconStyleMatch == null) return null;
        var iconStyle = iconStyleMatch[1];
        var style = {};
        var href = firstMatch(iconStyle, /<Icon\b[\s\S]*?<href[^>]*>([\s\S]*?)<\/href>[\s\S]*?<\/Icon>/i) || firstMatch(iconStyle, /<href[^>]*>([\s\S]*?)<\/href>/i);
        if (href != '') style.pic = resolveKmlHref(href, baseUrl);
        var scale = ns.toNumber(firstMatch(iconStyle, /<scale[^>]*>([\s\S]*?)<\/scale>/i), NaN);
        if (!isNaN(scale)) style.scale = scale;
        var heading = ns.toNumber(firstMatch(iconStyle, /<heading[^>]*>([\s\S]*?)<\/heading>/i), NaN);
        if (!isNaN(heading)) style.rotation = heading;
        return style.pic != null || style.scale != null || style.rotation != null ? style : null;
    }

    function parseKmlStyleDefinitions(text, baseUrl) {
        var output = { styles: {}, styleMaps: {} };
        var stylePattern = /<Style\b([^>]*)>([\s\S]*?)<\/Style>/gi;
        var match = null;
        while ((match = stylePattern.exec(text)) != null) {
            var id = normalizeStyleId(getXmlAttr(match[1], 'id'));
            if (id == '') continue;
            var style = parseIconStyleBlock(match[2], baseUrl);
            if (style != null) output.styles[id] = style;
        }

        var styleMapPattern = /<StyleMap\b([^>]*)>([\s\S]*?)<\/StyleMap>/gi;
        while ((match = styleMapPattern.exec(text)) != null) {
            var mapId = normalizeStyleId(getXmlAttr(match[1], 'id'));
            if (mapId == '') continue;
            var block = match[2];
            var selected = '';
            var pairPattern = /<Pair\b[^>]*>([\s\S]*?)<\/Pair>/gi;
            var pairMatch = null;
            while ((pairMatch = pairPattern.exec(block)) != null) {
                var pairBlock = pairMatch[1];
                var key = firstMatch(pairBlock, /<key[^>]*>([\s\S]*?)<\/key>/i).toLowerCase();
                var styleUrl = firstMatch(pairBlock, /<styleUrl[^>]*>([\s\S]*?)<\/styleUrl>/i);
                if (styleUrl == '') continue;
                if (selected == '') selected = styleUrl;
                if (key == 'normal') {
                    selected = styleUrl;
                    break;
                }
            }
            var styleId = normalizeStyleId(selected);
            if (styleId != '' && output.styles[styleId] != null) output.styleMaps[mapId] = output.styles[styleId];
        }
        return output;
    }

    function getPlacemarkIconStyle(block, styleDefinitions, baseUrl) {
        var merged = {};
        var hasStyle = false;
        var styleUrl = normalizeStyleId(firstMatch(block, /<styleUrl[^>]*>([\s\S]*?)<\/styleUrl>/i));
        if (styleUrl != '') {
            var refStyle = styleDefinitions.styles[styleUrl] || styleDefinitions.styleMaps[styleUrl];
            if (refStyle != null) {
                copyIconStyle(refStyle, merged);
                hasStyle = true;
            }
        }
        var inlineStyleMatch = String(block || '').match(/<Style\b[^>]*>([\s\S]*?)<\/Style>/i);
        if (inlineStyleMatch != null) {
            var inlineStyle = parseIconStyleBlock(inlineStyleMatch[0], baseUrl);
            if (inlineStyle != null) {
                copyIconStyle(inlineStyle, merged);
                hasStyle = true;
            }
        }
        return hasStyle ? merged : null;
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
            if (typeof failure == 'function') failure(new Error('KML load failed: ' + xhr.status), xhr);
        };
        xhr.onerror = function (event) {
            if (typeof failure == 'function') failure(event, xhr);
        };
        xhr.open('GET', url, true);
        xhr.send(null);
        return xhr;
    }

    function parseCoordinateText(text) {
        var rows = String(text || '').trim().split(/\s+/);
        var output = [];
        for (var i = 0; i < rows.length; i++) {
            var parts = rows[i].split(',');
            if (parts.length < 2) continue;
            var lng = ns.toNumber(parts[0], NaN);
            var lat = ns.toNumber(parts[1], NaN);
            if (!isNaN(lng) && !isNaN(lat)) output.push([lng, lat]);
        }
        return output;
    }

    function parsePlacemarkGeometry(text) {
        var point = text.match(/<Point[\s\S]*?<coordinates[^>]*>([\s\S]*?)<\/coordinates>[\s\S]*?<\/Point>/i);
        if (point != null) {
            var pointCoords = parseCoordinateText(point[1]);
            if (pointCoords.length > 0) return { type: 'Point', coordinates: pointCoords[0] };
        }

        var line = text.match(/<LineString[\s\S]*?<coordinates[^>]*>([\s\S]*?)<\/coordinates>[\s\S]*?<\/LineString>/i);
        if (line != null) {
            return { type: 'LineString', coordinates: parseCoordinateText(line[1]) };
        }

        var polygon = text.match(/<Polygon[\s\S]*?<outerBoundaryIs[\s\S]*?<coordinates[^>]*>([\s\S]*?)<\/coordinates>[\s\S]*?<\/outerBoundaryIs>[\s\S]*?<\/Polygon>/i);
        if (polygon != null) {
            var ring = parseCoordinateText(polygon[1]);
            return { type: 'Polygon', coordinates: [ring] };
        }
        return null;
    }

    function parseKmlToGeoJSON(kml, options) {
        var text = String(kml || '');
        options = typeof options == 'object' && options != null ? options : { baseUrl: options };
        var styleDefinitions = parseKmlStyleDefinitions(text, options.baseUrl || '');
        var placemarkPattern = /<Placemark[\s\S]*?<\/Placemark>/gi;
        var features = [];
        var match = null;
        var index = 0;
        while ((match = placemarkPattern.exec(text)) != null) {
            var block = match[0];
            var geometry = parsePlacemarkGeometry(block);
            if (geometry == null) continue;
            var properties = {
                data_index: index,
                name: firstMatch(block, /<name[^>]*>([\s\S]*?)<\/name>/i),
                description: firstMatch(block, /<description[^>]*>([\s\S]*?)<\/description>/i)
            };
            var iconStyle = getPlacemarkIconStyle(block, styleDefinitions, options.baseUrl || '');
            if (iconStyle != null) {
                if (iconStyle.pic != null) properties.pic = iconStyle.pic;
                if (iconStyle.scale != null) properties.scale = iconStyle.scale;
                if (iconStyle.rotation != null) properties.rotation = iconStyle.rotation;
            }
            features.push({
                type: 'Feature',
                properties: properties,
                geometry: geometry
            });
            index++;
        }
        return { type: 'FeatureCollection', features: features };
    }

    function dgKML(data, srs, callback, options) {
        this._type = 'dgkml';
        this._easymapClass = 'dgkml';
        this._kml = isKmlText(data) ? data : null;
        this._url = data || '';
        this._kmlBaseUrl = this._kml == null && typeof data == 'string' ? data : '';
        this._dataSRS = typeof srs == 'string' ? srs : 'EPSG:4326';
        this._callback = typeof callback == 'function' ? callback : (typeof srs == 'function' ? srs : null);
        this._options = options || (callback && typeof callback == 'object' ? callback : {});
        this._styleState = {};
        this._featureStyles = {};
        this._styleProxy = null;
        this._instance = null;
        this._wkt = null;
        this._setUpperZoomByBoundary = false;
        this._upperZoomByBoundaryOptions = null;
        this._xhr = null;
        this._isLoaded = this._kml != null;
        this._callbackCalled = false;
        this.labelVisible = false;
        this._showInSelect = true;
        this._Style = typeof window.dgGStyle == 'function' ? new window.dgGStyle() : null;
        this._clusterStyleKind = null;
        ns.initClusterDefaults(this);
        ns.attachItemBasics(this);
    }

    dgKML.prototype._notifyLoaded = function () {
        if (this._callbackCalled === true) return this;
        this._callbackCalled = true;
        if (typeof this._callback == 'function') this._callback.call(this, this);
        return this;
    };

    dgKML.prototype._load = function (success, failure) {
        var self = this;
        if (this._kml != null || isKmlText(this._url)) {
            if (this._kml == null) this._kml = this._url;
            this._isLoaded = true;
            this._wkt = null;
            if (typeof success == 'function') success(this);
            return null;
        }
        if (typeof this._url != 'string' || this._url == '') {
            this._kml = '';
            this._isLoaded = true;
            this._wkt = null;
            if (typeof success == 'function') success(this);
            return null;
        }
        this._xhr = loadText(this._url, function (text) {
            self._kmlBaseUrl = self._kmlBaseUrl || self._url;
            self._kml = text || '';
            self._url = self._kml;
            self._isLoaded = true;
            self._wkt = null;
            if (typeof success == 'function') success(self);
        }, failure);
        return this._xhr;
    };

    dgKML.prototype.setData = function (data) {
        this._kml = isKmlText(data) ? data : null;
        this._url = data || '';
        this._kmlBaseUrl = this._kml == null && typeof data == 'string' ? data : '';
        this._isLoaded = this._kml != null;
        this._callbackCalled = false;
        this._wkt = null;
        if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
            this._easymap._updateItemData(this);
        }
        return this;
    };

    dgKML.prototype.getData = function () {
        return this._kml || this._url;
    };

    dgKML.prototype.toGeoJSON = function () {
        if (this._kml != null) return parseKmlToGeoJSON(this._kml, { baseUrl: this._kmlBaseUrl });
        if (isKmlText(this._url)) {
            this._kml = this._url;
            this._isLoaded = true;
            return parseKmlToGeoJSON(this._kml, { baseUrl: this._kmlBaseUrl });
        }
        return emptyFeatureCollection();
    };

    dgKML.prototype.getStyle = function () {
        if (this._styleProxy == null) this._styleProxy = ns.createWktStyleProxy(this);
        return this._styleProxy;
    };

    dgKML.prototype.setCluster = function (value) {
        return ns.setItemCluster(this, value);
    };

    dgKML.prototype.getCluster = function () {
        return ns.getItemCluster(this);
    };

    dgKML.prototype.setClusterDistance = function (value) {
        return ns.setItemClusterDistance(this, value);
    };

    dgKML.prototype.getClusterDistance = function () {
        return ns.getItemClusterDistance(this);
    };

    dgKML.prototype.setMinClusterSize = function (value) {
        return ns.setItemMinClusterSize(this, value);
    };

    dgKML.prototype.getMinClusterSize = function () {
        return ns.getItemMinClusterSize(this);
    };

    dgKML.prototype.setClusterClickZoomToBBOX = function (value) {
        return ns.setItemClusterClickZoomToBBOX(this, value);
    };

    dgKML.prototype.getClusterClickZoomToBBOX = function () {
        return ns.getItemClusterClickZoomToBBOX(this);
    };

    dgKML.prototype.setLabelVisible = function (value) {
        if (typeof value != 'boolean') return this;
        this.labelVisible = value;
        ns.refreshItemData(this);
        return this;
    };

    dgKML.prototype.getShowInSelect = function () {
        return this._showInSelect;
    };

    dgKML.prototype.setShowInSelect = function (value) {
        if (typeof value != 'boolean') return this;
        this._showInSelect = value;
        return this;
    };

    dgKML.prototype.getClosestData = function (wktOrDgxy, counts) {
        var rows = getKmlWktRows(this);
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

    dgKML.prototype.setUpperZoomByBoundary = function (value, options) {
        this._setUpperZoomByBoundary = value !== false;
        this._upperZoomByBoundaryOptions = options || null;
        if (this._setUpperZoomByBoundary === true && this._easymap != null && typeof this._easymap._fitItemToBounds == 'function') {
            this._easymap._fitItemToBounds(this, this._upperZoomByBoundaryOptions);
        }
        return this;
    };

    dgKML.prototype.setExtrusion = function (value) {
        return ns.setItemExtrusion(this, value);
    };

    dgKML.prototype.setExtrusionHeight = function (value) {
        return ns.setItemExtrusionHeight(this, value);
    };

    dgKML.prototype.setExtrusionBase = function (value) {
        return ns.setItemExtrusionBase(this, value);
    };

    dgKML.prototype.setExtrusionColor = function (value) {
        return ns.setItemExtrusionColor(this, value);
    };

    dgKML.prototype.setExtrusionOpacity = function (value) {
        return ns.setItemExtrusionOpacity(this, value);
    };

    dgKML.prototype.enableCluster = function (distance, threshold, dgGStyle) {
        this._gMarkerEnabled = true;
        if (dgGStyle != null) {
            this._Style = dgGStyle;
            this._clusterStyleKind = 'dgGStyle';
        }
        this.setClusterDistance([distance, this.getClusterDistance()[1]]);
        this.setMinClusterSize(threshold || 2);
        return this.setCluster(true);
    };

    dgKML.prototype.setClusterEnable = function (distance, threshold, dgGStyle) {
        return this.enableCluster(distance, threshold, dgGStyle);
    };

    dgKML.prototype.setZoomWithoutCluster = function (enabled, zoom) {
        if (typeof enabled != 'boolean') return this;
        this._isZoomClusterEnabled = enabled;
        this._clusterMaxZoom = parseInt(zoom, 10);
        if (isNaN(this._clusterMaxZoom)) this._clusterMaxZoom = 17;
        ns.refreshItemLayers(this);
        return this;
    };

    ns.parseKmlToGeoJSON = parseKmlToGeoJSON;
    window.dgKML = dgKML;
    window.dgKml = dgKML;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgKML');
})(window);
