(function (window, document) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function clone(value) {
        if (value == null) return value;
        return JSON.parse(JSON.stringify(value));
    }

    function extend(target, source) {
        target = target || {};
        source = source || {};
        for (var key in source) {
            if (Object.prototype.hasOwnProperty.call(source, key)) {
                target[key] = source[key];
            }
        }
        return target;
    }

    function toLngLat(input) {
        if (input == null) return null;
        if (Array.isArray(input)) return [parseFloat(input[0]), parseFloat(input[1])];
        if (input.xy != null) return [parseFloat(input.xy[0]), parseFloat(input.xy[1])];
        if (input.x != null && input.y != null) return [parseFloat(input.x), parseFloat(input.y)];
        if (input.lng != null && input.lat != null) return [parseFloat(input.lng), parseFloat(input.lat)];
        if (input.lon != null && input.lat != null) return [parseFloat(input.lon), parseFloat(input.lat)];
        return null;
    }

    function extendBounds(bounds, coordinate) {
        if (!Array.isArray(coordinate) || coordinate.length < 2) return bounds;
        var lng = parseFloat(coordinate[0]);
        var lat = parseFloat(coordinate[1]);
        if (isNaN(lng) || isNaN(lat)) return bounds;
        if (bounds == null) return [lng, lat, lng, lat];
        if (lng < bounds[0]) bounds[0] = lng;
        if (lat < bounds[1]) bounds[1] = lat;
        if (lng > bounds[2]) bounds[2] = lng;
        if (lat > bounds[3]) bounds[3] = lat;
        return bounds;
    }

    function extendBoundsFromCoordinates(bounds, coordinates) {
        if (!Array.isArray(coordinates)) return bounds;
        if (coordinates.length >= 2 && typeof coordinates[0] == 'number' && typeof coordinates[1] == 'number') {
            return extendBounds(bounds, coordinates);
        }
        for (var i = 0; i < coordinates.length; i++) {
            bounds = extendBoundsFromCoordinates(bounds, coordinates[i]);
        }
        return bounds;
    }

    function getGeoJsonBounds(geojson) {
        var bounds = null;
        if (geojson == null) return null;
        var features = geojson.type == 'FeatureCollection' ? geojson.features : [geojson];
        if (!Array.isArray(features)) return null;
        for (var i = 0; i < features.length; i++) {
            var feature = features[i];
            var geometry = feature != null && feature.type == 'Feature' ? feature.geometry : feature;
            if (geometry == null) continue;
            if (geometry.type == 'GeometryCollection' && Array.isArray(geometry.geometries)) {
                for (var j = 0; j < geometry.geometries.length; j++) {
                    bounds = extendBoundsFromCoordinates(bounds, geometry.geometries[j].coordinates);
                }
                continue;
            }
            bounds = extendBoundsFromCoordinates(bounds, geometry.coordinates);
        }
        return bounds;
    }

    function toDgXY(coordinate) {
        if (!Array.isArray(coordinate) || coordinate.length < 2) return null;
        return new window.dgXY(parseFloat(coordinate[0]), parseFloat(coordinate[1]));
    }

    function toDgGeometry(coordinates) {
        if (!Array.isArray(coordinates)) return coordinates;
        if (coordinates.length >= 2 && typeof coordinates[0] == 'number' && typeof coordinates[1] == 'number') {
            return toDgXY(coordinates);
        }
        var list = [];
        for (var i = 0; i < coordinates.length; i++) {
            list.push(toDgGeometry(coordinates[i]));
        }
        return list;
    }

    function getFirstCoordinateFromGeometry(geometry) {
        if (geometry == null) return null;
        if (geometry.type == 'GeometryCollection' && Array.isArray(geometry.geometries) && geometry.geometries.length > 0) {
            return getFirstCoordinateFromGeometry(geometry.geometries[0]);
        }
        var coordinates = geometry.coordinates;
        while (Array.isArray(coordinates) && coordinates.length > 0 && Array.isArray(coordinates[0])) {
            coordinates = coordinates[0];
        }
        return Array.isArray(coordinates) && coordinates.length >= 2 ? coordinates : null;
    }

    function renderFeaturePopup(properties) {
        var title = '';
        var html = '';
        properties = properties || {};
        if (properties.name != null) title = properties.name;
        if (properties.description == null) {
            for (var name in properties) {
                if (!name) continue;
                var lower = String(name).toLowerCase();
                if (lower == 'geometry' || lower == 'styleurl' || lower.indexOf('__easymap_') === 0) continue;
                var value = properties[name];
                if (typeof value == 'undefined') continue;
                html += '<tr><td>' + name + '</td><td>' + value + '</td></tr>';
            }
            if (html.length > 0) html = "<table class='popup-table easymap-popup-table' border='1'>" + html + '</table>';
        } else {
            html = '' + properties.description + '';
        }
        return {
            title: title,
            html: html
        };
    }

    function clamp(value, min, max) {
        value = parseFloat(value);
        if (isNaN(value)) value = 0;
        return Math.max(min, Math.min(max, value));
    }

    function dataDriven(property, fallback) {
        return ['coalesce', ['get', property], fallback];
    }

    function dataDrivenLiteral(property, fallback) {
        return ['coalesce', ['get', property], ['literal', fallback]];
    }

    function getStyleSetting(styleSetting, key) {
        if (styleSetting == null || key == null) return {};
        if (styleSetting[key] != null) return styleSetting[key];
        var lower = String(key).toLowerCase();
        for (var name in styleSetting) {
            if (Object.prototype.hasOwnProperty.call(styleSetting, name) && String(name).toLowerCase() == lower) {
                return styleSetting[name] || {};
            }
        }
        return {};
    }

    function setFeatureNumber(properties, key, value, fallback) {
        if (value == null) return;
        properties[key] = ns.toNumber(value, fallback);
    }

    function setFeatureColor(properties, colorKey, opacityKey, value) {
        if (value == null) return;
        var parsed = ns.parseColor(value, value);
        properties[colorKey] = parsed.color;
        if (opacityKey != null && parsed.opacity != null) properties[opacityKey] = parsed.opacity;
    }

    function setPrivateTextStyle(properties, textStyle) {
        if (textStyle == null) return;
        var fontSize = ns.parseFontSize(textStyle.font, null);
        var size = ns.toNumber(
            textStyle['font-size'] != null ? textStyle['font-size'] : (textStyle.fontSize != null ? textStyle.fontSize : (textStyle.size != null ? textStyle.size : fontSize)),
            fontSize
        );
        if (size != null) properties.__easymap_text_size = size;
        setFeatureColor(properties, '__easymap_text_color', '__easymap_text_opacity', textStyle['font-color'] != null ? textStyle['font-color'] : textStyle.color);
        setFeatureColor(properties, '__easymap_text_halo_color', null, textStyle['font-stroke-color'] != null ? textStyle['font-stroke-color'] : textStyle.haloColor);
        setFeatureNumber(properties, '__easymap_text_halo_width', textStyle['font-stroke-width'] != null ? textStyle['font-stroke-width'] : textStyle.haloWidth, 1.5);
        setFeatureColor(properties, '__easymap_text_background_color', '__easymap_text_background_opacity', textStyle['background-color'] != null ? textStyle['background-color'] : textStyle.backgroundColor);
        if (Array.isArray(textStyle.offset)) {
            properties.__easymap_text_offset = textStyle.offset.slice();
        }
        else {
            var offset = ns.offsetFromPixels(textStyle.offsetX, textStyle.offsetY, size != null ? size : 13, null);
            if (offset != null) properties.__easymap_text_offset = offset;
        }
        if (textStyle.anchor != null) properties.__easymap_text_anchor = ns.normalizeAnchor(textStyle.anchor);
    }

    function setPrivatePointStyle(properties, pointStyle) {
        if (pointStyle == null) return;
        setFeatureNumber(properties, '__easymap_point_radius', pointStyle.radius, 5);
        setFeatureColor(properties, '__easymap_point_stroke_color', '__easymap_point_stroke_opacity', pointStyle.color != null ? pointStyle.color : pointStyle['stroke-color']);
        setFeatureColor(properties, '__easymap_point_color', '__easymap_point_opacity', pointStyle['fill-color'] != null ? pointStyle['fill-color'] : pointStyle.fillColor);
        setFeatureNumber(properties, '__easymap_point_stroke_width', pointStyle.width != null ? pointStyle.width : pointStyle['stroke-width'], 1);
        setFeatureNumber(properties, '__easymap_point_opacity', pointStyle.opacity, 1);
    }

    function setPrivateLineStyle(properties, lineStyle) {
        if (lineStyle == null) return;
        setFeatureNumber(properties, '__easymap_line_width', lineStyle.width, 1);
        setFeatureColor(properties, '__easymap_line_color', '__easymap_line_opacity', lineStyle['stroke-color'] != null ? lineStyle['stroke-color'] : lineStyle.color);
        if (Array.isArray(lineStyle.linedash)) properties.__easymap_line_dash = lineStyle.linedash.slice();
        if (lineStyle.linecap != null) properties.__easymap_line_cap = lineStyle.linecap;
    }

    function setPrivatePolygonStyle(properties, polygonStyle) {
        if (polygonStyle == null) return;
        setFeatureNumber(properties, '__easymap_polygon_stroke_width', polygonStyle.width, 3);
        setFeatureColor(properties, '__easymap_polygon_stroke_color', '__easymap_polygon_stroke_opacity', polygonStyle['stroke-color'] != null ? polygonStyle['stroke-color'] : polygonStyle.color);
        setFeatureColor(properties, '__easymap_polygon_fill_color', '__easymap_polygon_fill_opacity', polygonStyle['fill-color'] != null ? polygonStyle['fill-color'] : polygonStyle.fillColor);
        if (Array.isArray(polygonStyle.linedash)) properties.__easymap_polygon_dash = polygonStyle.linedash.slice();
        if (polygonStyle.linecap != null) properties.__easymap_polygon_cap = polygonStyle.linecap;
    }

    function getOutlinePaint(style) {
        var paint = {
            'line-color': dataDriven('__easymap_polygon_stroke_color', style.strokeColor),
            'line-width': dataDriven('__easymap_polygon_stroke_width', style.strokeWidth),
            'line-opacity': dataDriven('__easymap_polygon_stroke_opacity', style.strokeOpacity)
        };
        if (style.lineDash != null) paint['line-dasharray'] = style.lineDash;
        return paint;
    }

    function getLinePaint(style) {
        var paint = {
            'line-color': dataDriven('__easymap_line_color', style.lineColor),
            'line-width': dataDriven('__easymap_line_width', style.lineWidth),
            'line-opacity': dataDriven('__easymap_line_opacity', style.lineOpacity)
        };
        if (style.lineLineDash != null) paint['line-dasharray'] = style.lineLineDash;
        return paint;
    }

    function getCirclePaint(style) {
        return {
            'circle-radius': dataDriven('__easymap_point_radius', style.pointRadius),
            'circle-color': dataDriven('__easymap_point_color', style.pointColor),
            'circle-opacity': dataDriven('__easymap_point_opacity', style.pointOpacity),
            'circle-stroke-color': dataDriven('__easymap_point_stroke_color', style.pointStrokeColor),
            'circle-stroke-opacity': dataDriven('__easymap_point_stroke_opacity', style.pointStrokeOpacity),
            'circle-stroke-width': dataDriven('__easymap_point_stroke_width', style.pointStrokeWidth)
        };
    }

    var CAMERA_CONTEXT_MENU_DRAG_TOLERANCE_SQ = 16;
    var BASEMAP_SOURCE_ID = 'easymap-maplibre-basemap-source';
    var BASEMAP_LAYER_ID = 'easymap-maplibre-basemap-layer';
    var FALLBACK_BASE_MAPS = [
        {
            type: 'XYZ',
            name: 'OSM',
            chname: 'OpenStreetMap',
            url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            attribution: 'OpenStreetMap'
        },
        {
            type: 'GOOGLE',
            name: 'google',
            chname: '谷歌街道圖',
            url: 'https://mts1.google.com/vt?hl=zh-TW&gl=TW&lyrs=m&x=${x}&y=${y}&z=${z}',
            attribution: 'Google'
        },
        {
            type: 'WMTS',
            name: 'EMAP5',
            chname: '臺灣通用電子地圖',
            url: 'https://wmts.nlsc.gov.tw/wmts',
            layer: 'EMAP',
            matrixSet: 'EPSG:3857',
            format: 'image/png'
        },
        {
            type: 'WMTS',
            name: 'EMAP_2',
            chname: '通用版電子地圖透明',
            url: 'https://maps.nlsc.gov.tw/S_Maps/wmts',
            layer: 'EMAP2',
            matrixSet: 'EPSG:3857',
            format: 'image/png'
        },
        {
            type: 'WMTS',
            name: 'PHOTO2',
            chname: '臺灣通用電子地圖正射影像',
            url: 'https://wmts.nlsc.gov.tw/wmts',
            layer: 'PHOTO2',
            matrixSet: 'EPSG:3857',
            format: 'image/png'
        }
    ];

    function normalizeBearing(value) {
        value = parseFloat(value);
        if (isNaN(value)) value = 0;
        value = value % 360;
        if (value < 0) value += 360;
        return value;
    }

    function normalizeCameraControlOptions(options) {
        options = options || {};
        return {
            enabled: options.enabled !== false,
            button: options.button || 'both',
            pitchSpeed: ns.toNumber(options.pitchSpeed, 0.25),
            bearingSpeed: ns.toNumber(options.bearingSpeed, 0.3),
            minPitch: ns.toNumber(options.minPitch, 0),
            maxPitch: ns.toNumber(options.maxPitch, 85)
        };
    }

    function cameraButtonAllowed(config, button) {
        var value = config.button;
        if (Array.isArray(value)) {
            for (var i = 0; i < value.length; i++) {
                if (cameraButtonAllowed({ button: value[i] }, button)) return true;
            }
            return false;
        }
        value = String(value || 'both').toLowerCase();
        if (value == 'both' || value == 'all') return button == 1 || button == 2;
        if (value == 'middle') return button == 1;
        if (value == 'right') return button == 2;
        return false;
    }

    function makeId(prefix) {
        Easymap._nextId++;
        return 'easymap-maplibre-' + prefix + '-' + Easymap._nextId;
    }

    function makeFallbackIconImage() {
        var width = 20;
        var height = 28;
        var DataArray = typeof Uint8ClampedArray == 'function' ? Uint8ClampedArray : Uint8Array;
        var data = new DataArray(width * height * 4);
        var cx = 10;
        var cy = 9;
        var radius = 7;
        for (var y = 0; y < height; y++) {
            for (var x = 0; x < width; x++) {
                var dx = x - cx;
                var dy = y - cy;
                var inCircle = dx * dx + dy * dy <= radius * radius;
                var tailHalf = Math.max(0, 6 - Math.abs(y - 15));
                var inTail = y >= 10 && y <= 24 && Math.abs(x - cx) <= tailHalf / 2;
                if (!inCircle && !inTail) continue;
                var edge = dx * dx + dy * dy >= (radius - 1) * (radius - 1) || (inTail && (Math.abs(x - cx) >= tailHalf / 2 - 0.75 || y >= 23));
                var index = (y * width + x) * 4;
                data[index] = edge ? 255 : 37;
                data[index + 1] = edge ? 255 : 99;
                data[index + 2] = edge ? 255 : 235;
                data[index + 3] = 255;
            }
        }
        return {
            width: width,
            height: height,
            data: data
        };
    }

    function replaceMapImage(map, imageId, image) {
        if (map == null || image == null) return;
        try {
            if (map.hasImage != null && map.hasImage(imageId)) {
                map.removeImage(imageId);
            }
            map.addImage(imageId, image);
            if (typeof map.triggerRepaint == 'function') map.triggerRepaint();
        } catch (ignore) { }
    }

    function loadImageElement(map, imageId, src) {
        if (typeof window.Image != 'function') return;
        var image = new window.Image();
        image.crossOrigin = 'anonymous';
        image.onload = function () {
            replaceMapImage(map, imageId, image);
        };
        image.onerror = function () { };
        image.src = src;
    }

    function resolveDefaultFlag(options, defaults, key, fallback) {
        if (options != null && options[key] != null) return options[key] !== false;
        if (defaults != null && defaults[key] != null) return defaults[key] !== false;
        return fallback !== false;
    }

    function normalizeLegacyBool(value, fallback) {
        if (value == null) return fallback !== false;
        if (typeof value == 'boolean') return value;
        value = String(value).toLowerCase();
        if (value == 'true' || value == '1' || value == 'yes' || value == 'on') return true;
        if (value == 'false' || value == '0' || value == 'no' || value == 'off') return false;
        return fallback !== false;
    }

    function isTextItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'text' || type == 'dgtext';
    }

    function isPointItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'point' || type == 'dgpoint';
    }

    function isPolylineItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'polyline' || type == 'dgpolyline';
    }

    function isPolygonItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'polygon' || type == 'dgpolygon';
    }

    function isCurveItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'curve' || type == 'dgcurve';
    }

    function isStaticImageItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'dgstaticimage' || type == 'staticimage';
    }

    function isGroundOverlayQuadItem(item) {
        var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
        return type == 'dggroundoverlayquad' || type == 'groundoverlayquad';
    }

    function normalizeQuadCoordinate(coordinate) {
        if (!Array.isArray(coordinate) || coordinate.length < 2) return null;
        var lng = parseFloat(coordinate[0]);
        var lat = parseFloat(coordinate[1]);
        if (!isFinite(lng) || !isFinite(lat)) return null;
        return [lng, lat];
    }

    function parseGroundOverlayQuadWktFallback(wktString) {
        var text = String(wktString || '').trim();
        var match = text.match(/^POLYGON\s*\(\(([\s\S]*)\)\)\s*$/i);
        if (match == null) return null;
        var parts = match[1].split(',');
        var ring = [];
        for (var i = 0; i < parts.length; i++) {
            var pair = parts[i].trim().split(/\s+/);
            ring.push([pair[0], pair[1]]);
        }
        return ring;
    }

    function getGroundOverlayQuadCoordinatesFromWkt(wktString) {
        var geometry = null;
        if (ns != null && typeof ns.parseWktGeometry == 'function') {
            geometry = ns.parseWktGeometry(wktString);
        }

        var ring = null;
        if (geometry != null && geometry.type == 'Polygon' && Array.isArray(geometry.coordinates)) {
            ring = geometry.coordinates[0];
        }
        else if (geometry != null && geometry.type == 'MultiPolygon' && Array.isArray(geometry.coordinates)) {
            ring = geometry.coordinates[0] != null ? geometry.coordinates[0][0] : null;
        }
        if (ring == null) ring = parseGroundOverlayQuadWktFallback(wktString);
        if (!Array.isArray(ring) || ring.length < 4) return null;

        var coordinates = [];
        for (var i = 0; i < ring.length && coordinates.length < 4; i++) {
            var coordinate = normalizeQuadCoordinate(ring[i]);
            if (coordinate == null) return null;
            coordinates.push(coordinate);
        }
        return coordinates.length == 4 ? coordinates : null;
    }

    var STATIC_IMAGE_TRANSPARENT_PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=';

    function isSvgStaticImageUrl(url) {
        url = String(url || '');
        return /^data:image\/svg\+xml/i.test(url) || /\.svg(?:$|[?#])/i.test(url);
    }

    function getWindowNumber(name) {
        if (window == null || window[name] == null || window[name] === '') return null;
        var value = parseFloat(window[name]);
        return isNaN(value) ? null : value;
    }

    function getWindowString(name) {
        if (window == null || window[name] == null || window[name] === '') return null;
        return String(window[name]);
    }

    function getLegacyMapIniCenter() {
        var x = getWindowNumber('cx');
        var y = getWindowNumber('cy');
        if (x == null || y == null) return null;
        return [x, y];
    }

    function getSourceOptions(source) {
        if (source == null) return {};
        return source._options || source.options || source;
    }

    function getSourceType(source) {
        var options = getSourceOptions(source);
        return String(source && (source._layerType || source._sourceType) || options.layerType || options.sourceType || options.type || 'XYZ');
    }

    function getSourceName(source) {
        var options = getSourceOptions(source);
        return options.name || (source != null ? source._id || source.id : null);
    }

    function appendUrlParams(url, params) {
        var parts = [];
        for (var i = 0; i < params.length; i++) {
            if (params[i][1] == null || params[i][1] === '') continue;
            parts.push(params[i][0] + '=' + params[i][1]);
        }
        if (parts.length == 0) return url;
        return url + (url.indexOf('?') >= 0 ? '&' : '?') + parts.join('&');
    }

    function hasAjaxPostData(post) {
        return !(post == null || typeof post == 'undefined' || post === '');
    }

    function encodeAjaxPostData(post) {
        if (post == null || typeof post == 'undefined') return null;
        if (typeof post == 'string') return post;
        if (typeof post == 'object') {
            var pairs = [];
            for (var name in post) {
                if (Object.prototype.hasOwnProperty.call(post, name) == false) continue;
                pairs.push(encodeURIComponent(name) + '=' + encodeURIComponent(post[name] == null ? '' : post[name]));
            }
            return pairs.join('&');
        }
        return String(post);
    }

    function createAjaxRequest() {
        if (window != null && typeof window.XMLHttpRequest == 'function') return new window.XMLHttpRequest();
        if (typeof XMLHttpRequest == 'function') return new XMLHttpRequest();
        return null;
    }

    function callAjaxFailure(failFunc, xhr, error) {
        if (typeof failFunc == 'function') failFunc(xhr, error);
    }

    function sendAjaxRequest(url, post, successFunc, failFunc, options) {
        var xhr = createAjaxRequest();
        if (xhr == null) {
            callAjaxFailure(failFunc, null, new Error('XMLHttpRequest is unavailable'));
            return null;
        }
        var method = hasAjaxPostData(post) ? 'POST' : 'GET';
        var postData = method == 'POST' ? encodeAjaxPostData(post) : null;
        try {
            xhr.open(method, url, true);
        } catch (err) {
            callAjaxFailure(failFunc, xhr, err);
            return xhr;
        }
        if (method == 'POST' && typeof xhr.setRequestHeader == 'function') {
            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        }
        if (options != null && options.accept != null && typeof xhr.setRequestHeader == 'function') {
            xhr.setRequestHeader('Accept', options.accept);
        }
        xhr.onerror = function (event) {
            callAjaxFailure(failFunc, xhr, event);
        };
        xhr.onload = function (event) {
            if (!xhr.status || (xhr.status >= 200 && xhr.status < 300)) {
                if (typeof successFunc == 'function') successFunc(xhr.responseText, xhr);
            }
            else {
                callAjaxFailure(failFunc, xhr, event);
            }
        };
        try {
            xhr.send(postData);
        } catch (err2) {
            callAjaxFailure(failFunc, xhr, err2);
        }
        return xhr;
    }

    function encodedParam(value) {
        return encodeURIComponent(String(value));
    }

    function normalizeTileUrl(url) {
        if (url == null) return url;
        return String(url).replace(/\$\{([^}]+)\}/g, '{$1}');
    }

    function toMapLibreSourceRecord(source) {
        var options = clone(getSourceOptions(source)) || {};
        var type = getSourceType(source);
        var name = getSourceName(source) || options.layer || type;
        options.name = name;
        options.type = type;
        return {
            _id: name,
            _type: 'dgsource',
            _sourceType: type,
            _layerType: type,
            _options: options,
            options: options
        };
    }

    function formatCoordinate(value) {
        value = parseFloat(value);
        if (isNaN(value)) value = 0;
        return value.toFixed(6);
    }

    function formatDistance(meters) {
        meters = parseFloat(meters);
        if (isNaN(meters) || meters <= 0) meters = 1;
        if (meters >= 1000) {
            var km = meters / 1000;
            return (km >= 10 ? Math.round(km).toString() : km.toFixed(1).replace(/\.0$/, '')) + ' km';
        }
        return Math.round(meters).toString() + ' m';
    }

    function formatDrawLength(meters) {
        meters = parseFloat(meters);
        if (isNaN(meters) || meters < 0) meters = 0;
        if (meters >= 1000) return (meters / 1000.0).toFixed(2) + ' 公里';
        return meters.toFixed(3) + ' 公尺';
    }

    function formatDrawArea(squareMeters) {
        squareMeters = parseFloat(squareMeters);
        if (isNaN(squareMeters) || squareMeters < 0) squareMeters = 0;
        if (squareMeters >= 10000) return (Math.round((squareMeters / 1000000.0) * 100) / 100.0).toFixed(2) + ' 平方公里';
        return squareMeters.toFixed(3) + ' 平方公尺';
    }

    function niceDistance(value) {
        value = parseFloat(value);
        if (isNaN(value) || value <= 0) return 1;
        var exponent = Math.floor(Math.log(value) / Math.LN10);
        var base = Math.pow(10, exponent);
        var normalized = value / base;
        var nice = normalized >= 5 ? 5 : (normalized >= 2 ? 2 : 1);
        return nice * base;
    }

    function formatWktNumber(value) {
        value = parseFloat(value);
        if (isNaN(value)) value = 0;
        if (Math.abs(value) < 0.000000000001) value = 0;
        return parseFloat(value.toFixed(8)).toString();
    }

    function isHttpUrl(value) {
        return typeof value == 'string' && /^https?:\/\//i.test(value);
    }

    function isKmzUrl(value) {
        return typeof value == 'string' && /\.kmz(?:[?#].*)?$/i.test(value);
    }

    function coordinateEquals(a, b) {
        if (!Array.isArray(a) || !Array.isArray(b)) return false;
        return Math.abs(parseFloat(a[0]) - parseFloat(b[0])) < 0.0000000001 &&
            Math.abs(parseFloat(a[1]) - parseFloat(b[1])) < 0.0000000001;
    }

    function cloneCoordinates(coordinates) {
        if (!Array.isArray(coordinates)) return coordinates;
        var result = [];
        for (var i = 0; i < coordinates.length; i++) {
            result.push(Array.isArray(coordinates[i]) ? cloneCoordinates(coordinates[i]) : coordinates[i]);
        }
        return result;
    }

    function dgxyToCoordinate(dgxy) {
        var lngLat = toLngLat(dgxy);
        if (lngLat == null || isNaN(lngLat[0]) || isNaN(lngLat[1])) return null;
        return [lngLat[0], lngLat[1]];
    }

    function normalizeWktCoordinate(coordinate) {
        if (!Array.isArray(coordinate) || coordinate.length < 2) return null;
        var lng = parseFloat(coordinate[0]);
        var lat = parseFloat(coordinate[1]);
        if (isNaN(lng) || isNaN(lat)) return null;
        return [lng, lat];
    }

    function normalizeWktCoordinates(coordinates) {
        if (!Array.isArray(coordinates)) return null;
        var normalized = [];
        for (var i = 0; i < coordinates.length; i++) {
            var coordinate = normalizeWktCoordinate(coordinates[i]);
            if (coordinate == null) return null;
            normalized.push(coordinate);
        }
        return normalized;
    }

    function dgxyListToCoordinates(points) {
        var coordinates = [];
        for (var i = 0; i < points.length; i++) {
            var coordinate = dgxyToCoordinate(points[i]);
            if (coordinate != null) coordinates.push(coordinate);
        }
        return coordinates;
    }

    function trimTrailingDuplicateDgXY(points) {
        var result = Array.isArray(points) ? points.slice() : [];
        while (result.length >= 2) {
            var last = dgxyToCoordinate(result[result.length - 1]);
            var previous = dgxyToCoordinate(result[result.length - 2]);
            if (!coordinateEquals(last, previous)) break;
            result.pop();
        }
        return result;
    }

    function closeRing(coordinates) {
        var ring = cloneCoordinates(coordinates || []);
        if (ring.length > 0 && !coordinateEquals(ring[0], ring[ring.length - 1])) {
            ring.push([ring[0][0], ring[0][1]]);
        }
        return ring;
    }

    function coordinateToDgXY(coordinate) {
        return new window.dgXY(coordinate[0], coordinate[1]);
    }

    function coordinatesToDgXYList(coordinates) {
        var points = [];
        for (var i = 0; i < coordinates.length; i++) {
            points.push(coordinateToDgXY(coordinates[i]));
        }
        return points;
    }

    function haversineDistance(a, b) {
        if (!Array.isArray(a) || !Array.isArray(b)) return 0;
        var radius = 6371008.8;
        var lat1 = parseFloat(a[1]) * Math.PI / 180;
        var lat2 = parseFloat(b[1]) * Math.PI / 180;
        var dLat = (parseFloat(b[1]) - parseFloat(a[1])) * Math.PI / 180;
        var dLon = (parseFloat(b[0]) - parseFloat(a[0])) * Math.PI / 180;
        var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
        return radius * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
    }

    function measureLine(coordinates) {
        var total = 0;
        for (var i = 1; i < coordinates.length; i++) {
            total += haversineDistance(coordinates[i - 1], coordinates[i]);
        }
        return total;
    }

    function measurePolygonArea(ring) {
        if (!Array.isArray(ring) || ring.length < 4) return 0;
        var originLat = parseFloat(ring[0][1]) * Math.PI / 180;
        var metersPerDegreeLat = 111132;
        var metersPerDegreeLon = 111320 * Math.cos(originLat);
        var sum = 0;
        for (var i = 0; i < ring.length - 1; i++) {
            var x1 = parseFloat(ring[i][0]) * metersPerDegreeLon;
            var y1 = parseFloat(ring[i][1]) * metersPerDegreeLat;
            var x2 = parseFloat(ring[i + 1][0]) * metersPerDegreeLon;
            var y2 = parseFloat(ring[i + 1][1]) * metersPerDegreeLat;
            sum += x1 * y2 - x2 * y1;
        }
        return Math.abs(sum / 2);
    }

    function destinationPoint(center, distanceMeters, bearingRadians) {
        var radius = 6371008.8;
        var lon1 = parseFloat(center[0]) * Math.PI / 180;
        var lat1 = parseFloat(center[1]) * Math.PI / 180;
        var angular = distanceMeters / radius;
        var lat2 = Math.asin(Math.sin(lat1) * Math.cos(angular) +
            Math.cos(lat1) * Math.sin(angular) * Math.cos(bearingRadians));
        var lon2 = lon1 + Math.atan2(
            Math.sin(bearingRadians) * Math.sin(angular) * Math.cos(lat1),
            Math.cos(angular) - Math.sin(lat1) * Math.sin(lat2)
        );
        return [lon2 * 180 / Math.PI, lat2 * 180 / Math.PI];
    }

    function circleGeometryToPolygon(geometry) {
        var center = toLngLat(geometry.center);
        if (center == null) center = toLngLat(geometry.coordinates);
        if (center == null) return [[]];
        var radius = geometry.radiusMeters != null ? parseFloat(geometry.radiusMeters) : parseFloat(geometry.radius);
        if ((isNaN(radius) || radius <= 0) && geometry.end != null) {
            var end = toLngLat(geometry.end);
            if (end != null) radius = haversineDistance(center, end);
        }
        if (isNaN(radius) || radius <= 0) return [[]];
        var steps = parseInt(geometry.steps, 10);
        if (isNaN(steps) || steps < 16) steps = 64;
        var ring = [];
        for (var i = 0; i < steps; i++) {
            ring.push(destinationPoint(center, radius, Math.PI * 2 * i / steps));
        }
        ring.push([ring[0][0], ring[0][1]]);
        return [ring];
    }

    function formatWktCoordinate(coordinate) {
        coordinate = normalizeWktCoordinate(coordinate);
        if (coordinate == null) return null;
        return formatWktNumber(coordinate[0]) + ' ' + formatWktNumber(coordinate[1]);
    }

    function formatWktCoordinateList(coordinates, minimum) {
        coordinates = normalizeWktCoordinates(coordinates);
        if (coordinates == null || coordinates.length < minimum) return null;
        var output = [];
        for (var i = 0; i < coordinates.length; i++) {
            output.push(formatWktCoordinate(coordinates[i]));
        }
        return output.join(', ');
    }

    function formatWktRing(coordinates) {
        coordinates = normalizeWktCoordinates(coordinates);
        if (coordinates == null || coordinates.length < 3) return null;
        coordinates = closeRing(coordinates);
        if (coordinates.length < 4) return null;
        return '(' + formatWktCoordinateList(coordinates, 4) + ')';
    }

    function geometryToWktString(geometry) {
        if (geometry == null) return '';
        if (geometry.type == 'Feature' && geometry.geometry != null) geometry = geometry.geometry;
        if (geometry.type == 'Circle') {
            geometry = {
                type: 'Polygon',
                coordinates: circleGeometryToPolygon(geometry)
            };
        }
        if (geometry.type == 'Point') {
            var point = formatWktCoordinate(geometry.coordinates);
            return point == null ? '' : 'POINT(' + point + ')';
        }
        if (geometry.type == 'MultiPoint') {
            if (!Array.isArray(geometry.coordinates) || geometry.coordinates.length == 0) return '';
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
            if (!Array.isArray(geometry.coordinates) || geometry.coordinates.length == 0) return '';
            var lines = [];
            for (var j = 0; j < geometry.coordinates.length; j++) {
                var lineString = formatWktCoordinateList(geometry.coordinates[j], 2);
                if (lineString != null) lines.push('(' + lineString + ')');
            }
            return lines.length == 0 ? '' : 'MULTILINESTRING(' + lines.join(', ') + ')';
        }
        if (geometry.type == 'Polygon') {
            if (!Array.isArray(geometry.coordinates) || geometry.coordinates.length == 0) return '';
            var rings = [];
            for (var k = 0; k < geometry.coordinates.length; k++) {
                var ring = formatWktRing(geometry.coordinates[k]);
                if (ring != null) rings.push(ring);
            }
            return rings.length == 0 ? '' : 'POLYGON(' + rings.join(', ') + ')';
        }
        if (geometry.type == 'MultiPolygon') {
            if (!Array.isArray(geometry.coordinates) || geometry.coordinates.length == 0) return '';
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
        if (geometry.type == 'GeometryCollection' && Array.isArray(geometry.geometries)) {
            var geometries = [];
            for (var g = 0; g < geometry.geometries.length; g++) {
                var wkt = geometryToWktString(geometry.geometries[g]);
                if (wkt != '') geometries.push(wkt);
            }
            return geometries.length == 0 ? '' : 'GEOMETRYCOLLECTION(' + geometries.join(', ') + ')';
        }
        return '';
    }

    function geoJsonToWktArr(geojson) {
        if (geojson == null) return [];
        var features = geojson.type == 'FeatureCollection' ? geojson.features : [geojson];
        if (!Array.isArray(features)) return [];
        var output = [];
        for (var i = 0; i < features.length; i++) {
            var feature = features[i];
            var geometry = feature != null && feature.type == 'Feature' ? feature.geometry : feature;
            var wkt = geometryToWktString(geometry);
            if (wkt == '') continue;
            var row = {};
            var properties = feature != null && feature.type == 'Feature' && feature.properties != null ? feature.properties : {};
            for (var key in properties) {
                if (Object.prototype.hasOwnProperty.call(properties, key)) row[key] = clone(properties[key]);
            }
            row.wkt = wkt;
            output.push(row);
        }
        return output;
    }

    function sanitizeKmlText(kmlText) {
        kmlText = String(kmlText || '');
        kmlText = kmlText.replace(' xsi:schemaLocation="http://www.opengis.net/kml/2.2 http://schemas.opengis.net/kml/2.2.0/ogckml22.xsd http://www.google.com/kml/ext/2.2 http://code.google.com/apis/kml/schema/kml22gx.xsd"', '');
        kmlText = kmlText.replace(' xsi:schemaLocation=', ' easymap_xsi_schemaLocation=');
        return kmlText;
    }

    function createSvgElement(name) {
        if (window.document.createElementNS != null) {
            return window.document.createElementNS('http://www.w3.org/2000/svg', name);
        }
        return window.document.createElement(name);
    }

    function dgMenuFunc(label, callback, icon) {
        if (!(this instanceof dgMenuFunc)) return new dgMenuFunc(label, callback, icon);
        this.mname = label;
        this.label = label;
        this.name = label;
        this.afunc = callback;
        this.callback = callback;
        this.function = callback;
        this.icon = icon;
    }

    window.dgMenuFunc = window.dgMenuFunc || dgMenuFunc;

    function Easymap(targetId, options) {
        if (!(this instanceof Easymap)) return new Easymap(targetId, options);
        options = options || {};
        this._targetId = targetId;
        this._container = typeof targetId == 'string' ? document.getElementById(targetId) : targetId;
        this._options = options;
        this._engine = 'maplibre';
        this._items = {};
        this._defaultLayers = [];
        this._mname = null;
        this._baseMapSourceId = BASEMAP_SOURCE_ID;
        this._baseMapLayerId = BASEMAP_LAYER_ID;
        this._readyQueue = [];
        this._isReady = false;
        this._readyCheckTimer = null;
        this._readyCheckCount = 0;
        this._readyStartedAt = 0;
        this._readyReason = 'initial';
        this._popup = null;
        this._eventHandlers = [];
        this._imageUrls = {};
        this._itemAddOrder = 1;
        this._default3DCamera = null;
        this._cameraControlConfig = null;
        this._cameraControlHandlers = [];
        this._cameraDragState = null;
        this._suppressNextContextMenu = false;
        this._scaleLineControl = null;
        this._statusbarControl = null;
        this._builtinControlHandlers = [];
        this._statusbarCustomText = null;
        this._mousePosition = { lon: null, lat: null };
        this._scaleLineType = 'orin_style';
        this._customControler = null;
        this._mapControlButtons = null;
        this._eagleEyeControl = null;
        this._eagleEyeMap = null;
        this._eagleEyeHandlers = [];
        this._eagleEyeDomHandlers = [];
        this._eagleEyeDragState = null;
        this._eagleEyeSyncing = false;
        this._eagleEyeOptions = null;
        this._loadingControl = null;
        this._highlightLayer = null;
        this.dgCMenu = [];
        this._contextMenu = null;
        this._contextMenuHandlers = [];
        this._contextMenuLastEvent = null;
        this._dragBoxState = null;
        this._dragBoxHandlers = [];
        this._dragBoxOverlay = null;
        this._dragBoxPreviousCursor = '';
        this._dragBoxInteractionStates = null;
        this._drawState = null;
        this._drawHandlers = [];
        this._drawRenderHandlers = [];
        this._drawLayer = null;
        this._drawSvg = null;
        this._drawPath = null;
        this._drawTooltip = null;
        this._drawResult = null;
        this._drawMeasure = null;
        this._drawMessages = {
            start: '開始繪製',
            moving: '移動滑鼠繼續繪製'
        };
        this._drawPreviousCursor = '';
        this._drawInteractionStates = null;
        this._drawDblClickZoomWasEnabled = true;
        this._dblClickZoomEnabled = true;
        this._dragRotateEnabled = false;
        this._mobileDragRotateEnabled = false;
        this._initLegacyControlContracts();
        this._initMap();
    }

    Easymap._nextId = 0;

    Easymap.prototype = {
        _normalizeMapLibreBaseMaps: function (input) {
            var list = [];
            var appendInput = function (raw) {
                if (raw == null) return;
                if (Array.isArray(raw)) {
                    for (var i = 0; i < raw.length; i++) {
                        appendInput(raw[i]);
                    }
                    return;
                }
                if (typeof raw == 'object' && getSourceName(raw) == null && raw.url == null && raw.tiles == null && raw.layer == null && raw.type == null && raw._sourceType == null && raw._layerType == null) {
                    for (var key in raw) {
                        if (Object.prototype.hasOwnProperty.call(raw, key) == false || raw[key] == null) continue;
                        var item = raw[key];
                        var options = getSourceOptions(item);
                        if (getSourceName(item) == null && options.name == null && typeof item == 'object') {
                            item = clone(item);
                            item.name = key;
                        }
                        list.push(item);
                    }
                    return;
                }
                list.push(raw);
            };
            appendInput(input);
            if (list.length == 0) list = FALLBACK_BASE_MAPS;

            var records = [];
            var seen = {};
            for (var i = 0; i < list.length; i++) {
                var record = toMapLibreSourceRecord(list[i]);
                var name = getSourceName(record);
                var keyName = name != null ? String(name).toLowerCase() : '';
                if (keyName !== '' && seen[keyName] === true) continue;
                if (keyName !== '') seen[keyName] = true;
                records.push(record);
            }
            return records;
        },

        _getBaseMapDefinition: function (name) {
            if (name == null) return null;
            var target = String(name);
            for (var i = 0; i < this._defaultLayers.length; i++) {
                var recordName = getSourceName(this._defaultLayers[i]);
                if (recordName == target) return this._defaultLayers[i];
            }
            var lower = target.toLowerCase();
            for (var j = 0; j < this._defaultLayers.length; j++) {
                var candidateName = getSourceName(this._defaultLayers[j]);
                if (candidateName != null && String(candidateName).toLowerCase() == lower) return this._defaultLayers[j];
            }
            return null;
        },

        _buildWmtsTileUrl: function (options) {
            var url = options.url;
            if (Array.isArray(url)) url = url[0];
            if (url == null || url === '') return null;
            if (url.indexOf('{x}') >= 0 && url.indexOf('{y}') >= 0 && url.indexOf('{z}') >= 0) return url;

            var layer = options.layer || options.name;
            if (layer == null || layer === '') return null;
            var matrixSet = options.matrixSet || 'EPSG:3857';
            var format = options.format || 'image/png';
            var style = options.style;
            if (style == null || style === '') style = 'default';

            var params = [
                ['SERVICE', 'WMTS'],
                ['REQUEST', 'GetTile'],
                ['VERSION', encodedParam(options.version || '1.0.0')],
                ['LAYER', encodedParam(layer)],
                ['STYLE', encodedParam(style)],
                ['TILEMATRIXSET', encodedParam(matrixSet)],
                ['FORMAT', encodedParam(format)],
                ['TILEMATRIX', '{z}'],
                ['TILEROW', '{y}'],
                ['TILECOL', '{x}']
            ];
            if (options.transparent != null) params.push(['TRANSPARENT', encodedParam(options.transparent === true ? 'true' : options.transparent)]);
            return appendUrlParams(url, params);
        },

        _buildRasterSourceSpec: function (source) {
            var options = getSourceOptions(source);
            var sourceType = getSourceType(source).toLowerCase();
            var tiles = options.tiles;
            if (tiles == null && sourceType == 'wmts') {
                var wmtsUrl = this._buildWmtsTileUrl(options);
                if (wmtsUrl != null) tiles = [wmtsUrl];
            }
            if (tiles == null && options.url != null) {
                tiles = Array.isArray(options.url) ? options.url.slice() : [options.url];
            }
            if (tiles == null || tiles.length == 0) return null;
            for (var i = 0; i < tiles.length; i++) {
                tiles[i] = normalizeTileUrl(tiles[i]);
            }
            return {
                type: 'raster',
                tiles: tiles,
                tileSize: options.tileSize || 256,
                attribution: options.attribution || options.attributions || ''
            };
        },

        _isBaseMapLayer: function (layer, style) {
            if (layer == null) return false;
            if (layer.id == BASEMAP_LAYER_ID || layer.id == 'osm') return true;
            if (layer.metadata != null && (layer.metadata.easymapBaseMap === true || layer.metadata['easymap:basemap'] === true)) return true;
            var source = layer.source != null && style != null && style.sources != null ? style.sources[layer.source] : null;
            if (source != null && source.metadata != null && (source.metadata.easymapBaseMap === true || source.metadata['easymap:basemap'] === true)) return true;
            return false;
        },

        _isBaseMapSource: function (sourceId, source) {
            if (sourceId == BASEMAP_SOURCE_ID || sourceId == 'osm') return true;
            return source != null && source.metadata != null && (source.metadata.easymapBaseMap === true || source.metadata['easymap:basemap'] === true);
        },

        _isSourceInUse: function (mapObject, sourceId) {
            var style = mapObject != null && typeof mapObject.getStyle == 'function' ? mapObject.getStyle() : null;
            var layers = style != null && Array.isArray(style.layers) ? style.layers : [];
            for (var i = 0; i < layers.length; i++) {
                if (layers[i].source == sourceId) return true;
            }
            return false;
        },

        _removeMapLayerIfExists: function (mapObject, layerId) {
            if (mapObject != null && layerId != null && typeof mapObject.getLayer == 'function' && typeof mapObject.removeLayer == 'function' && mapObject.getLayer(layerId) != null) {
                mapObject.removeLayer(layerId);
            }
        },

        _removeMapSourceIfUnused: function (mapObject, sourceId) {
            if (mapObject != null && sourceId != null && typeof mapObject.getSource == 'function' && typeof mapObject.removeSource == 'function' && mapObject.getSource(sourceId) != null && this._isSourceInUse(mapObject, sourceId) !== true) {
                mapObject.removeSource(sourceId);
            }
        },

        _removeCurrentBaseMap: function (mapObject) {
            if (mapObject == null || typeof mapObject.getStyle != 'function') return;
            var style = mapObject.getStyle();
            var layers = style != null && Array.isArray(style.layers) ? style.layers.slice() : [];
            for (var i = layers.length - 1; i >= 0; i--) {
                if (this._isBaseMapLayer(layers[i], style)) {
                    this._removeMapLayerIfExists(mapObject, layers[i].id);
                }
            }
            var sources = style != null && style.sources != null ? style.sources : {};
            for (var sourceId in sources) {
                if (Object.prototype.hasOwnProperty.call(sources, sourceId) && this._isBaseMapSource(sourceId, sources[sourceId])) {
                    this._removeMapSourceIfUnused(mapObject, sourceId);
                }
            }
        },

        _getFirstOverlayLayerId: function (mapObject) {
            var style = mapObject != null && typeof mapObject.getStyle == 'function' ? mapObject.getStyle() : null;
            var layers = style != null && Array.isArray(style.layers) ? style.layers : [];
            for (var i = 0; i < layers.length; i++) {
                if (this._isBaseMapLayer(layers[i], style) !== true) return layers[i].id;
            }
            return null;
        },

        _applyBaseMapDefinition: function (mapObject, source) {
            if (mapObject == null || typeof mapObject.addSource != 'function' || typeof mapObject.addLayer != 'function') return false;
            var rasterSource = this._buildRasterSourceSpec(source);
            if (rasterSource == null) return false;
            var options = getSourceOptions(source);
            var layer = {
                id: BASEMAP_LAYER_ID,
                type: 'raster',
                source: BASEMAP_SOURCE_ID,
                metadata: {
                    easymapBaseMap: true
                },
                paint: {
                    'raster-opacity': options.opacity != null ? options.opacity : 1
                }
            };
            rasterSource.metadata = rasterSource.metadata || {};
            rasterSource.metadata.easymapBaseMap = true;
            this._removeCurrentBaseMap(mapObject);
            mapObject.addSource(BASEMAP_SOURCE_ID, rasterSource);
            var beforeId = this._getFirstOverlayLayerId(mapObject);
            if (beforeId != null) mapObject.addLayer(layer, beforeId);
            else mapObject.addLayer(layer);
            return true;
        },

        _buildInitialBaseMapStyle: function (style, source) {
            var rasterSource = this._buildRasterSourceSpec(source);
            if (rasterSource == null) return style;
            style = clone(style) || { version: 8, sources: {}, layers: [] };
            style.sources = style.sources || {};
            style.layers = Array.isArray(style.layers) ? style.layers : [];

            var layers = [];
            for (var i = 0; i < style.layers.length; i++) {
                if (this._isBaseMapLayer(style.layers[i], style) !== true) layers.push(style.layers[i]);
            }
            style.layers = layers;

            for (var sourceId in style.sources) {
                if (Object.prototype.hasOwnProperty.call(style.sources, sourceId) && this._isBaseMapSource(sourceId, style.sources[sourceId])) {
                    delete style.sources[sourceId];
                }
            }

            rasterSource.metadata = rasterSource.metadata || {};
            rasterSource.metadata.easymapBaseMap = true;
            style.sources[BASEMAP_SOURCE_ID] = rasterSource;
            style.layers.unshift({
                id: BASEMAP_LAYER_ID,
                type: 'raster',
                source: BASEMAP_SOURCE_ID,
                metadata: {
                    easymapBaseMap: true
                },
                paint: {
                    'raster-opacity': getSourceOptions(source).opacity != null ? getSourceOptions(source).opacity : 1
                }
            });
            return style;
        },

        _initMap: function () {
            if (this._container == null) {
                throw new Error('Easymap MapLibre container not found: ' + this._targetId);
            }
            if (window.maplibregl == null) {
                throw new Error('Easymap MapLibre runtime needs window.maplibregl');
            }

            var defaults = window.EASYMAP_MAPLIBRE_DEFAULTS || {};
            var legacyCenter = getLegacyMapIniCenter();
            var legacyZoom = getWindowNumber('cz');
            var legacyMapName = getWindowString('_mname');
            var hasLegacyMapIni = legacyCenter != null || legacyZoom != null || legacyMapName != null;
            var center = this._options.center || legacyCenter || defaults.center || [120.64681, 24.180936];
            var zoom = this._options.zoom != null ? this._options.zoom : (legacyZoom != null ? legacyZoom : (defaults.zoom != null ? defaults.zoom : 7));
            var pitch = clamp(this._options.pitch != null ? this._options.pitch : (hasLegacyMapIni === true ? 0 : (defaults.pitch || 0)), 0, 85);
            var bearing = normalizeBearing(this._options.bearing != null ? this._options.bearing : (defaults.bearing || 0));
            var mapIniTypes = Array.isArray(window._dm4_maps) && window._dm4_maps.length > 0 ? window._dm4_maps : null;
            this._defaultLayers = this._normalizeMapLibreBaseMaps([this._options.mapTypes, mapIniTypes, defaults.mapTypes, FALLBACK_BASE_MAPS]);
            this._mname = this._options.mapType || legacyMapName || defaults.mapType || 'google';
            var style = clone(this._options.style || defaults.style);
            if (this._options.style == null) {
                style = this._buildInitialBaseMapStyle(style, this._getBaseMapDefinition(this._mname));
            }
            this._default3DCamera = {
                center: [parseFloat(center[0]), parseFloat(center[1])],
                zoom: parseFloat(zoom),
                pitch: pitch,
                bearing: bearing
            };

            if (this._container.className.indexOf('easymap-maplibre-root') == -1) {
                this._container.className += ' easymap-maplibre-root';
            }
            this._container.setAttribute('data-easymap-drag-rotate', '0');
            this._container.setAttribute('data-easymap-mobile-drag-rotate', '0');

            this._readyStartedAt = Date.now();
            this._map = new maplibregl.Map({
                container: this._container,
                style: style,
                center: center,
                zoom: zoom,
                pitch: pitch,
                bearing: bearing,
                attributionControl: this._options.attributionControl === true || defaults.attributionControl === true
            });

            if (maplibregl.NavigationControl != null && resolveDefaultFlag(this._options, defaults, 'navigationControl', false)) {
                this._map.addControl(new maplibregl.NavigationControl(), 'top-right');
            }
            this._installBuiltinControls({
                scaleLine: resolveDefaultFlag(this._options, defaults, 'scaleLine', true),
                statusbar: resolveDefaultFlag(this._options, defaults, 'statusbar', true)
            });
            this._installCameraControl(this._options.cameraControl || defaults.cameraControl);
            this._installDrawRenderHandlers();

            var self = this;
            this._map.on('load', function () {
                self._readyReason = 'load';
                self._finishReady();
            });
            this._map.on('styledata', function () {
                self._scheduleReadyCheck();
            });
            this._scheduleReadyCheck();
        },

        _finishReady: function () {
            if (this._isReady === true) return;
            this._isReady = true;
            this._flushReadyQueue();
            if (this._container != null) {
                this._container.setAttribute('data-easymap-engine', 'maplibre');
                this._container.setAttribute('data-easymap-ready', '1');
                this._container.setAttribute('data-easymap-ready-reason', this._readyReason);
            }
            this._refreshBuiltinControls();
        },

        _scheduleReadyCheck: function () {
            if (this._isReady === true || this._readyCheckTimer != null) return;
            var self = this;
            this._readyCheckTimer = setTimeout(function () {
                self._readyCheckTimer = null;
                self._checkReady();
            }, 30);
        },

        _checkReady: function () {
            if (this._isReady === true || this._map == null) return;
            this._readyCheckCount++;
            var ready = false;
            var hasStyleObject = false;
            try {
                ready = (typeof this._map.isStyleLoaded == 'function' && this._map.isStyleLoaded()) ||
                    (typeof this._map.loaded == 'function' && this._map.loaded());
                hasStyleObject = this._map.getStyle != null && this._map.getStyle() != null;
                if (ready === false && hasStyleObject === true) {
                    var elapsed = Date.now() - this._readyStartedAt;
                    var fallbackMs = this._options.readyFallbackMs != null ? parseInt(this._options.readyFallbackMs, 10) : 800;
                    if (elapsed >= fallbackMs) {
                        ready = true;
                        this._readyReason = 'style-object-fallback';
                    }
                }
            } catch (err) {
                ready = false;
            }
            if (this._container != null) {
                this._container.setAttribute('data-easymap-ready-checks', this._readyCheckCount.toString());
                this._container.setAttribute('data-easymap-style-object', hasStyleObject === true ? '1' : '0');
                this._container.setAttribute('data-easymap-ready-last', ready === true ? '1' : '0');
            }
            if (ready === true) {
                this._finishReady();
                return;
            }
            this._scheduleReadyCheck();
        },

        _ready: function (callback) {
            if (this._isReady === true) {
                callback();
                return;
            }
            this._readyQueue.push(callback);
        },

        _flushReadyQueue: function () {
            var queue = this._readyQueue.slice();
            this._readyQueue = [];
            for (var i = 0; i < queue.length; i++) {
                queue[i]();
            }
        },

        _initLegacyControlContracts: function () {
            var self = this;
            this.scaleLine = {
                method: {
                    switchType: function (kind) {
                        return self._setScaleLineType(kind);
                    },
                    listScaleLineStyle: function () {
                        return ['orin_style', 'wra_style'];
                    }
                }
            };
            this.statusbar = {
                dom: null,
                is_open: false,
                _is_enable_z: false,
                _statusbarLon_Dom: null,
                _statusbarLat_Dom: null,
                _statusbarZ_Dom: null,
                open: function () {
                    self.switchStatusbar(true);
                },
                close: function () {
                    self.switchStatusbar(false);
                },
                updateInfo: function () {
                    self._refreshStatusbar();
                }
            };
            Object.defineProperty(this.statusbar, 'is_enable_z', {
                get: function () {
                    return this._is_enable_z === true;
                },
                set: function (value) {
                    this._is_enable_z = value === true;
                    self._refreshStatusbar();
                }
            });
        },

        onReady: function (callback) {
            if (typeof callback == 'function') this._ready(callback);
            return this;
        },

        _writeCameraAttributes: function () {
            if (this._container == null || this._map == null) return;
            var camera = this.get3DCamera();
            this._container.setAttribute('data-easymap-25d', camera.pitch > 0 ? '1' : '0');
            this._container.setAttribute('data-easymap-pitch', String(camera.pitch));
            this._container.setAttribute('data-easymap-bearing', String(camera.bearing));
            this._refreshMapControlState();
            this._refreshStatusbar();
            this._refreshScaleLine();
        },

        _applyCamera: function (camera) {
            if (this._map == null || camera == null) return this;
            var duration = camera.duration != null ? parseFloat(camera.duration) : 0;
            var payload = {};
            if (camera.center != null) payload.center = camera.center;
            if (camera.zoom != null) payload.zoom = camera.zoom;
            if (camera.pitch != null) payload.pitch = camera.pitch;
            if (camera.bearing != null) payload.bearing = camera.bearing;
            if (duration > 0 && typeof this._map.easeTo == 'function') {
                payload.duration = duration;
                this._map.easeTo(payload);
            }
            else if (typeof this._map.jumpTo == 'function') {
                this._map.jumpTo(payload);
            }
            else {
                if (payload.center != null && typeof this._map.setCenter == 'function') this._map.setCenter(payload.center);
                if (payload.zoom != null && typeof this._map.zoomTo == 'function') this._map.zoomTo(payload.zoom, { duration: duration });
                if (payload.pitch != null && typeof this._map.setPitch == 'function') this._map.setPitch(payload.pitch);
                if (payload.bearing != null && typeof this._map.setBearing == 'function') this._map.setBearing(payload.bearing);
            }
            this._writeCameraAttributes();
            return this;
        },

        get3DCamera: function () {
            var center = this._map.getCenter();
            var zoom = typeof this._map.getZoom == 'function' ? this._map.getZoom() : this._default3DCamera.zoom;
            var pitch = typeof this._map.getPitch == 'function' ? this._map.getPitch() : this._default3DCamera.pitch;
            var bearing = typeof this._map.getBearing == 'function' ? this._map.getBearing() : this._default3DCamera.bearing;
            return {
                center: [parseFloat(center.lng), parseFloat(center.lat)],
                zoom: parseFloat(zoom),
                pitch: clamp(pitch, 0, 85),
                bearing: normalizeBearing(bearing)
            };
        },

        set3DCamera: function (options) {
            options = options || {};
            var current = this.get3DCamera();
            var minPitch = this._cameraControlConfig != null ? this._cameraControlConfig.minPitch : 0;
            var maxPitch = this._cameraControlConfig != null ? this._cameraControlConfig.maxPitch : 85;
            var camera = {
                center: options.center != null ? toLngLat(options.center) : current.center,
                zoom: options.zoom != null ? parseFloat(options.zoom) : current.zoom,
                pitch: options.pitch != null ? clamp(options.pitch, minPitch, maxPitch) : current.pitch,
                bearing: options.bearing != null ? normalizeBearing(options.bearing) : current.bearing,
                duration: options.duration
            };
            return this._applyCamera(camera);
        },

        reset3DCamera: function (options) {
            var camera = extend({}, this._default3DCamera);
            if (options != null && options.duration != null) camera.duration = options.duration;
            return this._applyCamera(camera);
        },

        rotate: function (value) {
            if (arguments.length === 0) return this.get3DCamera().bearing;
            return this.set3DCamera({ bearing: normalizeBearing(value), duration: 0 });
        },

        openDragRotate: function () {
            if (this._map != null && this._map.dragRotate != null && typeof this._map.dragRotate.enable == 'function') {
                this._map.dragRotate.enable();
            }
            this._dragRotateEnabled = true;
            if (this._container != null) this._container.setAttribute('data-easymap-drag-rotate', '1');
            return this;
        },

        closeDragRotate: function () {
            if (this._map != null && this._map.dragRotate != null && typeof this._map.dragRotate.disable == 'function') {
                this._map.dragRotate.disable();
            }
            this._dragRotateEnabled = false;
            if (this._cameraDragState != null && this._cameraDragState.mode == 'legacy-shift-rotate') this._cameraDragState = null;
            if (this._container != null) this._container.setAttribute('data-easymap-drag-rotate', '0');
            return this;
        },

        openMobileDragRotate: function () {
            var handler = this._map != null ? this._map.touchZoomRotate : null;
            if (handler != null) {
                if (typeof handler.enableRotation == 'function') {
                    handler.enableRotation();
                }
                else if (typeof handler.enable == 'function') {
                    handler.enable();
                }
            }
            this._mobileDragRotateEnabled = true;
            if (this._container != null) this._container.setAttribute('data-easymap-mobile-drag-rotate', '1');
            return this;
        },

        closeMobileDragRotate: function () {
            var handler = this._map != null ? this._map.touchZoomRotate : null;
            if (handler != null) {
                if (typeof handler.disableRotation == 'function') {
                    handler.disableRotation();
                }
                else if (typeof handler.disable == 'function') {
                    handler.disable();
                }
            }
            this._mobileDragRotateEnabled = false;
            if (this._container != null) this._container.setAttribute('data-easymap-mobile-drag-rotate', '0');
            return this;
        },

        is3DEnabled: function () {
            return this.get3DCamera().pitch > 0;
        },

        enable3D: function (callback) {
            if (this.get3DCamera().pitch <= 0) {
                this.set3DCamera({ pitch: this._default3DCamera.pitch || 60, duration: 0 });
            }
            if (typeof callback == 'function') {
                this._ready(callback);
            }
            return this;
        },

        disable3D: function (callback) {
            this.set3DCamera({ pitch: 0, duration: 0 });
            if (typeof callback == 'function') {
                this._ready(callback);
            }
            return this;
        },

        addMapControl: function (itxy) {
            var position = Array.isArray(itxy) && itxy.length >= 2 ? itxy : [10, 10];
            if (this._customControler == null) {
                var subDiv = window.document.createElement('div');
                subDiv.className = 'map__wedget__btn';

                var btnLocation = this._createMapControlButton({
                    className: 'map-btn map-location',
                    title: '目前位置',
                    value: '',
                    onClick: function () {
                        this._zoomToCurrentPosition();
                    }
                });
                btnLocation.style.display = 'none';

                var pinDiv = window.document.createElement('div');
                pinDiv.className = 'map__compass';
                var btnPin = this._createMapControlButton({
                    className: 'map-btn map-compass--pin',
                    easymapId: 'map-btn-pin-Rotation',
                    title: '重設方位',
                    value: '',
                    onClick: function () {
                        this.set3DCamera({ bearing: 0, duration: 0 });
                    }
                });
                pinDiv.appendChild(btnPin);
                var self = this;
                pinDiv.addEventListener('click', function (event) {
                    if (event != null && typeof event.preventDefault == 'function') event.preventDefault();
                    self.set3DCamera({ bearing: 0, duration: 0 });
                    return false;
                }, false);

                var btn3d = this._createMapControlButton({
                    className: 'map-btn map-3d',
                    easymapId: 'easymap-btn-3D-2D-Trans',
                    title: '2D / 3D',
                    value: '',
                    onClick: function () {
                        if (this.is3DEnabled()) {
                            this.disable3D();
                        }
                        else {
                            this.enable3D();
                        }
                        this._refreshMapControlState();
                    }
                });

                var btnZoomIn = this._createMapControlButton({
                    className: 'map-btn map-zoomIn',
                    easymapId: 'easymap-btn-zoomIn',
                    title: '放大',
                    value: '',
                    onClick: function () {
                        this.zoomTo(this.getZoom() + 1);
                    }
                });

                var btnZoomOut = this._createMapControlButton({
                    className: 'map-btn map-zoomOut',
                    easymapId: 'easymap-btn-zoomOut',
                    title: '縮小',
                    value: '',
                    onClick: function () {
                        this.zoomTo(this.getZoom() - 1);
                    }
                });

                subDiv.appendChild(btnLocation);
                subDiv.appendChild(pinDiv);
                subDiv.appendChild(btn3d);
                subDiv.appendChild(btnZoomIn);
                subDiv.appendChild(btnZoomOut);

                this._customControler = window.document.createElement('div');
                this._customControler.className = 'map__wedget';
                this._customControler.setAttribute('easymap_id', this._targetId + '_customControler');
                this._customControler.setAttribute('data-easymap-control', 'legacy-map-control');
                this._customControler.appendChild(subDiv);
                this._container.appendChild(this._customControler);
                this._mapControlButtons = {
                    group: subDiv,
                    location: btnLocation,
                    pin: btnPin,
                    threeD: btn3d,
                    zoomIn: btnZoomIn,
                    zoomOut: btnZoomOut
                };
            }
            this.setMapControl(position);
            this._refreshMapControlState();
            return this;
        },

        _createMapControlButton: function (options) {
            options = options || {};
            var button = window.document.createElement('input');
            button.type = 'button';
            button.className = options.className || 'map-btn';
            button.value = options.value || '';
            if (options.easymapId != null) button.setAttribute('easymap_id', options.easymapId);
            if (options.title != null) {
                button.title = options.title;
                button.setAttribute('aria-label', options.title);
            }
            if (typeof options.onClick == 'function') {
                var self = this;
                button.addEventListener('click', function (event) {
                    if (event != null && typeof event.preventDefault == 'function') event.preventDefault();
                    options.onClick.call(self, event);
                    return false;
                }, false);
            }
            return button;
        },

        _zoomToCurrentPosition: function () {
            if (window.navigator == null || window.navigator.geolocation == null) {
                if (window.console != null && typeof window.console.warn == 'function') {
                    window.console.warn('Easymap MapLibre: geolocation is not available.');
                }
                return this;
            }
            var self = this;
            window.navigator.geolocation.getCurrentPosition(function (position) {
                if (position == null || position.coords == null) return;
                self.setCenter(new window.dgXY(position.coords.longitude, position.coords.latitude));
                self.zoomTo(13);
            });
            return this;
        },

        _refreshMapControlState: function () {
            if (this._customControler == null || this._mapControlButtons == null) return;
            var enabled = this.is3DEnabled();
            this._customControler.setAttribute('data-easymap-25d', enabled ? '1' : '0');
            this._mapControlButtons.threeD.setAttribute('data-easymap-active', enabled ? '1' : '0');
            this._mapControlButtons.threeD.className = enabled ? 'map-btn map-2d' : 'map-btn map-3d';
        },

        setMapControl: function (args) {
            if (this._customControler == null) this.addMapControl([10, 10]);
            if (Array.isArray(args)) {
                if (args.length != 2) {
                    if (window.console != null && typeof window.console.warn == 'function') {
                        window.console.warn('請傳入陣列，例如： map.setMapControl([10,10]); // 左,上');
                    }
                    return false;
                }
                this._customControler.style.left = parseInt(args[0], 10) + 'px';
                this._customControler.style.top = parseInt(args[1], 10) + 'px';
                this._customControler.style.width = '25px';
                return true;
            }
            if (args != null && typeof args == 'object') {
                for (var key in args) {
                    if (Object.prototype.hasOwnProperty.call(args, key)) {
                        this._customControler.style[key] = args[key];
                    }
                }
                return true;
            }
            if (window.console != null && typeof window.console.warn == 'function') {
                window.console.warn('請傳入陣列或物件，例如： [left, top] or { top: value, left: value }; // 左,上');
            }
            return false;
        },

        setMapControlV: function (tf) {
            if (this._customControler == null) this.addMapControl([10, 10]);
            if (this._mapControlButtons == null || this._mapControlButtons.group == null) return false;
            var visible = normalizeLegacyBool(tf, true);
            this._mapControlButtons.group.style.display = visible ? 'block' : 'none';
            if (this._container != null) this._container.setAttribute('data-easymap-mapcontrol', visible ? '1' : '0');
            return true;
        },

        setMapControl3DIconOnOff: function (truefalse) {
            if (this._customControler == null) this.addMapControl([10, 10]);
            if (this._mapControlButtons == null || this._mapControlButtons.threeD == null) return false;
            var visible = normalizeLegacyBool(truefalse, true);
            this._mapControlButtons.threeD.style.display = visible ? 'inline' : 'none';
            if (this._container != null) this._container.setAttribute('data-easymap-mapcontrol-3d', visible ? '1' : '0');
            return true;
        },

        _getEagleEyeOptions: function () {
            if (this._eagleEyeOptions != null) return this._eagleEyeOptions;
            var defaults = window.EASYMAP_MAPLIBRE_DEFAULTS || {};
            var options = extend(clone(defaults.eagleEye || {}), this._options.eagleEye || this._options.eagleEyeControl || {});
            var toNumber = typeof ns.toNumber == 'function' ? ns.toNumber : function (value, fallback) {
                var n = parseFloat(value);
                return isNaN(n) ? fallback : n;
            };
            options.zoomOffset = Math.max(0, toNumber(options.zoomOffset, 4));
            options.minZoom = Math.max(0, toNumber(options.minZoom, 0));
            options.allowRotate = options.allowRotate !== false;
            options.style = options.style || options.mapStyle || this._options.eagleEyeStyle || this._options.style || defaults.eagleEyeStyle || defaults.style;
            this._eagleEyeOptions = options;
            return this._eagleEyeOptions;
        },

        _ensureEagleEyeControl: function () {
            if (this._eagleEyeControl != null) return this._eagleEyeControl;
            var options = this._getEagleEyeOptions();
            var camera = this.get3DCamera();
            var element = window.document.createElement('div');
            var mapElement = window.document.createElement('div');
            var extentElement = window.document.createElement('div');
            var buttonElement = window.document.createElement('button');

            element.className = 'easymap-maplibre-eagleeye';
            element.setAttribute('easymap_id', 'easymap-eagleeye');
            element.setAttribute('data-easymap-control', 'eagleeye');
            mapElement.className = 'easymap-maplibre-eagleeye-map';
            mapElement.setAttribute('data-easymap-control', 'eagleeye-map');
            extentElement.className = 'easymap-maplibre-eagleeye-extent';
            extentElement.setAttribute('data-easymap-control', 'eagleeye-extent');
            buttonElement.className = 'easymap-maplibre-eagleeye-toggle';
            buttonElement.type = 'button';
            buttonElement.setAttribute('data-easymap-control', 'eagleeye-toggle');
            buttonElement.textContent = '<';
            element.appendChild(mapElement);
            element.appendChild(extentElement);
            element.appendChild(buttonElement);
            this._container.appendChild(element);

            var style = options.style;
            if (style == null && this._map != null && typeof this._map.getStyle == 'function') {
                try {
                    style = this._map.getStyle();
                } catch (err) {
                    style = null;
                }
            }

            this._eagleEyeMap = new maplibregl.Map({
                container: mapElement,
                style: clone(style),
                center: camera.center,
                zoom: Math.max(options.minZoom, camera.zoom - options.zoomOffset),
                pitch: 0,
                bearing: options.allowRotate ? camera.bearing : 0,
                interactive: false,
                attributionControl: false
            });

            this._eagleEyeControl = {
                element: element,
                mapElement: mapElement,
                extentElement: extentElement,
                buttonElement: buttonElement,
                collapsed: false,
                visible: false
            };

            var self = this;
            if (this._eagleEyeMap != null && typeof this._eagleEyeMap.on == 'function') {
                this._eagleEyeMap.on('load', function () {
                    self._syncEagleEye();
                });
            }
            return this._eagleEyeControl;
        },

        _bindEagleEyeHandlers: function () {
            if (this._map == null || typeof this._map.on != 'function' || this._eagleEyeHandlers.length > 0) return;
            var self = this;
            var handler = function () {
                self._syncEagleEye();
            };
            var names = ['move', 'zoom', 'rotate', 'pitch', 'resize'];
            for (var i = 0; i < names.length; i++) {
                this._map.on(names[i], handler);
                this._eagleEyeHandlers.push({ name: names[i], handler: handler });
            }
            this._bindEagleEyeDomHandlers();
        },

        _unbindEagleEyeHandlers: function () {
            if (this._map != null && typeof this._map.off == 'function') {
                for (var i = 0; i < this._eagleEyeHandlers.length; i++) {
                    this._map.off(this._eagleEyeHandlers[i].name, this._eagleEyeHandlers[i].handler);
                }
            }
            this._eagleEyeHandlers = [];
            this._unbindEagleEyeDomHandlers();
        },

        _bindEagleEyeDomHandlers: function () {
            if (this._eagleEyeControl == null || this._eagleEyeControl.extentElement == null || this._eagleEyeDomHandlers.length > 0) return;
            var self = this;
            var extentElement = this._eagleEyeControl.extentElement;
            var buttonElement = this._eagleEyeControl.buttonElement;
            var onMouseDown = function (event) {
                if (event != null && event.button != null && event.button !== 0) return;
                if (self._startEagleEyeBoxDrag(event) === true) self._stopEagleEyeDomEvent(event);
            };
            var onMouseMove = function (event) {
                if (self._eagleEyeDragState == null || self._eagleEyeDragState.active !== true) return;
                self._previewEagleEyeBoxDrag(event);
                self._stopEagleEyeDomEvent(event);
            };
            var onMouseUp = function (event) {
                if (self._eagleEyeDragState == null) return;
                self._finishEagleEyeBoxDrag(event);
                self._stopEagleEyeDomEvent(event);
            };
            var onToggleClick = function (event) {
                self._toggleEagleEyeCollapsed();
                self._stopEagleEyeDomEvent(event);
            };
            var onToggleMouseDown = function (event) {
                self._stopEagleEyeDomEvent(event);
            };
            this._addEagleEyeDomHandler(extentElement, 'mousedown', onMouseDown);
            this._addEagleEyeDomHandler(buttonElement, 'click', onToggleClick);
            this._addEagleEyeDomHandler(buttonElement, 'mousedown', onToggleMouseDown);
            if (window.document != null) {
                this._addEagleEyeDomHandler(window.document, 'mousemove', onMouseMove);
                this._addEagleEyeDomHandler(window.document, 'mouseup', onMouseUp);
            }
        },

        _addEagleEyeDomHandler: function (target, name, handler) {
            if (target == null || typeof target.addEventListener != 'function') return;
            target.addEventListener(name, handler);
            this._eagleEyeDomHandlers.push({
                target: target,
                name: name,
                handler: handler
            });
        },

        _unbindEagleEyeDomHandlers: function () {
            for (var i = 0; i < this._eagleEyeDomHandlers.length; i++) {
                var entry = this._eagleEyeDomHandlers[i];
                if (entry.target != null && typeof entry.target.removeEventListener == 'function') {
                    entry.target.removeEventListener(entry.name, entry.handler);
                }
            }
            this._eagleEyeDomHandlers = [];
            this._eagleEyeDragState = null;
        },

        _stopEagleEyeDomEvent: function (event) {
            if (event == null) return;
            if (typeof event.preventDefault == 'function') event.preventDefault();
            if (typeof event.stopPropagation == 'function') event.stopPropagation();
        },

        _getEagleEyeMapSize: function () {
            if (this._eagleEyeControl == null || this._eagleEyeControl.mapElement == null) return null;
            var mapElement = this._eagleEyeControl.mapElement;
            return {
                width: mapElement.clientWidth || mapElement.offsetWidth || 150,
                height: mapElement.clientHeight || mapElement.offsetHeight || 150
            };
        },

        _getEagleEyeEventPixel: function (event) {
            if (event == null || this._eagleEyeControl == null || this._eagleEyeControl.mapElement == null) return null;
            if (event.clientX == null || event.clientY == null) return null;
            var mapElement = this._eagleEyeControl.mapElement;
            var rect = typeof mapElement.getBoundingClientRect == 'function' ? mapElement.getBoundingClientRect() : null;
            var left = rect != null && rect.left != null ? rect.left : 0;
            var top = rect != null && rect.top != null ? rect.top : 0;
            var width = rect != null && rect.width != null ? rect.width : (mapElement.clientWidth || mapElement.offsetWidth || 0);
            var height = rect != null && rect.height != null ? rect.height : (mapElement.clientHeight || mapElement.offsetHeight || 0);
            var x = parseFloat(event.clientX) - left;
            var y = parseFloat(event.clientY) - top;
            if (width > 0) x = Math.max(0, Math.min(width, x));
            if (height > 0) y = Math.max(0, Math.min(height, y));
            return { x: x, y: y, width: width, height: height };
        },

        _normalizeEagleEyeLngLat: function (lngLat) {
            if (lngLat == null) return null;
            var center = Array.isArray(lngLat) ? [parseFloat(lngLat[0]), parseFloat(lngLat[1])] : [parseFloat(lngLat.lng), parseFloat(lngLat.lat)];
            if (isNaN(center[0]) || isNaN(center[1])) return null;
            return center;
        },

        _getEagleEyeLngLatAtPixel: function (x, y) {
            if (this._eagleEyeMap == null || typeof this._eagleEyeMap.unproject != 'function') return null;
            var lngLat = this._eagleEyeMap.unproject([x, y]);
            return this._normalizeEagleEyeLngLat(lngLat);
        },

        _getEagleEyeEventLngLat: function (event) {
            var pixel = this._getEagleEyeEventPixel(event);
            if (pixel == null) return null;
            return this._getEagleEyeLngLatAtPixel(pixel.x, pixel.y);
        },

        _getEagleEyeExtentRect: function () {
            if (this._eagleEyeControl == null || this._eagleEyeControl.extentElement == null) return null;
            var size = this._getEagleEyeMapSize();
            if (size == null) return null;
            var extent = this._eagleEyeControl.extentElement;
            var rect = {
                left: parseFloat(extent.style.left),
                top: parseFloat(extent.style.top),
                width: parseFloat(extent.style.width),
                height: parseFloat(extent.style.height),
                mapWidth: size.width,
                mapHeight: size.height
            };
            if (isNaN(rect.left) || isNaN(rect.top) || isNaN(rect.width) || isNaN(rect.height)) return null;
            if (rect.width <= 0 || rect.height <= 0 || rect.mapWidth <= 0 || rect.mapHeight <= 0) return null;
            return rect;
        },

        _setEagleEyeExtentRect: function (rect) {
            if (this._eagleEyeControl == null || this._eagleEyeControl.extentElement == null || rect == null) return null;
            var size = this._getEagleEyeMapSize();
            if (size == null) return null;
            var width = Math.max(6, parseFloat(rect.width) || 6);
            var height = Math.max(6, parseFloat(rect.height) || 6);
            var left = parseFloat(rect.left) || 0;
            var top = parseFloat(rect.top) || 0;
            left = Math.max(0, Math.min(Math.max(0, size.width - width), left));
            top = Math.max(0, Math.min(Math.max(0, size.height - height), top));
            var extent = this._eagleEyeControl.extentElement;
            extent.style.left = Math.round(left) + 'px';
            extent.style.top = Math.round(top) + 'px';
            extent.style.width = Math.round(width) + 'px';
            extent.style.height = Math.round(height) + 'px';
            extent.style.display = '';
            return {
                left: Math.round(left),
                top: Math.round(top),
                width: Math.round(width),
                height: Math.round(height),
                mapWidth: size.width,
                mapHeight: size.height
            };
        },

        _setEagleEyeDraggingClass: function (active) {
            if (this._eagleEyeControl == null || this._eagleEyeControl.element == null) return;
            var element = this._eagleEyeControl.element;
            if (element.classList != null) {
                if (active === true) element.classList.add('easymap-maplibre-eagleeye-dragging');
                else element.classList.remove('easymap-maplibre-eagleeye-dragging');
                return;
            }
            var className = element.className || '';
            className = className.replace(/\s*easymap-maplibre-eagleeye-dragging/g, '');
            if (active === true) className += ' easymap-maplibre-eagleeye-dragging';
            element.className = className;
        },

        _toggleEagleEyeCollapsed: function (collapsed) {
            if (this._eagleEyeControl == null) return;
            var control = this._eagleEyeControl;
            control.collapsed = collapsed == null ? control.collapsed !== true : collapsed === true;
            var element = control.element;
            var className = element.className || '';
            className = className.replace(/\s*easymap-maplibre-eagleeye-collapsed/g, '');
            if (control.collapsed === true) className += ' easymap-maplibre-eagleeye-collapsed';
            element.className = className;
            if (control.mapElement != null) control.mapElement.style.display = control.collapsed === true ? 'none' : '';
            if (control.extentElement != null) control.extentElement.style.display = control.collapsed === true ? 'none' : '';
            if (control.buttonElement != null) control.buttonElement.textContent = control.collapsed === true ? '>' : '<';
            if (control.collapsed !== true) this._syncEagleEye();
        },

        _startEagleEyeBoxDrag: function (event) {
            if (this._eagleEyeControl == null || this._eagleEyeControl.collapsed === true) return false;
            var pixel = this._getEagleEyeEventPixel(event);
            var rect = this._getEagleEyeExtentRect();
            if (pixel == null || rect == null) return false;
            var tolerance = 2;
            if (pixel.x < rect.left - tolerance || pixel.x > rect.left + rect.width + tolerance || pixel.y < rect.top - tolerance || pixel.y > rect.top + rect.height + tolerance) return false;
            this._eagleEyeDragState = {
                active: true,
                startX: pixel.x,
                startY: pixel.y,
                startRect: {
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height
                },
                currentRect: {
                    left: rect.left,
                    top: rect.top,
                    width: rect.width,
                    height: rect.height
                },
                camera: this.get3DCamera()
            };
            this._setEagleEyeDraggingClass(true);
            return true;
        },

        _previewEagleEyeBoxDrag: function (event) {
            var state = this._eagleEyeDragState;
            if (state == null || state.active !== true) return null;
            var pixel = this._getEagleEyeEventPixel(event);
            if (pixel == null) return state.currentRect;
            var rect = this._setEagleEyeExtentRect({
                left: state.startRect.left + pixel.x - state.startX,
                top: state.startRect.top + pixel.y - state.startY,
                width: state.startRect.width,
                height: state.startRect.height
            });
            if (rect != null) state.currentRect = rect;
            return state.currentRect;
        },

        _finishEagleEyeBoxDrag: function (event) {
            var state = this._eagleEyeDragState;
            if (state == null) return false;
            var rect = this._previewEagleEyeBoxDrag(event) || state.currentRect || state.startRect;
            this._eagleEyeDragState = null;
            this._setEagleEyeDraggingClass(false);
            if (rect == null) return false;
            var center = this._getEagleEyeLngLatAtPixel(rect.left + rect.width / 2, rect.top + rect.height / 2);
            if (center == null) return false;
            return this._setMainMapCenterFromEagleEye(center, state.camera);
        },

        _setMainMapCenterFromEagleEye: function (center, camera) {
            center = this._normalizeEagleEyeLngLat(center);
            if (center == null || this._map == null) return false;
            camera = camera || this.get3DCamera();
            var payload = {
                center: center,
                zoom: camera.zoom,
                pitch: camera.pitch,
                bearing: camera.bearing
            };
            if (typeof this._map.jumpTo == 'function') {
                this._map.jumpTo(payload);
            }
            else {
                if (typeof this._map.setCenter == 'function') this._map.setCenter(center);
                if (typeof this._map.zoomTo == 'function') this._map.zoomTo(payload.zoom, { duration: 0 });
                if (typeof this._map.setPitch == 'function') this._map.setPitch(payload.pitch);
                if (typeof this._map.setBearing == 'function') this._map.setBearing(payload.bearing);
            }
            this._writeCameraAttributes();
            this._syncEagleEye();
            return true;
        },

        _syncEagleEye: function () {
            if (this._eagleEyeSyncing === true || this._eagleEyeControl == null || this._eagleEyeMap == null || this._map == null) return;
            var options = this._getEagleEyeOptions();
            var camera = this.get3DCamera();
            var payload = {
                center: camera.center,
                zoom: Math.max(options.minZoom, camera.zoom - options.zoomOffset),
                pitch: 0,
                bearing: options.allowRotate ? camera.bearing : 0
            };
            this._eagleEyeSyncing = true;
            try {
                if (typeof this._eagleEyeMap.jumpTo == 'function') {
                    this._eagleEyeMap.jumpTo(payload);
                }
                else {
                    if (payload.center != null && typeof this._eagleEyeMap.setCenter == 'function') this._eagleEyeMap.setCenter(payload.center);
                    if (payload.zoom != null && typeof this._eagleEyeMap.zoomTo == 'function') this._eagleEyeMap.zoomTo(payload.zoom, { duration: 0 });
                    if (payload.bearing != null && typeof this._eagleEyeMap.setBearing == 'function') this._eagleEyeMap.setBearing(payload.bearing);
                    if (payload.pitch != null && typeof this._eagleEyeMap.setPitch == 'function') this._eagleEyeMap.setPitch(payload.pitch);
                }
                if (typeof this._eagleEyeMap.resize == 'function') this._eagleEyeMap.resize();
            }
            finally {
                this._eagleEyeSyncing = false;
            }
            this._refreshEagleEyeExtent();
        },

        _refreshEagleEyeExtent: function () {
            if (this._eagleEyeControl == null || this._eagleEyeControl.extentElement == null || this._map == null || this._eagleEyeMap == null) return;
            if (typeof this._map.getBounds != 'function' || typeof this._eagleEyeMap.project != 'function') return;
            var bounds = this._map.getBounds();
            if (bounds == null) return;
            var west = typeof bounds.getWest == 'function' ? bounds.getWest() : (bounds._sw != null ? bounds._sw.lng : bounds.west);
            var east = typeof bounds.getEast == 'function' ? bounds.getEast() : (bounds._ne != null ? bounds._ne.lng : bounds.east);
            var south = typeof bounds.getSouth == 'function' ? bounds.getSouth() : (bounds._sw != null ? bounds._sw.lat : bounds.south);
            var north = typeof bounds.getNorth == 'function' ? bounds.getNorth() : (bounds._ne != null ? bounds._ne.lat : bounds.north);
            if ([west, east, south, north].some(function (v) { return isNaN(parseFloat(v)); })) return;

            var pixels = [
                this._eagleEyeMap.project([west, north]),
                this._eagleEyeMap.project([east, north]),
                this._eagleEyeMap.project([east, south]),
                this._eagleEyeMap.project([west, south])
            ];
            var minX = Infinity;
            var minY = Infinity;
            var maxX = -Infinity;
            var maxY = -Infinity;
            for (var i = 0; i < pixels.length; i++) {
                if (pixels[i] == null) continue;
                var x = parseFloat(pixels[i].x);
                var y = parseFloat(pixels[i].y);
                if (isNaN(x) || isNaN(y)) continue;
                if (x < minX) minX = x;
                if (y < minY) minY = y;
                if (x > maxX) maxX = x;
                if (y > maxY) maxY = y;
            }
            if (!isFinite(minX) || !isFinite(minY) || !isFinite(maxX) || !isFinite(maxY)) return;

            var mapElement = this._eagleEyeControl.mapElement;
            var width = mapElement.clientWidth || mapElement.offsetWidth || 120;
            var height = mapElement.clientHeight || mapElement.offsetHeight || 86;
            minX = Math.max(0, Math.min(width, minX));
            maxX = Math.max(0, Math.min(width, maxX));
            minY = Math.max(0, Math.min(height, minY));
            maxY = Math.max(0, Math.min(height, maxY));
            var rectWidth = Math.max(6, maxX - minX);
            var rectHeight = Math.max(6, maxY - minY);
            var left = Math.max(0, Math.min(width - rectWidth, minX));
            var top = Math.max(0, Math.min(height - rectHeight, minY));
            var extent = this._eagleEyeControl.extentElement;
            extent.style.left = Math.round(left) + 'px';
            extent.style.top = Math.round(top) + 'px';
            extent.style.width = Math.round(rectWidth) + 'px';
            extent.style.height = Math.round(rectHeight) + 'px';
            extent.style.display = '';
        },

        _removeEagleEyeControl: function () {
            this._unbindEagleEyeHandlers();
            if (this._eagleEyeMap != null && typeof this._eagleEyeMap.remove == 'function') {
                this._eagleEyeMap.remove();
            }
            if (this._eagleEyeControl != null && this._eagleEyeControl.element != null && this._eagleEyeControl.element.parentNode != null) {
                this._eagleEyeControl.element.parentNode.removeChild(this._eagleEyeControl.element);
            }
            this._eagleEyeControl = null;
            this._eagleEyeMap = null;
            this._eagleEyeOptions = null;
            this._eagleEyeSyncing = false;
        },

        enableEagleEye: function () {
            var control = this._ensureEagleEyeControl();
            control.visible = true;
            control.element.style.display = '';
            this._bindEagleEyeHandlers();
            this._syncEagleEye();
            if (this._container != null) this._container.setAttribute('data-easymap-eagleeye', '1');
            return this;
        },

        disableEagleEye: function () {
            if (this._eagleEyeControl != null) {
                this._eagleEyeControl.visible = false;
                this._eagleEyeControl.element.style.display = 'none';
            }
            this._unbindEagleEyeHandlers();
            if (this._container != null) this._container.setAttribute('data-easymap-eagleeye', '0');
            return this;
        },

        isEagleEyeEnable: function () {
            return this._eagleEyeControl != null && this._eagleEyeControl.visible === true && this._eagleEyeControl.element.style.display != 'none';
        },

        _enableDblClickZoom: function () {
            if (this._map != null && this._map.doubleClickZoom != null && typeof this._map.doubleClickZoom.enable == 'function') {
                this._map.doubleClickZoom.enable();
            }
            this._dblClickZoomEnabled = true;
            if (this._container != null) this._container.setAttribute('data-easymap-dblclick-zoom', '1');
            return this;
        },

        _disableDblClickZoom: function () {
            if (this._map != null && this._map.doubleClickZoom != null && typeof this._map.doubleClickZoom.disable == 'function') {
                this._map.doubleClickZoom.disable();
            }
            this._dblClickZoomEnabled = false;
            if (this._container != null) this._container.setAttribute('data-easymap-dblclick-zoom', '0');
            return this;
        },

        enableLoading: function () {
            var element = this._ensureLoadingControl();
            element.style.display = '';
            if (this._container != null) this._container.setAttribute('data-easymap-loading', '1');
            return this;
        },

        disableLoading: function () {
            var element = this._ensureLoadingControl();
            element.style.display = 'none';
            if (this._container != null) this._container.setAttribute('data-easymap-loading', '0');
            return this;
        },

        _ensureLoadingControl: function () {
            if (this._loadingControl != null) return this._loadingControl;
            var element = window.document.createElement('div');
            element.className = 'easymap-maplibre-loading';
            element.setAttribute('easymap_id', 'easymap-loading');
            element.setAttribute('data-easymap-control', 'loading');
            element.textContent = 'Loading...';
            this._container.appendChild(element);
            this._loadingControl = element;
            return element;
        },

        _installBuiltinControls: function (options) {
            if (this._container == null || window.document == null || typeof window.document.createElement != 'function') return;
            options = options || {};
            this._ensureScaleLineControl();
            this._ensureStatusbarControl();
            this.switchScaleLine(options.scaleLine !== false);
            this.switchStatusbar(options.statusbar !== false);

            var self = this;
            var events = ['move', 'zoom', 'pitch', 'rotate', 'resize'];
            for (var i = 0; i < events.length; i++) {
                var name = events[i];
                var handler = function () {
                    self._refreshBuiltinControls();
                };
                if (this._map != null && typeof this._map.on == 'function') {
                    this._map.on(name, handler);
                    this._builtinControlHandlers.push({ name: name, handler: handler });
                }
            }
            if (this._map != null && typeof this._map.on == 'function') {
                var mouseMoveHandler = function (event) {
                    if (event != null && event.lngLat != null) {
                        self._mousePosition = {
                            lon: parseFloat(event.lngLat.lng),
                            lat: parseFloat(event.lngLat.lat)
                        };
                        self._refreshStatusbar();
                    }
                };
                this._map.on('mousemove', mouseMoveHandler);
                this._builtinControlHandlers.push({ name: 'mousemove', handler: mouseMoveHandler });
            }
            this._refreshBuiltinControls();
        },

        _ensureScaleLineControl: function () {
            if (this._scaleLineControl != null) return this._scaleLineControl;
            var element = window.document.createElement('div');
            element.className = 'easymap-maplibre-scaleline';
            element.setAttribute('data-easymap-control', 'scaleline');
            this._container.appendChild(element);
            this._scaleLineControl = {
                element: element,
                visible: true
            };
            return this._scaleLineControl;
        },

        _ensureStatusbarControl: function () {
            if (this._statusbarControl != null) return this._statusbarControl;
            var element = window.document.createElement('div');
            element.className = 'easymap-maplibre-statusbar';
            element.setAttribute('data-easymap-control', 'statusbar');
            element.setAttribute('easymap_id', 'statusbar');
            this._container.appendChild(element);
            this._statusbarControl = {
                element: element,
                visible: true
            };
            this.statusbar.dom = element;
            this._ensureStatusbarParts();
            return this._statusbarControl;
        },

        _clearElement: function (element) {
            if (element == null) return;
            while (element.children != null && element.children.length > 0 && typeof element.removeChild == 'function') {
                element.removeChild(element.children[0]);
            }
            element.textContent = '';
        },

        _appendStatusbarPart: function (element, easymapId, text) {
            var span = window.document.createElement('span');
            span.setAttribute('easymap_id', easymapId);
            span.textContent = text || '';
            element.appendChild(span);
            return span;
        },

        _ensureStatusbarParts: function () {
            if (this._statusbarControl == null || this._statusbarControl.element == null) return;
            if (this.statusbar._statusbarLon_Dom != null && this.statusbar._statusbarLat_Dom != null && this.statusbar._statusbarZ_Dom != null) return;
            var element = this._statusbarControl.element;
            this._clearElement(element);
            this._appendStatusbarPart(element, 'statusbar_label', '經緯度:');
            this.statusbar._statusbarLon_Dom = this._appendStatusbarPart(element, 'statusbar_lon', '');
            this._appendStatusbarPart(element, 'statusbar_gap_1', ' ');
            this.statusbar._statusbarLat_Dom = this._appendStatusbarPart(element, 'statusbar_lat', '');
            this._appendStatusbarPart(element, 'statusbar_gap_2', ' ');
            this.statusbar._statusbarZ_Dom = this._appendStatusbarPart(element, 'statusbar_z', '');
        },

        _refreshBuiltinControls: function () {
            this._refreshScaleLine();
            this._refreshStatusbar();
        },

        _refreshScaleLine: function () {
            if (this._scaleLineControl == null || this._scaleLineControl.visible !== true || this._map == null) return;
            var camera = this.get3DCamera();
            var lat = camera.center[1] || 0;
            var zoom = camera.zoom || 0;
            var metersPerPixel = 156543.03392804097 * Math.cos(lat * Math.PI / 180) / Math.pow(2, zoom);
            var distance = niceDistance(metersPerPixel * 100);
            var width = Math.max(48, Math.min(180, Math.round(distance / metersPerPixel)));
            var element = this._scaleLineControl.element;
            element.style.width = width + 'px';
            element.textContent = formatDistance(distance);
            element.setAttribute('data-scale-distance', String(distance));
            element.setAttribute('data-scale-width', String(width));
        },

        _refreshStatusbar: function () {
            if (this._statusbarControl == null || this._statusbarControl.visible !== true || this._map == null) return;
            if (this._statusbarCustomText != null) {
                this.statusbar._statusbarLon_Dom = null;
                this.statusbar._statusbarLat_Dom = null;
                this.statusbar._statusbarZ_Dom = null;
                this._statusbarControl.element.textContent = this._statusbarCustomText;
                return;
            }
            var camera = this.get3DCamera();
            if (this._mousePosition.lon == null || this._mousePosition.lat == null) {
                this._mousePosition.lon = camera.center[0];
                this._mousePosition.lat = camera.center[1];
            }
            this._ensureStatusbarParts();
            this.statusbar._statusbarLon_Dom.textContent = formatCoordinate(this._mousePosition.lon);
            this.statusbar._statusbarLat_Dom.textContent = formatCoordinate(this._mousePosition.lat);
            this.statusbar._statusbarZ_Dom.textContent = 'Z ' + camera.zoom.toFixed(2).replace(/\.00$/, '');
            this.statusbar._statusbarZ_Dom.style.display = this.statusbar.is_enable_z === true ? 'inline' : 'none';
        },

        switchScaleLine: function (visible) {
            var control = this._ensureScaleLineControl();
            if (visible == null) visible = control.visible !== true;
            control.visible = visible !== false;
            control.element.style.display = control.visible ? '' : 'none';
            if (this._container != null) this._container.setAttribute('data-easymap-scaleline', control.visible ? '1' : '0');
            this._refreshScaleLine();
            return this;
        },

        setScaleLineVisible: function (visible) {
            return this.switchScaleLine(visible);
        },

        switchScaleline: function (visible) {
            return this.switchScaleLine(visible);
        },

        switchScaleBar: function (visible) {
            return this.switchScaleLine(visible);
        },

        showScaleLine: function () {
            return this.switchScaleLine(true);
        },

        hideScaleLine: function () {
            return this.switchScaleLine(false);
        },

        _setScaleLineType: function (kind) {
            var list = this.scaleLine.method.listScaleLineStyle();
            if (list.indexOf(kind) < 0) kind = 'orin_style';
            this._scaleLineType = kind;
            var control = this._ensureScaleLineControl();
            control.element.setAttribute('data-scaleline-style', kind);
            var className = control.element.className.replace(/\s*is-wra-style|\s*is-orin-style/g, '');
            control.element.className = className + (kind == 'wra_style' ? ' is-wra-style' : ' is-orin-style');
            return kind;
        },

        switchStatusbar: function (visible) {
            var control = this._ensureStatusbarControl();
            if (visible == null) visible = control.visible !== true;
            control.visible = visible !== false;
            control.element.style.display = control.visible ? '' : 'none';
            this.statusbar.is_open = control.visible;
            if (this._container != null) this._container.setAttribute('data-easymap-statusbar', control.visible ? '1' : '0');
            this._refreshStatusbar();
            return this;
        },

        setStatusBarVisible: function (visible) {
            return this.switchStatusbar(visible);
        },

        switchStatusBar: function (visible) {
            return this.switchStatusbar(visible);
        },

        switchStatus: function (visible) {
            return this.switchStatusbar(visible);
        },

        showStatusbar: function () {
            return this.switchStatusbar(true);
        },

        showStatusBar: function () {
            return this.switchStatusbar(true);
        },

        hideStatusbar: function () {
            return this.switchStatusbar(false);
        },

        hideStatusBar: function () {
            return this.switchStatusbar(false);
        },

        setStatusText: function (text) {
            this._statusbarCustomText = text == null ? null : String(text);
            this._refreshStatusbar();
            return this;
        },

        setStatusbarText: function (text) {
            return this.setStatusText(text);
        },

        _removeBuiltinControls: function () {
            if (this._map != null && typeof this._map.off == 'function') {
                for (var i = 0; i < this._builtinControlHandlers.length; i++) {
                    this._map.off(this._builtinControlHandlers[i].name, this._builtinControlHandlers[i].handler);
                }
            }
            this._builtinControlHandlers = [];
            var controls = [this._scaleLineControl, this._statusbarControl];
            for (var j = 0; j < controls.length; j++) {
                if (controls[j] != null && controls[j].element != null && controls[j].element.parentNode != null) {
                    controls[j].element.parentNode.removeChild(controls[j].element);
                }
            }
            this._removeEagleEyeControl();
            var legacyControls = [this._customControler, this._loadingControl];
            for (var k = 0; k < legacyControls.length; k++) {
                if (legacyControls[k] != null && legacyControls[k].parentNode != null) {
                    legacyControls[k].parentNode.removeChild(legacyControls[k]);
                }
            }
            this._scaleLineControl = null;
            this._statusbarControl = null;
            this._statusbarCustomText = null;
            this._customControler = null;
            this._mapControlButtons = null;
            this._loadingControl = null;
        },

        _installCameraControl: function (options) {
            this._cameraControlConfig = normalizeCameraControlOptions(options);
            if (this._cameraControlConfig.enabled !== true || this._map == null || typeof this._map.getCanvas != 'function') return;
            var canvas = this._map.getCanvas();
            if (canvas == null || typeof canvas.addEventListener != 'function') return;
            var self = this;
            var updateCameraDragDistance = function (state, event) {
                var clientX = event != null && event.clientX != null ? event.clientX : state.x;
                var clientY = event != null && event.clientY != null ? event.clientY : state.y;
                var dx = clientX - state.x;
                var dy = clientY - state.y;
                var distanceSq = dx * dx + dy * dy;
                if (distanceSq > state.maxDistanceSq) state.maxDistanceSq = distanceSq;
                if (state.maxDistanceSq >= CAMERA_CONTEXT_MENU_DRAG_TOLERANCE_SQ) state.moved = true;
                return { dx: dx, dy: dy };
            };
            var onMouseDown = function (event) {
                var legacyShiftRotate = self._dragRotateEnabled === true && event.button === 0 && event.shiftKey === true;
                if (!legacyShiftRotate && !cameraButtonAllowed(self._cameraControlConfig, event.button)) return;
                self._suppressNextContextMenu = false;
                if (event.preventDefault != null) event.preventDefault();
                self._cameraDragState = {
                    x: event.clientX,
                    y: event.clientY,
                    camera: self.get3DCamera(),
                    mode: legacyShiftRotate ? 'legacy-shift-rotate' : 'camera',
                    button: event.button,
                    moved: false,
                    maxDistanceSq: 0
                };
            };
            var onMouseMove = function (event) {
                if (self._cameraDragState == null) return;
                if (event.preventDefault != null) event.preventDefault();
                var movement = updateCameraDragDistance(self._cameraDragState, event);
                if (self._cameraDragState.button === 2 && self._cameraDragState.moved === true) {
                    self._suppressNextContextMenu = true;
                }
                var dx = movement.dx;
                var dy = movement.dy;
                if (self._cameraDragState.mode == 'legacy-shift-rotate') {
                    self.set3DCamera({
                        bearing: self._cameraDragState.camera.bearing + dx * self._cameraControlConfig.bearingSpeed,
                        duration: 0
                    });
                    return;
                }
                self.set3DCamera({
                    bearing: self._cameraDragState.camera.bearing + dx * self._cameraControlConfig.bearingSpeed,
                    pitch: self._cameraDragState.camera.pitch + dy * self._cameraControlConfig.pitchSpeed,
                    duration: 0
                });
            };
            var onMouseUp = function (event) {
                if (self._cameraDragState != null) {
                    updateCameraDragDistance(self._cameraDragState, event);
                    if (self._cameraDragState.button === 2 && self._cameraDragState.moved === true) {
                        self._suppressNextContextMenu = true;
                    }
                }
                self._cameraDragState = null;
            };
            var onContextMenu = function (event) {
                if (self._cameraControlConfig.enabled === true && cameraButtonAllowed(self._cameraControlConfig, 2) && event.preventDefault != null) {
                    event.preventDefault();
                }
            };
            canvas.addEventListener('mousedown', onMouseDown);
            canvas.addEventListener('contextmenu', onContextMenu);
            window.document.addEventListener('mousemove', onMouseMove);
            window.document.addEventListener('mouseup', onMouseUp);
            this._cameraControlHandlers.push({ target: canvas, name: 'mousedown', handler: onMouseDown });
            this._cameraControlHandlers.push({ target: canvas, name: 'contextmenu', handler: onContextMenu });
            this._cameraControlHandlers.push({ target: window.document, name: 'mousemove', handler: onMouseMove });
            this._cameraControlHandlers.push({ target: window.document, name: 'mouseup', handler: onMouseUp });
        },

        _removeCameraControl: function () {
            for (var i = 0; i < this._cameraControlHandlers.length; i++) {
                var entry = this._cameraControlHandlers[i];
                if (entry.target != null && typeof entry.target.removeEventListener == 'function') {
                    entry.target.removeEventListener(entry.name, entry.handler);
                }
            }
            this._cameraControlHandlers = [];
            this._cameraDragState = null;
            this._suppressNextContextMenu = false;
        },

        _normalizeContextMenuItem: function (menuItem) {
            if (menuItem == null) return null;
            var label = menuItem.mname != null ? menuItem.mname : (menuItem.label != null ? menuItem.label : menuItem.name);
            var callback = menuItem.afunc || menuItem.callback || menuItem.function;
            var hasLabel = label != null && String(label) !== '';
            var hasCallback = typeof callback == 'function';
            if (!hasLabel && !hasCallback) return null;
            return {
                source: menuItem,
                mname: label == null ? '' : String(label),
                afunc: hasCallback ? callback : function () { },
                icon: menuItem.icon
            };
        },

        _ensureContextMenu: function () {
            if (this._contextMenu != null) return this._contextMenu;
            if (this._container == null || window.document == null || typeof window.document.createElement != 'function') return null;
            if (this._container.style != null && (this._container.style.position == null || this._container.style.position === '')) {
                this._container.style.position = 'relative';
            }
            var menu = window.document.createElement('div');
            menu.className = 'easymap-maplibre-context-menu';
            menu.setAttribute('easymap_id', 'exMenu');
            menu.style.visibility = 'hidden';
            menu.style.left = '0px';
            menu.style.top = '0px';
            this._container.appendChild(menu);
            this._contextMenu = menu;
            this._renderContextMenu();
            return menu;
        },

        _renderContextMenu: function () {
            var menu = this._contextMenu;
            if (menu == null) return;
            var self = this;
            while (menu.children != null && menu.children.length > 0) {
                menu.removeChild(menu.children[0]);
            }
            for (var i = 0; i < this.dgCMenu.length; i++) {
                (function (entry) {
                    var item = window.document.createElement('div');
                    item.className = 'easymap-maplibre-context-menu-item';
                    item.textContent = entry.mname;
                    if (entry.icon != null && entry.icon !== '') {
                        item.setAttribute('data-easymap-menu-icon', entry.icon);
                        item.style.backgroundImage = 'url("' + String(entry.icon).replace(/"/g, '\\"') + '")';
                    }
                    item.addEventListener('click', function (event) {
                        if (event != null && event.preventDefault != null) event.preventDefault();
                        if (event != null && event.stopPropagation != null) event.stopPropagation();
                        var contextEvent = self._contextMenuLastEvent;
                        if (event != null) event.easymapContextMenuEvent = contextEvent;
                        self._hideContextMenu();
                        entry.afunc.call(item, event || contextEvent, contextEvent);
                    });
                    menu.appendChild(item);
                })(this.dgCMenu[i]);
            }
        },

        _contextMenuEventToPixel: function (event) {
            if (event == null) return null;
            if (event.originalEvent != null) return this._contextMenuEventToPixel(event.originalEvent);
            if (event.clientX != null && event.clientY != null && this._container != null && typeof this._container.getBoundingClientRect == 'function') {
                var rect = this._container.getBoundingClientRect();
                return { x: event.clientX - rect.left, y: event.clientY - rect.top };
            }
            if (event.point != null) {
                return {
                    x: event.point.x != null ? event.point.x : event.point[0],
                    y: event.point.y != null ? event.point.y : event.point[1]
                };
            }
            if (event.offsetX != null && event.offsetY != null) {
                return { x: event.offsetX, y: event.offsetY };
            }
            if (event.layerX != null && event.layerY != null) {
                return { x: event.layerX, y: event.layerY };
            }
            return { x: 0, y: 0 };
        },

        _consumeSuppressedContextMenu: function (event) {
            if (this._suppressNextContextMenu !== true) return false;
            this._suppressNextContextMenu = false;
            if (event != null && event.preventDefault != null) event.preventDefault();
            if (event != null && event.stopPropagation != null) event.stopPropagation();
            this._hideContextMenu();
            return true;
        },

        _showContextMenu: function (event) {
            if (this._consumeSuppressedContextMenu(event)) return false;
            if (event != null && event.preventDefault != null) event.preventDefault();
            if (event != null && event.stopPropagation != null) event.stopPropagation();
            if (this.dgCMenu == null || this.dgCMenu.length <= 0) return false;
            var menu = this._ensureContextMenu();
            if (menu == null) return false;
            this._contextMenuLastEvent = event || null;
            this._renderContextMenu();
            menu.style.visibility = 'hidden';
            menu.style.display = 'block';
            var pixel = this._contextMenuEventToPixel(event);
            var rect = this._container != null && typeof this._container.getBoundingClientRect == 'function' ? this._container.getBoundingClientRect() : null;
            var containerWidth = rect != null && rect.width != null ? rect.width : (this._container != null ? this._container.clientWidth : 0);
            var containerHeight = rect != null && rect.height != null ? rect.height : (this._container != null ? this._container.clientHeight : 0);
            var menuWidth = menu.offsetWidth > 0 && menu.offsetWidth < containerWidth ? menu.offsetWidth : 160;
            var menuHeight = menu.offsetHeight > 0 && menu.offsetHeight < containerHeight ? menu.offsetHeight : Math.max(32, this.dgCMenu.length * 32);
            var left = clamp(pixel.x, 0, Math.max(0, containerWidth - menuWidth));
            var top = clamp(pixel.y, 0, Math.max(0, containerHeight - menuHeight));
            menu.style.left = Math.round(left) + 'px';
            menu.style.top = Math.round(top) + 'px';
            menu.style.visibility = 'visible';
            return false;
        },

        _hideContextMenu: function () {
            if (this._contextMenu != null) {
                this._contextMenu.style.visibility = 'hidden';
            }
            return this;
        },

        _installContextMenuHandlers: function () {
            if (this._contextMenuHandlers.length > 0) return;
            var canvas = this._map != null && typeof this._map.getCanvas == 'function' ? this._map.getCanvas() : null;
            if (canvas == null || typeof canvas.addEventListener != 'function') return;
            var self = this;
            var onContextMenu = function (event) {
                return self._showContextMenu(event);
            };
            var onDocumentMouseDown = function (event) {
                if (self._contextMenu == null) return;
                var target = event != null ? event.target : null;
                if (target != null && typeof self._contextMenu.contains == 'function' && self._contextMenu.contains(target)) return;
                self._hideContextMenu();
            };
            var onResize = function () {
                self._hideContextMenu();
            };
            canvas.addEventListener('contextmenu', onContextMenu);
            this._contextMenuHandlers.push({ target: canvas, name: 'contextmenu', handler: onContextMenu });
            if (window.document != null && typeof window.document.addEventListener == 'function') {
                window.document.addEventListener('mousedown', onDocumentMouseDown);
                this._contextMenuHandlers.push({ target: window.document, name: 'mousedown', handler: onDocumentMouseDown });
            }
            if (window.addEventListener != null) {
                window.addEventListener('resize', onResize);
                this._contextMenuHandlers.push({ target: window, name: 'resize', handler: onResize });
            }
        },

        _removeContextMenu: function () {
            for (var i = 0; i < this._contextMenuHandlers.length; i++) {
                var entry = this._contextMenuHandlers[i];
                if (entry.target != null && typeof entry.target.removeEventListener == 'function') {
                    entry.target.removeEventListener(entry.name, entry.handler);
                }
            }
            this._contextMenuHandlers = [];
            if (this._contextMenu != null && this._contextMenu.parentNode != null) {
                this._contextMenu.parentNode.removeChild(this._contextMenu);
            }
            this._contextMenu = null;
            this._contextMenuLastEvent = null;
        },

        addMenu: function (menuItem) {
            var entry = this._normalizeContextMenuItem(menuItem);
            if (entry == null) return null;
            this.dgCMenu.push(entry);
            this._ensureContextMenu();
            this._installContextMenuHandlers();
            return this;
        },

        _dragBoxEventToPixel: function (event, preferClient) {
            if (event == null) return null;
            if (event.originalEvent != null) return this._dragBoxEventToPixel(event.originalEvent, preferClient);
            if (preferClient === true && event.clientX != null && event.clientY != null && this._container != null && typeof this._container.getBoundingClientRect == 'function') {
                var preferRect = this._container.getBoundingClientRect();
                return { x: event.clientX - preferRect.left, y: event.clientY - preferRect.top };
            }
            if (event.point != null) {
                return {
                    x: event.point.x != null ? event.point.x : event.point[0],
                    y: event.point.y != null ? event.point.y : event.point[1]
                };
            }
            if (event.offsetX != null && event.offsetY != null) {
                return { x: event.offsetX, y: event.offsetY };
            }
            if (event.clientX != null && event.clientY != null && this._container != null && typeof this._container.getBoundingClientRect == 'function') {
                var rect = this._container.getBoundingClientRect();
                return { x: event.clientX - rect.left, y: event.clientY - rect.top };
            }
            return null;
        },

        _ensureDragBoxOverlay: function () {
            if (this._dragBoxOverlay != null) return this._dragBoxOverlay;
            if (this._container == null || window.document == null || typeof window.document.createElement != 'function') return null;
            if (this._container.style != null && (this._container.style.position == null || this._container.style.position === '')) {
                this._container.style.position = 'relative';
            }
            var overlay = window.document.createElement('div');
            overlay.id = 'easymap-maplibre-dragbox';
            overlay.className = 'easymap-maplibre-dragbox';
            overlay.setAttribute('easymap_id', 'easymap-maplibre-dragbox');
            overlay.style.display = 'none';
            this._container.appendChild(overlay);
            this._dragBoxOverlay = overlay;
            return overlay;
        },

        _updateDragBoxOverlay: function (startPixel, endPixel) {
            var overlay = this._ensureDragBoxOverlay();
            if (overlay == null || startPixel == null || endPixel == null) return;
            var left = Math.min(startPixel.x, endPixel.x);
            var top = Math.min(startPixel.y, endPixel.y);
            var width = Math.abs(endPixel.x - startPixel.x);
            var height = Math.abs(endPixel.y - startPixel.y);
            overlay.style.display = '';
            overlay.style.left = left + 'px';
            overlay.style.top = top + 'px';
            overlay.style.width = width + 'px';
            overlay.style.height = height + 'px';
        },

        _removeDragBoxOverlay: function () {
            if (this._dragBoxOverlay != null && this._dragBoxOverlay.parentNode != null) {
                this._dragBoxOverlay.parentNode.removeChild(this._dragBoxOverlay);
            }
            this._dragBoxOverlay = null;
        },

        _getDragBoxExtent: function (startPixel, endPixel) {
            if (this._map == null || typeof this._map.unproject != 'function' || startPixel == null || endPixel == null) return null;
            var start = this._map.unproject([startPixel.x, startPixel.y]);
            var end = this._map.unproject([endPixel.x, endPixel.y]);
            var startLng = start.lng != null ? start.lng : start[0];
            var startLat = start.lat != null ? start.lat : start[1];
            var endLng = end.lng != null ? end.lng : end[0];
            var endLat = end.lat != null ? end.lat : end[1];
            return [
                Math.min(startLng, endLng),
                Math.max(startLat, endLat),
                Math.max(startLng, endLng),
                Math.min(startLat, endLat)
            ];
        },

        _pauseDragBoxMapInteractions: function () {
            var states = {};
            var names = ['dragPan', 'boxZoom'];
            for (var i = 0; i < names.length; i++) {
                var name = names[i];
                var handler = this._map != null ? this._map[name] : null;
                if (handler == null || typeof handler.disable != 'function') {
                    states[name] = false;
                    continue;
                }
                var enabled = true;
                if (typeof handler.isEnabled == 'function') {
                    enabled = handler.isEnabled() === true;
                }
                states[name] = enabled;
                if (enabled === true) {
                    handler.disable();
                }
            }
            this._dragBoxInteractionStates = states;
        },

        _restoreDragBoxMapInteractions: function () {
            if (this._dragBoxInteractionStates == null) return;
            var names = ['dragPan', 'boxZoom'];
            for (var i = 0; i < names.length; i++) {
                var name = names[i];
                var handler = this._map != null ? this._map[name] : null;
                if (this._dragBoxInteractionStates[name] === true && handler != null && typeof handler.enable == 'function') {
                    handler.enable();
                }
            }
            this._dragBoxInteractionStates = null;
        },

        enableDragBox: function (callback) {
            this.cancelDrawMode();
            this.disableDragBox();
            if (this._map == null || typeof this._map.getCanvas != 'function') return this;
            var canvas = this._map.getCanvas();
            if (canvas == null || typeof canvas.addEventListener != 'function') return this;
            var self = this;
            this._dragBoxPreviousCursor = canvas.style != null ? (canvas.style.cursor || '') : '';
            this._dragBoxState = {
                callback: typeof callback == 'function' ? callback : null,
                dragging: false,
                startPixel: null,
                endPixel: null,
                box_: {
                    startPixel_: null,
                    endPixel_: null
                }
            };
            if (canvas.style != null) canvas.style.cursor = 'crosshair';
            if (this._container != null) this._container.setAttribute('data-easymap-dragbox', '1');
            this._pauseDragBoxMapInteractions();

            var onMouseDown = function (event) {
                if (event != null && event.button != null && event.button !== 0) return;
                var pixel = self._dragBoxEventToPixel(event);
                if (pixel == null) return;
                if (event != null && event.preventDefault != null) event.preventDefault();
                if (event != null && event.stopPropagation != null) event.stopPropagation();
                self._dragBoxState.dragging = true;
                self._dragBoxState.startPixel = pixel;
                self._dragBoxState.endPixel = pixel;
                self._dragBoxState.box_.startPixel_ = [pixel.x, pixel.y];
                self._dragBoxState.box_.endPixel_ = [pixel.x, pixel.y];
                self._updateDragBoxOverlay(pixel, pixel);
            };
            var onMouseMove = function (event) {
                if (self._dragBoxState == null || self._dragBoxState.dragging !== true) return;
                var pixel = self._dragBoxEventToPixel(event, true);
                if (pixel == null) return;
                if (event != null && event.preventDefault != null) event.preventDefault();
                self._dragBoxState.endPixel = pixel;
                self._dragBoxState.box_.endPixel_ = [pixel.x, pixel.y];
                self._updateDragBoxOverlay(self._dragBoxState.startPixel, pixel);
            };
            var onMouseUp = function (event) {
                if (self._dragBoxState == null || self._dragBoxState.dragging !== true) return;
                var pixel = self._dragBoxEventToPixel(event, true) || self._dragBoxState.endPixel;
                self._dragBoxState.dragging = false;
                self._dragBoxState.endPixel = pixel;
                self._dragBoxState.box_.endPixel_ = [pixel.x, pixel.y];
                self._updateDragBoxOverlay(self._dragBoxState.startPixel, pixel);
                var extent = self._getDragBoxExtent(self._dragBoxState.startPixel, pixel);
                var dragbox = {
                    box_: {
                        startPixel_: self._dragBoxState.box_.startPixel_.slice(),
                        endPixel_: self._dragBoxState.box_.endPixel_.slice()
                    },
                    startPixel_: self._dragBoxState.box_.startPixel_.slice(),
                    endPixel_: self._dragBoxState.box_.endPixel_.slice()
                };
                var cb = self._dragBoxState.callback;
                self._removeDragBoxOverlay();
                if (cb != null && extent != null) {
                    cb.call(extent, extent, dragbox);
                }
            };

            canvas.addEventListener('mousedown', onMouseDown);
            window.document.addEventListener('mousemove', onMouseMove);
            window.document.addEventListener('mouseup', onMouseUp);
            this._dragBoxHandlers.push({ target: canvas, name: 'mousedown', handler: onMouseDown });
            this._dragBoxHandlers.push({ target: window.document, name: 'mousemove', handler: onMouseMove });
            this._dragBoxHandlers.push({ target: window.document, name: 'mouseup', handler: onMouseUp });
            return this;
        },

        disableDragBox: function () {
            for (var i = 0; i < this._dragBoxHandlers.length; i++) {
                var entry = this._dragBoxHandlers[i];
                if (entry.target != null && typeof entry.target.removeEventListener == 'function') {
                    entry.target.removeEventListener(entry.name, entry.handler);
                }
            }
            this._dragBoxHandlers = [];
            this._dragBoxState = null;
            this._removeDragBoxOverlay();
            this._restoreDragBoxMapInteractions();
            if (this._map != null && typeof this._map.getCanvas == 'function') {
                var canvas = this._map.getCanvas();
                if (canvas != null && canvas.style != null) canvas.style.cursor = this._dragBoxPreviousCursor || '';
            }
            this._dragBoxPreviousCursor = '';
            if (this._container != null) this._container.setAttribute('data-easymap-dragbox', '0');
            return this;
        },

        _normalizeDrawMode: function (dtype) {
            dtype = String(dtype || '').toLowerCase();
            if (dtype == 'line') return 'polyline';
            if (dtype == 'erbl') return 'polyline';
            if (dtype == 'polyline' || dtype == 'polygon' || dtype == 'box' || dtype == 'circle') return dtype;
            return null;
        },

        _ensureDrawLayer: function () {
            if (this._drawLayer != null && this._drawLayer.parentNode != null) return this._drawLayer;
            if (this._container == null || window.document == null || typeof window.document.createElement != 'function') return null;
            if (this._container.style != null && (this._container.style.position == null || this._container.style.position === '')) {
                this._container.style.position = 'relative';
            }
            var layer = window.document.createElement('div');
            layer.className = 'easymap-maplibre-draw-layer';
            layer.setAttribute('easymap_id', 'easymap-maplibre-draw-layer');
            var svg = createSvgElement('svg');
            try { svg.className = 'easymap-maplibre-draw-svg'; } catch (err) { }
            if (svg.setAttribute != null) {
                svg.setAttribute('class', 'easymap-maplibre-draw-svg');
                svg.setAttribute('width', '100%');
                svg.setAttribute('height', '100%');
            }
            var path = createSvgElement('path');
            try { path.className = 'easymap-maplibre-draw-path'; } catch (err2) { }
            if (path.setAttribute != null) path.setAttribute('class', 'easymap-maplibre-draw-path');
            svg.appendChild(path);
            var tooltip = window.document.createElement('div');
            tooltip.className = 'easymap-maplibre-draw-tooltip';
            tooltip.setAttribute('easymap_id', 'easymap-maplibre-draw-tooltip');
            layer.appendChild(svg);
            layer.appendChild(tooltip);
            this._container.appendChild(layer);
            this._drawLayer = layer;
            this._drawSvg = svg;
            this._drawPath = path;
            this._drawTooltip = tooltip;
            return layer;
        },

        _removeDrawLayer: function () {
            if (this._drawLayer != null && this._drawLayer.parentNode != null) {
                this._drawLayer.parentNode.removeChild(this._drawLayer);
            }
            this._drawLayer = null;
            this._drawSvg = null;
            this._drawPath = null;
            this._drawTooltip = null;
        },

        _setDrawTooltip: function (message, dgxy) {
            this._ensureDrawLayer();
            if (this._drawTooltip == null) return;
            this._drawTooltip.className = 'easymap-maplibre-draw-tooltip';
            this._drawTooltip.textContent = message || '';
            var pixel = dgxy != null ? this._projectPixel(dgxy) : null;
            if (pixel != null) {
                this._drawTooltip.style.left = Math.round(pixel[0] + 12) + 'px';
                this._drawTooltip.style.top = Math.round(pixel[1] + 12) + 'px';
            }
        },

        _getDrawGeometryClassName: function (geometry, completed) {
            var className = 'easymap-maplibre-draw-path';
            if (geometry != null && geometry.type == 'LineString') className += ' easymap-maplibre-draw-path-line';
            if (completed === true) className += ' easymap-maplibre-draw-path-done';
            return className;
        },

        _drawGeometryToPath: function (geometry) {
            if (geometry == null) return '';
            var coordinates = null;
            var close = false;
            if (geometry.type == 'Circle') {
                coordinates = circleGeometryToPolygon(geometry)[0];
                close = true;
            }
            else if (geometry.type == 'Polygon') {
                coordinates = geometry.coordinates != null ? geometry.coordinates[0] : null;
                close = true;
            }
            else if (geometry.type == 'LineString') {
                coordinates = geometry.coordinates;
            }
            if (!Array.isArray(coordinates) || coordinates.length <= 0) return '';
            var d = '';
            for (var i = 0; i < coordinates.length; i++) {
                var pixel = this._projectPixel(coordinateToDgXY(coordinates[i]));
                if (pixel == null) continue;
                d += (d === '' ? 'M ' : ' L ') + Math.round(pixel[0]) + ' ' + Math.round(pixel[1]);
            }
            if (d !== '' && close === true) d += ' Z';
            return d;
        },

        _renderDrawGeometry: function (geometry, completed) {
            this._ensureDrawLayer();
            if (this._drawPath == null) return;
            var className = this._getDrawGeometryClassName(geometry, completed);
            try { this._drawPath.className = className; } catch (err) { }
            if (this._drawPath.setAttribute != null) {
                this._drawPath.setAttribute('class', className);
                this._drawPath.setAttribute('d', this._drawGeometryToPath(geometry));
                if (geometry != null && geometry.type != null) this._drawPath.setAttribute('data-easymap-geometry-type', geometry.type);
            }
        },

        _getDrawTooltipCoordinate: function (geometry) {
            if (geometry == null) return null;
            if (geometry.type == 'LineString' && Array.isArray(geometry.coordinates) && geometry.coordinates.length > 0) {
                return coordinateToDgXY(geometry.coordinates[geometry.coordinates.length - 1]);
            }
            if (geometry.type == 'Circle') {
                return geometry.center != null ? coordinateToDgXY(geometry.center) : null;
            }
            if (geometry.type == 'Polygon' && Array.isArray(geometry.coordinates) && Array.isArray(geometry.coordinates[0])) {
                var ring = geometry.coordinates[0];
                if (ring.length <= 0) return null;
                var count = 0;
                var sumX = 0;
                var sumY = 0;
                for (var i = 0; i < ring.length; i++) {
                    if (i == ring.length - 1 && coordinateEquals(ring[i], ring[0])) continue;
                    sumX += parseFloat(ring[i][0]);
                    sumY += parseFloat(ring[i][1]);
                    count++;
                }
                return count > 0 ? new window.dgXY(sumX / count, sumY / count) : coordinateToDgXY(ring[0]);
            }
            return null;
        },

        _formatDrawMeasureText: function (measure) {
            if (measure == null || measure.geom == null) return '';
            if (measure.geom.type == 'LineString') return formatDrawLength(measure.length != null ? measure.length : measure.measure);
            if (measure.geom.type == 'Polygon') return formatDrawArea(measure.area != null ? measure.area : measure.measure);
            if (measure.geom.type == 'Circle') return formatDrawArea(measure.area != null ? measure.area : measure.measure);
            return '';
        },

        _setDrawMeasureTooltip: function (measure) {
            this._ensureDrawLayer();
            if (this._drawTooltip == null || measure == null) return;
            var text = this._formatDrawMeasureText(measure);
            if (text === '') return;
            this._drawTooltip.className = 'easymap-maplibre-draw-tooltip easymap-maplibre-draw-measure';
            this._drawTooltip.textContent = text;
            var dgxy = this._getDrawTooltipCoordinate(measure.geom);
            var pixel = dgxy != null ? this._projectPixel(dgxy) : null;
            if (pixel != null) {
                this._drawTooltip.style.left = Math.round(pixel[0]) + 'px';
                this._drawTooltip.style.top = Math.round(pixel[1]) + 'px';
            }
        },

        _rerenderDrawOverlay: function () {
            if (this._drawState != null) {
                this._updateDrawOverlay();
                return;
            }
            if (this._drawMeasure != null && this._drawMeasure.geom != null && this._drawLayer != null) {
                this._renderDrawGeometry(this._drawMeasure.geom, true);
                this._setDrawMeasureTooltip(this._drawMeasure);
            }
        },

        _installDrawRenderHandlers: function () {
            if (this._drawRenderHandlers.length > 0 || this._map == null || typeof this._map.on != 'function') return;
            var self = this;
            var events = ['move', 'zoom', 'resize', 'moveend', 'zoomend'];
            for (var i = 0; i < events.length; i++) {
                (function (name) {
                    var handler = function () {
                        self._rerenderDrawOverlay();
                    };
                    self._map.on(name, handler);
                    self._drawRenderHandlers.push({ name: name, handler: handler });
                })(events[i]);
            }
        },

        _removeDrawRenderHandlers: function () {
            for (var i = 0; i < this._drawRenderHandlers.length; i++) {
                var entry = this._drawRenderHandlers[i];
                if (this._map != null && typeof this._map.off == 'function') {
                    this._map.off(entry.name, entry.handler);
                }
            }
            this._drawRenderHandlers = [];
        },

        _makeBoxCoordinates: function (start, end) {
            var a = dgxyToCoordinate(start);
            var b = dgxyToCoordinate(end);
            if (a == null || b == null) return [];
            var west = Math.min(a[0], b[0]);
            var east = Math.max(a[0], b[0]);
            var south = Math.min(a[1], b[1]);
            var north = Math.max(a[1], b[1]);
            return [[west, south], [east, south], [east, north], [west, north]];
        },

        _makeBoxGeometry: function (start, end) {
            return {
                type: 'Polygon',
                coordinates: [closeRing(this._makeBoxCoordinates(start, end))]
            };
        },

        _makeCircleGeometry: function (center, end) {
            var centerCoordinate = dgxyToCoordinate(center);
            var endCoordinate = dgxyToCoordinate(end);
            var radius = centerCoordinate != null && endCoordinate != null ? haversineDistance(centerCoordinate, endCoordinate) : 0;
            return {
                type: 'Circle',
                center: centerCoordinate,
                end: endCoordinate,
                radius: radius,
                radiusMeters: radius,
                steps: 64
            };
        },

        _getPreviewDrawGeometry: function () {
            var state = this._drawState;
            if (state == null) return null;
            if (state.mode == 'polyline') {
                var lineCoordinates = dgxyListToCoordinates(state.points);
                if (state.previewPoint != null) {
                    var previewLine = dgxyToCoordinate(state.previewPoint);
                    if (previewLine != null && (lineCoordinates.length <= 0 || !coordinateEquals(previewLine, lineCoordinates[lineCoordinates.length - 1]))) {
                        lineCoordinates.push(previewLine);
                    }
                }
                return { type: 'LineString', coordinates: lineCoordinates };
            }
            if (state.mode == 'polygon') {
                var polygonCoordinates = dgxyListToCoordinates(state.points);
                if (state.previewPoint != null) {
                    var previewPolygon = dgxyToCoordinate(state.previewPoint);
                    if (previewPolygon != null && (polygonCoordinates.length <= 0 || !coordinateEquals(previewPolygon, polygonCoordinates[polygonCoordinates.length - 1]))) {
                        polygonCoordinates.push(previewPolygon);
                    }
                }
                if (polygonCoordinates.length >= 3) return { type: 'Polygon', coordinates: [closeRing(polygonCoordinates)] };
                return { type: 'LineString', coordinates: polygonCoordinates };
            }
            if (state.mode == 'box' && state.startPoint != null && state.previewPoint != null) {
                return this._makeBoxGeometry(state.startPoint, state.previewPoint);
            }
            if (state.mode == 'circle' && state.startPoint != null && state.previewPoint != null) {
                return this._makeCircleGeometry(state.startPoint, state.previewPoint);
            }
            return null;
        },

        _updateDrawOverlay: function () {
            var state = this._drawState;
            if (state == null) return;
            var geometry = this._getPreviewDrawGeometry();
            this._renderDrawGeometry(geometry, false);
            var anchor = state.previewPoint || state.points[state.points.length - 1] || state.startPoint;
            this._setDrawTooltip(state.started === true ? this._drawMessages.moving : this._drawMessages.start, anchor);
        },

        _consumeDrawEvent: function (event) {
            if (event == null) return;
            event.__easymapDrawConsumed = true;
            if (event.preventDefault != null) event.preventDefault();
            if (event.stopPropagation != null) event.stopPropagation();
            if (event.stopImmediatePropagation != null) event.stopImmediatePropagation();
        },

        _pauseDrawMapInteractions: function () {
            var states = {};
            var names = ['dragPan', 'boxZoom'];
            for (var i = 0; i < names.length; i++) {
                var name = names[i];
                var handler = this._map != null ? this._map[name] : null;
                if (handler == null || typeof handler.disable != 'function') {
                    states[name] = false;
                    continue;
                }
                var enabled = true;
                if (typeof handler.isEnabled == 'function') enabled = handler.isEnabled() === true;
                states[name] = enabled;
                if (enabled === true) handler.disable();
            }
            this._drawInteractionStates = states;
            this._drawDblClickZoomWasEnabled = this._dblClickZoomEnabled !== false;
            this._disableDblClickZoom();
        },

        _restoreDrawMapInteractions: function () {
            if (this._drawInteractionStates != null) {
                var names = ['dragPan', 'boxZoom'];
                for (var i = 0; i < names.length; i++) {
                    var name = names[i];
                    var handler = this._map != null ? this._map[name] : null;
                    if (this._drawInteractionStates[name] === true && handler != null && typeof handler.enable == 'function') {
                        handler.enable();
                    }
                }
            }
            this._drawInteractionStates = null;
            if (this._drawDblClickZoomWasEnabled === true) {
                this._enableDblClickZoom();
            }
        },

        _detachDrawHandlers: function () {
            var hadActiveDraw = this._drawState != null || this._drawHandlers.length > 0 || this._drawInteractionStates != null;
            for (var i = 0; i < this._drawHandlers.length; i++) {
                var entry = this._drawHandlers[i];
                if (entry.target != null && typeof entry.target.removeEventListener == 'function') {
                    entry.target.removeEventListener(entry.name, entry.handler);
                }
            }
            this._drawHandlers = [];
            if (hadActiveDraw === true && this._map != null && typeof this._map.getCanvas == 'function') {
                var canvas = this._map.getCanvas();
                if (canvas != null && canvas.style != null) canvas.style.cursor = this._drawPreviousCursor || '';
            }
            this._drawPreviousCursor = '';
            if (hadActiveDraw === true) this._restoreDrawMapInteractions();
            this._drawState = null;
            if (hadActiveDraw === true && this._container != null) this._container.setAttribute('data-easymap-draw', '0');
        },

        _makeDrawMeasure: function (mode, resultPoints, geometry) {
            var points = Array.isArray(resultPoints) ? resultPoints.slice() : [];
            if (geometry.type == 'LineString' && Array.isArray(geometry.coordinates)) {
                points = coordinatesToDgXYList(geometry.coordinates);
            }
            else if (geometry.type == 'Polygon' && Array.isArray(geometry.coordinates) && Array.isArray(geometry.coordinates[0])) {
                points = coordinatesToDgXYList(geometry.coordinates[0]);
            }
            var measure = {
                type: mode,
                dtype: mode,
                points: points,
                geom: geometry,
                measure: 0
            };
            if (geometry.type == 'LineString') {
                measure.measure = measureLine(geometry.coordinates);
                measure.length = measure.measure;
            }
            else if (geometry.type == 'Polygon') {
                measure.measure = measurePolygonArea(geometry.coordinates[0]);
                measure.area = measure.measure;
            }
            else if (geometry.type == 'Circle') {
                measure.center = geometry.center != null ? coordinateToDgXY(geometry.center) : (points[0] || null);
                measure.start = measure.center;
                measure.end = geometry.end != null ? coordinateToDgXY(geometry.end) : (points[1] || null);
                measure.points = [];
                if (measure.center != null) measure.points.push(measure.center);
                if (measure.end != null) measure.points.push(measure.end);
                measure.radius = geometry.radiusMeters || geometry.radius || 0;
                measure.area = Math.PI * measure.radius * measure.radius;
                measure.measure = measure.area;
            }
            measure.wkt = this.geometryToWKT(geometry);
            return measure;
        },

        _completeDraw: function (geometry, resultPoints) {
            if (this._drawState == null || geometry == null || !Array.isArray(resultPoints)) return;
            var endFunc = this._drawState.drawEnd;
            this._drawMeasure = this._makeDrawMeasure(this._drawState.mode, resultPoints, geometry);
            this._drawResult = this._drawMeasure != null ? this._drawMeasure.points : resultPoints;
            if (this._container != null) this._container.setAttribute('data-easymap-draw-result', '1');
            this._renderDrawGeometry(geometry, true);
            this._setDrawMeasureTooltip(this._drawMeasure);
            this._detachDrawHandlers();
            if (typeof endFunc == 'function') {
                endFunc.call(this, this._drawResult, this._drawMeasure);
            }
        },

        _handleDrawClick: function (event) {
            var state = this._drawState;
            if (state == null) return;
            this._consumeDrawEvent(event);
            var dgxy = this._eventToDgXY(event);
            if (state.started !== true) {
                state.started = true;
                state.startPoint = dgxy;
                state.previewPoint = dgxy;
                if (state.mode == 'polyline' || state.mode == 'polygon') state.points.push(dgxy);
                this._updateDrawOverlay();
                if (typeof state.drawStart == 'function') state.drawStart.call(this, dgxy, state);
                return;
            }
            if (state.mode == 'polyline' || state.mode == 'polygon') {
                state.points.push(dgxy);
                state.previewPoint = dgxy;
                this._updateDrawOverlay();
                return;
            }
            if (state.mode == 'box') {
                var boxCoordinates = this._makeBoxCoordinates(state.startPoint, dgxy);
                this._completeDraw(this._makeBoxGeometry(state.startPoint, dgxy), coordinatesToDgXYList(boxCoordinates));
                return;
            }
            if (state.mode == 'circle') {
                this._completeDraw(this._makeCircleGeometry(state.startPoint, dgxy), [state.startPoint, dgxy]);
            }
        },

        _handleDrawMove: function (event) {
            var state = this._drawState;
            if (state == null) return;
            this._consumeDrawEvent(event);
            var dgxy = this._eventToDgXY(event);
            state.previewPoint = dgxy;
            this._updateDrawOverlay();
            if (state.started === true && typeof state.drawMoving == 'function') {
                state.drawMoving.call(this, dgxy, state);
            }
        },

        _handleDrawDoubleClick: function (event) {
            var state = this._drawState;
            if (state == null) return;
            this._consumeDrawEvent(event);
            if (state.mode == 'polyline') {
                var linePoints = trimTrailingDuplicateDgXY(state.points);
                if (linePoints.length < 2) return;
                this._completeDraw({
                    type: 'LineString',
                    coordinates: dgxyListToCoordinates(linePoints)
                }, linePoints.slice());
                return;
            }
            if (state.mode == 'polygon') {
                var polygonPoints = trimTrailingDuplicateDgXY(state.points);
                if (polygonPoints.length < 3) return;
                this._completeDraw({
                    type: 'Polygon',
                    coordinates: [closeRing(dgxyListToCoordinates(polygonPoints))]
                }, polygonPoints.slice());
            }
        },

        setDrawMessage: function (startMessage, movingMessage) {
            if (startMessage != null) this._drawMessages.start = String(startMessage);
            if (movingMessage != null) this._drawMessages.moving = String(movingMessage);
            if (this._drawState != null) this._updateDrawOverlay();
            return this;
        },

        setDrawMode: function (dtype, draw_end_func, draw_start_func, draw_moving_func, extra_opt) {
            var mode = this._normalizeDrawMode(dtype);
            this.cancelDrawMode();
            if (mode == null) {
                console.log('MapLibre draw mode unsupported: ' + dtype);
                return this;
            }
            this.disableDragBox();
            if (this._map == null || typeof this._map.getCanvas != 'function') return this;
            var canvas = this._map.getCanvas();
            if (canvas == null || typeof canvas.addEventListener != 'function') return this;
            this._drawResult = null;
            this._drawMeasure = null;
            if (this._container != null) {
                this._container.setAttribute('data-easymap-draw', '1');
                this._container.setAttribute('data-easymap-draw-result', '0');
            }
            this._drawState = {
                mode: mode,
                dtype: dtype,
                points: [],
                started: false,
                startPoint: null,
                previewPoint: null,
                drawEnd: typeof draw_end_func == 'function' ? draw_end_func : null,
                drawStart: typeof draw_start_func == 'function' ? draw_start_func : null,
                drawMoving: typeof draw_moving_func == 'function' ? draw_moving_func : null,
                extra: extra_opt || {}
            };
            this._removeDrawLayer();
            this._ensureDrawLayer();
            this._setDrawTooltip(this._drawMessages.start, null);
            this._drawPreviousCursor = canvas.style != null ? (canvas.style.cursor || '') : '';
            if (canvas.style != null) canvas.style.cursor = 'crosshair';
            this._pauseDrawMapInteractions();
            var self = this;
            var onClick = function (event) { self._handleDrawClick(event); };
            var onMove = function (event) { self._handleDrawMove(event); };
            var onDoubleClick = function (event) { self._handleDrawDoubleClick(event); };
            canvas.addEventListener('click', onClick);
            canvas.addEventListener('mousemove', onMove);
            canvas.addEventListener('dblclick', onDoubleClick);
            this._drawHandlers.push({ target: canvas, name: 'click', handler: onClick });
            this._drawHandlers.push({ target: canvas, name: 'mousemove', handler: onMove });
            this._drawHandlers.push({ target: canvas, name: 'dblclick', handler: onDoubleClick });
            return this;
        },

        getDrawResult: function () {
            return this._drawResult;
        },

        getDrawMeasure: function () {
            return this._drawMeasure;
        },

        getDrawResultObject: function () {
            return this._drawMeasure;
        },

        clearDraw: function () {
            this.cancelDrawMode();
            this._drawResult = null;
            this._drawMeasure = null;
            this._removeDrawLayer();
            if (this._container != null) {
                this._container.setAttribute('data-easymap-draw', '0');
                this._container.setAttribute('data-easymap-draw-result', '0');
            }
            return this;
        },

        cancelDrawMode: function () {
            var hadActiveDraw = this._drawState != null || this._drawHandlers.length > 0;
            this._detachDrawHandlers();
            if (hadActiveDraw === true) this._removeDrawLayer();
            return this;
        },

        isDrawMode: function () {
            return this._drawState != null;
        },

        geometryToWKT: function (geometry) {
            return geometryToWktString(geometry);
        },

        _createGroundOverlayQuadItem: function (imageUrl, wktString, options) {
            options = options || {};
            var item = {
                _id: makeId('dggroundoverlayquad'),
                _type: 'dggroundoverlayquad',
                _imageUrl: imageUrl == null ? '' : String(imageUrl),
                _wktString: wktString == null ? '' : String(wktString),
                _instance: null,
                _parent: this,
                _visible: true,
                _opacity: options.opacity == null ? 1 : parseFloat(options.opacity)
            };
            if (isNaN(item._opacity)) item._opacity = 1;
            if (item._opacity < 0) item._opacity = 0;
            if (item._opacity > 1) item._opacity = 1;
            if (ns != null && typeof ns.attachItemBasics == 'function') ns.attachItemBasics(item);
            item.getOpacity = function () {
                return this._opacity;
            };
            item.setOpacity = function (opacity) {
                this._opacity = parseFloat(opacity);
                if (isNaN(this._opacity)) this._opacity = 1;
                if (this._opacity < 0) this._opacity = 0;
                if (this._opacity > 1) this._opacity = 1;
                if (this._easymap != null && typeof this._easymap._refreshItemStyle == 'function') {
                    this._easymap._refreshItemStyle(this);
                }
                return this;
            };
            item.getCoordinates = function () {
                return getGroundOverlayQuadCoordinatesFromWkt(this._wktString);
            };
            item.setWKT = function (wkt) {
                this._wktString = wkt == null ? '' : String(wkt);
                if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
                    this._easymap._updateItemData(this);
                }
                return this;
            };
            item.setURL = function (url) {
                this._imageUrl = url == null ? '' : String(url);
                if (this._easymap != null && typeof this._easymap._updateItemData == 'function') {
                    this._easymap._updateItemData(this);
                }
                return this;
            };
            item.getURL = function () {
                return this._imageUrl;
            };
            return item;
        },

        addGroundOverlayQuad: function (imageUrl, wktString, options) {
            var item = this._createGroundOverlayQuadItem(imageUrl, wktString, options || {});
            this.addItem(item);
            return item;
        },

        removeGroundOverlayQuad: function (item) {
            if (item == null) return this;
            var target = item.item != null && isGroundOverlayQuadItem(item.item) ? item.item : item;
            if (isGroundOverlayQuadItem(target) && target._instance != null) {
                this.removeItem(target);
            }
            return this;
        },

        addItem: function (item) {
            if (item == null) return null;
            if (Array.isArray(item)) {
                for (var i = 0; i < item.length; i++) {
                    this.addItem(item[i]);
                }
                return item;
            }
            var self = this;
            this._ready(function () {
                self._addItemNow(item);
            });
            return item;
        },

        _addItemNow: function (item) {
            if (item._easymap != null && item._easymap !== this) {
                item._easymap.removeItem(item);
            }
            if (item._instance != null) {
                this.removeItem(item);
            }
            item._easymap = this;
            var record = null;
            switch ((item._type || '').toLowerCase()) {
                case 'text':
                case 'dgtext':
                    record = this._addText(item);
                    break;
                case 'point':
                case 'dgpoint':
                    record = this._addPoint(item);
                    break;
                case 'polyline':
                case 'dgpolyline':
                    record = this._addPolyline(item);
                    break;
                case 'polygon':
                case 'dgpolygon':
                    record = this._addPolygon(item);
                    break;
                case 'curve':
                case 'dgcurve':
                    record = this._addCurve(item);
                    break;
                case 'dgmarker':
                    record = this._addMarker(item);
                    break;
                case 'dgwkt':
                    record = this._addWkt(item);
                    break;
                case 'dggeojson':
                    record = this._addDgGeoJson(item);
                    break;
                case 'dgkml':
                    record = this._addKml(item);
                    break;
                case 'dggml':
                    record = this._addGml(item);
                    break;
                case 'dgsource':
                    record = this._addSourceItem(item);
                    break;
                case 'dgstaticimage':
                case 'staticimage':
                    record = this._addStaticImage(item);
                    break;
                case 'dggroundoverlayquad':
                case 'groundoverlayquad':
                    record = this._addGroundOverlayQuad(item);
                    break;
                case 'dg3d':
                    record = this._add3DPlaceholder(item);
                    break;
                default:
                    record = this._makeEmptyRecord(item, 'unsupported');
                    break;
            }
            item._instance = record;
            if (record.zIndex == null) record.zIndex = item.getZIndex != null ? item.getZIndex() : 0;
            if (record.addOrder == null) record.addOrder = this._itemAddOrder++;
            this._items[item._id || record.id] = record;
            if (isPolylineItem(item) && item._isLinestringArrowEnabled === true) {
                this._enablePolylineArrow(item);
            }
            this._setItemVisible(item, item.getVisible == null ? true : item.getVisible());
            this._reorderItemLayers();
            this._registerWktSpiderDisplayCleanup(item);
            if (item._setUpperZoomByBoundary === true) {
                this._fitItemToBounds(item, item._upperZoomByBoundaryOptions);
            }
            if ((item._type || '').toLowerCase() == 'dggml') {
                this._loadGmlItem(item, record);
            }
            if ((item._type || '').toLowerCase() == 'dgkml') {
                this._loadKmlItem(item, record);
            }
            if ((item._type || '').toLowerCase() == 'dggeojson') {
                this._loadGeoJsonItem(item, record);
            }
            return record;
        },

        _makeEmptyRecord: function (item, status) {
            return {
                id: makeId('item'),
                item: item,
                status: status || 'empty',
                sourceId: null,
                layerIds: [],
                clickHandlers: []
            };
        },

        _clearDomElement: function (element) {
            if (element == null) return;
            if (element.children != null) {
                while (element.children.length > 0) {
                    if (typeof element.removeChild == 'function') element.removeChild(element.children[0]);
                    else element.children.splice(0, 1);
                }
            }
            element.innerHTML = '';
        },

        _renderMarkerDomContent: function (item, record, style) {
            if (record == null || record.visualElement == null) return;
            var html = item != null && item._icontype == 'string' ? item._htmlstr || '' : '';
            var contentKey = (item != null ? item._icontype : '') + '|' + (style.src || '') + '|' + style.width + '|' + style.height + '|' + html;
            if (record.contentKey == contentKey) return;
            this._clearDomElement(record.visualElement);
            if (html != '') {
                record.visualElement.innerHTML = html;
            }
            else if (style.src != '') {
                var img = window.document.createElement('img');
                img.setAttribute('src', style.src);
                img.style.width = style.width + 'px';
                img.style.height = style.height + 'px';
                img.style.display = 'block';
                img.style.border = '0';
                record.visualElement.appendChild(img);
            }
            else {
                var fallback = window.document.createElement('div');
                fallback.style.width = Math.max(8, style.width || 16) + 'px';
                fallback.style.height = Math.max(8, style.height || 16) + 'px';
                fallback.style.borderRadius = '50%';
                fallback.style.background = '#2563eb';
                fallback.style.border = '2px solid #ffffff';
                record.visualElement.appendChild(fallback);
            }
            record.contentKey = contentKey;
        },

        _applyDomMarkerStyle: function (item, record) {
            if (record == null || record.element == null) return;
            var style = ns.getMarkerStyle(item);
            this._renderMarkerDomContent(item, record, style);
            record.anchor = style.anchor;
            record.element.setAttribute('data-easymap-anchor', style.anchor);
            record.element.style.cursor = item._drag === true ? 'move' : 'pointer';
            record.element.style.zIndex = String(record.zIndex || (item.getZIndex != null ? item.getZIndex() : 0) || 0);
            if (record.visualElement != null) {
                record.visualElement.style.opacity = String(style.opacity);
                record.visualElement.style.transform = 'scale(' + style.scale + ') rotate(' + style.rotate + 'deg)';
                record.visualElement.style.transformOrigin = 'center center';
                record.visualElement.style.pointerEvents = 'auto';
            }
            if (record.labelElement != null) {
                var labelStyle = ns.getMarkerLabelStyle(item);
                var text = labelStyle.text || '';
                record.labelElement.textContent = text;
                record.labelElement.style.display = text == '' ? 'none' : 'block';
                record.labelElement.style.color = labelStyle.color;
                record.labelElement.style.opacity = String(labelStyle.opacity);
                record.labelElement.style.fontSize = labelStyle.size + 'px';
                record.labelElement.style.textShadow = '0 0 ' + labelStyle.haloWidth + 'px ' + labelStyle.haloColor;
                record.labelElement.style.textAlign = 'center';
                record.labelElement.style.whiteSpace = 'nowrap';
            }
        },

        _syncMarkerDgXYFromRecord: function (item, record) {
            if (item == null) return null;
            var lngLat = record != null && record.marker != null && typeof record.marker.getLngLat == 'function' ? record.marker.getLngLat() : null;
            var xy = lngLat != null ? new window.dgXY(lngLat.lng, lngLat.lat) : (item.getXY != null ? item.getXY() : item._dgxy);
            if (!(xy instanceof window.dgXY)) xy = new window.dgXY(xy);
            item._dgxy = xy;
            return xy;
        },

        _getMarkerFeaturesAtSameLocation: function (item) {
            var target = toLngLat(item != null && item.getXY != null ? item.getXY() : item != null ? item._dgxy : null);
            var features = [];
            if (target == null) return features;
            for (var key in this._items) {
                if (Object.prototype.hasOwnProperty.call(this._items, key) == false) continue;
                var record = this._items[key];
                var marker = record != null ? record.item : null;
                if (marker == null || marker._type != 'dgmarker') continue;
                var xy = toLngLat(marker.getXY != null ? marker.getXY() : marker._dgxy);
                if (xy == null) continue;
                if (Math.abs(xy[0] - target[0]) < 0.000000000001 && Math.abs(xy[1] - target[1]) < 0.000000000001) {
                    features.push({
                        values_: { _dgmarker: marker },
                        item: marker,
                        properties: marker._properties || {}
                    });
                }
            }
            return features;
        },

        _dispatchMarkerDomClick: function (record, event) {
            var item = record != null ? record.item : null;
            if (item == null) return;
            var xy = this._syncMarkerDgXYFromRecord(item, record);
            var features = this._getMarkerFeaturesAtSameLocation(item);
            var result = {
                engine: 'maplibre',
                type: 'dgmarker',
                itemType: 'dgmarker',
                cluster: false,
                item: item,
                feature: item,
                properties: item._properties || {},
                coordinate: xy != null ? [xy.x, xy.y] : null,
                originalEvent: event
            };
            if (typeof item._featureClick == 'function') item._featureClick(result);
            if (typeof item.onclick == 'function') item.onclick.call(item, xy, item, features);
            if (typeof item.onFeatureSelect == 'function') item.onFeatureSelect(result);
        },

        _dispatchMarkerDomPointer: function (record, name, event) {
            var item = record != null ? record.item : null;
            if (item == null) return;
            var xy = item.getXY != null ? item.getXY() : item._dgxy;
            if (!(xy instanceof window.dgXY)) xy = new window.dgXY(xy);
            var callback = item[name];
            if (typeof callback == 'function') callback.call(item, xy, item, event);
        },

        _bindMarkerDomEvents: function (record) {
            if (record == null || record.element == null) return;
            var self = this;
            record.domHandlers = record.domHandlers || [];
            function bind(name, handler) {
                record.element.addEventListener(name, handler);
                record.domHandlers.push({ name: name, handler: handler });
            }
            bind('click', function (event) {
                if (event != null && typeof event.stopPropagation == 'function') event.stopPropagation();
                self._dispatchMarkerDomClick(record, event);
            });
            bind('dblclick', function (event) {
                if (event != null && typeof event.stopPropagation == 'function') event.stopPropagation();
                self._dispatchMarkerDomPointer(record, 'ondblclick', event);
            });
            bind('mouseover', function (event) {
                self._dispatchMarkerDomPointer(record, 'onmouseover', event);
                self._dispatchMarkerDomPointer(record, 'mouseover', event);
            });
            bind('mouseout', function (event) {
                self._dispatchMarkerDomPointer(record, 'onmouseout', event);
                self._dispatchMarkerDomPointer(record, 'mouseout', event);
            });
            bind('mousedown', function (event) {
                self._dispatchMarkerDomPointer(record, 'mousedown', event);
            });
            bind('mouseup', function (event) {
                self._dispatchMarkerDomPointer(record, 'mouseup', event);
            });
        },

        _bindMarkerDragEvents: function (record) {
            if (record == null || record.marker == null || typeof record.marker.on != 'function') return;
            var self = this;
            var item = record.item;
            record.dragHandlers = record.dragHandlers || [];
            function bind(name, callbackName) {
                var handler = function () {
                    var xy = self._syncMarkerDgXYFromRecord(item, record);
                    if (typeof item[callbackName] == 'function') item[callbackName].call(item, xy, item);
                };
                record.marker.on(name, handler);
                record.dragHandlers.push({ name: name, handler: handler });
            }
            bind('dragstart', 'ondragstart');
            bind('dragend', 'ondragend');
        },

        _updateDomMarkerPosition: function (item, record) {
            if (record == null || record.marker == null || typeof record.marker.setLngLat != 'function') return;
            var lngLat = toLngLat(item.getXY != null ? item.getXY() : item._dgxy);
            if (lngLat != null) record.marker.setLngLat(lngLat);
        },

        _ensureImage: function (src) {
            if (src == null || src == '') return '';
            var imageId = ns.makeImageId(src);
            if (this._map.hasImage != null && this._map.hasImage(imageId) === false) {
                this._map.addImage(imageId, makeFallbackIconImage());
            }
            if (this._imageUrls[imageId] == src) return imageId;
            this._imageUrls[imageId] = src;
            var elementFallbackStarted = false;
            var startElementFallback = function (map) {
                if (elementFallbackStarted) return;
                elementFallbackStarted = true;
                loadImageElement(map, imageId, src);
            };
            if (typeof this._map.loadImage == 'function') {
                var self = this;
                this._map.loadImage(src, function (err, image) {
                    if (err != null || image == null) {
                        startElementFallback(self._map);
                        return;
                    }
                    replaceMapImage(self._map, imageId, image);
                });
                startElementFallback(this._map);
            }
            else {
                startElementFallback(this._map);
            }
            return imageId;
        },

        _addText: function (item) {
            var sourceId = makeId('text-source');
            var layerId = makeId('text-symbol');
            var style = ns.getTextStyle(item);
            var data = this._getTextGeoJson(item);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            this._map.addLayer({
                id: layerId,
                type: 'symbol',
                source: sourceId,
                layout: {
                    'text-field': ['get', '__easymap_text'],
                    'text-size': style.size,
                    'text-rotate': style.rotate,
                    'text-offset': style.offset,
                    'text-anchor': style.anchor,
                    'text-justify': 'center',
                    'text-allow-overlap': true,
                    'text-ignore-placement': true
                },
                paint: {
                    'text-color': style.color,
                    'text-opacity': style.opacity,
                    'text-halo-color': style.haloColor,
                    'text-halo-width': style.haloWidth
                }
            });
            var record = {
                id: sourceId,
                item: item,
                type: 'dgtext',
                itemType: 'dgtext',
                status: 'active',
                sourceId: sourceId,
                layerIds: [layerId],
                styleLayers: {
                    text: layerId
                },
                clickHandlers: []
            };
            this._bindItemClick(record, layerId);
            return record;
        },

        _getTextGeoJson: function (item) {
            var xy = item != null && typeof item.getXY == 'function' ? item.getXY() : new window.dgXY(item._x, item._y);
            var lngLat = toLngLat(xy) || [0, 0];
            var label = item != null && typeof item.getText == 'function' ? item.getText() : (item != null && item._label != null ? String(item._label) : '');
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: {
                            __easymap_item_id: item != null ? item._id : '',
                            __easymap_text: label,
                            easymap_type: 'dgtext',
                            _easymapClass: 'dgText',
                            label: label,
                            name: label
                        },
                        geometry: {
                            type: 'Point',
                            coordinates: lngLat
                        }
                    }
                ]
            };
        },

        _addPoint: function (item) {
            var sourceId = makeId('point-source');
            var layerId = makeId('point-circle');
            var style = ns.getPointStyle(item);
            var data = this._getPointGeoJson(item);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            this._map.addLayer({
                id: layerId,
                type: 'circle',
                source: sourceId,
                paint: {
                    'circle-radius': style.radius,
                    'circle-color': style.fillColor,
                    'circle-opacity': style.fillOpacity,
                    'circle-stroke-color': style.strokeColor,
                    'circle-stroke-opacity': style.strokeOpacity,
                    'circle-stroke-width': style.strokeWidth
                }
            });
            var record = {
                id: sourceId,
                item: item,
                type: 'dgpoint',
                itemType: 'dgpoint',
                status: 'active',
                sourceId: sourceId,
                layerIds: [layerId],
                styleLayers: {
                    point: layerId
                },
                clickHandlers: []
            };
            this._bindItemClick(record, layerId);
            return record;
        },

        _getPointGeoJson: function (item) {
            var xy = item != null && typeof item.getXY == 'function' ? item.getXY() : new window.dgXY(item._x, item._y);
            var lngLat = toLngLat(xy) || [0, 0];
            var label = item != null && typeof item.getLabel == 'function' ? item.getLabel() : (item != null && item._label != null ? String(item._label) : '');
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: {
                            __easymap_item_id: item != null ? item._id : '',
                            easymap_type: 'dgpoint',
                            _easymapClass: 'dgPoint',
                            label: label,
                            name: label
                        },
                        geometry: {
                            type: 'Point',
                            coordinates: lngLat
                        }
                    }
                ]
            };
        },

        _addPolyline: function (item) {
            var sourceId = makeId('polyline-source');
            var layerId = makeId('polyline-line');
            var style = ns.getPolylineStyle(item);
            var data = this._getPolylineGeoJson(item);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            this._map.addLayer({
                id: layerId,
                type: 'line',
                source: sourceId,
                layout: {
                    'line-cap': style.lineCap,
                    'line-join': style.lineJoin
                },
                paint: {
                    'line-color': style.color,
                    'line-opacity': style.opacity,
                    'line-width': style.width
                }
            });
            if (style.lineDash != null) {
                this._map.setPaintProperty(layerId, 'line-dasharray', style.lineDash);
            }
            var record = {
                id: sourceId,
                item: item,
                type: 'dgpolyline',
                itemType: 'dgpolyline',
                status: 'active',
                sourceId: sourceId,
                layerIds: [layerId],
                styleLayers: {
                    line: layerId
                },
                clickHandlers: []
            };
            this._bindItemClick(record, layerId);
            if (item._isLinestringArrowEnabled === true) {
                this._enablePolylineArrow(item);
            }
            return record;
        },

        _getPolylineGeoJson: function (item) {
            var coordinates = [];
            var xys = item != null && Array.isArray(item._xys) ? item._xys : [];
            for (var i = 0; i < xys.length; i++) {
                var lngLat = toLngLat(xys[i]);
                if (lngLat != null) coordinates.push(lngLat);
            }
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: {
                            __easymap_item_id: item != null ? item._id : '',
                            easymap_type: 'dgpolyline',
                            _easymapClass: 'dgPolyline'
                        },
                        geometry: {
                            type: 'LineString',
                            coordinates: coordinates
                        }
                    }
                ]
            };
        },

        _getPolylineArrowGeoJson: function (item) {
            var features = [];
            var xys = item != null && Array.isArray(item._xys) ? item._xys : [];
            for (var i = 1; i < xys.length; i++) {
                var start = toLngLat(xys[i - 1]);
                var end = toLngLat(xys[i]);
                if (start == null || end == null) continue;
                var dx = end[0] - start[0];
                var dy = end[1] - start[1];
                var rotate = -Math.atan2(dy, dx) * 180 / Math.PI;
                features.push({
                    type: 'Feature',
                    properties: {
                        __easymap_item_id: item != null ? item._id : '',
                        easymap_type: 'dgpolyline-arrow',
                        _easymapClass: 'dgPolylineArrow',
                        rotate: rotate
                    },
                    geometry: {
                        type: 'Point',
                        coordinates: end
                    }
                });
            }
            return this._makeFeatureCollection(features);
        },

        _enablePolylineArrow: function (item) {
            if (item == null || item._instance == null) return this;
            var record = item._instance;
            var src = item._lineStringIconsrc || 'https://openlayers.org/en/latest/examples/data/arrow.png';
            var scale = ns.toNumber(item._lineStringIconsrcScale, 1);
            var imageId = this._ensureImage(src);
            var data = this._getPolylineArrowGeoJson(item);
            if (record.arrowSourceId == null) {
                record.arrowSourceId = makeId('polyline-arrow-source');
                record.arrowLayerId = makeId('polyline-arrow-symbol');
                this._map.addSource(record.arrowSourceId, { type: 'geojson', data: data });
                this._map.addLayer({
                    id: record.arrowLayerId,
                    type: 'symbol',
                    source: record.arrowSourceId,
                    layout: {
                        'icon-image': imageId,
                        'icon-size': scale,
                        'icon-rotate': ['get', 'rotate'],
                        'icon-rotation-alignment': 'map',
                        'icon-allow-overlap': true,
                        'icon-ignore-placement': true
                    },
                    paint: {
                        'icon-opacity': 1
                    }
                });
                record.layerIds.push(record.arrowLayerId);
                record.sourceIds = [record.sourceId, record.arrowSourceId];
                record.styleLayers = record.styleLayers || {};
                record.styleLayers.arrow = record.arrowLayerId;
                this._setItemVisible(item, item.getVisible == null ? true : item.getVisible());
                this._reorderItemLayers();
                return this;
            }
            if (this._map.getSource(record.arrowSourceId) != null) {
                this._map.getSource(record.arrowSourceId).setData(data);
            }
            if (this._map.getLayer(record.arrowLayerId) != null) {
                this._setLayout(record.arrowLayerId, 'icon-image', imageId);
                this._setLayout(record.arrowLayerId, 'icon-size', scale);
            }
            return this;
        },

        _refreshPolylineArrow: function (item) {
            if (item == null || item._instance == null) return this;
            if (item._isLinestringArrowEnabled === true) return this._enablePolylineArrow(item);
            return this;
        },

        _removePolylineArrow: function (item) {
            if (item == null || item._instance == null) return this;
            var record = item._instance;
            if (record.arrowLayerId != null && this._map.getLayer(record.arrowLayerId) != null) {
                this._map.removeLayer(record.arrowLayerId);
            }
            if (record.arrowSourceId != null && this._map.getSource(record.arrowSourceId) != null) {
                this._map.removeSource(record.arrowSourceId);
            }
            if (record.layerIds != null) {
                record.layerIds = record.layerIds.filter(function (layerId) {
                    return layerId != record.arrowLayerId;
                });
            }
            if (record.sourceIds != null) {
                record.sourceIds = record.sourceIds.filter(function (sourceId) {
                    return sourceId != record.arrowSourceId;
                });
                if (record.sourceIds.length == 0 && record.sourceId != null) record.sourceIds = [record.sourceId];
            }
            if (record.styleLayers != null) delete record.styleLayers.arrow;
            record.arrowLayerId = null;
            record.arrowSourceId = null;
            return this;
        },

        _addPolygon: function (item) {
            var sourceId = makeId('polygon-source');
            var fillLayerId = makeId('polygon-fill');
            var lineLayerId = makeId('polygon-line');
            var style = ns.getPolygonStyle(item);
            var data = this._getPolygonGeoJson(item);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            this._map.addLayer({
                id: fillLayerId,
                type: 'fill',
                source: sourceId,
                paint: {
                    'fill-color': style.fillColor,
                    'fill-opacity': style.fillOpacity
                }
            });
            this._map.addLayer({
                id: lineLayerId,
                type: 'line',
                source: sourceId,
                layout: {
                    'line-cap': style.lineCap,
                    'line-join': style.lineJoin
                },
                paint: {
                    'line-color': style.strokeColor,
                    'line-opacity': style.strokeOpacity,
                    'line-width': style.strokeWidth
                }
            });
            if (style.lineDash != null) {
                this._map.setPaintProperty(lineLayerId, 'line-dasharray', style.lineDash);
            }
            var record = {
                id: sourceId,
                item: item,
                type: 'dgpolygon',
                itemType: 'dgpolygon',
                status: 'active',
                sourceId: sourceId,
                layerIds: [fillLayerId, lineLayerId],
                styleLayers: {
                    fill: fillLayerId,
                    line: lineLayerId
                },
                clickHandlers: []
            };
            this._bindItemClick(record, fillLayerId);
            this._bindItemClick(record, lineLayerId);
            return record;
        },

        _getPolygonGeoJson: function (item) {
            var coordinates = [];
            var xys = item != null && Array.isArray(item._xys) ? item._xys : [];
            for (var i = 0; i < xys.length; i++) {
                var lngLat = toLngLat(xys[i]);
                if (lngLat != null) coordinates.push(lngLat);
            }
            if (coordinates.length > 0) {
                var first = coordinates[0];
                var last = coordinates[coordinates.length - 1];
                if (first[0] != last[0] || first[1] != last[1]) {
                    coordinates.push([first[0], first[1]]);
                }
            }
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: extend({
                            __easymap_item_id: item != null ? item._id : '',
                            easymap_type: 'dgpolygon',
                            _easymapClass: 'dgPolygon'
                        }, item != null ? item._attributes || {} : {}),
                        geometry: {
                            type: 'Polygon',
                            coordinates: [coordinates]
                        }
                    }
                ]
            };
        },

        _addCurve: function (item) {
            var sourceId = makeId('curve-source');
            var fillLayerId = makeId('curve-fill');
            var lineLayerId = makeId('curve-line');
            var style = ns.getPolygonStyle(item);
            var data = this._getCurveGeoJson(item);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            this._map.addLayer({
                id: fillLayerId,
                type: 'fill',
                source: sourceId,
                paint: {
                    'fill-color': style.fillColor,
                    'fill-opacity': style.fillOpacity
                }
            });
            this._map.addLayer({
                id: lineLayerId,
                type: 'line',
                source: sourceId,
                layout: {
                    'line-cap': style.lineCap,
                    'line-join': style.lineJoin
                },
                paint: {
                    'line-color': style.strokeColor,
                    'line-opacity': style.strokeOpacity,
                    'line-width': style.strokeWidth
                }
            });
            if (style.lineDash != null) {
                this._map.setPaintProperty(lineLayerId, 'line-dasharray', style.lineDash);
            }
            var record = {
                id: sourceId,
                item: item,
                type: 'dgcurve',
                itemType: 'dgcurve',
                status: 'active',
                sourceId: sourceId,
                layerIds: [fillLayerId, lineLayerId],
                styleLayers: {
                    fill: fillLayerId,
                    line: lineLayerId
                },
                clickHandlers: []
            };
            this._bindItemClick(record, fillLayerId);
            this._bindItemClick(record, lineLayerId);
            return record;
        },

        _getCurveGeoJson: function (item) {
            if (item != null && typeof item._ensureCurveCoordinates == 'function') item._ensureCurveCoordinates();
            var coordinates = [];
            var xys = item != null && Array.isArray(item._xys) ? item._xys : [];
            for (var i = 0; i < xys.length; i++) {
                var lngLat = toLngLat(xys[i]);
                if (lngLat != null) coordinates.push(lngLat);
            }
            if (coordinates.length > 0) {
                var first = coordinates[0];
                var last = coordinates[coordinates.length - 1];
                if (first[0] != last[0] || first[1] != last[1]) {
                    coordinates.push([first[0], first[1]]);
                }
            }
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: extend({
                            __easymap_item_id: item != null ? item._id : '',
                            easymap_type: 'dgcurve',
                            _easymapClass: 'dgCurve'
                        }, item != null ? item._attributes || {} : {}),
                        geometry: {
                            type: 'Polygon',
                            coordinates: [coordinates]
                        }
                    }
                ]
            };
        },

        _getStaticImageCoordinates: function (item) {
            if (item != null && typeof item._getCoordinates == 'function') return item._getCoordinates();
            var lt = item != null ? item._lt_xy : null;
            var rb = item != null ? item._rb_xy : null;
            var left = Math.min(parseFloat(lt.x), parseFloat(rb.x));
            var right = Math.max(parseFloat(lt.x), parseFloat(rb.x));
            var top = Math.max(parseFloat(lt.y), parseFloat(rb.y));
            var bottom = Math.min(parseFloat(lt.y), parseFloat(rb.y));
            return [
                [left, top],
                [right, top],
                [right, bottom],
                [left, bottom]
            ];
        },

        _getStaticImageSourceOptions: function (item, resolvedUrl) {
            var url = resolvedUrl != null ? resolvedUrl : (item != null && item._src != null ? item._src : '');
            if (resolvedUrl == null && isSvgStaticImageUrl(url)) {
                url = STATIC_IMAGE_TRANSPARENT_PNG;
            }
            return {
                type: 'image',
                url: url,
                coordinates: this._getStaticImageCoordinates(item)
            };
        },

        _toStaticImageUpdateOptions: function (sourceOptions) {
            return {
                url: sourceOptions.url,
                coordinates: sourceOptions.coordinates
            };
        },

        _getStaticImageOpacity: function (item) {
            var opacity = item != null && typeof item.getOpacity == 'function' ? item.getOpacity() : item != null ? item._opacity : 1;
            opacity = parseFloat(opacity);
            if (isNaN(opacity)) opacity = 1;
            if (opacity < 0) opacity = 0;
            if (opacity > 1) opacity = 1;
            return opacity;
        },

        _addStaticImage: function (item) {
            var sourceId = makeId('staticimage-source');
            var layerId = makeId('staticimage-raster');
            var sourceOptions = this._getStaticImageSourceOptions(item);
            this._map.addSource(sourceId, sourceOptions);
            this._map.addLayer({
                id: layerId,
                type: 'raster',
                source: sourceId,
                paint: {
                    'raster-opacity': this._getStaticImageOpacity(item)
                }
            });
            var self = this;
            var record = {
                id: sourceId,
                item: item,
                type: 'dgstaticimage',
                itemType: 'dgstaticimage',
                status: 'active',
                sourceId: sourceId,
                layerIds: [layerId],
                styleLayers: {
                    raster: layerId
                },
                clickHandlers: [],
                setOpacity: function (opacity) {
                    if (item != null && typeof item.setOpacity == 'function') item.setOpacity(opacity);
                    else {
                        item._opacity = opacity;
                        self._applyStaticImageStyle(item, record);
                    }
                    return record;
                },
                getOpacity: function () {
                    return self._getStaticImageOpacity(item);
                }
            };
            this._resolveStaticImageSource(item, record);
            return record;
        },

        _getGroundOverlayQuadOpacity: function (item) {
            var opacity = item != null && typeof item.getOpacity == 'function' ? item.getOpacity() : item != null ? item._opacity : 1;
            opacity = parseFloat(opacity);
            if (isNaN(opacity)) opacity = 1;
            if (opacity < 0) opacity = 0;
            if (opacity > 1) opacity = 1;
            return opacity;
        },

        _getGroundOverlayQuadCoordinates: function (item) {
            if (item != null && typeof item.getCoordinates == 'function') return item.getCoordinates();
            return getGroundOverlayQuadCoordinatesFromWkt(item != null ? item._wktString : '');
        },

        _getGroundOverlayQuadSourceOptions: function (item) {
            return {
                type: 'image',
                url: item != null && item._imageUrl != null ? item._imageUrl : '',
                coordinates: this._getGroundOverlayQuadCoordinates(item)
            };
        },

        _addGroundOverlayQuad: function (item) {
            var sourceOptions = this._getGroundOverlayQuadSourceOptions(item);
            if (sourceOptions.coordinates == null) {
                return this._makeEmptyRecord(item, 'invalid');
            }
            var sourceId = makeId('groundoverlayquad-source');
            var layerId = makeId('groundoverlayquad-raster');
            this._map.addSource(sourceId, sourceOptions);
            this._map.addLayer({
                id: layerId,
                type: 'raster',
                source: sourceId,
                paint: {
                    'raster-opacity': this._getGroundOverlayQuadOpacity(item)
                }
            });
            return {
                id: sourceId,
                item: item,
                type: 'dggroundoverlayquad',
                itemType: 'dggroundoverlayquad',
                status: 'active',
                sourceId: sourceId,
                layerIds: [layerId],
                styleLayers: {
                    raster: layerId
                },
                clickHandlers: []
            };
        },

        _getDgWktImageOpacity: function (item) {
            var opacity = item != null && typeof item.getOpacity == 'function' ? item.getOpacity() : item != null ? item.opacity : 1;
            opacity = parseFloat(opacity);
            if (isNaN(opacity)) opacity = 1;
            if (opacity < 0) opacity = 0;
            if (opacity > 1) opacity = 1;
            return opacity;
        },

        _addDgWktImage: function (item, imageUrl, wktString, bounds) {
            var coordinates = getGroundOverlayQuadCoordinatesFromWkt(wktString);
            if (coordinates == null) return this._makeEmptyRecord(item, 'invalid');
            var sourceId = makeId('dgwkt-image-source');
            var layerId = makeId('dgwkt-image-raster');
            this._map.addSource(sourceId, {
                type: 'image',
                url: imageUrl || '',
                coordinates: coordinates
            });
            this._map.addLayer({
                id: layerId,
                type: 'raster',
                source: sourceId,
                paint: {
                    'raster-opacity': this._getDgWktImageOpacity(item)
                }
            });
            var record = {
                id: sourceId,
                item: item,
                type: 'dgwkt',
                itemType: 'dgwkt',
                status: 'active',
                renderMode: 'image',
                sourceId: sourceId,
                sourceIds: [sourceId],
                layerIds: [layerId],
                styleLayers: {
                    raster: layerId
                },
                clickHandlers: [],
                imageBounds: bounds,
                zIndex: item != null && item.getZIndex != null ? item.getZIndex() : 0,
                addOrder: this._itemAddOrder++
            };
            item._instance = record;
            this._items[item._id || record.id] = record;
            this._setItemVisible(item, item.getVisible == null ? true : item.getVisible());
            this._reorderItemLayers();
            return record;
        },

        _removeDgWktImage: function (record) {
            if (record == null) return false;
            if (record._dgwktImageRecordRemoved === true) return false;
            record._dgwktImageRecordRemoved = true;
            var item = record.item;
            if (record.clickHandlers != null) {
                for (var i = 0; i < record.clickHandlers.length; i++) {
                    var clickHandler = record.clickHandlers[i];
                    if (clickHandler.layerId != null && this._map.getLayer(clickHandler.layerId) != null) {
                        this._map.off('click', clickHandler.layerId, clickHandler.handler);
                    }
                }
            }
            if (record.layerIds != null) {
                for (var j = record.layerIds.length - 1; j >= 0; j--) {
                    if (this._map.getLayer(record.layerIds[j]) != null) this._map.removeLayer(record.layerIds[j]);
                }
            }
            var sourceIds = record.sourceIds || (record.sourceId != null ? [record.sourceId] : []);
            for (var k = 0; k < sourceIds.length; k++) {
                if (sourceIds[k] != null && this._map.getSource(sourceIds[k]) != null) this._map.removeSource(sourceIds[k]);
            }
            if (item != null) {
                var itemKey = item._id || record.id;
                if (this._items[itemKey] === record) delete this._items[itemKey];
                if (item._instance === record) item._instance = null;
            }
            return true;
        },

        _applyDgWktImageStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var layerId = record.styleLayers.raster;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            this._setPaint(layerId, 'raster-opacity', this._getDgWktImageOpacity(item));
        },

        _getStaticImageGeoJson: function (item) {
            var coordinates = this._getStaticImageCoordinates(item);
            var ring = coordinates.slice();
            if (ring.length > 0) ring.push([ring[0][0], ring[0][1]]);
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: {
                            __easymap_item_id: item != null ? item._id : '',
                            easymap_type: 'dgstaticimage',
                            _easymapClass: 'dgStaticImage'
                        },
                        geometry: {
                            type: 'Polygon',
                            coordinates: [ring]
                        }
                    }
                ]
            };
        },

        _getGroundOverlayQuadGeoJson: function (item) {
            var coordinates = this._getGroundOverlayQuadCoordinates(item);
            if (coordinates == null) return this._makeFeatureCollection([]);
            var ring = coordinates.slice();
            ring.push([coordinates[0][0], coordinates[0][1]]);
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: {
                            __easymap_item_id: item != null ? item._id : '',
                            easymap_type: 'dggroundoverlayquad',
                            _easymapClass: 'dgGroundOverlayQuad'
                        },
                        geometry: {
                            type: 'Polygon',
                            coordinates: [ring]
                        }
                    }
                ]
            };
        },

        _addMarker: function (item) {
            var style = ns.getMarkerStyle(item);
            var root = window.document.createElement('div');
            var visual = window.document.createElement('div');
            var label = window.document.createElement('div');
            root.className = 'easymap-maplibre-marker';
            visual.className = 'easymap-maplibre-marker-visual';
            label.className = 'easymap-maplibre-marker-label';
            root.appendChild(visual);
            root.appendChild(label);
            var lngLat = toLngLat(item.getXY != null ? item.getXY() : item._dgxy) || [0, 0];
            var marker = new maplibregl.Marker({
                element: root,
                draggable: item._drag === true,
                anchor: style.anchor
            }).setLngLat(lngLat).addTo(this._map);
            var record = {
                id: makeId('marker-dom'),
                item: item,
                status: 'active',
                markerMode: 'dom',
                marker: marker,
                element: root,
                visualElement: visual,
                labelElement: label,
                anchor: style.anchor,
                sourceId: null,
                layerIds: [],
                clickHandlers: [],
                domHandlers: [],
                dragHandlers: []
            };
            this._applyDomMarkerStyle(item, record);
            this._bindMarkerDomEvents(record);
            this._bindMarkerDragEvents(record);
            return record;
        },

        _addMarkerLayer: function (item) {
            var sourceId = makeId('marker-source');
            var style = ns.getMarkerStyle(item);
            var layerId = makeId(style.src != '' ? 'marker-symbol' : 'marker-circle');
            var labelLayerId = makeId('marker-label');
            var data = this._getMarkerGeoJson(item);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            if (style.src != '') {
                var imageId = this._ensureImage(style.src);
                this._map.addLayer({
                    id: layerId,
                    type: 'symbol',
                    source: sourceId,
                    layout: {
                        'icon-image': imageId,
                        'icon-size': style.scale,
                        'icon-rotate': style.rotate,
                        'icon-anchor': style.anchor,
                        'icon-allow-overlap': true,
                        'icon-ignore-placement': true
                    },
                    paint: {
                        'icon-opacity': style.opacity
                    }
                });
            }
            else {
                this._map.addLayer({
                    id: layerId,
                    type: 'circle',
                    source: sourceId,
                    paint: {
                        'circle-radius': Math.max(6, style.width / 4),
                        'circle-color': '#2563eb',
                        'circle-stroke-color': '#ffffff',
                        'circle-stroke-width': 2,
                        'circle-opacity': style.opacity
                    }
                });
            }
            var labelStyle = ns.getMarkerLabelStyle(item);
            this._map.addLayer({
                id: labelLayerId,
                type: 'symbol',
                source: sourceId,
                filter: ['has', '__easymap_label'],
                layout: {
                    'text-field': ['get', '__easymap_label'],
                    'text-size': labelStyle.size,
                    'text-offset': labelStyle.offset,
                    'text-anchor': labelStyle.anchor,
                    'text-allow-overlap': true,
                    'text-ignore-placement': true
                },
                paint: {
                    'text-color': labelStyle.color,
                    'text-opacity': labelStyle.opacity,
                    'text-halo-color': labelStyle.haloColor,
                    'text-halo-width': labelStyle.haloWidth
                }
            });
            var record = {
                id: sourceId,
                item: item,
                status: 'active',
                sourceId: sourceId,
                layerIds: [layerId, labelLayerId],
                styleLayers: {
                    marker: layerId,
                    label: labelLayerId
                },
                markerStyleType: style.src != '' ? 'symbol' : 'circle',
                clickHandlers: []
            };
            this._bindItemClick(record, layerId);
            this._bindItemClick(record, labelLayerId);
            return record;
        },

        _getMarkerGeoJson: function (item) {
            var point = item.getXY != null ? item.getXY() : item._dgxy;
            var lngLat = toLngLat(point) || [0, 0];
            var properties = extend({}, item._properties || {});
            properties.__easymap_item_id = item._id;
            properties.easymap_type = 'dgmarker';
            if (item._text != null && item._text != '') {
                properties.__easymap_label = item._text;
            }
            return {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        properties: properties,
                        geometry: { type: 'Point', coordinates: lngLat }
                    }
                ]
            };
        },

        _addWkt: function (item) {
            if (item != null && typeof item._resolveRenderMode == 'function' && item._resolveRenderMode(item.getData ? item.getData() : item._url) == 'image' && typeof item._renderImageMode == 'function') {
                var imageRecord = item._renderImageMode();
                if (imageRecord != null && imageRecord !== false) return imageRecord;
                if (window.console && typeof window.console.log == 'function') {
                    window.console.log('dgWKT image mode 建立失敗，改用 vector mode');
                }
            }
            var data = window.EASYMAP_MAPLIBRE_PARSE_WKT(item.getData ? item.getData() : item._url);
            return this._addGeoJson(item, data);
        },

        _addKml: function (item) {
            var data = item.toGeoJSON != null ? item.toGeoJSON() : ns.parseKmlToGeoJSON(item.getData ? item.getData() : item._kml);
            var record = this._addGeoJson(item, data);
            record.kmlInitialLoaded = item._isLoaded === true;
            return record;
        },

        _addDgGeoJson: function (item) {
            var data = item.toGeoJSON != null ? item.toGeoJSON() : (item.getData ? item.getData() : item._geojson);
            var record = this._addGeoJson(item, data);
            record.geoJsonInitialLoaded = item._isLoaded === true;
            return record;
        },

        _addGml: function (item) {
            var data = item.toGeoJSON != null ? item.toGeoJSON() : ns.parseGmlToGeoJSON(item.getData ? item.getData() : item._gml, item._dataSRS);
            var record = this._addGeoJson(item, data);
            record.gmlInitialLoaded = item._isLoaded === true;
            return record;
        },

        _loadKmlItem: function (item, record) {
            if (item == null || record == null) return;
            var self = this;
            if (record.kmlInitialLoaded === true) {
                record.kmlInitialLoaded = false;
                if (typeof item._notifyLoaded == 'function') item._notifyLoaded();
                return;
            }
            var finish = function () {
                if (item._instance !== record) return;
                self._setVectorRecordData(item, record, self._getItemGeoJson(item));
                if (item._setUpperZoomByBoundary === true) {
                    self._fitItemToBounds(item, item._upperZoomByBoundaryOptions);
                }
                if (typeof item._notifyLoaded == 'function') item._notifyLoaded();
            };
            var fail = function (err) {
                if (window.console && typeof window.console.log == 'function') {
                    window.console.log('dgKml load failed', err);
                }
            };
            if (typeof item._load == 'function') {
                item._load(finish, fail);
                return;
            }
            finish();
        },

        _loadGeoJsonItem: function (item, record) {
            if (item == null || record == null) return;
            var self = this;
            if (record.geoJsonInitialLoaded === true) {
                record.geoJsonInitialLoaded = false;
                if (typeof item._notifyLoaded == 'function') item._notifyLoaded();
                return;
            }
            var finish = function () {
                if (item._instance !== record) return;
                self._setVectorRecordData(item, record, self._getItemGeoJson(item));
                if (item._setUpperZoomByBoundary === true) {
                    self._fitItemToBounds(item, item._upperZoomByBoundaryOptions);
                }
                if (typeof item._notifyLoaded == 'function') item._notifyLoaded();
            };
            var fail = function (err) {
                if (window.console && typeof window.console.log == 'function') {
                    window.console.log('dgGeoJson load failed', err);
                }
            };
            if (typeof item._load == 'function') {
                item._load(finish, fail);
                return;
            }
            finish();
        },

        _loadGmlItem: function (item, record) {
            if (item == null || record == null) return;
            var self = this;
            if (record.gmlInitialLoaded === true) {
                record.gmlInitialLoaded = false;
                if (typeof item._notifyLoaded == 'function') item._notifyLoaded();
                return;
            }
            var finish = function () {
                if (item._instance !== record) return;
                self._setVectorRecordData(item, record, self._getItemGeoJson(item));
                if (item._setUpperZoomByBoundary === true) {
                    self._fitItemToBounds(item, item._upperZoomByBoundaryOptions);
                }
                if (typeof item._notifyLoaded == 'function') item._notifyLoaded();
            };
            var fail = function (err) {
                if (window.console && typeof window.console.log == 'function') {
                    window.console.log('dgGML load failed', err);
                }
            };
            if (typeof item._load == 'function') {
                item._load(finish, fail);
                return;
            }
            finish();
        },

        _isClusterEnabled: function (item) {
            return item != null && item._isCluster === true;
        },

        _getClusterOptions: function (item) {
            var distance = item != null && item.getClusterDistance != null ? item.getClusterDistance() : [40, 20];
            var radius = parseInt(distance[0], 10);
            var minDistance = parseInt(distance[1], 10);
            var minSize = item != null && item.getMinClusterSize != null ? parseInt(item.getMinClusterSize(), 10) : 2;
            var maxZoom = item != null && item._clusterMaxZoom != null ? parseInt(item._clusterMaxZoom, 10) : 17;
            return {
                radius: isNaN(radius) || radius <= 0 ? 40 : radius,
                minDistance: isNaN(minDistance) || minDistance < 0 ? 0 : minDistance,
                minSize: isNaN(minSize) || minSize < 2 ? 2 : minSize,
                maxZoom: isNaN(maxZoom) || maxZoom < 0 ? 17 : maxZoom
            };
        },

        _makeFeatureCollection: function (features) {
            return { type: 'FeatureCollection', features: features || [] };
        },

        _cloneFeatureAsPoint: function (feature, coordinates, multiIndex) {
            var cloned = clone(feature);
            cloned.geometry = {
                type: 'Point',
                coordinates: coordinates
            };
            cloned.properties = cloned.properties || {};
            if (multiIndex != null) cloned.properties.__easymap_multipoint_index = multiIndex;
            return cloned;
        },

        _splitClusterGeoJson: function (geojson) {
            var points = [];
            var vectors = [];
            var features = geojson != null && Array.isArray(geojson.features) ? geojson.features : [];
            for (var i = 0; i < features.length; i++) {
                var feature = features[i];
                var geometry = feature != null ? feature.geometry : null;
                if (geometry == null) continue;
                if (geometry.type == 'Point') {
                    points.push(this._cloneFeatureAsPoint(feature, geometry.coordinates));
                    continue;
                }
                if (geometry.type == 'MultiPoint' && Array.isArray(geometry.coordinates)) {
                    for (var j = 0; j < geometry.coordinates.length; j++) {
                        points.push(this._cloneFeatureAsPoint(feature, geometry.coordinates[j], j));
                    }
                    continue;
                }
                vectors.push(feature);
            }
            return {
                points: this._makeFeatureCollection(points),
                vectors: this._makeFeatureCollection(vectors)
            };
        },

        _addGeoJsonLabelLayer: function (layerId, sourceId, filter, style, kind) {
            if (kind === true) kind = 'line';
            if (kind == null || kind === false) kind = 'point';
            var isLine = kind == 'line';
            var isSurface = kind == 'surface';
            var offset = isLine === true ? style.lineOffset : (isSurface === true ? style.surfaceOffset : style.pointOffset);
            var anchor = isLine === true ? 'center' : (isSurface === true ? style.surfaceAnchor : style.pointAnchor);
            var layout = {
                'text-field': ['get', '__easymap_label'],
                'text-size': dataDriven('__easymap_text_size', style.size),
                'text-offset': dataDrivenLiteral('__easymap_text_offset', offset),
                'text-anchor': dataDriven('__easymap_text_anchor', anchor),
                'text-pitch-alignment': 'map',
                'text-rotation-alignment': 'map',
                'text-allow-overlap': true,
                'text-ignore-placement': true
            };
            if (isLine === true) {
                layout['symbol-placement'] = 'line';
                layout['text-keep-upright'] = true;
            }
            this._map.addLayer({
                id: layerId,
                type: 'symbol',
                source: sourceId,
                filter: filter,
                layout: layout,
                paint: {
                    'text-color': dataDriven('__easymap_text_color', style.color),
                    'text-opacity': dataDriven('__easymap_text_opacity', style.opacity),
                    'text-halo-color': dataDriven('__easymap_text_halo_color', style.haloColor),
                    'text-halo-width': dataDriven('__easymap_text_halo_width', style.haloWidth)
                }
            });
        },

        _addGeoJson: function (item, geojson) {
            var sourceId = makeId('geojson-source');
            var circleLayerId = makeId('geojson-circle');
            var symbolLayerId = makeId('geojson-symbol');
            var labelLayerId = makeId('geojson-label');
            var surfaceLabelLayerId = makeId('geojson-surface-label');
            var lineLabelLayerId = makeId('geojson-line-label');
            var lineLayerId = makeId('geojson-line');
            var fillLayerId = makeId('geojson-fill');
            var extrusionLayerId = makeId('geojson-extrusion');
            var outlineLayerId = makeId('geojson-outline');
            var data = this._prepareStyledGeoJson(item, this._transformItemGeoJson(item, this._normalizeGeoJson(geojson)));
            var style = ns.getVectorStyle(item);
            var labelStyle = ns.getWktLabelStyle(item);
            if (this._isClusterEnabled(item)) {
                return this._addClusteredGeoJson(item, sourceId, data, style, {
                    fill: fillLayerId,
                    extrusion: extrusionLayerId,
                    outline: outlineLayerId,
                    line: lineLayerId,
                    circle: circleLayerId,
                    symbol: symbolLayerId,
                    label: labelLayerId,
                    surfaceLabel: surfaceLabelLayerId,
                    lineLabel: lineLabelLayerId
                });
            }
            var outlinePaint = getOutlinePaint(style);
            var linePaint = getLinePaint(style);
            this._map.addSource(sourceId, { type: 'geojson', data: data });
            this._map.addLayer({
                id: fillLayerId,
                type: 'fill',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'Polygon'],
                paint: {
                    'fill-color': dataDriven('__easymap_polygon_fill_color', style.fillColor),
                    'fill-opacity': dataDriven('__easymap_polygon_fill_opacity', style.fillOpacity)
                }
            });
            this._map.addLayer({
                id: extrusionLayerId,
                type: 'fill-extrusion',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'Polygon'],
                layout: {
                    visibility: style.extrusionEnabled === true ? 'visible' : 'none'
                },
                paint: {
                    'fill-extrusion-color': style.extrusionColor,
                    'fill-extrusion-height': style.extrusionHeight,
                    'fill-extrusion-base': style.extrusionBase,
                    'fill-extrusion-opacity': style.extrusionOpacity
                }
            });
            this._map.addLayer({
                id: outlineLayerId,
                type: 'line',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'Polygon'],
                layout: {
                    'line-cap': style.lineCap,
                    'line-join': 'round'
                },
                paint: outlinePaint
            });
            this._map.addLayer({
                id: lineLayerId,
                type: 'line',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'LineString'],
                layout: {
                    'line-cap': style.lineLineCap,
                    'line-join': 'round'
                },
                paint: linePaint
            });
            this._map.addLayer({
                id: circleLayerId,
                type: 'circle',
                source: sourceId,
                filter: ['all', ['==', ['geometry-type'], 'Point'], ['!', ['has', '__easymap_icon_image']]],
                paint: getCirclePaint(style)
            });
            this._map.addLayer({
                id: symbolLayerId,
                type: 'symbol',
                source: sourceId,
                filter: ['all', ['==', ['geometry-type'], 'Point'], ['has', '__easymap_icon_image']],
                layout: {
                    'icon-image': ['get', '__easymap_icon_image'],
                    'icon-size': dataDriven('__easymap_icon_scale', 1),
                    'icon-rotate': dataDriven('__easymap_icon_rotate', 0),
                    'icon-anchor': dataDriven('__easymap_icon_anchor', 'bottom'),
                    'icon-allow-overlap': true,
                    'icon-ignore-placement': true
                },
                paint: {
                    'icon-opacity': dataDriven('__easymap_icon_opacity', 1)
                }
            });
            this._addGeoJsonLabelLayer(labelLayerId, sourceId, ['all', ['==', ['geometry-type'], 'Point'], ['has', '__easymap_label']], labelStyle, 'point');
            this._addGeoJsonLabelLayer(surfaceLabelLayerId, sourceId, ['all', ['==', ['geometry-type'], 'Polygon'], ['has', '__easymap_label']], labelStyle, 'surface');
            this._addGeoJsonLabelLayer(lineLabelLayerId, sourceId, ['all', ['==', ['geometry-type'], 'LineString'], ['has', '__easymap_label']], labelStyle, 'line');
            var record = {
                id: sourceId,
                item: item,
                status: 'active',
                sourceId: sourceId,
                clusterSourceId: null,
                sourceIds: [sourceId],
                isClustered: false,
                layerIds: [fillLayerId, extrusionLayerId, outlineLayerId, lineLayerId, circleLayerId, symbolLayerId, labelLayerId, surfaceLabelLayerId, lineLabelLayerId],
                styleLayers: {
                    fill: fillLayerId,
                    extrusion: extrusionLayerId,
                    outline: outlineLayerId,
                    line: lineLayerId,
                    circle: circleLayerId,
                    symbol: symbolLayerId,
                    label: labelLayerId,
                    surfaceLabel: surfaceLabelLayerId,
                    lineLabel: lineLabelLayerId
                },
                clickHandlers: []
            };
            for (var i = 0; i < record.layerIds.length; i++) {
                this._bindItemClick(record, record.layerIds[i]);
            }
            return record;
        },

        _addClusteredGeoJson: function (item, sourceId, data, style, baseLayerIds) {
            var split = this._splitClusterGeoJson(data);
            var clusterSourceId = makeId('geojson-cluster-source');
            var clusterCircleLayerId = makeId('geojson-cluster-circle');
            var clusterCountLayerId = makeId('geojson-cluster-count');
            var clusterLabelLayerId = makeId('geojson-cluster-label');
            var clusterOptions = this._getClusterOptions(item);
            var clusterStyle = ns.getClusterStyle(item);
            var labelStyle = ns.getWktLabelStyle(item);
            var outlinePaint = getOutlinePaint(style);
            var linePaint = getLinePaint(style);

            this._map.addSource(sourceId, { type: 'geojson', data: split.vectors });
            this._map.addSource(clusterSourceId, {
                type: 'geojson',
                data: split.points,
                cluster: true,
                clusterRadius: clusterOptions.radius,
                clusterMaxZoom: clusterOptions.maxZoom,
                clusterMinPoints: clusterOptions.minSize
            });
            this._map.addLayer({
                id: baseLayerIds.fill,
                type: 'fill',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'Polygon'],
                paint: {
                    'fill-color': dataDriven('__easymap_polygon_fill_color', style.fillColor),
                    'fill-opacity': dataDriven('__easymap_polygon_fill_opacity', style.fillOpacity)
                }
            });
            this._map.addLayer({
                id: baseLayerIds.extrusion,
                type: 'fill-extrusion',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'Polygon'],
                layout: {
                    visibility: style.extrusionEnabled === true ? 'visible' : 'none'
                },
                paint: {
                    'fill-extrusion-color': style.extrusionColor,
                    'fill-extrusion-height': style.extrusionHeight,
                    'fill-extrusion-base': style.extrusionBase,
                    'fill-extrusion-opacity': style.extrusionOpacity
                }
            });
            this._map.addLayer({
                id: baseLayerIds.outline,
                type: 'line',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'Polygon'],
                layout: {
                    'line-cap': style.lineCap,
                    'line-join': 'round'
                },
                paint: outlinePaint
            });
            this._map.addLayer({
                id: baseLayerIds.line,
                type: 'line',
                source: sourceId,
                filter: ['==', ['geometry-type'], 'LineString'],
                layout: {
                    'line-cap': style.lineLineCap,
                    'line-join': 'round'
                },
                paint: linePaint
            });
            this._map.addLayer({
                id: clusterCircleLayerId,
                type: 'circle',
                source: clusterSourceId,
                filter: ['has', 'point_count'],
                paint: {
                    'circle-radius': clusterStyle.circleRadius,
                    'circle-color': clusterStyle.circleColor,
                    'circle-opacity': clusterStyle.circleOpacity,
                    'circle-stroke-color': clusterStyle.circleStrokeColor,
                    'circle-stroke-width': clusterStyle.circleStrokeWidth
                }
            });
            this._map.addLayer({
                id: clusterCountLayerId,
                type: 'symbol',
                source: clusterSourceId,
                filter: ['has', 'point_count'],
                layout: {
                    'text-field': ['get', 'point_count_abbreviated'],
                    'text-size': clusterStyle.textSize,
                    'text-allow-overlap': true,
                    'text-ignore-placement': true
                },
                paint: {
                    'text-color': clusterStyle.textColor,
                    'text-opacity': clusterStyle.textOpacity,
                    'text-halo-color': clusterStyle.textHaloColor,
                    'text-halo-width': clusterStyle.textHaloWidth
                }
            });
            this._map.addLayer({
                id: baseLayerIds.circle,
                type: 'circle',
                source: clusterSourceId,
                filter: ['all', ['==', ['geometry-type'], 'Point'], ['!', ['has', 'point_count']], ['!', ['has', '__easymap_icon_image']]],
                paint: getCirclePaint(style)
            });
            this._map.addLayer({
                id: baseLayerIds.symbol,
                type: 'symbol',
                source: clusterSourceId,
                filter: ['all', ['==', ['geometry-type'], 'Point'], ['!', ['has', 'point_count']], ['has', '__easymap_icon_image']],
                layout: {
                    'icon-image': ['get', '__easymap_icon_image'],
                    'icon-size': dataDriven('__easymap_icon_scale', 1),
                    'icon-rotate': dataDriven('__easymap_icon_rotate', 0),
                    'icon-anchor': dataDriven('__easymap_icon_anchor', 'bottom'),
                    'icon-allow-overlap': true,
                    'icon-ignore-placement': true
                },
                paint: {
                    'icon-opacity': dataDriven('__easymap_icon_opacity', 1)
                }
            });
            this._addGeoJsonLabelLayer(baseLayerIds.surfaceLabel, sourceId, ['all', ['==', ['geometry-type'], 'Polygon'], ['has', '__easymap_label']], labelStyle, 'surface');
            this._addGeoJsonLabelLayer(baseLayerIds.lineLabel, sourceId, ['all', ['==', ['geometry-type'], 'LineString'], ['has', '__easymap_label']], labelStyle, 'line');
            this._addGeoJsonLabelLayer(clusterLabelLayerId, clusterSourceId, ['all', ['==', ['geometry-type'], 'Point'], ['!', ['has', 'point_count']], ['has', '__easymap_label']], labelStyle, 'point');
            var record = {
                id: sourceId,
                item: item,
                status: 'active',
                sourceId: sourceId,
                clusterSourceId: clusterSourceId,
                sourceIds: [sourceId, clusterSourceId],
                isClustered: true,
                clusterOptions: clusterOptions,
                layerIds: [
                    baseLayerIds.fill,
                    baseLayerIds.extrusion,
                    baseLayerIds.outline,
                    baseLayerIds.line,
                    clusterCircleLayerId,
                    clusterCountLayerId,
                    baseLayerIds.circle,
                    baseLayerIds.symbol,
                    baseLayerIds.surfaceLabel,
                    baseLayerIds.lineLabel,
                    clusterLabelLayerId
                ],
                styleLayers: {
                    fill: baseLayerIds.fill,
                    extrusion: baseLayerIds.extrusion,
                    outline: baseLayerIds.outline,
                    line: baseLayerIds.line,
                    clusterCircle: clusterCircleLayerId,
                    clusterCount: clusterCountLayerId,
                    circle: baseLayerIds.circle,
                    symbol: baseLayerIds.symbol,
                    surfaceLabel: baseLayerIds.surfaceLabel,
                    lineLabel: baseLayerIds.lineLabel,
                    clusterLabel: clusterLabelLayerId
                },
                clickHandlers: []
            };
            for (var i = 0; i < record.layerIds.length; i++) {
                this._bindItemClick(record, record.layerIds[i]);
            }
            return record;
        },

        _prepareStyledGeoJson: function (item, geojson) {
            geojson = this._normalizeGeoJson(geojson);
            var features = geojson.features || [];
            for (var i = 0; i < features.length; i++) {
                if (features[i].properties == null) features[i].properties = {};
                this._applyFeatureStyle(item, features[i], i);
            }
            return geojson;
        },

        _transformItemGeoJson: function (item, geojson) {
            var dataSrs = item != null && item._dataSRS != null ? item._dataSRS : 'EPSG:4326';
            if (ns.normalizeSrs(dataSrs) == 'EPSG:4326') return geojson;
            return ns.transformGeoJson(geojson, dataSrs, 'EPSG:4326');
        },

        _applyFeatureStyle: function (item, feature, fallbackIndex) {
            if (feature == null || feature.properties == null) return;
            var properties = feature.properties;
            var dataIndex = properties.data_index != null ? properties.data_index : fallbackIndex;
            var featureStyle = item != null && item._featureStyles != null ? item._featureStyles[dataIndex] : null;
            var styleSetting = properties.style_setting || {};
            var imageStyle = getStyleSetting(styleSetting, 'Image');
            var textStyle = getStyleSetting(styleSetting, 'Text');
            var pointStyle = getStyleSetting(styleSetting, 'Point');
            var lineStyle = getStyleSetting(styleSetting, 'LineString');
            var multiLineStyle = getStyleSetting(styleSetting, 'MultiLineString');
            var polygonStyle = getStyleSetting(styleSetting, 'Polygon');
            var multiPolygonStyle = getStyleSetting(styleSetting, 'MultiPolygon');
            var itemType = item != null && item._type != null ? String(item._type).toLowerCase() : '';
            var label = featureStyle && featureStyle.label != null ? featureStyle.label : properties.label;
            if (itemType == 'dgkml') {
                label = item.labelVisible === true ? (label != null ? label : properties.name) : null;
            }
            if (label != null && String(label) != '') {
                properties.__easymap_label = String(label);
            }
            else {
                delete properties.__easymap_label;
            }
            var pic = featureStyle && featureStyle.pic != null ? featureStyle.pic : (properties.pic || imageStyle.pic || imageStyle.src);
            if (pic != null && pic != '') {
                var defaultIconScale = item != null && item._iconScale != null ? item._iconScale : 1;
                properties.__easymap_icon_image = this._ensureImage(pic);
                properties.__easymap_icon_scale = featureStyle && featureStyle.scale != null ? featureStyle.scale : ns.toNumber(properties.scale != null ? properties.scale : imageStyle.scale, defaultIconScale);
                properties.__easymap_icon_rotate = featureStyle && featureStyle.rotate != null ? featureStyle.rotate : ns.toNumber(properties.rotation != null ? properties.rotation : imageStyle.rotate, 0);
                properties.__easymap_icon_opacity = ns.toNumber(imageStyle.opacity, 1);
                var iconAnchor = featureStyle && featureStyle.anchor != null ? featureStyle.anchor : (properties.postion != null ? properties.postion : (properties.position != null ? properties.position : imageStyle.anchor));
                if (iconAnchor != null) properties.__easymap_icon_anchor = ns.normalizeAnchor(iconAnchor);
            }
            setPrivateTextStyle(properties, textStyle);
            setPrivatePointStyle(properties, pointStyle);
            setPrivateLineStyle(properties, lineStyle);
            setPrivateLineStyle(properties, multiLineStyle);
            setPrivatePolygonStyle(properties, polygonStyle);
            setPrivatePolygonStyle(properties, multiPolygonStyle);
        },

        _normalizeGeoJson: function (geojson) {
            if (geojson == null) return { type: 'FeatureCollection', features: [] };
            if (typeof geojson == 'string') {
                var text = geojson.replace(/^\s+|\s+$/g, '');
                if (/^[\{\[]/.test(text)) {
                    try {
                        return this._normalizeGeoJson(JSON.parse(text));
                    } catch (ignore) { }
                }
                return window.EASYMAP_MAPLIBRE_PARSE_WKT(geojson);
            }
            if (geojson.type == 'FeatureCollection') return geojson;
            if (geojson.type == 'Feature') return { type: 'FeatureCollection', features: [geojson] };
            if (geojson.type != null && geojson.coordinates != null) {
                return {
                    type: 'FeatureCollection',
                    features: [{ type: 'Feature', properties: {}, geometry: geojson }]
                };
            }
            if (Array.isArray(geojson)) {
                if (geojson.length > 0 && geojson[0] != null && geojson[0].type == 'Feature') {
                    return { type: 'FeatureCollection', features: geojson };
                }
                return window.EASYMAP_MAPLIBRE_PARSE_WKT(geojson);
            }
            return { type: 'FeatureCollection', features: [] };
        },

        _addSourceItem: function (item) {
            var options = item._options || {};
            var sourceId = makeId('dgsource');
            var layerId = makeId('dgsource-layer');
            var sourceType = getSourceType(item).toLowerCase();
            if (sourceType == 'raster' || sourceType == 'wmts' || sourceType == 'xyz' || sourceType == 'osm' || sourceType == 'google' || options.tiles != null || options.url != null) {
                var rasterSource = this._buildRasterSourceSpec(item);
                if (rasterSource == null) return this._makeEmptyRecord(item, 'adapter-gap');
                this._map.addSource(sourceId, rasterSource);
                this._map.addLayer({
                    id: layerId,
                    type: 'raster',
                    source: sourceId,
                    paint: {
                        'raster-opacity': options.opacity != null ? options.opacity : 1
                    }
                });
                return {
                    id: sourceId,
                    item: item,
                    status: 'active',
                    sourceId: sourceId,
                    layerIds: [layerId],
                    clickHandlers: []
                };
            }
            return this._makeEmptyRecord(item, 'adapter-gap');
        },

        _add3DPlaceholder: function (item) {
            var record = this._makeEmptyRecord(item, 'three-pending');
            record.reason = 'dg3D MapLibre native runtime bridge is Phase ML3';
            return record;
        },

        _getOption: function (item, key, fallback) {
            if (item._options != null && item._options[key] != null) return item._options[key];
            return fallback;
        },

        _bindItemClick: function (record, layerId) {
            var self = this;
            var handler = function (event) {
                var feature = event.features && event.features.length > 0 ? event.features[0] : null;
                var properties = feature != null ? feature.properties || {} : {};
                var isCluster = properties.point_count != null || properties.cluster === true;
                var result = {
                    engine: 'maplibre',
                    type: isCluster ? 'cluster' : (record.itemType || record.item._type),
                    itemType: record.itemType || record.item._type,
                    cluster: isCluster,
                    item: record.item,
                    feature: feature,
                    features: event.features || (feature != null ? [feature] : []),
                    properties: properties,
                    coordinate: [event.lngLat.lng, event.lngLat.lat],
                    originalEvent: event.originalEvent || event,
                    layerId: layerId
                };
                if (isCluster === true && self._handleClusterSpiderDisplay(record, event, feature, result) === true) return;
                if (isCluster === true) self._zoomToClusterFeature(record, event, feature);
                self._dispatchItemClick(record.item, result);
            };
            this._map.on('click', layerId, handler);
            record.clickHandlers.push({ layerId: layerId, handler: handler });
        },

        _zoomToClusterFeature: function (record, event, feature) {
            if (record == null || record.item == null || record.item.getClusterClickZoomToBBOX == null) return;
            if (record.item.getClusterClickZoomToBBOX() !== true) return;
            var source = this._map.getSource(record.clusterSourceId || record.sourceId);
            var clusterId = feature != null && feature.properties != null ? feature.properties.cluster_id : null;
            if (source == null || typeof source.getClusterExpansionZoom != 'function' || clusterId == null) return;
            var self = this;
            source.getClusterExpansionZoom(clusterId, function (err, zoom) {
                if (err != null || zoom == null) return;
                var center = [event.lngLat.lng, event.lngLat.lat];
                if (typeof self._map.easeTo == 'function') {
                    self._map.easeTo({ center: center, zoom: zoom });
                }
                else if (typeof self._map.zoomTo == 'function') {
                    self._map.setCenter(center);
                    self._map.zoomTo(zoom);
                }
            });
        },

        _registerWktSpiderDisplayCleanup: function (item) {
            if (item == null || item._type != 'dgwkt' || item._isSpiderDisplay !== true) return;
            if (item._spiderDisplayMapEvent != null) return;
            var self = this;
            item._spiderDisplayMapEvent = function () {
                if (item._isSpiderDisplay === true) self._clearWktSpiderDisplay(item);
            };
            this.attachEvent('zoomstart', item._spiderDisplayMapEvent);
        },

        _clearWktSpiderDisplay: function (item) {
            if (item == null || item._spiderDisplayWKTOBJ == null) return;
            var spider = item._spiderDisplayWKTOBJ;
            item._spiderDisplayWKTOBJ = null;
            if (spider._instance == null) return;
            if (spider._easymap != null && typeof spider._easymap.removeItem == 'function') {
                spider._easymap.removeItem(spider);
            }
        },

        _getWktSpiderClusterCenter: function (event, feature) {
            if (feature != null && feature.geometry != null && Array.isArray(feature.geometry.coordinates)) {
                return [parseFloat(feature.geometry.coordinates[0]), parseFloat(feature.geometry.coordinates[1])];
            }
            if (event != null && event.lngLat != null) return [parseFloat(event.lngLat.lng), parseFloat(event.lngLat.lat)];
            return null;
        },

        _projectSpiderCoordinate: function (coordinate, fallbackPoint) {
            if (Array.isArray(coordinate) && this._map != null && typeof this._map.project == 'function') {
                var projected = this._map.project(coordinate);
                return {
                    x: projected.x != null ? projected.x : projected[0],
                    y: projected.y != null ? projected.y : projected[1]
                };
            }
            if (fallbackPoint != null) {
                return {
                    x: fallbackPoint.x != null ? fallbackPoint.x : fallbackPoint[0],
                    y: fallbackPoint.y != null ? fallbackPoint.y : fallbackPoint[1]
                };
            }
            return null;
        },

        _unprojectSpiderPixel: function (pixel) {
            if (pixel == null || this._map == null || typeof this._map.unproject != 'function') return null;
            var lngLat = this._map.unproject([pixel.x, pixel.y]);
            var coordinate = toLngLat(lngLat);
            if (coordinate == null || isNaN(coordinate[0]) || isNaN(coordinate[1])) return null;
            return coordinate;
        },

        _formatSpiderWktCoordinate: function (coordinate) {
            return parseFloat(coordinate[0]) + ' ' + parseFloat(coordinate[1]);
        },

        _makeWktSpiderPointRow: function (item, leaf, coordinate) {
            var properties = clone(leaf != null && leaf.properties != null ? leaf.properties : {});
            var rows = item != null && item.getData != null ? item.getData() : item != null ? item._url : null;
            var dataIndex = properties.data_index != null ? parseInt(properties.data_index, 10) : null;
            var row = null;
            if (Array.isArray(rows) && dataIndex != null && !isNaN(dataIndex) && rows[dataIndex] != null) {
                row = clone(rows[dataIndex]);
            }
            if (row == null || typeof row != 'object' || row.type == 'Feature') row = clone(properties);
            delete row.__easymap_icon_image;
            delete row.__easymap_icon_scale;
            delete row.__easymap_icon_rotate;
            delete row.__easymap_icon_opacity;
            row.wkt = 'POINT(' + this._formatSpiderWktCoordinate(coordinate) + ')';
            return row;
        },

        _displayWktSpiderDisplay: function (item, leaves, event, feature) {
            if (item == null || window.dgWKT == null || !Array.isArray(leaves) || leaves.length <= 1) return false;
            this._clearWktSpiderDisplay(item);
            var center = this._getWktSpiderClusterCenter(event, feature);
            var centerPixel = this._projectSpiderCoordinate(center, event != null ? event.point : null);
            if (center == null || centerPixel == null) return false;
            var angleStep = (2 * Math.PI) / leaves.length;
            var radius = item._spiderDisplayRadius != null ? parseFloat(item._spiderDisplayRadius) : 80;
            if (isNaN(radius) || radius <= 0) radius = 80;
            var rows = [];
            for (var i = 0; i < leaves.length; i++) {
                var angle = i * angleStep;
                var point = {
                    x: centerPixel.x + Math.cos(angle) * radius,
                    y: centerPixel.y + Math.sin(angle) * radius
                };
                var coordinate = this._unprojectSpiderPixel(point);
                if (coordinate == null) continue;
                rows.push({
                    wkt: 'LINESTRING(' + this._formatSpiderWktCoordinate(center) + ', ' + this._formatSpiderWktCoordinate(coordinate) + ')',
                    label: ''
                });
                rows.push(this._makeWktSpiderPointRow(item, leaves[i], coordinate));
            }
            if (rows.length <= 0) return false;
            var spider = new window.dgWKT(rows, 'EPSG:4326');
            spider._isSpiderDisplayChild = true;
            spider._featureClick = item._featureClick;
            spider.onFeatureSelect = item.onFeatureSelect;
            spider.onclick = item.onclick;
            if (typeof item.getIconScale == 'function' && typeof spider.setIconScale == 'function') {
                spider.setIconScale(item.getIconScale());
            }
            item._spiderDisplayWKTOBJ = spider;
            this.addItem(spider);
            if (spider.getStyle != null && spider.getStyle().Point != null && spider.getStyle().Point.getImage != null) {
                spider.getStyle().Point.getImage().setRadius(0);
            }
            return true;
        },

        _handleClusterSpiderDisplay: function (record, event, feature, result) {
            var item = record != null ? record.item : null;
            if (item == null || item._type != 'dgwkt' || item._isSpiderDisplay !== true) return false;
            this._registerWktSpiderDisplayCleanup(item);
            this._clearWktSpiderDisplay(item);
            var zoom = this.getZoom != null ? this.getZoom() : this._map.getZoom();
            var minZoom = parseFloat(item._spiderDisplayZoomLevel);
            if (isNaN(minZoom)) minZoom = 15;
            if (zoom < minZoom) return false;
            var properties = feature != null && feature.properties != null ? feature.properties : {};
            var pointCount = parseInt(properties.point_count, 10);
            if (isNaN(pointCount) || pointCount <= 1) return false;
            var clusterId = properties.cluster_id;
            var source = this._map.getSource(record.clusterSourceId || record.sourceId);
            if (source == null || typeof source.getClusterLeaves != 'function' || clusterId == null) return false;
            var self = this;
            var settled = false;
            var onLeaves = function (err, leaves) {
                if (settled === true) return;
                settled = true;
                if (err != null || !Array.isArray(leaves) || leaves.length <= 1) {
                    self._zoomToClusterFeature(record, event, feature);
                    self._dispatchItemClick(record.item, result);
                    return;
                }
                self._displayWktSpiderDisplay(item, leaves, event, feature);
            };
            var returned = source.getClusterLeaves(clusterId, pointCount, 0, onLeaves);
            if (returned != null && typeof returned.then == 'function') {
                returned.then(function (leaves) {
                    onLeaves(null, leaves);
                }).catch(function (err) {
                    onLeaves(err);
                });
            }
            return true;
        },

        _dispatchItemClick: function (item, result) {
            var handled = false;
            if (typeof item._featureClick == 'function') {
                this._dispatchFeatureClick(item, item._featureClick, result);
                handled = true;
            }
            if (typeof item.onclick == 'function') {
                item.onclick(result);
                handled = true;
            }
            if (typeof item.onFeatureSelect == 'function') {
                this._dispatchFeatureClick(item, item.onFeatureSelect, result);
                handled = true;
            }
            if (handled !== true) this._dispatchDefaultItemClick(item, result);
        },

        _dispatchDefaultItemClick: function (item, result) {
            var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
            if (type != 'dgkml' || item._featureSelect === false) return;
            result = result || {};
            if (result.cluster === true) return;
            var feature = result.feature || (Array.isArray(result.features) && result.features.length > 0 ? result.features[0] : null);
            var properties = result.properties || (feature != null && feature.properties != null ? feature.properties : {});
            var coordinate = result.coordinate;
            if (coordinate == null && feature != null) coordinate = getFirstCoordinateFromGeometry(feature.geometry || null);
            var dgxy = toDgXY(coordinate);
            if (dgxy == null) return;
            var popup = renderFeaturePopup(properties);
            this._openInfoWindow(dgxy, popup.title, popup.html);
        },

        _isFeatureClickItem: function (item) {
            var type = item != null && item._type != null ? String(item._type).toLowerCase() : '';
            return type == 'dgwkt' || type == 'dggeojson' || type == 'dgkml' || type == 'dggml' || type == 'dgwfs';
        },

        _dispatchFeatureClick: function (item, callback, result) {
            if (typeof callback != 'function') return;
            if (this._isFeatureClickItem(item) !== true) {
                callback.call(item, result);
                return;
            }
            result = result || {};
            var feature = result.feature || null;
            var properties = result.properties || (feature != null ? feature.properties || {} : {});
            var geometry = feature != null ? feature.geometry || null : null;
            var geometryType = result.cluster === true ? 'wktCluster' : (geometry != null ? geometry.type : null);
            var callbackGeometry = result.cluster === true ? (result.features || []) : (geometry != null ? toDgGeometry(geometry.coordinates) : toDgXY(result.coordinate));
            callback.apply(properties, [
                properties,
                geometryType,
                callbackGeometry,
                feature,
                result.originalEvent || null,
                result.features || (feature != null ? [feature] : []),
                result
            ]);
        },

        _reloadItem: function (item) {
            if (item == null || item._easymap !== this) return null;
            var visible = item.getVisible == null ? true : item.getVisible();
            var zIndex = item.getZIndex == null ? 0 : item.getZIndex();
            this.removeItem(item);
            item._visible = visible;
            item._zIndex = zIndex;
            this._addItemNow(item);
            return item._instance;
        },

        _getItemGeoJson: function (item) {
            if (item == null) return this._makeFeatureCollection([]);
            if (isTextItem(item)) {
                return this._getTextGeoJson(item);
            }
            if (isPointItem(item)) {
                return this._getPointGeoJson(item);
            }
            if (isPolylineItem(item)) {
                return this._getPolylineGeoJson(item);
            }
            if (isPolygonItem(item)) {
                return this._getPolygonGeoJson(item);
            }
            if (isCurveItem(item)) {
                return this._getCurveGeoJson(item);
            }
            if (isStaticImageItem(item)) {
                return this._getStaticImageGeoJson(item);
            }
            if (isGroundOverlayQuadItem(item)) {
                return this._getGroundOverlayQuadGeoJson(item);
            }
            if (item._type == 'dgwkt') {
                return window.EASYMAP_MAPLIBRE_PARSE_WKT(item.getData ? item.getData() : item._url);
            }
            if (item._type == 'dggeojson') {
                return item.toGeoJSON != null ? item.toGeoJSON() : this._normalizeGeoJson(item.getData ? item.getData() : item._geojson);
            }
            if (item._type == 'dgkml') {
                return item.toGeoJSON != null ? item.toGeoJSON() : ns.parseKmlToGeoJSON(item.getData ? item.getData() : item._kml);
            }
            if (item._type == 'dggml') {
                return item.toGeoJSON != null ? item.toGeoJSON() : ns.parseGmlToGeoJSON(item.getData ? item.getData() : item._gml, item._dataSRS);
            }
            return this._normalizeGeoJson(item.getData ? item.getData() : item._geojson);
        },

        _fitGeoJsonBounds: function (geojson, options) {
            var bounds = getGeoJsonBounds(geojson);
            if (bounds == null) return this;
            var west = bounds[0];
            var south = bounds[1];
            var east = bounds[2];
            var north = bounds[3];
            var fitOptions = extend({
                padding: 40,
                maxZoom: 17,
                duration: 0
            }, options || {});

            if (west == east && south == north) {
                if (typeof this._map.setCenter == 'function') this._map.setCenter([west, south]);
                if (fitOptions.maxZoom != null && typeof this._map.zoomTo == 'function') this._map.zoomTo(fitOptions.maxZoom, { duration: fitOptions.duration || 0 });
                return this;
            }

            if (typeof this._map.fitBounds == 'function') {
                this._map.fitBounds([[west, south], [east, north]], fitOptions);
                return this;
            }

            if (typeof this._map.setCenter == 'function') {
                this._map.setCenter([(west + east) / 2, (south + north) / 2]);
            }
            if (fitOptions.maxZoom != null && typeof this._map.zoomTo == 'function') {
                this._map.zoomTo(fitOptions.maxZoom, { duration: fitOptions.duration || 0 });
            }
            return this;
        },

        _fitItemToBounds: function (item, options) {
            if (item == null) return this;
            var geojson = this._getItemGeoJson(item);
            var data = this._transformItemGeoJson(item, this._normalizeGeoJson(geojson));
            return this._fitGeoJsonBounds(data, options);
        },

        _setVectorRecordData: function (item, record, geojson) {
            var data = this._prepareStyledGeoJson(item, this._transformItemGeoJson(item, this._normalizeGeoJson(geojson)));
            if (record.isClustered === true) {
                var split = this._splitClusterGeoJson(data);
                if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                    this._map.getSource(record.sourceId).setData(split.vectors);
                }
                if (record.clusterSourceId != null && this._map.getSource(record.clusterSourceId) != null) {
                    this._map.getSource(record.clusterSourceId).setData(split.points);
                }
                return;
            }
            if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                this._map.getSource(record.sourceId).setData(data);
            }
        },

        _updateItemData: function (item) {
            var record = item._instance;
            if (record == null) return;
            if (isTextItem(item)) {
                if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                    this._map.getSource(record.sourceId).setData(this._getTextGeoJson(item));
                }
                return;
            }
            if (isPointItem(item)) {
                if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                    this._map.getSource(record.sourceId).setData(this._getPointGeoJson(item));
                }
                return;
            }
            if (isPolylineItem(item)) {
                if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                    this._map.getSource(record.sourceId).setData(this._getPolylineGeoJson(item));
                }
                this._refreshPolylineArrow(item);
                return;
            }
            if (isPolygonItem(item)) {
                if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                    this._map.getSource(record.sourceId).setData(this._getPolygonGeoJson(item));
                }
                return;
            }
            if (isCurveItem(item)) {
                if (record.sourceId != null && this._map.getSource(record.sourceId) != null) {
                    this._map.getSource(record.sourceId).setData(this._getCurveGeoJson(item));
                }
                return;
            }
            if (isStaticImageItem(item)) {
                this._updateStaticImageSource(item, record);
                return;
            }
            if (isGroundOverlayQuadItem(item)) {
                this._updateGroundOverlayQuadSource(item, record);
                return;
            }
            if (item._type == 'dgmarker') {
                if (record.markerMode == 'dom') {
                    this._updateDomMarkerPosition(item, record);
                    this._applyDomMarkerStyle(item, record);
                    return;
                }
                if (record.sourceId == null || this._map.getSource(record.sourceId) == null) return;
                this._map.getSource(record.sourceId).setData(this._getMarkerGeoJson(item));
                return;
            }
            if (item._type == 'dgwkt' && record.renderMode == 'image') {
                if (typeof item._redrawImageMode == 'function') item._redrawImageMode();
                return;
            }
            if (record.sourceId == null || this._map.getSource(record.sourceId) == null) return;
            if (item._type == 'dggeojson') {
                this._loadGeoJsonItem(item, record);
                return;
            }
            if (item._type == 'dgkml') {
                this._loadKmlItem(item, record);
                return;
            }
            if (item._type == 'dggml') {
                this._loadGmlItem(item, record);
                return;
            }
            if (item._type == 'dgwkt') {
                this._setVectorRecordData(item, record, this._getItemGeoJson(item));
                return;
            }
        },

        _setPaint: function (layerId, key, value) {
            if (layerId != null && this._map.getLayer(layerId) != null && value != null) {
                this._map.setPaintProperty(layerId, key, value);
            }
        },

        _setLayout: function (layerId, key, value) {
            if (layerId != null && this._map.getLayer(layerId) != null && value != null) {
                this._map.setLayoutProperty(layerId, key, value);
            }
        },

        _refreshItemStyle: function (item) {
            var record = item != null ? item._instance : null;
            if (record == null) return;
            if (isTextItem(item)) {
                this._applyTextStyle(item, record);
                return;
            }
            if (isPointItem(item)) {
                this._applyPointStyle(item, record);
                return;
            }
            if (isPolylineItem(item)) {
                this._applyPolylineStyle(item, record);
                return;
            }
            if (isPolygonItem(item)) {
                this._applyPolygonStyle(item, record);
                return;
            }
            if (isCurveItem(item)) {
                this._applyPolygonStyle(item, record);
                return;
            }
            if (isStaticImageItem(item)) {
                this._applyStaticImageStyle(item, record);
                return;
            }
            if (isGroundOverlayQuadItem(item)) {
                this._applyGroundOverlayQuadStyle(item, record);
                return;
            }
            if (item._type == 'dgmarker') {
                this._applyMarkerStyle(item, record);
                return;
            }
            if (item._type == 'dgwkt' && record.renderMode == 'image') {
                this._applyDgWktImageStyle(item, record);
                return;
            }
            if (item._type == 'dgwkt' || item._type == 'dggeojson' || item._type == 'dgkml' || item._type == 'dggml') {
                this._applyVectorStyle(item, record);
            }
        },

        _applyTextStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var layerId = record.styleLayers.text;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            var style = ns.getTextStyle(item);
            this._setLayout(layerId, 'text-size', style.size);
            this._setLayout(layerId, 'text-rotate', style.rotate);
            this._setLayout(layerId, 'text-offset', style.offset);
            this._setLayout(layerId, 'text-anchor', style.anchor);
            this._setPaint(layerId, 'text-color', style.color);
            this._setPaint(layerId, 'text-opacity', style.opacity);
            this._setPaint(layerId, 'text-halo-color', style.haloColor);
            this._setPaint(layerId, 'text-halo-width', style.haloWidth);
        },

        _applyPointStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var layerId = record.styleLayers.point;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            var style = ns.getPointStyle(item);
            this._setPaint(layerId, 'circle-radius', style.radius);
            this._setPaint(layerId, 'circle-color', style.fillColor);
            this._setPaint(layerId, 'circle-opacity', style.fillOpacity);
            this._setPaint(layerId, 'circle-stroke-color', style.strokeColor);
            this._setPaint(layerId, 'circle-stroke-opacity', style.strokeOpacity);
            this._setPaint(layerId, 'circle-stroke-width', style.strokeWidth);
        },

        _applyPolylineStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var layerId = record.styleLayers.line;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            var style = ns.getPolylineStyle(item);
            this._setLayout(layerId, 'line-cap', style.lineCap);
            this._setLayout(layerId, 'line-join', style.lineJoin);
            this._setPaint(layerId, 'line-color', style.color);
            this._setPaint(layerId, 'line-opacity', style.opacity);
            this._setPaint(layerId, 'line-width', style.width);
            this._map.setPaintProperty(layerId, 'line-dasharray', style.lineDash);
        },

        _applyPolygonStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var fillLayerId = record.styleLayers.fill;
            var lineLayerId = record.styleLayers.line;
            var style = ns.getPolygonStyle(item);
            if (fillLayerId != null && this._map.getLayer(fillLayerId) != null) {
                this._setPaint(fillLayerId, 'fill-color', style.fillColor);
                this._setPaint(fillLayerId, 'fill-opacity', style.fillOpacity);
            }
            if (lineLayerId != null && this._map.getLayer(lineLayerId) != null) {
                this._setLayout(lineLayerId, 'line-cap', style.lineCap);
                this._setLayout(lineLayerId, 'line-join', style.lineJoin);
                this._setPaint(lineLayerId, 'line-color', style.strokeColor);
                this._setPaint(lineLayerId, 'line-opacity', style.strokeOpacity);
                this._setPaint(lineLayerId, 'line-width', style.strokeWidth);
                this._map.setPaintProperty(lineLayerId, 'line-dasharray', style.lineDash);
            }
        },

        _updateStaticImageSource: function (item, record) {
            if (record == null || record.sourceId == null || this._map.getSource(record.sourceId) == null) return;
            var source = this._map.getSource(record.sourceId);
            var options = this._getStaticImageSourceOptions(item);
            if (typeof source.updateImage == 'function') {
                source.updateImage(this._toStaticImageUpdateOptions(options));
            }
            else {
                if (typeof source.setCoordinates == 'function') {
                    source.setCoordinates(options.coordinates);
                }
                source.url = options.url;
                source.coordinates = options.coordinates;
            }
            this._resolveStaticImageSource(item, record);
        },

        _updateGroundOverlayQuadSource: function (item, record) {
            if (record == null || record.sourceId == null || this._map.getSource(record.sourceId) == null) return;
            var source = this._map.getSource(record.sourceId);
            var options = this._getGroundOverlayQuadSourceOptions(item);
            if (options.coordinates == null) return;
            if (typeof source.updateImage == 'function') {
                source.updateImage({
                    url: options.url,
                    coordinates: options.coordinates
                });
            }
            else {
                if (typeof source.setCoordinates == 'function') source.setCoordinates(options.coordinates);
                source.url = options.url;
                source.coordinates = options.coordinates;
            }
        },

        _resolveStaticImageSource: function (item, record) {
            if (item == null || record == null || !isSvgStaticImageUrl(item._src)) return;
            var originalUrl = item._src;
            this._rasterizeStaticImageSvg(originalUrl, item).then(function (rasterUrl) {
                if (item._src !== originalUrl || item._instance !== record) return;
                if (record.sourceId == null || this._map.getSource(record.sourceId) == null) return;
                var source = this._map.getSource(record.sourceId);
                var options = this._toStaticImageUpdateOptions(this._getStaticImageSourceOptions(item, rasterUrl));
                if (typeof source.updateImage == 'function') {
                    source.updateImage(options);
                }
                else {
                    if (typeof source.setCoordinates == 'function') source.setCoordinates(options.coordinates);
                    source.url = options.url;
                    source.coordinates = options.coordinates;
                }
            }.bind(this)).catch(function (err) {
                if (window.console && typeof window.console.log == 'function') {
                    window.console.log('dgStaticImage SVG rasterize failed', err);
                }
            });
        },

        _rasterizeStaticImageSvg: function (url, item) {
            return new Promise(function (resolve, reject) {
                if (window.Image == null || window.document == null || typeof window.document.createElement != 'function') {
                    reject(new Error('Browser image/canvas is unavailable'));
                    return;
                }
                var image = new window.Image();
                if (!/^data:/i.test(String(url || ''))) {
                    image.crossOrigin = 'anonymous';
                }
                image.onload = function () {
                    try {
                        var canvas = window.document.createElement('canvas');
                        var width = parseFloat(item != null ? item._width : null);
                        var height = parseFloat(item != null ? item._height : null);
                        if (isNaN(width) || width <= 0) width = image.naturalWidth || image.width || 1;
                        if (isNaN(height) || height <= 0) height = image.naturalHeight || image.height || 1;
                        canvas.width = Math.max(1, Math.round(width));
                        canvas.height = Math.max(1, Math.round(height));
                        var context = canvas.getContext('2d');
                        context.drawImage(image, 0, 0, canvas.width, canvas.height);
                        resolve(canvas.toDataURL('image/png'));
                    }
                    catch (err) {
                        reject(err);
                    }
                };
                image.onerror = function () {
                    reject(new Error('SVG image load failed'));
                };
                image.src = url;
            });
        },

        _applyStaticImageStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var layerId = record.styleLayers.raster;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            this._setPaint(layerId, 'raster-opacity', this._getStaticImageOpacity(item));
        },

        _applyGroundOverlayQuadStyle: function (item, record) {
            if (record == null || record.styleLayers == null) return;
            var layerId = record.styleLayers.raster;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            this._setPaint(layerId, 'raster-opacity', this._getGroundOverlayQuadOpacity(item));
        },

        _applyMarkerStyle: function (item, record) {
            if (record != null && record.markerMode == 'dom') {
                this._applyDomMarkerStyle(item, record);
                return;
            }
            var layerId = record.styleLayers != null ? record.styleLayers.marker : null;
            if (layerId == null || this._map.getLayer(layerId) == null) return;
            var style = ns.getMarkerStyle(item);
            if (record.markerStyleType == 'symbol') {
                if (style.src != '') this._setLayout(layerId, 'icon-image', this._ensureImage(style.src));
                this._setLayout(layerId, 'icon-size', style.scale);
                this._setLayout(layerId, 'icon-rotate', style.rotate);
                this._setLayout(layerId, 'icon-anchor', style.anchor);
                this._setPaint(layerId, 'icon-opacity', style.opacity);
            }
            else {
                this._setPaint(layerId, 'circle-radius', Math.max(6, style.width / 4) * style.scale);
                this._setPaint(layerId, 'circle-opacity', style.opacity);
            }
            var labelLayerId = record.styleLayers != null ? record.styleLayers.label : null;
            var labelStyle = ns.getMarkerLabelStyle(item);
            this._setLayout(labelLayerId, 'text-size', labelStyle.size);
            this._setLayout(labelLayerId, 'text-offset', labelStyle.offset);
            this._setLayout(labelLayerId, 'text-anchor', labelStyle.anchor);
            this._setPaint(labelLayerId, 'text-color', labelStyle.color);
            this._setPaint(labelLayerId, 'text-opacity', labelStyle.opacity);
            this._setPaint(labelLayerId, 'text-halo-color', labelStyle.haloColor);
            this._setPaint(labelLayerId, 'text-halo-width', labelStyle.haloWidth);
        },

        _applyVectorStyle: function (item, record) {
            if (record.styleLayers == null) return;
            var style = ns.getVectorStyle(item);
            this._setPaint(record.styleLayers.fill, 'fill-color', dataDriven('__easymap_polygon_fill_color', style.fillColor));
            this._setPaint(record.styleLayers.fill, 'fill-opacity', dataDriven('__easymap_polygon_fill_opacity', style.fillOpacity));
            this._setPaint(record.styleLayers.extrusion, 'fill-extrusion-color', style.extrusionColor);
            this._setPaint(record.styleLayers.extrusion, 'fill-extrusion-height', style.extrusionHeight);
            this._setPaint(record.styleLayers.extrusion, 'fill-extrusion-base', style.extrusionBase);
            this._setPaint(record.styleLayers.extrusion, 'fill-extrusion-opacity', style.extrusionOpacity);
            this._setLayout(record.styleLayers.extrusion, 'visibility', style.extrusionEnabled === true ? 'visible' : 'none');

            this._setPaint(record.styleLayers.outline, 'line-color', dataDriven('__easymap_polygon_stroke_color', style.strokeColor));
            this._setPaint(record.styleLayers.outline, 'line-width', dataDriven('__easymap_polygon_stroke_width', style.strokeWidth));
            this._setPaint(record.styleLayers.outline, 'line-opacity', dataDriven('__easymap_polygon_stroke_opacity', style.strokeOpacity));
            this._setLayout(record.styleLayers.outline, 'line-cap', style.lineCap);
            this._setLayout(record.styleLayers.outline, 'line-join', 'round');
            this._setPaint(record.styleLayers.line, 'line-color', dataDriven('__easymap_line_color', style.lineColor));
            this._setPaint(record.styleLayers.line, 'line-width', dataDriven('__easymap_line_width', style.lineWidth));
            this._setPaint(record.styleLayers.line, 'line-opacity', dataDriven('__easymap_line_opacity', style.lineOpacity));
            this._setLayout(record.styleLayers.line, 'line-cap', style.lineLineCap);
            this._setLayout(record.styleLayers.line, 'line-join', 'round');
            if (style.lineDash != null) {
                this._setPaint(record.styleLayers.outline, 'line-dasharray', style.lineDash);
            }
            if (style.lineLineDash != null) {
                this._setPaint(record.styleLayers.line, 'line-dasharray', style.lineLineDash);
            }

            this._setPaint(record.styleLayers.circle, 'circle-radius', dataDriven('__easymap_point_radius', style.pointRadius));
            this._setPaint(record.styleLayers.circle, 'circle-color', dataDriven('__easymap_point_color', style.pointColor));
            this._setPaint(record.styleLayers.circle, 'circle-opacity', dataDriven('__easymap_point_opacity', style.pointOpacity));
            this._setPaint(record.styleLayers.circle, 'circle-stroke-color', dataDriven('__easymap_point_stroke_color', style.pointStrokeColor));
            this._setPaint(record.styleLayers.circle, 'circle-stroke-opacity', dataDriven('__easymap_point_stroke_opacity', style.pointStrokeOpacity));
            this._setPaint(record.styleLayers.circle, 'circle-stroke-width', dataDriven('__easymap_point_stroke_width', style.pointStrokeWidth));
            this._setLayout(record.styleLayers.symbol, 'icon-size', dataDriven('__easymap_icon_scale', 1));
            this._setLayout(record.styleLayers.symbol, 'icon-rotate', dataDriven('__easymap_icon_rotate', 0));
            this._setLayout(record.styleLayers.symbol, 'icon-anchor', dataDriven('__easymap_icon_anchor', 'bottom'));
            this._setPaint(record.styleLayers.symbol, 'icon-opacity', dataDriven('__easymap_icon_opacity', 1));

            var labelStyle = ns.getWktLabelStyle(item);
            var pointLabelLayers = [record.styleLayers.label, record.styleLayers.clusterLabel];
            for (var i = 0; i < pointLabelLayers.length; i++) {
                this._setLayout(pointLabelLayers[i], 'text-size', dataDriven('__easymap_text_size', labelStyle.size));
                this._setLayout(pointLabelLayers[i], 'text-offset', dataDrivenLiteral('__easymap_text_offset', labelStyle.pointOffset));
                this._setLayout(pointLabelLayers[i], 'text-anchor', dataDriven('__easymap_text_anchor', labelStyle.pointAnchor));
                this._setLayout(pointLabelLayers[i], 'text-pitch-alignment', 'map');
                this._setLayout(pointLabelLayers[i], 'text-rotation-alignment', 'map');
                this._setPaint(pointLabelLayers[i], 'text-color', dataDriven('__easymap_text_color', labelStyle.color));
                this._setPaint(pointLabelLayers[i], 'text-opacity', dataDriven('__easymap_text_opacity', labelStyle.opacity));
                this._setPaint(pointLabelLayers[i], 'text-halo-color', dataDriven('__easymap_text_halo_color', labelStyle.haloColor));
                this._setPaint(pointLabelLayers[i], 'text-halo-width', dataDriven('__easymap_text_halo_width', labelStyle.haloWidth));
            }
            this._setLayout(record.styleLayers.surfaceLabel, 'text-size', dataDriven('__easymap_text_size', labelStyle.size));
            this._setLayout(record.styleLayers.surfaceLabel, 'text-offset', dataDrivenLiteral('__easymap_text_offset', labelStyle.surfaceOffset));
            this._setLayout(record.styleLayers.surfaceLabel, 'text-anchor', dataDriven('__easymap_text_anchor', labelStyle.surfaceAnchor));
            this._setLayout(record.styleLayers.surfaceLabel, 'text-pitch-alignment', 'map');
            this._setLayout(record.styleLayers.surfaceLabel, 'text-rotation-alignment', 'map');
            this._setPaint(record.styleLayers.surfaceLabel, 'text-color', dataDriven('__easymap_text_color', labelStyle.color));
            this._setPaint(record.styleLayers.surfaceLabel, 'text-opacity', dataDriven('__easymap_text_opacity', labelStyle.opacity));
            this._setPaint(record.styleLayers.surfaceLabel, 'text-halo-color', dataDriven('__easymap_text_halo_color', labelStyle.haloColor));
            this._setPaint(record.styleLayers.surfaceLabel, 'text-halo-width', dataDriven('__easymap_text_halo_width', labelStyle.haloWidth));

            this._setLayout(record.styleLayers.lineLabel, 'text-size', dataDriven('__easymap_text_size', labelStyle.size));
            this._setLayout(record.styleLayers.lineLabel, 'text-offset', dataDrivenLiteral('__easymap_text_offset', labelStyle.lineOffset));
            this._setLayout(record.styleLayers.lineLabel, 'text-anchor', dataDriven('__easymap_text_anchor', 'center'));
            this._setLayout(record.styleLayers.lineLabel, 'text-pitch-alignment', 'map');
            this._setLayout(record.styleLayers.lineLabel, 'text-rotation-alignment', 'map');
            this._setLayout(record.styleLayers.lineLabel, 'text-keep-upright', true);
            this._setPaint(record.styleLayers.lineLabel, 'text-color', dataDriven('__easymap_text_color', labelStyle.color));
            this._setPaint(record.styleLayers.lineLabel, 'text-opacity', dataDriven('__easymap_text_opacity', labelStyle.opacity));
            this._setPaint(record.styleLayers.lineLabel, 'text-halo-color', dataDriven('__easymap_text_halo_color', labelStyle.haloColor));
            this._setPaint(record.styleLayers.lineLabel, 'text-halo-width', dataDriven('__easymap_text_halo_width', labelStyle.haloWidth));
        },

        _setItemVisible: function (item, visible) {
            var record = item._instance;
            if (record == null) return;
            if (record.markerMode == 'dom') {
                if (record.element != null) record.element.style.display = visible === false ? 'none' : '';
                return;
            }
            if (record.layerIds == null) return;
            var style = item != null && (item._type == 'dgwkt' || item._type == 'dggeojson' || item._type == 'dgkml') ? ns.getVectorStyle(item) : null;
            for (var i = 0; i < record.layerIds.length; i++) {
                if (this._map.getLayer(record.layerIds[i]) != null) {
                    var value = visible === false ? 'none' : 'visible';
                    if (visible !== false && style != null && record.styleLayers != null && record.layerIds[i] == record.styleLayers.extrusion && style.extrusionEnabled !== true) {
                        value = 'none';
                    }
                    this._map.setLayoutProperty(record.layerIds[i], 'visibility', value);
                }
            }
        },

        _formatItems: function (items) {
            if (items == null) return [];
            return Array.isArray(items) ? items : [items];
        },

        getItemZIndex: function (item) {
            if (item == null) return false;
            var record = item._instance || null;
            if (record != null) {
                if (typeof record.getZIndex == 'function') return record.getZIndex();
                if (record.element != null && record.element.style != null && record.element.style.zIndex != null) {
                    if (record.element.style.zIndex == '') return 0;
                    var domZIndex = parseInt(record.element.style.zIndex, 10);
                    return isNaN(domZIndex) ? 0 : domZIndex;
                }
                if (record.zIndex != null) {
                    var recordZIndex = parseInt(record.zIndex, 10);
                    return isNaN(recordZIndex) ? 0 : recordZIndex;
                }
            }
            if (typeof item.getZIndex == 'function') return item.getZIndex();
            if (item._zIndex != null) {
                var itemZIndex = parseInt(item._zIndex, 10);
                return isNaN(itemZIndex) ? 0 : itemZIndex;
            }
            return 0;
        },

        setItemZIndex: function (items, zIndex) {
            var list = this._formatItems(items);
            var value = parseInt(zIndex, 10);
            if (isNaN(value)) value = 0;
            for (var i = 0; i < list.length; i++) {
                var item = list[i];
                if (item == null) continue;
                item._zIndex = value;
                if (item._instance != null) {
                    item._instance.zIndex = value;
                    if (item._instance.markerMode == 'dom' && item._instance.element != null) {
                        item._instance.element.style.zIndex = String(value);
                    }
                }
            }
            this._reorderItemLayers();
            return this;
        },

        setItemTop: function (items) {
            var max = 0;
            for (var key in this._items) {
                if (Object.prototype.hasOwnProperty.call(this._items, key) && this._items[key].zIndex > max) {
                    max = this._items[key].zIndex;
                }
            }
            return this.setItemZIndex(items, max + 1);
        },

        setZIndexTop: function (items) {
            return this.setItemTop(items);
        },

        _reorderItemLayers: function () {
            if (this._map == null || typeof this._map.moveLayer != 'function') return;
            var records = [];
            for (var key in this._items) {
                if (Object.prototype.hasOwnProperty.call(this._items, key)) {
                    var record = this._items[key];
                    if (record != null && record.markerMode == 'dom' && record.element != null) {
                        record.element.style.zIndex = String(record.zIndex || 0);
                    }
                    if (record != null && record.layerIds != null && record.layerIds.length > 0) {
                        records.push(record);
                    }
                }
            }
            records.sort(function (a, b) {
                var za = a.zIndex || 0;
                var zb = b.zIndex || 0;
                if (za != zb) return za - zb;
                return (a.addOrder || 0) - (b.addOrder || 0);
            });
            for (var i = 0; i < records.length; i++) {
                for (var j = 0; j < records[i].layerIds.length; j++) {
                    var layerId = records[i].layerIds[j];
                    if (this._map.getLayer(layerId) != null) {
                        this._map.moveLayer(layerId);
                    }
                }
            }
        },

        removeItem: function (item) {
            if (item == null || item._instance == null) return this;
            this._clearWktSpiderDisplay(item);
            if (item._spiderDisplayMapEvent != null) {
                this.detachEvent('zoomstart', item._spiderDisplayMapEvent);
                item._spiderDisplayMapEvent = null;
            }
            var record = item._instance;
            if (record.renderMode == 'image' && item._type == 'dgwkt' && typeof item._destroyImageRenderer == 'function') {
                item._destroyImageRenderer();
                item._easymap = null;
                return this;
            }
            if (record.domHandlers != null && record.element != null) {
                for (var d = 0; d < record.domHandlers.length; d++) {
                    record.element.removeEventListener(record.domHandlers[d].name, record.domHandlers[d].handler);
                }
            }
            if (record.dragHandlers != null && record.marker != null && typeof record.marker.off == 'function') {
                for (var g = 0; g < record.dragHandlers.length; g++) {
                    record.marker.off(record.dragHandlers[g].name, record.dragHandlers[g].handler);
                }
            }
            if (record.markerMode == 'dom' && record.marker != null && typeof record.marker.remove == 'function') {
                record.marker.remove();
            }
            if (record.clickHandlers != null) {
                for (var i = 0; i < record.clickHandlers.length; i++) {
                    var clickHandler = record.clickHandlers[i];
                    if (this._map.getLayer(clickHandler.layerId) != null) {
                        this._map.off('click', clickHandler.layerId, clickHandler.handler);
                    }
                }
            }
            if (record.layerIds != null) {
                for (var j = record.layerIds.length - 1; j >= 0; j--) {
                    if (this._map.getLayer(record.layerIds[j]) != null) {
                        this._map.removeLayer(record.layerIds[j]);
                    }
                }
            }
            var sourceIds = record.sourceIds || (record.sourceId != null ? [record.sourceId] : []);
            for (var k = 0; k < sourceIds.length; k++) {
                if (sourceIds[k] != null && this._map.getSource(sourceIds[k]) != null) {
                    this._map.removeSource(sourceIds[k]);
                }
            }
            delete this._items[item._id || record.id];
            item._instance = null;
            item._easymap = null;
            return this;
        },

        getWidth: function () {
            if (this._container == null) return 0;
            return this._container.clientWidth || this._container.offsetWidth || 0;
        },

        getHeight: function () {
            if (this._container == null) return 0;
            return this._container.clientHeight || this._container.offsetHeight || 0;
        },

        getRectBound: function () {
            if (this._map != null && typeof this._map.getBounds == 'function') {
                var bounds = this._map.getBounds();
                if (bounds != null) {
                    if (typeof bounds.getWest == 'function') {
                        return [bounds.getWest(), bounds.getNorth(), bounds.getEast(), bounds.getSouth()];
                    }
                    if (bounds._sw != null && bounds._ne != null) {
                        return [bounds._sw.lng, bounds._ne.lat, bounds._ne.lng, bounds._sw.lat];
                    }
                }
            }
            var center = this.getCenter();
            return [center.x, center.y, center.x, center.y];
        },

        panTo: function (dgxy, options) {
            var center = toLngLat(dgxy);
            if (center != null) {
                var panOptions = {};
                if (typeof options == 'number' || (typeof options == 'string' && options !== '')) {
                    panOptions.duration = ns.toNumber(options, 400);
                }
                else if (options != null && typeof options == 'object') {
                    panOptions = options;
                }
                else {
                    panOptions.duration = 400;
                }
                this._map.panTo(center, panOptions);
            }
            return this;
        },

        setCenter: function (dgxy, options) {
            var center = toLngLat(dgxy);
            if (center != null) this._map.setCenter(center, options || {});
            return this;
        },

        getCenter: function () {
            var center = this._map.getCenter();
            return new window.dgXY(center.lng, center.lat);
        },

        getCX: function () {
            return this.getCenter().x;
        },

        getCY: function () {
            return this.getCenter().y;
        },

        zoomToXY: function (dgxy, zoom) {
            var center = toLngLat(dgxy);
            if (center == null) {
                console.log('zoomToXY 資料內容坐標錯誤:');
                console.log(dgxy != null ? dgxy.xy : dgxy);
                return this;
            }
            var payload = { center: center };
            if (zoom != null) payload.zoom = parseFloat(zoom);
            if (typeof this._map.jumpTo == 'function') {
                this._map.jumpTo(payload);
            }
            else {
                this._map.setCenter(center);
                if (payload.zoom != null && typeof this._map.zoomTo == 'function') this._map.zoomTo(payload.zoom, { duration: 0 });
            }
            this._writeCameraAttributes();
            return this;
        },

        goXY: function (dgxy) {
            return this.zoomToXY(dgxy, this.getZoom());
        },

        panToXYZ: function (dgxy, zoomLevel, dis) {
            var center = toLngLat(dgxy);
            if (center == null) {
                console.log('panToXYZ 資料內容坐標錯誤:');
                console.log(dgxy != null ? dgxy.xy : dgxy);
                return this;
            }
            var duration = ns.toNumber(dis, 400);
            var payload = {
                center: center,
                zoom: zoomLevel != null ? parseFloat(zoomLevel) : this.getZoom(),
                duration: duration
            };
            if (duration > 0 && typeof this._map.easeTo == 'function') {
                this._map.easeTo(payload);
            }
            else if (typeof this._map.jumpTo == 'function') {
                this._map.jumpTo(payload);
            }
            else {
                this._map.setCenter(center);
                if (payload.zoom != null && typeof this._map.zoomTo == 'function') this._map.zoomTo(payload.zoom, { duration: duration });
            }
            this._writeCameraAttributes();
            return this;
        },

        revXY: function (x, y) {
            if (this._map != null && typeof this._map.unproject == 'function') {
                var lngLat = this._map.unproject([parseFloat(x), parseFloat(y)]);
                return new window.dgXY(lngLat.lng, lngLat.lat);
            }
            return new window.dgXY(0, 0);
        },

        tranXY: function (dgxy) {
            var pixel = this._projectPixel(dgxy);
            if (pixel == null) return { x: 0, y: 0 };
            return { x: pixel[0], y: pixel[1] };
        },

        _normalizeFitOptions: function (extra) {
            var options = {
                maxZoom: 20,
                padding: [0, 0, 0, 0]
            };
            if (extra != null && typeof extra == 'object') {
                for (var key in extra) {
                    if (Object.prototype.hasOwnProperty.call(extra, key)) {
                        options[key] = clone(extra[key]);
                    }
                }
            }
            if (Array.isArray(options.padding)) {
                options.padding = {
                    top: ns.toNumber(options.padding[0], 0),
                    right: ns.toNumber(options.padding[1], 0),
                    bottom: ns.toNumber(options.padding[2], 0),
                    left: ns.toNumber(options.padding[3], 0)
                };
            }
            return options;
        },

        getUpperZoomByBoundary: function (dgxy_lt, dgxy_rb, extra) {
            var lt = toLngLat(dgxy_lt);
            var rb = toLngLat(dgxy_rb);
            if (lt == null || rb == null) return null;
            var west = Math.min(lt[0], rb[0]);
            var east = Math.max(lt[0], rb[0]);
            var north = Math.max(lt[1], rb[1]);
            var south = Math.min(lt[1], rb[1]);
            var options = this._normalizeFitOptions(extra);
            if (this._map != null && typeof this._map.fitBounds == 'function') {
                this._map.fitBounds([[west, south], [east, north]], options);
                this._writeCameraAttributes();
            }
            var lt3857 = ns.projTransfer([west, north], 'EPSG:4326', 'EPSG:3857');
            var rb3857 = ns.projTransfer([east, south], 'EPSG:4326', 'EPSG:3857');
            return [lt3857[0], rb3857[1], rb3857[0], lt3857[1]];
        },

        _getHighlightLayer: function () {
            if (this._highlightLayer != null && this._highlightLayer.parentNode != null) return this._highlightLayer;
            var layer = window.document.createElement('div');
            layer.className = 'easymap-maplibre-highlight-layer';
            layer.setAttribute('easymap_id', 'easymap-maplibre-highlight-layer');
            layer.style.position = 'absolute';
            layer.style.left = '0';
            layer.style.top = '0';
            layer.style.right = '0';
            layer.style.bottom = '0';
            layer.style.pointerEvents = 'none';
            layer.style.overflow = 'hidden';
            layer.style.zIndex = '20';
            if (this._container.style != null && (this._container.style.position == null || this._container.style.position === '')) {
                this._container.style.position = 'relative';
            }
            this._container.appendChild(layer);
            this._highlightLayer = layer;
            return layer;
        },

        _projectPixel: function (dgxy) {
            var center = toLngLat(dgxy);
            if (center == null || this._map == null || typeof this._map.project != 'function') return null;
            var pixel = this._map.project(center);
            if (pixel == null) return null;
            var x = pixel.x != null ? pixel.x : pixel[0];
            var y = pixel.y != null ? pixel.y : pixel[1];
            if (isNaN(x) || isNaN(y)) return null;
            return [x, y];
        },

        highlightXY: function (dgxy, playTimes) {
            var layer = this._getHighlightLayer();
            var times = parseInt(playTimes, 10);
            if (isNaN(times) || times < 1) times = 1;
            var self = this;
            var makeRing = function () {
                var ring = window.document.createElement('div');
                ring.className = 'easymap-maplibre-highlight-ring';
                ring.setAttribute('easymap_id', 'easymap-maplibre-highlight-ring');
                ring.style.position = 'absolute';
                ring.style.left = '0';
                ring.style.top = '0';
                ring.style.borderRadius = '50%';
                ring.style.boxSizing = 'border-box';
                ring.style.pointerEvents = 'none';
                ring.style.willChange = 'transform,width,height,opacity';
                layer.appendChild(ring);

                var start = Date.now();
                var duration = 1200;
                var animate = function () {
                    var elapsed = Date.now() - start;
                    var t = Math.min(elapsed / duration, 1);
                    var ease = 1 - Math.pow(1 - t, 2);
                    var radius = 8 + ease * 34;
                    var opacity = Math.max(0, 1 - t);
                    var pixel = self._projectPixel(dgxy);
                    if (pixel != null) {
                        ring.style.display = 'block';
                        ring.style.width = (radius * 2) + 'px';
                        ring.style.height = (radius * 2) + 'px';
                        ring.style.opacity = String(opacity);
                        ring.style.border = (2 + opacity) + 'px solid rgba(255, 0, 0, ' + opacity + ')';
                        ring.style.transform = 'translate(' + Math.round(pixel[0] - radius) + 'px, ' + Math.round(pixel[1] - radius) + 'px)';
                    }
                    else {
                        ring.style.display = 'none';
                    }
                    if (t < 1) {
                        if (window.requestAnimationFrame != null) {
                            window.requestAnimationFrame(animate);
                        }
                        else {
                            window.setTimeout(animate, 16);
                        }
                    }
                    else if (ring.parentNode != null) {
                        ring.parentNode.removeChild(ring);
                    }
                };
                animate();
            };
            for (var i = 0; i < times; i++) {
                window.setTimeout(makeRing, i * 500);
            }
            return true;
        },

        zoomTo: function (zoom, options) {
            if (zoom != null) this._map.zoomTo(parseFloat(zoom), options || {});
            this._writeCameraAttributes();
            return this;
        },

        getZoom: function () {
            return this._map.getZoom();
        },

        getZoomLevel: function () {
            return this.getZoom();
        },

        setZoom: function (zoom) {
            return this.zoomTo(zoom);
        },

        setZoomLevel: function (zoom) {
            return this.zoomTo(zoom);
        },

        switchMap: function (name) {
            if (name == null) return false;
            var source = this._getBaseMapDefinition(name);
            if (source == null) return false;
            if (this._applyBaseMapDefinition(this._map, source) !== true) return false;
            this._mname = getSourceName(source) || name;
            if (this._eagleEyeMap != null) {
                try {
                    this._applyBaseMapDefinition(this._eagleEyeMap, source);
                } catch (ignore) { }
            }
            if (this._container != null) this._container.setAttribute('data-easymap-basemap', this._mname);
            return true;
        },

        switchMapType: function (name) {
            return this.switchMap(name);
        },

        getBasemapName: function () {
            return this._mname;
        },

        getMapName: function () {
            return this.getBasemapName();
        },

        myAjax_async: function (url, post, successFunc, failFunc) {
            return sendAjaxRequest(url, post, successFunc, failFunc);
        },

        myAjax_async_json: function (url, post, successFunc, failFunc) {
            return sendAjaxRequest(url, post, function (html, xhr) {
                var json = null;
                try {
                    json = html === '' || html == null ? null : JSON.parse(html);
                } catch (err) {
                    callAjaxFailure(failFunc, xhr, err);
                    return;
                }
                if (typeof successFunc == 'function') successFunc(json, xhr);
            }, failFunc, { accept: 'application/json' });
        },

        KmlToWKTArr: function (UrlOrKmlStr, doneFunc, errFunc) {
            var input = UrlOrKmlStr == null ? '' : String(UrlOrKmlStr);
            var self = this;

            if (isKmzUrl(input)) {
                return this._loadKmzToWKTArr(input, doneFunc, errFunc);
            }

            if (isHttpUrl(input)) {
                return this.myAjax_async(input, null, function (data, xhr) {
                    var text = xhr != null && xhr.responseText != null ? xhr.responseText : data;
                    var rows = self._KmlToWKTArr_init(text);
                    if (typeof doneFunc == 'function') doneFunc(rows);
                }, function (xhr, err) {
                    if (typeof errFunc == 'function') errFunc(err || xhr);
                });
            }

            var rows = this._KmlToWKTArr_init(input);
            if (typeof doneFunc == 'function') doneFunc(rows);
            return rows;
        },

        _KmlToWKTArr_init: function (kmlStr) {
            var geojson = { type: 'FeatureCollection', features: [] };
            if (ns.parseKmlToGeoJSON != null) {
                geojson = ns.parseKmlToGeoJSON(sanitizeKmlText(kmlStr));
            }
            return geoJsonToWktArr(geojson);
        },

        _geoJsonToWKTArr_init: function (geojsonObj) {
            return geoJsonToWktArr(this._normalizeGeoJson(geojsonObj));
        },

        _loadKmzToWKTArr: function (url, doneFunc, errFunc) {
            var xhr = createAjaxRequest();
            var self = this;
            var fail = function (err) {
                if (typeof errFunc == 'function') errFunc(err);
            };
            if (xhr == null) {
                fail(new Error('XMLHttpRequest is unavailable'));
                return null;
            }
            if (window.JSZip == null) {
                fail(new Error('JSZip is unavailable'));
                return null;
            }
            try {
                xhr.open('GET', url, true);
                xhr.responseType = 'arraybuffer';
            } catch (err) {
                fail(err);
                return xhr;
            }
            xhr.onerror = function (event) {
                fail(event);
            };
            xhr.onload = function (event) {
                if (xhr.status && (xhr.status < 200 || xhr.status >= 300)) {
                    fail(event);
                    return;
                }
                var data = xhr.response || xhr.responseText;
                var parseKmlFile = function (zip) {
                    var files = typeof zip.file == 'function' ? zip.file(/\.kml$/i) : [];
                    var kmlFile = files != null && files.length > 0 ? files[0] : null;
                    if (kmlFile == null) {
                        fail(new Error('KMZ does not contain KML'));
                        return;
                    }
                    var complete = function (text) {
                        var rows = self._KmlToWKTArr_init(text);
                        if (typeof doneFunc == 'function') doneFunc(rows);
                    };
                    if (typeof kmlFile.async == 'function') {
                        kmlFile.async('text').then(complete).catch(fail);
                    }
                    else if (typeof kmlFile.asText == 'function') {
                        complete(kmlFile.asText());
                    }
                    else {
                        fail(new Error('Unsupported JSZip KML entry'));
                    }
                };
                if (typeof window.JSZip.loadAsync == 'function') {
                    window.JSZip.loadAsync(data).then(parseKmlFile).catch(fail);
                    return;
                }
                try {
                    var zip = new window.JSZip();
                    var loaded = typeof zip.load == 'function' ? zip.load(data) : zip;
                    parseKmlFile(loaded || zip);
                } catch (err2) {
                    fail(err2);
                }
            };
            try {
                xhr.send(null);
            } catch (err3) {
                fail(err3);
            }
            return xhr;
        },

        zoomIn: function () {
            return this.setZoom(this.getZoom() + 1);
        },

        zoomOut: function () {
            return this.setZoom(this.getZoom() - 1);
        },

        projTransfer: function (input, fromEPSG, toEPSG) {
            return ns.projTransfer(input, fromEPSG, toEPSG);
        },

        projWKTTransfer: function (wktStr, fromSRS, toSRS) {
            return ns.transformWkt(wktStr, fromSRS, toSRS);
        },

        resize: function (w, h) {
            if (this._container != null) {
                if (w != null) this._container.style.width = parseFloat(w) + 'px';
                if (h != null) this._container.style.height = parseFloat(h) + 'px';
            }
            this._map.resize();
            return this;
        },

        _normalizeLegacyEventName: function (name) {
            name = String(name || '').toLowerCase();
            switch (name) {
                case 'onmousedown':
                case 'mousedown':
                case 'touchstart':
                    return 'mousedown';
                case 'onmouseup':
                case 'mouseup':
                case 'touchend':
                    return 'mouseup';
                case 'onmousemove':
                case 'mousemove':
                case 'mouseover':
                case 'onmouseover':
                    return 'mousemove';
                case 'onmouseout':
                case 'mouseout':
                    return 'mouseout';
                case 'onclick':
                case 'click':
                    return 'click';
                case 'ondblclick':
                case 'dblclick':
                    return 'dblclick';
                case 'zoomstart':
                case 'onzoomstart':
                    return 'zoomstart';
                case 'zoomend':
                case 'onzoomend':
                    return 'zoomend';
                case 'movestart':
                case 'onmovestart':
                    return 'movestart';
                case 'moveend':
                case 'onmoveend':
                    return 'moveend';
            }
            if (name.indexOf('on') === 0 && name.length > 2) return name.substring(2);
            return name;
        },

        _eventToDgXY: function (event) {
            if (event != null && event.lngLat != null) {
                return new window.dgXY(event.lngLat.lng, event.lngLat.lat);
            }
            if (event != null && event.point != null) {
                var pointX = event.point.x != null ? event.point.x : event.point[0];
                var pointY = event.point.y != null ? event.point.y : event.point[1];
                return this.revXY(pointX, pointY);
            }
            if (event != null && event.offsetX != null && event.offsetY != null) {
                return this.revXY(event.offsetX, event.offsetY);
            }
            if (event != null && event.originalEvent != null) {
                var original = event.originalEvent;
                if (original.offsetX != null && original.offsetY != null) return this.revXY(original.offsetX, original.offsetY);
                if (original.clientX != null && original.clientY != null && this._container != null && typeof this._container.getBoundingClientRect == 'function') {
                    var rect = this._container.getBoundingClientRect();
                    return this.revXY(original.clientX - rect.left, original.clientY - rect.top);
                }
            }
            return this.getCenter();
        },

        _eventToPixel: function (event) {
            if (event != null && event.point != null) {
                var pointX = event.point.x != null ? event.point.x : event.point[0];
                var pointY = event.point.y != null ? event.point.y : event.point[1];
                return { x: pointX, y: pointY };
            }
            if (event != null && event.offsetX != null && event.offsetY != null) {
                return { x: event.offsetX, y: event.offsetY };
            }
            if (event != null && event.originalEvent != null) {
                return this._eventToPixel(event.originalEvent);
            }
            return null;
        },

        _legacyDomEventName: function (mapEventName) {
            switch (mapEventName) {
                case 'click':
                case 'dblclick':
                case 'mousedown':
                case 'mouseup':
                case 'mousemove':
                case 'mouseout':
                    return mapEventName;
            }
            return null;
        },

        attachEvent: function (name, handler) {
            if (typeof handler != 'function') return this;
            var mapEventName = this._normalizeLegacyEventName(name);
            var self = this;
            var wrapped = function (event) {
                var marker = event != null && event.originalEvent != null ? event.originalEvent : event;
                if (marker != null && marker.__easymapDrawConsumed === true) return;
                if (self._drawState != null && (mapEventName == 'click' || mapEventName == 'dblclick' || mapEventName == 'mousemove')) return;
                if (marker != null && marker.__easymapLegacyHandled === true) return;
                if (marker != null) marker.__easymapLegacyHandled = true;
                var dgxy = self._eventToDgXY(event);
                var pixel = self._eventToPixel(event);
                handler.apply(self, [event, dgxy, pixel, []]);
            };
            this._map.on(mapEventName, wrapped);
            var canvas = this._map != null && typeof this._map.getCanvas == 'function' ? this._map.getCanvas() : null;
            var domEventName = this._legacyDomEventName(mapEventName);
            if (canvas != null && domEventName != null && typeof canvas.addEventListener == 'function') {
                canvas.addEventListener(domEventName, wrapped);
            }
            this._eventHandlers.push({
                name: mapEventName,
                originalName: name,
                handler: wrapped,
                originalHandler: handler,
                domEventName: domEventName,
                domTarget: canvas
            });
            return this;
        },

        detachEvent: function (name, handler) {
            var mapEventName = this._normalizeLegacyEventName(name);
            for (var i = this._eventHandlers.length - 1; i >= 0; i--) {
                var entry = this._eventHandlers[i];
                if (entry.name != mapEventName) continue;
                if (handler != null && entry.originalHandler !== handler && entry.handler !== handler) continue;
                this._map.off(entry.name, entry.handler);
                if (entry.domTarget != null && entry.domEventName != null && typeof entry.domTarget.removeEventListener == 'function') {
                    entry.domTarget.removeEventListener(entry.domEventName, entry.handler);
                }
                this._eventHandlers.splice(i, 1);
            }
            return this;
        },

        _getInfoWindowOffset: function (options) {
            var baseOffset = 16;
            var marker = options != null && options.marker != null ? options.marker : null;
            if (marker == null || marker._icontype != 'dgicon' || marker._dgicon == null) return baseOffset;

            var style = ns.getMarkerStyle(marker);
            var anchor = String(style.anchor || 'bottom');
            var visibleHeightRate = 1;
            if (anchor.indexOf('top') == 0) visibleHeightRate = 0;
            else if (anchor == 'center' || anchor == 'left' || anchor == 'right') visibleHeightRate = 0.5;

            var iconHeight = Math.max(0, ns.toNumber(style.height, marker._dgicon._height || 32) * ns.toNumber(style.scale, 1) * visibleHeightRate);
            return baseOffset + iconHeight;
        },

        openInfoWindow: function (dgxy, html, width, height, options) {
            var lngLat = toLngLat(dgxy);
            if (lngLat == null) return null;
            this.closeInfoWindow();
            this._popup = new maplibregl.Popup({
                className: 'easymap-maplibre-popup',
                closeButton: true,
                closeOnClick: false,
                offset: this._getInfoWindowOffset(options)
            });
            if (width != null && typeof this._popup.setMaxWidth == 'function') {
                this._popup.setMaxWidth(parseInt(width, 10) + 'px');
            }
            this._popup.setLngLat(lngLat).setHTML(html || '').addTo(this._map);
            if (height != null) this._popup._easymapHeight = parseInt(height, 10);
            return this._popup;
        },

        _openInfoWindow: function (dgxy, title, content, options) {
            var html = content == null ? (title || '') : (title != null && title !== '' ? '<div class="easymap-maplibre-popup-title">' + title + '</div>' + content : content);
            return this.openInfoWindow(dgxy, html, null, null, options);
        },

        isOpenInfoWindowOpen: function () {
            return this._popup != null;
        },

        openInfoWindow_setXY: function (dgxy) {
            var lngLat = toLngLat(dgxy);
            if (lngLat != null && this._popup != null && typeof this._popup.setLngLat == 'function') {
                this._popup.setLngLat(lngLat);
            }
            return this;
        },

        closeInfoWindow: function () {
            if (this._popup != null) {
                this._popup.remove();
                this._popup = null;
            }
            return this;
        },

        get3DEngine: function () {
            return 'maplibre-three';
        },

        getMapLibreMap: function () {
            return this._map;
        },

        destroy: function () {
            var keys = [];
            for (var key in this._items) {
                if (Object.prototype.hasOwnProperty.call(this._items, key)) keys.push(key);
            }
            for (var i = 0; i < keys.length; i++) {
                this.removeItem(this._items[keys[i]].item);
            }
            for (var j = 0; j < this._eventHandlers.length; j++) {
                this._map.off(this._eventHandlers[j].name, this._eventHandlers[j].handler);
                if (this._eventHandlers[j].domTarget != null && this._eventHandlers[j].domEventName != null && typeof this._eventHandlers[j].domTarget.removeEventListener == 'function') {
                    this._eventHandlers[j].domTarget.removeEventListener(this._eventHandlers[j].domEventName, this._eventHandlers[j].handler);
                }
            }
            this._eventHandlers = [];
            this._removeCameraControl();
            this.disableDragBox();
            this.clearDraw();
            this._removeDrawRenderHandlers();
            this._removeContextMenu();
            this._removeBuiltinControls();
            this.closeInfoWindow();
            this._map.remove();
        }
    };

    window.Easymap = Easymap;
})(window, document);
