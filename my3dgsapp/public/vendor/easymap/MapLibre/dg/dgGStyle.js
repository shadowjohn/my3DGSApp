(function (window) {
    function isStringLike(data, findString) {
        if (findString == '') return true;
        var parts = findString.split('%');
        var offset = 0;
        var hasPrefixWildcard = false;
        for (var i = 0; i < parts.length; i++) {
            if (parts[i] == '') {
                if (i == 0) hasPrefixWildcard = true;
                continue;
            }
            var next = String(data).indexOf(parts[i], offset);
            if (next < 0) return false;
            if (!hasPrefixWildcard && offset != next) return false;
            if (i == parts.length - 1 && parts[i] != String(data).substr(String(data).length - parts[i].length)) return false;
            offset = next + parts[i].length;
        }
        return true;
    }

    function parseColor(value) {
        var color = value;
        var rgb = null;
        if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(color)) {
            var hex = color.substring(1).split('');
            if (hex.length == 3) {
                hex = [hex[0], hex[0], hex[1], hex[1], hex[2], hex[2]];
            }
            var intValue = parseInt(hex.join(''), 16);
            return [(intValue >> 16) & 255, (intValue >> 8) & 255, intValue & 255, 255];
        }
        if (typeof color == 'string') {
            var normalized = color.replace(/\s+/g, '');
            var rgbMatch = normalized.match(/^rgb\((\d+),(\d+),(\d+)\)$/i);
            if (rgbMatch != null) return [
                parseInt(rgbMatch[1], 10),
                parseInt(rgbMatch[2], 10),
                parseInt(rgbMatch[3], 10),
                255
            ];
            var rgbaMatch = normalized.match(/^rgba\((\d+),(\d+),(\d+),([0-9.]+)\)$/i);
            if (rgbaMatch != null) return [
                parseInt(rgbaMatch[1], 10),
                parseInt(rgbaMatch[2], 10),
                parseInt(rgbaMatch[3], 10),
                parseFloat(rgbaMatch[4])
            ];
        }
        if (typeof color == 'string' && isStringLike(color.toLowerCase(), 'rgb(%)')) {
            rgb = color.split(',');
            return [
                parseInt(rgb[0].toLowerCase().replace('rgb(', ''), 10),
                parseInt(rgb[1], 10),
                parseInt(rgb[2].replace(')', ''), 10),
                255
            ];
        }
        if (typeof color == 'string' && isStringLike(color.toLowerCase(), 'rgba(%)')) {
            rgb = color.split(',');
            return [
                parseInt(rgb[0].toLowerCase().replace('rgba(', ''), 10),
                parseInt(rgb[1], 10),
                parseInt(rgb[2], 10),
                parseFloat(rgb[3].replace(')', ''))
            ];
        }
        throw null;
    }

    function setColor(target, color) {
        var rgb = parseColor(color);
        target.r = rgb[0];
        target.g = rgb[1];
        target.b = rgb[2];
    }

    function dgGStyle() {
        this._high = 100;
        this._medium = 20;
        this._colorHigh = { r: 247, g: 14, b: 26 };
        this._colorMedium = { r: 255, g: 153, b: 0 };
        this._colorLow = { r: 37, g: 169, b: 59 };
    }

    dgGStyle.prototype.setHigh = function (high) {
        this._high = high;
        return this;
    };

    dgGStyle.prototype.setMedium = function (medium) {
        this._medium = medium;
        return this;
    };

    dgGStyle.prototype.getHigh = function () {
        return this._high;
    };

    dgGStyle.prototype.getMedium = function () {
        return this._medium;
    };

    dgGStyle.prototype.setColorHigh = function (color) {
        setColor(this._colorHigh, color);
        return this;
    };

    dgGStyle.prototype.setColorMedium = function (color) {
        setColor(this._colorMedium, color);
        return this;
    };

    dgGStyle.prototype.setColorLow = function (color) {
        setColor(this._colorLow, color);
        return this;
    };

    dgGStyle.prototype._hexToRgbA = parseColor;
    dgGStyle.prototype._is_string_like = isStringLike;

    window.dgGStyle = dgGStyle;
    var ns = window.EASYMAP_MAPLIBRE = window.EASYMAP_MAPLIBRE || {};
    ns.modulesLoaded = ns.modulesLoaded || [];
    ns.modulesLoaded.push('dg/dgGStyle');
})(window);
