(function (window) {
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};

    function hashText(text) {
        text = String(text || '');
        var hash = 5381;
        for (var i = 0; i < text.length; i++) {
            hash = ((hash << 5) + hash) + text.charCodeAt(i);
            hash = hash & hash;
        }
        return Math.abs(hash).toString(36);
    }

    function parseColor(value, fallback) {
        var color = value || fallback;
        var output = {
            color: color,
            opacity: null
        };
        if (typeof color != 'string') return output;
        var match = color.replace(/\s+/g, '').match(/^rgba\((\d+),(\d+),(\d+),([0-9.]+)\)$/i);
        if (match != null) {
            output.color = 'rgb(' + match[1] + ',' + match[2] + ',' + match[3] + ')';
            output.opacity = Math.max(0, Math.min(1, parseFloat(match[4])));
            return output;
        }
        match = color.replace(/\s+/g, '').match(/^rgb\((\d+),(\d+),(\d+)\)$/i);
        if (match != null) {
            output.color = 'rgb(' + match[1] + ',' + match[2] + ',' + match[3] + ')';
        }
        return output;
    }

    function numberOr(value, fallback) {
        var num = parseFloat(value);
        return isNaN(num) ? fallback : num;
    }

    function cloneArray(value, fallback) {
        if (Array.isArray(value)) return value.slice();
        return fallback;
    }

    function parseFontSize(font, fallback) {
        if (typeof font != 'string') return fallback;
        var match = font.match(/(\d+(?:\.\d+)?)(px|pt)/i);
        if (match == null) return fallback;
        var value = parseFloat(match[1]);
        if (isNaN(value)) return fallback;
        return match[2].toLowerCase() == 'pt' ? value * 4 / 3 : value;
    }

    function offsetFromPixels(x, y, size, fallback) {
        if (x == null && y == null) return fallback;
        var textSize = numberOr(size, 13);
        if (textSize <= 0) textSize = 13;
        return [
            numberOr(x, 0) / textSize,
            numberOr(y, 0) / textSize
        ];
    }

    function normalizeAnchor(anchor) {
        if (typeof anchor == 'string') return anchor;
        if (!Array.isArray(anchor)) return 'bottom';
        var x = numberOr(anchor[0], 0.5);
        var y = numberOr(anchor[1], 1);
        if (y <= 0.25) return x <= 0.25 ? 'top-left' : (x >= 0.75 ? 'top-right' : 'top');
        if (y >= 0.75) return x <= 0.25 ? 'bottom-left' : (x >= 0.75 ? 'bottom-right' : 'bottom');
        return x <= 0.25 ? 'left' : (x >= 0.75 ? 'right' : 'center');
    }

    function refreshItemStyle(item) {
        if (item != null && item._easymap != null && typeof item._easymap._refreshItemStyle == 'function') {
            item._easymap._refreshItemStyle(item);
        }
    }

    function refreshItemData(item) {
        if (item != null && item._easymap != null && typeof item._easymap._updateItemData == 'function') {
            item._easymap._updateItemData(item);
        }
    }

    function getVectorStyle(item) {
        var options = item && item._options ? item._options : {};
        var state = item._styleState || {};
        var lineStroke = parseColor(state.lineStrokeColor || state.lineColor || state.strokeColor || options.lineStrokeColor || options.lineColor || options.strokeColor || options['stroke-color'], 'green');
        var polygonStroke = parseColor(state.polygonStrokeColor || state.polygonColor || state.strokeColor || options.polygonStrokeColor || options.polygonColor || options.strokeColor || options['stroke-color'], 'blue');
        var fill = parseColor(state.polygonFillColor || state.fillColor || options.polygonFillColor || options.fillColor || options['fill-color'], 'rgba(0,0,255,0.1)');
        var extrusionOptions = options.extrusion != null && typeof options.extrusion == 'object' ? options.extrusion : {};
        var extrusion = parseColor(state.extrusionColor || options.extrusionColor || options['extrusion-color'] || extrusionOptions.color || fill.color, fill.color);
        var point = parseColor(state.pointColor || options.pointColor || options['point-color'], 'transparent');
        var pointStroke = parseColor(state.pointStrokeColor || options.pointStrokeColor || 'red', 'red');
        var extrusionEnabled = state.extrusionEnabled != null ? state.extrusionEnabled : (options.extrusionEnabled != null ? options.extrusionEnabled : null);
        if (extrusionEnabled == null && typeof options.extrusion == 'boolean') extrusionEnabled = options.extrusion;
        if (extrusionEnabled == null && options.extrusion != null && typeof options.extrusion == 'object') extrusionEnabled = extrusionOptions.enabled !== false;
        if (extrusionEnabled == null) extrusionEnabled = false;
        var extrusionVisible = extrusionEnabled === true || extrusionEnabled == 'true';
        return {
            strokeColor: polygonStroke.color,
            strokeOpacity: state.polygonStrokeOpacity != null ? state.polygonStrokeOpacity : (state.strokeOpacity != null ? state.strokeOpacity : (polygonStroke.opacity != null ? polygonStroke.opacity : numberOr(options.lineOpacity, 0.92))),
            strokeWidth: numberOr(state.polygonStrokeWidth != null ? state.polygonStrokeWidth : (state.strokeWidth != null ? state.strokeWidth : (options.strokeWidth != null ? options.strokeWidth : options.width)), 3),
            lineDash: cloneArray(state.polygonLineDash != null ? state.polygonLineDash : (state.lineDash != null ? state.lineDash : options.lineDash), [4]),
            lineCap: state.polygonLineCap || state.lineCap || options.lineCap || 'round',
            lineColor: lineStroke.color,
            lineOpacity: state.lineStrokeOpacity != null ? state.lineStrokeOpacity : (state.strokeOpacity != null ? state.strokeOpacity : (lineStroke.opacity != null ? lineStroke.opacity : numberOr(options.lineOpacity, 1))),
            lineWidth: numberOr(state.lineStrokeWidth != null ? state.lineStrokeWidth : (state.strokeWidth != null ? state.strokeWidth : (options.strokeWidth != null ? options.strokeWidth : options.width)), 1),
            lineLineDash: cloneArray(state.lineLineDash != null ? state.lineLineDash : options.lineLineDash, null),
            lineLineCap: state.lineLineCap || options.lineLineCap || 'round',
            fillColor: fill.color,
            fillOpacity: state.fillOpacity != null ? state.fillOpacity : (fill.opacity != null ? fill.opacity : numberOr(options.fillOpacity, 0.22)),
            extrusionEnabled: extrusionVisible,
            extrusionColor: extrusion.color,
            extrusionHeight: numberOr(state.extrusionHeight != null ? state.extrusionHeight : (options.extrusionHeight != null ? options.extrusionHeight : (options.height != null ? options.height : extrusionOptions.height)), extrusionVisible ? 60 : 0),
            extrusionBase: numberOr(state.extrusionBase != null ? state.extrusionBase : (options.extrusionBase != null ? options.extrusionBase : (options.base != null ? options.base : extrusionOptions.base)), 0),
            extrusionOpacity: state.extrusionOpacity != null ? state.extrusionOpacity : (extrusion.opacity != null ? extrusion.opacity : numberOr(options.extrusionOpacity != null ? options.extrusionOpacity : extrusionOptions.opacity, 0.58)),
            pointColor: point.color,
            pointOpacity: state.pointOpacity != null ? state.pointOpacity : (point.opacity != null ? point.opacity : 1),
            pointRadius: numberOr(state.pointRadius != null ? state.pointRadius : options.pointRadius, 5),
            pointStrokeColor: pointStroke.color,
            pointStrokeOpacity: state.pointStrokeOpacity != null ? state.pointStrokeOpacity : (pointStroke.opacity != null ? pointStroke.opacity : 1),
            pointStrokeWidth: numberOr(state.pointStrokeWidth != null ? state.pointStrokeWidth : options.pointStrokeWidth, 1)
        };
    }

    function getMarkerStyle(item) {
        var icon = item ? item._dgicon : null;
        return {
            src: icon != null ? icon._src : '',
            width: icon != null ? numberOr(icon._w, 32) : 32,
            height: icon != null ? numberOr(icon._h, 32) : 32,
            scale: numberOr(item && item._scale != null ? item._scale : (icon != null ? icon._scale : 1), 1),
            opacity: numberOr(item && item._opacity != null ? item._opacity : (icon != null ? icon._opacity : 0.95), 0.95),
            rotate: numberOr(item && item._rotate != null ? item._rotate : (icon != null ? icon._rotate : 0), 0),
            anchor: normalizeAnchor(item && item._anchor != null ? item._anchor : [0.5, 1])
        };
    }

    function getMarkerLabelStyle(item) {
        var style = item && item._textStyle ? item._textStyle : {};
        var color = parseColor(style.color || style['font-color'] || '#111827', '#111827');
        var halo = parseColor(style.haloColor || style['halo-color'] || style['font-stroke-color'] || '#ffffff', '#ffffff');
        return {
            text: item && item._text != null ? String(item._text) : '',
            size: numberOr(style.fontSize != null ? style.fontSize : style.size, 13),
            color: color.color,
            opacity: color.opacity != null ? color.opacity : numberOr(style.opacity, 1),
            haloColor: halo.color,
            haloWidth: numberOr(style.haloWidth != null ? style.haloWidth : style['font-stroke-width'], 1.5),
            offset: cloneArray(style.offset || [0, 1.2], [0, 1.2]),
            anchor: style.anchor || 'top'
        };
    }

    function getWktLabelStyle(item) {
        var options = item && item._options ? item._options : {};
        var state = item && item._styleState ? item._styleState : {};
        var style = options.Text || options.text || options.labelStyle || {};
        var font = state.labelFont || style.font || options.labelFont || '12pt sans-serif';
        var size = numberOr(state.labelSize != null ? state.labelSize : (style.fontSize != null ? style.fontSize : (style.size != null ? style.size : options.labelSize)), parseFontSize(font, 13));
        var color = parseColor(state.labelColor || style.color || style['font-color'] || options.labelColor || '#111827', '#111827');
        var halo = parseColor(state.labelHaloColor || style.haloColor || style['halo-color'] || style['font-stroke-color'] || options.labelHaloColor || '#ffffff', '#ffffff');
        var basePointOffset = cloneArray(style.pointOffset || options.labelPointOffset || style.offset || options.labelOffset || [0, 1.6], [0, 1.6]);
        var baseSurfaceOffset = cloneArray(style.surfaceOffset || options.labelSurfaceOffset || [0, 0], [0, 0]);
        var baseLineOffset = cloneArray(style.lineOffset || options.labelLineOffset || [0, 0], [0, 0]);
        if (item != null && item._point_positionY != null) basePointOffset = offsetFromPixels(state.labelOffsetX, item._point_positionY, size, basePointOffset);
        if (item != null && item._polygon_positionY != null) baseSurfaceOffset = offsetFromPixels(state.labelOffsetX, item._polygon_positionY, size, baseSurfaceOffset);
        if (item != null && item._linestring_positionY != null) baseLineOffset = offsetFromPixels(state.labelOffsetX, item._linestring_positionY, size, baseLineOffset);
        var globalOffset = offsetFromPixels(state.labelOffsetX, state.labelOffsetY, size, null);
        if (globalOffset != null) {
            basePointOffset = globalOffset.slice();
            baseSurfaceOffset = globalOffset.slice();
            baseLineOffset = globalOffset.slice();
        }
        return {
            size: size,
            color: color.color,
            opacity: state.labelOpacity != null ? state.labelOpacity : (color.opacity != null ? color.opacity : numberOr(style.opacity != null ? style.opacity : options.labelOpacity, 1)),
            haloColor: halo.color,
            haloWidth: numberOr(state.labelHaloWidth != null ? state.labelHaloWidth : (style.haloWidth != null ? style.haloWidth : (style['font-stroke-width'] != null ? style['font-stroke-width'] : options.labelHaloWidth)), 1.5),
            offset: basePointOffset.slice(),
            pointOffset: basePointOffset,
            surfaceOffset: baseSurfaceOffset,
            lineOffset: baseLineOffset,
            anchor: style.anchor || options.labelAnchor || 'top',
            pointAnchor: style.pointAnchor || options.labelPointAnchor || style.anchor || options.labelAnchor || 'top',
            surfaceAnchor: style.surfaceAnchor || options.labelSurfaceAnchor || 'center'
        };
    }

    function getTextStyle(item) {
        var color = parseColor(item != null ? item._textColor : null, 'rgba(255,0,0,1)');
        var size = numberOr(item != null ? item._fontSize : null, 10);
        var rotate = parseInt(item != null ? item._rotate : 0, 10);
        if (isNaN(rotate)) rotate = 0;
        return {
            text: item != null && item._label != null ? String(item._label) : '',
            size: size,
            color: color.color,
            opacity: color.opacity != null ? color.opacity : 1,
            haloColor: item != null && item._textOuterColor != null ? item._textOuterColor : 'rgba(255,255,255,0.5)',
            haloWidth: numberOr(item != null ? item._textOuterWidth : null, 0.5),
            rotate: rotate % 360,
            offset: item != null && Array.isArray(item._textOffset) ? item._textOffset.slice() : [0, 0],
            anchor: item != null && item._textAnchor != null ? item._textAnchor : 'center'
        };
    }

    function getPointStyle(item) {
        var fill = parseColor(item != null ? item._fillStyle : null, 'rgba(0,0,255,1)');
        var stroke = parseColor(item != null ? item._strokeStyle : null, fill.color);
        var radius = numberOr(item != null && item._lineWidth != null ? item._lineWidth : (item != null ? item._ptRadius : null), 6);
        return {
            label: item != null && item._label != null ? String(item._label) : '',
            radius: radius,
            fillColor: fill.color,
            fillOpacity: fill.opacity != null ? fill.opacity : 1,
            strokeColor: stroke.color,
            strokeOpacity: stroke.opacity != null ? stroke.opacity : 1,
            strokeWidth: numberOr(item != null ? item._strokeWidth : null, 0)
        };
    }

    function getPolylineStyle(item) {
        var stroke = parseColor(item != null ? item._strokeStyle : null, 'rgba(0,0,255,1)');
        var dash = item != null && item._dash != null ? item._dash : {};
        return {
            color: stroke.color,
            opacity: stroke.opacity != null ? stroke.opacity : 1,
            width: numberOr(item != null ? item._lineWidth : null, 2),
            lineDash: cloneArray(dash.lineDash, null),
            lineCap: dash.lineCap || 'round',
            lineJoin: dash.lineJoin || 'round'
        };
    }

    function getPolygonStyle(item) {
        var stroke = parseColor(item != null ? item._strokeStyle : null, 'rgba(0,0,255,1)');
        var fill = parseColor(item != null ? item._fillStyle : null, 'rgba(0,0,255,0.25)');
        var dash = item != null && item._dash != null ? item._dash : {};
        return {
            strokeColor: stroke.color,
            strokeOpacity: stroke.opacity != null ? stroke.opacity : 1,
            strokeWidth: numberOr(item != null ? item._lineWidth : null, 2),
            fillColor: fill.color,
            fillOpacity: fill.opacity != null ? fill.opacity : 0.25,
            lineDash: cloneArray(dash.lineDash, null),
            lineCap: dash.lineCap || 'round',
            lineJoin: dash.lineJoin || 'round'
        };
    }

    function rgbFromGStyleColor(value, fallback) {
        var color = value || fallback || {};
        var r = parseInt(color.r, 10);
        var g = parseInt(color.g, 10);
        var b = parseInt(color.b, 10);
        if (isNaN(r) || isNaN(g) || isNaN(b)) return fallback;
        return 'rgb(' + r + ',' + g + ',' + b + ')';
    }

    function getDgGStyleClusterStyle(gStyle, options) {
        var high = parseInt(gStyle != null ? gStyle._high : null, 10);
        var medium = parseInt(gStyle != null ? gStyle._medium : null, 10);
        if (isNaN(high) || high < 2) high = 100;
        if (isNaN(medium) || medium < 2) medium = 20;
        if (medium >= high) medium = high - 1;
        var lowColor = rgbFromGStyleColor(gStyle._colorLow, 'rgb(37,169,59)');
        var mediumColor = rgbFromGStyleColor(gStyle._colorMedium, 'rgb(255,153,0)');
        var highColor = rgbFromGStyleColor(gStyle._colorHigh, 'rgb(247,14,26)');
        return {
            circleRadius: options.clusterCircleRadius || ['step', ['get', 'point_count'], 18, medium + 1, 24, high + 1, 32],
            circleColor: options.clusterCircleColor || options.clusterColor || ['step', ['get', 'point_count'], lowColor, medium + 1, mediumColor, high + 1, highColor],
            circleOpacity: numberOr(options.clusterCircleOpacity, 0.72),
            circleStrokeColor: options.clusterCircleStrokeColor || 'rgba(255,255,255,0.9)',
            circleStrokeWidth: numberOr(options.clusterCircleStrokeWidth, 2),
            textSize: numberOr(options.clusterTextSize, 12),
            textColor: options.clusterTextColor || '#ffffff',
            textOpacity: numberOr(options.clusterTextOpacity, 1),
            textHaloColor: options.clusterTextHaloColor || 'rgba(0,0,0,0.6)',
            textHaloWidth: numberOr(options.clusterTextHaloWidth, 3)
        };
    }

    function getClusterStyle(item) {
        var options = item && item._options ? item._options : {};
        if (item != null && item._clusterStyleKind == 'dgGStyle' && item._Style != null) {
            return getDgGStyleClusterStyle(item._Style, options);
        }
        var circle = parseColor(options.clusterCircleColor || options.clusterColor || '#22c55e', '#22c55e');
        var stroke = parseColor(options.clusterCircleStrokeColor || '#0f172a', '#0f172a');
        var text = parseColor(options.clusterTextColor || '#0f172a', '#0f172a');
        var halo = parseColor(options.clusterTextHaloColor || '#ffffff', '#ffffff');
        return {
            circleRadius: options.clusterCircleRadius || ['step', ['get', 'point_count'], 18, 50, 24, 200, 32],
            circleColor: circle.color,
            circleOpacity: circle.opacity != null ? circle.opacity : numberOr(options.clusterCircleOpacity, 0.88),
            circleStrokeColor: stroke.color,
            circleStrokeWidth: numberOr(options.clusterCircleStrokeWidth, 2),
            textSize: numberOr(options.clusterTextSize, 12),
            textColor: text.color,
            textOpacity: text.opacity != null ? text.opacity : numberOr(options.clusterTextOpacity, 1),
            textHaloColor: halo.color,
            textHaloWidth: numberOr(options.clusterTextHaloWidth, 1)
        };
    }

    function makeImageId(src) {
        return 'easymap-maplibre-img-' + hashText(src);
    }

    function setVectorColor(item, key, value) {
        item._styleState = item._styleState || {};
        var parsed = parseColor(value, value);
        item._styleState[key] = parsed.color;
        if (parsed.opacity != null) {
            if (key == 'strokeColor') item._styleState.strokeOpacity = parsed.opacity;
            if (key == 'lineStrokeColor') item._styleState.lineStrokeOpacity = parsed.opacity;
            if (key == 'polygonStrokeColor') item._styleState.polygonStrokeOpacity = parsed.opacity;
            if (key == 'fillColor') item._styleState.fillOpacity = parsed.opacity;
            if (key == 'polygonFillColor') item._styleState.fillOpacity = parsed.opacity;
            if (key == 'pointColor') item._styleState.pointOpacity = parsed.opacity;
            if (key == 'pointStrokeColor') item._styleState.pointStrokeOpacity = parsed.opacity;
            if (key == 'labelColor') item._styleState.labelOpacity = parsed.opacity;
        }
        refreshItemStyle(item);
    }

    function getStrokeKeys(kind) {
        if (kind == 'point') {
            return { color: 'pointStrokeColor', width: 'pointStrokeWidth' };
        }
        if (kind == 'line') {
            return { color: 'lineStrokeColor', width: 'lineStrokeWidth', dash: 'lineLineDash', cap: 'lineLineCap' };
        }
        if (kind == 'polygon') {
            return { color: 'polygonStrokeColor', width: 'polygonStrokeWidth', dash: 'polygonLineDash', cap: 'polygonLineCap' };
        }
        return { color: 'strokeColor', width: 'strokeWidth', dash: 'lineDash', cap: 'lineCap' };
    }

    function createStrokeApi(item, kind) {
        var keys = getStrokeKeys(kind);
        return {
            setColor: function (value) {
                setVectorColor(item, keys.color, value);
                return this;
            },
            setWidth: function (value) {
                item._styleState = item._styleState || {};
                item._styleState[keys.width] = numberOr(value, kind == 'line' ? 1 : 3);
                refreshItemStyle(item);
                return this;
            },
            setLineDash: function (value) {
                if (Array.isArray(value)) {
                    item._styleState = item._styleState || {};
                    item._styleState[keys.dash] = value.slice();
                    refreshItemStyle(item);
                }
                return this;
            },
            setLineCap: function (value) {
                if (['round', 'square', 'butt'].indexOf(value) >= 0) {
                    item._styleState = item._styleState || {};
                    item._styleState[keys.cap] = value;
                    refreshItemStyle(item);
                }
                return this;
            }
        };
    }

    function createFillApi(item, key) {
        return {
            setColor: function (value) {
                setVectorColor(item, key || 'fillColor', value);
                return this;
            }
        };
    }

    function createImageApi(item) {
        return {
            setRadius: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.pointRadius = numberOr(value, 5);
                refreshItemStyle(item);
                return this;
            },
            getStroke: function () {
                return createStrokeApi(item, 'point');
            },
            getFill: function () {
                return createFillApi(item, 'pointColor');
            },
            setOpacity: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.pointOpacity = numberOr(value, 0.95);
                refreshItemStyle(item);
                return this;
            }
        };
    }

    function createGeometryStyle(item, kind) {
        var fillKey = kind == 'point' ? 'pointColor' : (kind == 'polygon' ? 'polygonFillColor' : 'fillColor');
        return {
            getStroke: function () {
                return createStrokeApi(item, kind);
            },
            getFill: function () {
                return createFillApi(item, fillKey);
            },
            getImage: function () {
                return createImageApi(item);
            }
        };
    }

    function createTextStrokeApi(item) {
        return {
            setColor: function (value) {
                setVectorColor(item, 'labelHaloColor', value);
                return this;
            },
            setWidth: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.labelHaloWidth = numberOr(value, 1.5);
                refreshItemStyle(item);
                return this;
            }
        };
    }

    function createTextApi(item) {
        var textApi = {
            getFill: function () {
                return createFillApi(item, 'labelColor');
            },
            getStroke: function () {
                return createTextStrokeApi(item);
            },
            getBackgroundFill: function () {
                return createFillApi(item, 'labelBackgroundColor');
            },
            setFont: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.labelFont = value;
                var size = parseFontSize(value, null);
                if (size != null) item._styleState.labelSize = size;
                refreshItemStyle(item);
                return this;
            },
            setOffsetX: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.labelOffsetX = numberOr(value, 0);
                refreshItemStyle(item);
                return this;
            },
            setOffsetY: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.labelOffsetY = numberOr(value, 0);
                refreshItemStyle(item);
                return this;
            },
            setOverflow: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.labelOverflow = value !== false;
                refreshItemStyle(item);
                return this;
            },
            setPlacement: function (value) {
                item._styleState = item._styleState || {};
                item._styleState.labelPlacement = value;
                refreshItemStyle(item);
                return this;
            },
            setText: function () {
                return this;
            }
        };
        return {
            getText: function () {
                return textApi;
            }
        };
    }

    ns.hashText = hashText;
    ns.parseColor = parseColor;
    ns.parseFontSize = parseFontSize;
    ns.offsetFromPixels = offsetFromPixels;
    ns.cloneArray = cloneArray;
    ns.normalizeAnchor = normalizeAnchor;
    ns.refreshItemStyle = refreshItemStyle;
    ns.refreshItemData = refreshItemData;
    ns.getVectorStyle = getVectorStyle;
    ns.getMarkerStyle = getMarkerStyle;
    ns.getMarkerLabelStyle = getMarkerLabelStyle;
    ns.getWktLabelStyle = getWktLabelStyle;
    ns.getTextStyle = getTextStyle;
    ns.getPointStyle = getPointStyle;
    ns.getPolylineStyle = getPolylineStyle;
    ns.getPolygonStyle = getPolygonStyle;
    ns.getClusterStyle = getClusterStyle;
    ns.makeImageId = makeImageId;
    ns.createWktStyleProxy = function (item) {
        return {
            Text: createTextApi(item),
            Point: createGeometryStyle(item, 'point'),
            MultiPoint: createGeometryStyle(item, 'point'),
            LineString: createGeometryStyle(item, 'line'),
            MultiLineString: createGeometryStyle(item, 'line'),
            Polygon: createGeometryStyle(item, 'polygon'),
            MultiPolygon: createGeometryStyle(item, 'polygon'),
            GeometryCollection: createGeometryStyle(item, 'geometrycollection')
        };
    };

    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('core/style-utils');
})(window);
