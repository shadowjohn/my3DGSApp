(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};
    var DEG = Math.PI / 180;
    var RAD = 180 / Math.PI;

    var ELLIPSOIDS = {
        WGS84: { a: 6378137, f: 1 / 298.257223563 },
        GRS80: { a: 6378137, f: 1 / 298.257222101 },
        AUST_SA: { a: 6378160, f: 1 / 298.25 }
    };

    var TM2 = {
        'EPSG:3825': { lon0: 119, ellipsoid: 'GRS80', datum: 'twd97' },
        'EPSG:3826': { lon0: 121, ellipsoid: 'GRS80', datum: 'twd97' },
        'EPSG:102443': { lon0: 121, ellipsoid: 'GRS80', datum: 'twd97' },
        'EPSG:3827': { lon0: 119, ellipsoid: 'AUST_SA', datum: 'twd67' },
        'EPSG:3828': { lon0: 121, ellipsoid: 'AUST_SA', datum: 'twd67' },
        'EPSG:3822': { lon0: 121, ellipsoid: 'AUST_SA', datum: 'twd67' }
    };

    var TWD67_TO_WGS84 = {
        dx: -752,
        dy: -358,
        dz: -179,
        rx: -0.0000011698,
        ry: 0.0000018398,
        rz: 0.0000009822,
        ds: 0.00002329
    };

    function normalizeSrs(srs) {
        srs = String(srs || 'EPSG:4326').toUpperCase().replace(/\s+/g, '');
        if (srs == 'EPSG:900913') return 'EPSG:3857';
        return srs;
    }

    function ellipsoidParams(name) {
        var e = ELLIPSOIDS[name] || ELLIPSOIDS.WGS84;
        var b = e.a * (1 - e.f);
        var e2 = 2 * e.f - e.f * e.f;
        return {
            a: e.a,
            b: b,
            f: e.f,
            e2: e2,
            ep2: e2 / (1 - e2)
        };
    }

    function lonLatToMercator(coord) {
        var lon = parseFloat(coord[0]);
        var lat = Math.max(-85.0511287798, Math.min(85.0511287798, parseFloat(coord[1])));
        return [
            6378137 * lon * DEG,
            6378137 * Math.log(Math.tan(Math.PI / 4 + lat * DEG / 2))
        ];
    }

    function mercatorToLonLat(coord) {
        var x = parseFloat(coord[0]);
        var y = parseFloat(coord[1]);
        return [
            x / 6378137 * RAD,
            (2 * Math.atan(Math.exp(y / 6378137)) - Math.PI / 2) * RAD
        ];
    }

    function tmForward(lonLat, config) {
        var e = ellipsoidParams(config.ellipsoid);
        var lat = lonLat[1] * DEG;
        var lon = lonLat[0] * DEG;
        var lon0 = config.lon0 * DEG;
        var k0 = 0.9999;
        var x0 = 250000;
        var y0 = 0;
        var sinLat = Math.sin(lat);
        var cosLat = Math.cos(lat);
        var tanLat = Math.tan(lat);
        var n = e.a / Math.sqrt(1 - e.e2 * sinLat * sinLat);
        var t = tanLat * tanLat;
        var c = e.ep2 * cosLat * cosLat;
        var a = (lon - lon0) * cosLat;
        var e4 = e.e2 * e.e2;
        var e6 = e4 * e.e2;
        var m = e.a * (
            (1 - e.e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * lat -
            (3 * e.e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * Math.sin(2 * lat) +
            (15 * e4 / 256 + 45 * e6 / 1024) * Math.sin(4 * lat) -
            (35 * e6 / 3072) * Math.sin(6 * lat)
        );
        var x = x0 + k0 * n * (
            a +
            (1 - t + c) * Math.pow(a, 3) / 6 +
            (5 - 18 * t + t * t + 72 * c - 58 * e.ep2) * Math.pow(a, 5) / 120
        );
        var y = y0 + k0 * (
            m +
            n * tanLat * (
                a * a / 2 +
                (5 - t + 9 * c + 4 * c * c) * Math.pow(a, 4) / 24 +
                (61 - 58 * t + t * t + 600 * c - 330 * e.ep2) * Math.pow(a, 6) / 720
            )
        );
        return [x, y];
    }

    function tmInverse(coord, config) {
        var e = ellipsoidParams(config.ellipsoid);
        var x = parseFloat(coord[0]) - 250000;
        var y = parseFloat(coord[1]);
        var k0 = 0.9999;
        var lon0 = config.lon0 * DEG;
        var e4 = e.e2 * e.e2;
        var e6 = e4 * e.e2;
        var m = y / k0;
        var mu = m / (e.a * (1 - e.e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256));
        var e1 = (1 - Math.sqrt(1 - e.e2)) / (1 + Math.sqrt(1 - e.e2));
        var phi1 = mu +
            (3 * e1 / 2 - 27 * Math.pow(e1, 3) / 32) * Math.sin(2 * mu) +
            (21 * e1 * e1 / 16 - 55 * Math.pow(e1, 4) / 32) * Math.sin(4 * mu) +
            (151 * Math.pow(e1, 3) / 96) * Math.sin(6 * mu) +
            (1097 * Math.pow(e1, 4) / 512) * Math.sin(8 * mu);
        var sin1 = Math.sin(phi1);
        var cos1 = Math.cos(phi1);
        var tan1 = Math.tan(phi1);
        var n1 = e.a / Math.sqrt(1 - e.e2 * sin1 * sin1);
        var r1 = e.a * (1 - e.e2) / Math.pow(1 - e.e2 * sin1 * sin1, 1.5);
        var t1 = tan1 * tan1;
        var c1 = e.ep2 * cos1 * cos1;
        var d = x / (n1 * k0);
        var lat = phi1 - (n1 * tan1 / r1) * (
            d * d / 2 -
            (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * e.ep2) * Math.pow(d, 4) / 24 +
            (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * e.ep2 - 3 * c1 * c1) * Math.pow(d, 6) / 720
        );
        var lon = lon0 + (
            d -
            (1 + 2 * t1 + c1) * Math.pow(d, 3) / 6 +
            (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * e.ep2 + 24 * t1 * t1) * Math.pow(d, 5) / 120
        ) / cos1;
        return [lon * RAD, lat * RAD];
    }

    function geodeticToEcef(lonLat, ellipsoidName) {
        var e = ellipsoidParams(ellipsoidName);
        var lon = lonLat[0] * DEG;
        var lat = lonLat[1] * DEG;
        var h = lonLat[2] || 0;
        var sinLat = Math.sin(lat);
        var cosLat = Math.cos(lat);
        var n = e.a / Math.sqrt(1 - e.e2 * sinLat * sinLat);
        return [
            (n + h) * cosLat * Math.cos(lon),
            (n + h) * cosLat * Math.sin(lon),
            (n * (1 - e.e2) + h) * sinLat
        ];
    }

    function ecefToGeodetic(xyz, ellipsoidName) {
        var e = ellipsoidParams(ellipsoidName);
        var x = xyz[0];
        var y = xyz[1];
        var z = xyz[2];
        var lon = Math.atan2(y, x);
        var p = Math.sqrt(x * x + y * y);
        var lat = Math.atan2(z, p * (1 - e.e2));
        for (var i = 0; i < 8; i++) {
            var sinLat = Math.sin(lat);
            var n = e.a / Math.sqrt(1 - e.e2 * sinLat * sinLat);
            lat = Math.atan2(z + e.e2 * n * sinLat, p);
        }
        return [lon * RAD, lat * RAD];
    }

    function applyHelmert(xyz, p, inverse) {
        var dx = p.dx, dy = p.dy, dz = p.dz;
        var rx = p.rx, ry = p.ry, rz = p.rz;
        var ds = p.ds;
        if (inverse === true) {
            dx = -dx; dy = -dy; dz = -dz;
            rx = -rx; ry = -ry; rz = -rz;
            ds = -ds;
        }
        var x = xyz[0], y = xyz[1], z = xyz[2];
        return [
            dx + (1 + ds) * x - rz * y + ry * z,
            dy + rz * x + (1 + ds) * y - rx * z,
            dz - ry * x + rx * y + (1 + ds) * z
        ];
    }

    function twd67ToWgs84(lonLat) {
        return ecefToGeodetic(applyHelmert(geodeticToEcef(lonLat, 'AUST_SA'), TWD67_TO_WGS84, false), 'WGS84');
    }

    function wgs84ToTwd67(lonLat) {
        return ecefToGeodetic(applyHelmert(geodeticToEcef(lonLat, 'WGS84'), TWD67_TO_WGS84, true), 'AUST_SA');
    }

    function toWgs84(coord, srs) {
        srs = normalizeSrs(srs);
        if (srs == 'EPSG:4326') return [parseFloat(coord[0]), parseFloat(coord[1])];
        if (srs == 'EPSG:3857') return mercatorToLonLat(coord);
        if (srs == 'EPSG:3821') return twd67ToWgs84([parseFloat(coord[0]), parseFloat(coord[1])]);
        if (TM2[srs] != null) {
            var config = TM2[srs];
            var lonLat = tmInverse(coord, config);
            return config.datum == 'twd67' ? twd67ToWgs84(lonLat) : lonLat;
        }
        return [parseFloat(coord[0]), parseFloat(coord[1])];
    }

    function fromWgs84(lonLat, srs) {
        srs = normalizeSrs(srs);
        if (srs == 'EPSG:4326') return [lonLat[0], lonLat[1]];
        if (srs == 'EPSG:3857') return lonLatToMercator(lonLat);
        if (srs == 'EPSG:3821') return wgs84ToTwd67(lonLat);
        if (TM2[srs] != null) {
            var config = TM2[srs];
            var sourceLonLat = config.datum == 'twd67' ? wgs84ToTwd67(lonLat) : lonLat;
            return tmForward(sourceLonLat, config);
        }
        return [lonLat[0], lonLat[1]];
    }

    function transformCoord(coord, fromSrs, toSrs) {
        var out = fromWgs84(toWgs84(coord, fromSrs), toSrs);
        if (coord.length > 2) out.push(coord[2]);
        return out;
    }

    function transformInput(input, fromSrs, toSrs) {
        if (input == null) return input;
        fromSrs = normalizeSrs(fromSrs);
        toSrs = normalizeSrs(toSrs);
        if (Array.isArray(input) && input.length > 0 && Array.isArray(input[0])) {
            return input.map(function (coord) {
                return transformCoord(coord, fromSrs, toSrs);
            });
        }
        if (Array.isArray(input) && input.length > 0 && typeof input[0] == 'object') {
            return input.map(function (coord) {
                var out = transformCoord([coord.x, coord.y], fromSrs, toSrs);
                var item = { x: out[0], y: out[1] };
                if (coord.z != null) item.z = coord.z;
                return item;
            });
        }
        if (Array.isArray(input) && input.length > 0) {
            var flat = [];
            for (var i = 0; i < input.length - 1; i += 2) {
                var point = transformCoord([input[i], input[i + 1]], fromSrs, toSrs);
                flat.push(point[0], point[1]);
            }
            return flat;
        }
        if (typeof input == 'object' && input.x != null && input.y != null) {
            return transformCoord([input.x, input.y], fromSrs, toSrs);
        }
        return input;
    }

    function transformCoordinates(coords, fromSrs, toSrs) {
        if (!Array.isArray(coords)) return coords;
        if (coords.length >= 2 && typeof coords[0] == 'number' && typeof coords[1] == 'number') {
            return transformCoord(coords, fromSrs, toSrs);
        }
        return coords.map(function (part) {
            return transformCoordinates(part, fromSrs, toSrs);
        });
    }

    function transformGeometry(geometry, fromSrs, toSrs) {
        if (geometry == null || geometry.coordinates == null) return geometry;
        return {
            type: geometry.type,
            coordinates: transformCoordinates(geometry.coordinates, fromSrs, toSrs)
        };
    }

    function transformGeoJson(geojson, fromSrs, toSrs) {
        if (geojson == null || normalizeSrs(fromSrs) == normalizeSrs(toSrs)) return geojson;
        if (geojson.type == 'FeatureCollection') {
            return {
                type: 'FeatureCollection',
                features: (geojson.features || []).map(function (feature) {
                    return {
                        type: 'Feature',
                        properties: feature.properties || {},
                        geometry: transformGeometry(feature.geometry, fromSrs, toSrs)
                    };
                })
            };
        }
        if (geojson.type == 'Feature') {
            return {
                type: 'Feature',
                properties: geojson.properties || {},
                geometry: transformGeometry(geojson.geometry, fromSrs, toSrs)
            };
        }
        return transformGeometry(geojson, fromSrs, toSrs);
    }

    function formatNumber(num) {
        num = Math.round(parseFloat(num) * 100000000) / 100000000;
        var text = num.toString();
        return text.indexOf('e') == -1 ? text : num.toFixed(8).replace(/\.?0+$/, '');
    }

    function coordToWkt(coord) {
        return coord.map(formatNumber).join(' ');
    }

    function coordsToWkt(coords, depth) {
        if (depth == 0) return coordToWkt(coords);
        return '(' + coords.map(function (part) {
            return coordsToWkt(part, depth - 1);
        }).join(', ') + ')';
    }

    function geometryToWkt(geometry) {
        if (geometry == null) return '';
        var type = geometry.type;
        if (type == 'Point') return 'POINT (' + coordToWkt(geometry.coordinates) + ')';
        if (type == 'LineString') return 'LINESTRING ' + coordsToWkt(geometry.coordinates, 1);
        if (type == 'Polygon') return 'POLYGON ' + coordsToWkt(geometry.coordinates, 2);
        if (type == 'MultiPoint') return 'MULTIPOINT ' + coordsToWkt(geometry.coordinates, 1);
        if (type == 'MultiLineString') return 'MULTILINESTRING ' + coordsToWkt(geometry.coordinates, 2);
        if (type == 'MultiPolygon') return 'MULTIPOLYGON ' + coordsToWkt(geometry.coordinates, 3);
        return '';
    }

    function transformWkt(wkt, fromSrs, toSrs) {
        if (typeof ns.parseWktGeometry != 'function') return wkt;
        var geometry = ns.parseWktGeometry(wkt);
        return geometryToWkt(transformGeometry(geometry, fromSrs, toSrs));
    }

    ns.normalizeSrs = normalizeSrs;
    ns.projTransfer = transformInput;
    ns.projCoordinate = transformCoord;
    ns.transformGeoJson = transformGeoJson;
    ns.transformWkt = transformWkt;
    ns.geometryToWkt = geometryToWkt;
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('core/projection');
})(window);
