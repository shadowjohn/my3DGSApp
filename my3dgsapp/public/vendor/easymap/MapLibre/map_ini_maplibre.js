(function (window) {
    window.EASYMAP_MAPLIBRE_DEFAULTS = {
        center: [120.64681, 24.180936],
        zoom: 7,
        pitch: 0,
        bearing: 0,
        attributionControl: false,
        navigationControl: false,
        scaleLine: true,
        statusbar: true,
        mapType: 'google',
        mapTypes: [
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
        ],
        cameraControl: {
            enabled: true,
            button: 'both',
            pitchSpeed: 0.25,
            bearingSpeed: 0.3,
            minPitch: 0,
            maxPitch: 85
        },
        style: {
            version: 8,
            sources: {
                osm: {
                    type: 'raster',
                    tiles: [
                        'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
                    ],
                    tileSize: 256,
                    attribution: 'OpenStreetMap',
                    metadata: {
                        easymapBaseMap: true
                    }
                }
            },
            layers: [
                {
                    id: 'osm',
                    type: 'raster',
                    source: 'osm',
                    metadata: {
                        easymapBaseMap: true
                    }
                }
            ]
        }
    };
})(window);
