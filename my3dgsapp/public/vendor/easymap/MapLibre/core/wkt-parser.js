(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function parsePair(text) {
        var parts = text.trim().split(/\s+/);
        return [ns.toNumber(parts[0], 0), ns.toNumber(parts[1], 0)];
    }

    function splitTopLevel(text) {
        var output = [];
        var level = 0;
        var start = 0;
        for (var i = 0; i < text.length; i++) {
            var ch = text.charAt(i);
            if (ch == '(') level++;
            if (ch == ')') level--;
            if (ch == ',' && level == 0) {
                output.push(text.substring(start, i).trim());
                start = i + 1;
            }
        }
        output.push(text.substring(start).trim());
        return output.filter(function (part) { return part != ''; });
    }

    function stripOuterParens(text) {
        text = text.trim();
        if (text.charAt(0) == '(' && text.charAt(text.length - 1) == ')') {
            return text.substring(1, text.length - 1).trim();
        }
        return text;
    }

    function parseRing(text) {
        return splitTopLevel(stripOuterParens(text)).map(parsePair);
    }

    function parseWktGeometry(wkt) {
        if (typeof wkt != 'string') return null;
        var text = wkt.trim();
        var typeMatch = text.match(/^([a-zA-Z]+)\s*/);
        if (typeMatch == null) return null;
        var type = typeMatch[1].toUpperCase();
        var body = text.substring(typeMatch[0].length).trim();
        if (body.toUpperCase() == 'EMPTY') return null;
        body = stripOuterParens(body);
        if (type == 'POINT') {
            return { type: 'Point', coordinates: parsePair(body) };
        }
        if (type == 'LINESTRING') {
            return { type: 'LineString', coordinates: splitTopLevel(body).map(parsePair) };
        }
        if (type == 'POLYGON') {
            return { type: 'Polygon', coordinates: splitTopLevel(body).map(parseRing) };
        }
        if (type == 'MULTIPOINT') {
            return {
                type: 'MultiPoint',
                coordinates: splitTopLevel(body).map(function (part) {
                    return parsePair(stripOuterParens(part));
                })
            };
        }
        if (type == 'MULTILINESTRING') {
            return {
                type: 'MultiLineString',
                coordinates: splitTopLevel(body).map(function (part) {
                    return splitTopLevel(stripOuterParens(part)).map(parsePair);
                })
            };
        }
        if (type == 'MULTIPOLYGON') {
            return {
                type: 'MultiPolygon',
                coordinates: splitTopLevel(body).map(function (part) {
                    return splitTopLevel(stripOuterParens(part)).map(parseRing);
                })
            };
        }
        return null;
    }

    function rowToFeature(row, index) {
        if (typeof row == 'string') {
            var geometry = parseWktGeometry(row);
            return geometry == null ? null : {
                type: 'Feature',
                properties: { data_index: index },
                geometry: geometry
            };
        }
        if (row != null && typeof row == 'object') {
            if (row.type == 'Feature') return row;
            if (row.type != null && row.coordinates != null) {
                return { type: 'Feature', properties: { data_index: index }, geometry: row };
            }
            var wkt = row.WKT || row.wkt || row.geom || row.geometry_wkt || row.GEOM;
            var rowGeometry = parseWktGeometry(wkt);
            if (rowGeometry == null) return null;
            var properties = {};
            for (var key in row) {
                if (Object.prototype.hasOwnProperty.call(row, key) && key != 'WKT' && key != 'wkt' && key != 'geom' && key != 'geometry_wkt' && key != 'GEOM') {
                    properties[key] = row[key];
                }
            }
            properties.data_index = index;
            return { type: 'Feature', properties: properties, geometry: rowGeometry };
        }
        return null;
    }

    function parseWktToGeoJSON(data) {
        if (data == null) return { type: 'FeatureCollection', features: [] };
        if (typeof data == 'object' && data.type == 'FeatureCollection') return data;
        var rows = Array.isArray(data) ? data : [data];
        var features = [];
        for (var i = 0; i < rows.length; i++) {
            var feature = rowToFeature(rows[i], i);
            if (feature != null) features.push(feature);
        }
        return { type: 'FeatureCollection', features: features };
    }

    ns.parseWktGeometry = parseWktGeometry;
    ns.parseWktToGeoJSON = parseWktToGeoJSON;
    window.EASYMAP_MAPLIBRE_PARSE_WKT = parseWktToGeoJSON;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('core/wkt-parser');
})(window);
