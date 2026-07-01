function my_fix_random() {
    //var array = new Uint32Array(1);
    //var v = window.crypto.getRandomValues(array)[0];
    //return parseFloat((v / (Math.pow(10, v.toString().length))).toFixed(10));    
    var crypto = window.crypto /*native*/ || window.msCrypto /*IE11 native*/ || window.msrCrypto; /*polyfill*/
    return parseFloat(((new Uint32Array(1))[0] / 4294967295).toString(36).substring(2, 15) + (crypto.getRandomValues(new Uint32Array(1))[0] / 4294967295));
}
var userAgent = navigator.userAgent.toLowerCase();
var is_opera = userAgent.indexOf('opera') != -1;
var is_moz = userAgent.indexOf('firefox') != -1;
var is_chrome = userAgent.indexOf('chrome') != -1;
var is_safari = userAgent.indexOf('safari') != -1;
//var is_ie = (userAgent.indexOf('msie') != -1 || userAgent.indexOf('rv:11') != -1) && !is_moz && !is_opera && !is_chrome && !is_safari;
//var is_ie = (((userAgent.indexOf('msie') != -1 && !is_opera) && userAgent.substr(userAgent.indexOf('msie') + 5, 3)) || !!window.MSInputMethodContext && !!document.documentMode);
var is_ie = ((userAgent.indexOf('msie') != -1 && !is_opera) && userAgent.substr(userAgent.indexOf('msie') + 5, 3)) || userAgent.indexOf("rv:11.0") > 0;
var isAndroid = userAgent.indexOf("android") > -1;
var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
function isMobile() {
    // 判斷是否為行動裝置
    return (isAndroid || isIOS || userAgent.indexOf("Mobile") > -1 || userAgent.indexOf("iPad") > -1 || userAgent.indexOf("iPhone") > -1);
}
/*
  //iframe包含
  if (top.location != location) {
        top.location.href = location.href;
  }

  function $(id) {
     return document.getElementById(id);
  }
*/

/*
 * 注意事項，value請直接以純字串處理，不建議用什麼boolean，可能會失敗
 * 例如 setMemory("isDrag",true);
 * 那麼，判斷true or false 記得要這樣 if(getMemory("isDrag")=='true'))
 * 要以字串來判斷，最好 setMemory 也當純字串使用 'true'
 */
function setMemory(wtfkey, value) {
    localStorage.setItem(wtfkey, value);
}
function getMemory(wtfkey) {
    return localStorage.getItem(wtfkey);
}
function removeMemory(wtfkey) {
    return localStorage.removeItem(wtfkey);
}
String.prototype.trim = function () { return this.replace(/(^\s*)|(\s*$)/g, "") };

function safeHtml(value) {
    return htmlspecialchars(value == null ? "" : String(value), "ENT_QUOTES");
}

function appendCsrf(postdata) {
    if (!window.CSRF_TOKEN || postdata == null || postdata === "") {
        return postdata;
    }
    if (typeof FormData !== "undefined" && postdata instanceof FormData) {
        if (!postdata.has("_csrf_token")) {
            postdata.append("_csrf_token", window.CSRF_TOKEN);
        }
        return postdata;
    }
    if (typeof postdata === "object") {
        postdata._csrf_token = window.CSRF_TOKEN;
        return postdata;
    }
    if (typeof postdata === "string" && postdata.indexOf("_csrf_token=") === -1) {
        return postdata + (postdata === "" ? "" : "&") + "_csrf_token=" + encodeURIComponent(window.CSRF_TOKEN);
    }
    return postdata;
}

function getWindowSize() {
    var myWidth = 0, myHeight = 0;
    if (typeof (window.innerWidth) == 'number') {
        //Non-IE
        myWidth = window.innerWidth;
        myHeight = window.innerHeight;
    } else if (document.documentElement && (document.documentElement.clientWidth || document.documentElement.clientHeight)) {
        //IE 6+ in 'standards compliant mode'
        myWidth = document.documentElement.clientWidth;
        myHeight = document.documentElement.clientHeight;
    } else if (document.body && (document.body.clientWidth || document.body.clientHeight)) {
        //IE 4 compatible
        myWidth = document.body.clientWidth;
        myHeight = document.body.clientHeight;
    }
    var a = {};
    a['width'] = myWidth;
    a['height'] = myHeight;
    return a;
}
function myAjax(url, postdata) {
    $method = "POST";
    if (postdata == "") {
        $method = "GET";
    }
    if ($method === "POST") {
        postdata = appendCsrf(postdata);
    }
    var tmp = $.ajax({
        url: url,
        type: $method,
        data: postdata,
        dataType: 'html',
        //crossDomain:true,
        async: false
    }).responseText;
    return tmp;
}
function myAjax_async(url, postdata, dom, func) {
    $method = "POST";
    if (postdata == "") {
        $method = "GET";
    }
    if ($method === "POST") {
        postdata = appendCsrf(postdata);
    }
    $.ajax({
        url: url,
        type: $method,
        data: postdata,
        async: true,
        dataType: 'html',
        success: function (html) {
            if (dom != "") {
                $(dom)[decodeURIComponent(encodeURIComponent('html'))](html);
            }
            func(html);
        }
    });
}
function myAjax_async_json(url, postdata, func) {
    var method = "POST";
    if (postdata == "") {
        method = "GET";
    }
    if (method === "POST") {
        postdata = appendCsrf(postdata);
    }
    $.ajax({
        url: url,
        type: method,
        data: postdata,
        async: true,
        dataType: 'json',
        success: function (html) {
            func(html);
            my_gc(html);
            html = null;
        }
    });
}
function myAjax_async_form(url, formData, func) {
    //配合 var formData = new FormData();
    //formData.append('file', $('#file')[0].files[0]);
    formData = appendCsrf(formData);
    $.ajax({
        url: url,
        type: "POST",
        data: formData,
        async: true,
        cache: false,
        processData: false, // 禁止處理 `postdata`（因為是檔案）
        contentType: false, // 禁止自動設定 `Content-Type`
        enctype: 'multipart/form-data',
        dataType: 'html',
        success: function (html) {
            func(html);
            my_gc(html);
            html = null;
        }
    });
}
function ValidEmail(emailtoCheck) {
    //  email
    //  規則:  1.只有一個  "@"
    //              2.網址中,  至少要有一個".",  且不能連續出現
    //              3.不能有空白
    var regExp = /^[^@^\s]+@[^\.@^\s]+(\.[^\.@^\s]+)+$/;
    if (emailtoCheck.match(regExp))
        return true;
    else
        return false;
}
function size_hum_read($size) {
    /* Returns a human readable size */
    $size = parseInt($size);
    var $i = 0;
    var $iec = [];
    var $iec_kind = "B,KB,MB,GB,TB,PB,EB,ZB,YB";
    $iec = explode(',', $iec_kind);
    while (($size / 1024) > 1) {
        $size = $size / 1024;
        $i++;
    }
    return sprintf("%s %s", substr($size, 0, strpos($size, '.') + 3), $iec[$i]);
}
$.fn.center = function () {
    this.css("position", "absolute");
    this.css("top", ($(window).height() - this.height()) / 2 + $(window).scrollTop() + "px");
    this.css("left", ($(window).width() - this.width()) / 2 + $(window).scrollLeft() + "px");
    return this;
}
$.fn.centerX = function () {
    this.css("position", "absolute");
    this.css("left", ($(window).width() - this.width()) / 2 + $(window).scrollLeft() + "px");
    return this;
}
$.fn.centerY = function () {
    this.css("position", "absolute");
    this.css("top", ($(window).height() - this.height()) / 2 + $(window).scrollTop() + "px");
    return this;
}
function dialogMyBoxOn(message, isTouchOutSideClose, functionAction) {
    $.mybox({
        is_background_touch_close: isTouchOutSideClose,
        message: message,
        css: {
            border: '2px solid #fff',
            backgroundColor: '#fff',
            padding: '15px'
        },
        onBlock: function () {
            functionAction();
        }
    });
}
function dialogMyBoxOff() {
    $.unmybox();
}
function basename(filepath) {
    m = explode("/", filepath);
    mdata = explode("?", end(m));
    return mdata[0];
}
function mainname(filepath) {
    filepath = basename(filepath);
    var mdata = explode(".", filepath);
    return mdata[0];
}
function subname(filepath) {
    filepath = basename(filepath);
    var m = explode(".", filepath);
    return end(m);
}
function is_string_like($data, $find_string) {
    /*
      is_string_like($data,$fine_string)
    
      $mystring = "Hi, this is good!";
      $searchthis = "%thi% goo%";
    
      $resp = string_like($mystring,$searchthis);
    
    
      if ($resp){
         echo "milike = VERDADERO";
      } else{
         echo "milike = FALSO";
      }
    
      Will print:
      milike = VERDADERO
    
      and so on...
    
      this is the function:
    */
    $tieneini = 0;
    if ($find_string == "") return 1;
    $vi = explode("%", $find_string);
    $offset = 0;
    for ($n = 0, $max_n = count($vi); $n < $max_n; $n++) {
        if ($vi[$n] == "") {
            if ($vi[0] == "") {
                $tieneini = 1;
            }
        } else {
            $newoff = strpos($data, $vi[$n], $offset);
            if ($newoff !== false) {
                if (!$tieneini) {
                    if ($offset != $newoff) {
                        return false;
                    }
                }
                if ($n == $max_n - 1) {
                    if ($vi[$n] != substr($data, strlen($data) - strlen($vi[$n]), strlen($vi[$n]))) {
                        return false;
                    }

                } else {
                    $offset = $newoff + strlen($vi[$n]);
                }
            } else {
                return false;
            }
        }
    }
    return true;
}
//加密與解密
function enPWD_string($str, $key) {
    if ($str == null) {
        $str = "";
    }
    $str = base64_encode($str);
    $key = base64_encode($key);
    $xored = "";
    //alert($str);
    for ($i = 0, $max_i = $str.length; $i < $max_i; $i++) {
        $a = ord(substr($str, $i, 1));
        for ($j = 0, $max_j = $key.length; $j < $max_j; $j++) {
            $k = ord(substr($key, $j, 1));
            $a = $a ^ $k;
        }
        $xored = sprintf("%s%s", $xored, chr($a));
    }
    return base64_encode($xored);
}
function dePWD_string($str, $key) {
    if ($str == null) {
        $str = "";
    }
    $str = base64_decode($str);
    $key = base64_encode($key);
    $xored = "";
    for ($i = 0, $max_i = $str.length; $i < $max_i; $i++) {
        $a = ord(substr($str, $i, 1));
        for ($j = $key.length - 1; $j >= 0; $j--) {
            $k = ord(substr($key, $j, 1));
            $a = $a ^ $k;
        }
        $xored = sprintf("%s%s", $xored, chr($a));
    }
    $xored = base64_decode($xored);
    return $xored;
}
function get_between($data, $s_begin, $s_end) {
    /*
      $a = "abcdefg";
      echo get_between($a, "cde", "g");
      // get "f"
    */
    $s = $data;
    $start = strpos($s, $s_begin);
    $new_s = substr($s, $start + strlen($s_begin));
    $end = strpos($new_s, $s_end);
    return substr($s, $start + strlen($s_begin), $end);
}
function smallComment(message, seconds, is_need_motion, cssOptions) {
    //畫面的1/15	
    if ($("#mysmallComment").length == 0) {
        $("body").append("<div id='mysmallComment'><span class='' id='mysmallCommentContent'></span></div>");
        $("#mysmallComment").css({
            'display': 'none',
            'position': 'fixed',
            'left': '0px',
            'right': '0px',
            'padding': '15px',
            'bottom': '3em',
            'z-index': new Date().getTime(),
            'text-align': 'center',
            'opacity': 0.8,
            'pointer-events': 'none'
        });
        $("#mysmallCommentContent").css({
            'color': '#fff',
            'background-color': '#000',
            'padding': '10px',
            'border': '3px solid #fff',
            'pointer-events': 'none'
        });
        $("#mysmallCommentContent").css(cssOptions);
        /*
        $("#mysmallComment").css({
            'left': (wh['width']-$("#mysmallComment").width())/2+'px' 
        });
        */

        //$("#mysmallComment").corner();
    }
    var mlen = strlen(strip_tags(message));
    var font_size = "16px";
    if (mlen >= 10) {
        font_size = "12px";
    }
    $("#mysmallCommentContent").css({
        'font-size': font_size
    });
    $("#mysmallCommentContent")[decodeURIComponent(encodeURIComponent('html'))](message);
    if (is_need_motion == true) {
        $("#mysmallComment").stop();
        $("#mysmallComment").fadeIn("slow");
        clearTimeout(window['smallComment_TIMEOUT']);
        window['smallComment_TIMEOUT'] = setTimeout(function () {
            $("#mysmallComment").fadeOut('fast');
        }, seconds);
    }
    else {
        $("#mysmallComment").stop();
        $("#mysmallComment").show();
        clearTimeout(window['smallComment_TIMEOUT']);
        window['smallComment_TIMEOUT'] = setTimeout(function () {
            $("#mysmallComment").hide();
        }, seconds);
    }
}
/// <summary>
/// $ra:Array
/// $fields:欄位名稱
/// $headers:中文欄位名稱
/// $classname:使用的style css名稱
/// </summary>
function print_table($ra, $fields, $headers, $classname) {
    $classname = (typeof ($classname) == "undefined" || $classname == '') ? '' : " class='" + $classname + "' ";
    if (typeof ($fields) == "undefined" || $fields == '' || $fields == '*') {

        $tmp = "<table " + $classname + " border='1' cellspacing='0' cellpadding='0'>";
        $tmp += "<thead><tr>";
        for (var k in $ra[0]) {
            $tmp += "<th field=\"" + k + "\">" + k + "</th>";
        }
        $tmp += "</tr></thead>";
        $tmp += "<tbody>";
        for ($i = 0, $max_i = $ra.length; $i < $max_i; $i++) {
            $tmp += "<tr>";
            for (var k in $ra[$i]) {
                $tmp += "<td field=\"" + k + "\">" + $ra[$i][k] + "</td>";
            }
            $tmp += "</tr>";
        }
        $tmp += "</tbody>";
        $tmp += "</table>";
        return $tmp;
    }
    else {
        $tmp = "<table " + $classname + " border='1' cellspacing='0' cellpadding='0'>";
        $tmp += "<thead><tr>";
        $mheaders = $headers.split(',');
        $m_fields = $fields.split(',');
        for (var k = 0, max_k = $mheaders.length; k < max_k; k++) {
            $tmp += "<th field=\"" + $m_fields[k] + "\">" + $mheaders[k] + "</th>";
        }
        $tmp += "</tr></thead>";
        $tmp += "<tbody>";

        for ($i = 0, $max_i = $ra.length; $i < $max_i; $i++) {
            $tmp += "<tr>";
            for (var k = 0, max_k = $m_fields.length; k < max_k; k++) {
                $tmp += "<td field=\"" + $m_fields[k] + "\">" + $ra[$i][$m_fields[k]] + "</td>";
            }
            $tmp += "</tr>";
        }
        $tmp += "</tbody>";
        $tmp += "</table>";
        return $tmp;
    }
}
function print_table_v(ra, fields, show_fields, theclass) {
    var names = [];
    var show_names = [];
    if (count(ra) > 0) {
        for (var k in ra[0]) {
            names.push(k);
            show_names.push(k);
        }
    }
    if (typeof (fields) != "undefined") {
        names = [];
        show_names = [];
        fields = trim(fields);
        show_fields = trim(show_fields);
        var m = explode(",", fields);
        var sm = explode(",", show_fields);
        if (count(m) != count(sm)) {
            alert('Now same array...');
            return;
        }

        for (var i = 0, max_i = count(m); i < max_i; i++) {
            names.push(m[i]);
            show_names.push(sm[i]);
        }
    }
    var table_data = "";
    var class_append = "";
    if (typeof (theclass) != "undefined") {
        class_append += " class=\"" + theclass + "\" ";
    }
    table_data = "<table " + class_append + ">";
    table_data += "<thead>";
    table_data += "<tr>";
    table_data += "<th>項目</th>";
    table_data += "<th colspan=\"" + count(ra) + "\">內容</th>";
    table_data += "</tr>";
    table_data += "</thead>";
    table_data += "<tbody>";
    for (var k = 0, max_k = names.length; k < max_k; k++) {
        table_data += "<tr>";
        table_data += "<th>" + show_names[k] + "</th>";
        for (var i = 0; i < ra.length; i++) {
            for (var obj in ra[i]) {
                if (obj == names[k]) {
                    table_data += "<td fields=\"" + names[k] + "\">" + ra[i][obj] + "</td>";
                }
            }
        }
        table_data += "</tr>";
    }
    table_data += "</tbody>";
    table_data += "</table>";
    return table_data;
}
function myW(html, func, cssOption) {
    if (typeof (window['myW_t']) == "undefined") {
        window['myW_t'] = 0;
    }
    $.fn.center = function () {
        this.css("position", "absolute");
        this.css("top", ($(window).height() - this.height()) / 2 + $(window).scrollTop() + "px");
        this.css("left", ($(window).width() - this.width()) / 2 + $(window).scrollLeft() + "px");
        return this;
    }
    var t = new Date().getTime() + "_" + window['myW_t']++;
    var id = "myW_" + t;
    $("body").append("<div id='" + id + "'></div>");
    $("#" + id).css({
        'position': 'absolute',
        'z-index': new Date().getTime(),
        'padding': '3px',
        'background-color': '#fff',
        'color': 'black',
        'border': '2px solid #00f'
    });
    if (typeof (cssOption) != "undefined" && typeof (cssOption) == "object") {
        for (var k in cssOption) {
            $("#" + id).css(k, cssOption[k]);
        }
    }
    html = html.replace("{myW_id}", id);
    $("#" + id)[decodeURIComponent(encodeURIComponent('html'))](html);
    $(window).bind("scroll", { id: id }, function (event) {
        $("#" + event.data.id).center();
    });
    $("#" + id).center();
    func(id);
    return id;
}
function nl2br(varTest) {
    return varTest.replace(/(\r\n|\n\r|\n)/g, "<br>");
}
function br2nl(varTest) {
    return varTest.replace(/<br>/g, "\n").replace(/<br \/>/g, "\n");
}
function json_format(json) {
    if (typeof (json) == "string") {
        return JSON.stringify(json_decode(json, true), null, 2);
    }
    else {
        return JSON.stringify(json, null, 2);
    }
}
function json_highlight(json) {
    /*
    pre {outline: 1px solid #ccc; padding: 5px; margin: 5px; }
    .string { color: green; }
    .number { color: darkorange; }
    .boolean { color: blue; }
    .null { color: magenta; }
    .key { color: red; }
    */
    if (typeof json != 'string') {
        json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'color: red;'; //key
            } else {
                cls = 'color: green;'; //string
            }
        } else if (/true|false/.test(match)) {
            cls = 'color: blue;'; //boolean
        } else if (/null/.test(match)) {
            cls = 'color: magenta;'; //null
        }
        return '<span style="' + cls + '">' + match + '</span>';
    });
}
// ref: http://stackoverflow.com/a/1293163/2343
// This will parse a delimited string into an array of
// arrays. The default delimiter is the comma, but this
// can be overriden in the second argument.
// ref: http://stackoverflow.com/a/1293163/2343
// This will parse a delimited string into an array of
// arrays. The default delimiter is the comma, but this
// can be overriden in the second argument.
function csvtoarray(strData, strDelimiter, isToAssoc = false) {
    // Check to see if the delimiter is defined. If not,
    // then default to comma.
    strData = str_replace("\r", "", strData).trim();
    strDelimiter = (strDelimiter || ",");

    // Create a regular expression to parse the CSV values.
    var objPattern = new RegExp(
        (
            // Delimiters.
            "(\\" + strDelimiter + "|\\r?\\n|\\r|^)" +

            // Quoted fields.
            "(?:\"([^\"]*(?:\"\"[^\"]*)*)\"|" +

            // Standard fields.
            "([^\"\\" + strDelimiter + "\\r\\n]*))"
        ),
        "gi"
    );


    // Create an array to hold our data. Give the array
    // a default empty first row.
    var arrData = [
        []
    ];

    // Create an array to hold our individual pattern
    // matching groups.
    var arrMatches = null;


    // Keep looping over the regular expression matches
    // until we can no longer find a match.
    while (arrMatches = objPattern.exec(strData)) {
        // Get the delimiter that was found.
        var strMatchedDelimiter = arrMatches[1];
        // Check to see if the given delimiter has a length
        // (is not the start of string) and if it matches
        // field delimiter. If id does not, then we know
        // that this delimiter is a row delimiter.
        if (
            strMatchedDelimiter.length &&
            strMatchedDelimiter !== strDelimiter
        ) {
            // Since we have reached a new row of data,
            // add an empty row to our data array.
            arrData.push([]);

        }

        var strMatchedValue;

        // Now that we have our delimiter out of the way,
        // let's check to see which kind of value we
        // captured (quoted or unquoted).
        if (arrMatches[2]) {

            // We found a quoted value. When we capture
            // this value, unescape any double quotes.
            strMatchedValue = arrMatches[2].replace(
                new RegExp("\"\"", "g"),
                "\""
            );
        } else {
            // We found a non-quoted value.
            strMatchedValue = arrMatches[3];
        }
        // Now that we have our value string, let's add
        // it to the data array.
        arrData[arrData.length - 1].push(strMatchedValue);
    }
    // Return the parsed data.
    if (isToAssoc) {
        //轉成二維陣列
        var o = arrData.slice();
        arrData = [];
        var keys = [];
        for (var i = 0, max_i = o[0].length; i < max_i; i++) {
            keys.push(o[0][i]);
        }
        for (var i = 1, max_i = o.length; i < max_i; i++) {
            var d = {};
            for (var j = 0, max_j = keys.length; j < max_j; j++) {
                d[keys[j]] = o[i][j];
            }
            arrData.push(d);
        }
    }
    return arrData;
}
function img_mouseover_show(dom, options = null) {
    dom.unbind("mouseout").mouseout(function () {
        $("#show_pic_div_img_mouseover_show").stop().fadeOut();
    });

    //for copy
    dom.unbind("mousedown").mousedown(function () {
        var o_w = $(this).width();
        var o_h = $(this).height();
        if ($(this).attr('bsrc') != null) {
            $(this).attr('src', $(this).attr('bsrc')).width(o_w).height(o_h);
        }
    });

    dom.unbind("mouseover").bind("mouseover", function () {
        window['wh'] = getWindowSize();
        console.log(window['wh']);
        if ($("#show_pic_div_img_mouseover_show").length == 0) {
            $("body").append("<div id='show_pic_div_img_mouseover_show'></div>");
        }
        //console.log($(this).css('width')+","+$(this).css('height'));
        //var r = parseInt(str_replace("px","",$(this).css('height'))) / parseInt(str_replace("px","",$(this).css('width')));
        if (window['wh']['width'] > window['wh']['height']) {
            if (parseInt(str_replace("px", "", $(this).css('width'))) > parseInt(str_replace("px", "", $(this).css('height')))) {

                console.log('ww1：一般電腦螢幕，橫圖');
                $("#show_pic_div_img_mouseover_show").css({
                    'position': 'fixed',
                    'pointer-events': 'none',
                    'max-width': (window['wh']['width'] * 80 / 100) + 'px',
                    'max-height': (window['wh']['height'] * 80 / 100) + 'px',
                    'height': (window['wh']['height'] * 80 / 100) + 'px',
                    'background-color': '#dcdcdc',
                    'box-shadow': '1px 1px 10px rgba(0,0,0,0.5)',
                    'z-index': time() * 100,
                    'opacity': 1,
                    'padding': '15px',
                    'display': 'none'
                });
            }
            else {
                //一般電腦螢幕-直圖
                console.log('ww2：一般電腦螢幕，直圖');
                $("#show_pic_div_img_mouseover_show").css({
                    'position': 'fixed',
                    'pointer-events': 'none',
                    'max-width': (window['wh']['width'] * 80 / 100) + 'px',
                    'max-height': (window['wh']['height'] * 80 / 100) + 'px',
                    'height': (window['wh']['height'] * 80 / 100) + 'px',
                    'background-color': '#dcdcdc',
                    'box-shadow': '1px 1px 10px rgba(0,0,0,0.5)',
                    'z-index': time() * 100,
                    'opacity': 1,
                    'padding': '15px',
                    'display': 'none',
                    'top': (window['wh']['height'] - window['wh']['height'] * 70 / 100) + 'px'
                });
            }
        }
        else {
            //手機直螢幕-橫圖
            if (parseInt(str_replace("px", "", $(this).css('width'))) > parseInt(str_replace("px", "", $(this).css('height')))) {
                console.log('ww3：手機直螢幕-橫圖');
                $("#show_pic_div_img_mouseover_show").css({
                    'position': 'fixed',
                    'pointer-events': 'none',
                    'max-width': (window['wh']['width'] * 80 / 100) + 'px',
                    'max-height': (window['wh']['height'] * 80 / 100) + 'px',
                    'height': (window['wh']['height'] * 80 / 100) + 'px',
                    'background-color': '#dcdcdc',
                    'box-shadow': '1px 1px 10px rgba(0,0,0,0.5)',
                    'z-index': time() * 100,
                    'opacity': 1,
                    'padding': '15px',
                    'display': 'none',
                    'top': (window['wh']['height'] - window['wh']['height'] * 70 / 100) + 'px'
                });
            }
            else {
                console.log('ww4：手機直螢幕-直圖');
                $("#show_pic_div_img_mouseover_show").css({
                    'position': 'fixed',
                    'pointer-events': 'none',
                    'max-width': (window['wh']['width'] * 80 / 100) + 'px',
                    'max-height': (window['wh']['height'] * 80 / 100) + 'px',
                    'background-color': '#dcdcdc',
                    'box-shadow': '1px 1px 10px rgba(0,0,0,0.5)',
                    'z-index': time() * 100,
                    'opacity': 1,
                    'padding': '15px',
                    'display': 'none'
                });
            }

        }
        //$("#show_pic_div").center();
        //$("#show_pic_div").corner();
        var Img = new Image();
        Img.onload = function () {
            if (options != null) {
                var w = "100%";
                var h = "100%";
                if (options['width'] != null) {
                    w = options['width'];
                }
                if (options['height'] != null) {
                    h = options['height'];
                }
                $("#show_pic_div_img_mouseover_show").css({
                    "width": "auto",
                    "height": "auto"
                });
                $('#show_pic_div_img_mouseover_show')[decodeURIComponent(encodeURIComponent('html'))]("<img src='" + this.src + "' style='pointer-events:none;width:" + w + ";height:" + h + ";'>");
            }
            else {
                $('#show_pic_div_img_mouseover_show')[decodeURIComponent(encodeURIComponent('html'))]("<img src='" + this.src + "' style='pointer-events:none;width:100%;height:100%;'>");
            }
            $('#show_pic_div_img_mouseover_show').center();
            if (this.width > window['wh']['width'] * 80 / 100) {
                $('#show_pic_div_img_mouseover_show')[decodeURIComponent(encodeURIComponent('html'))]("<img src='" + this.src + "' style='pointer-events:none;width:" + (window['wh']['width'] * 80 / 100) + "px;height:auto;'>");
            }
            if (this.height > window['wh']['height'] * 77 / 100) {
                $('#show_pic_div_img_mouseover_show')[decodeURIComponent(encodeURIComponent('html'))]("<img src='" + this.src + "' style='pointer-events:none;width:auto;height:" + (window['wh']['height'] * 77 / 100) + "px;'>");
            }

            $('#show_pic_div_img_mouseover_show').center();
        };
        Img.src = ($(this).attr('bsrc') != null) ? $(this).attr('bsrc') : $(this).attr('src');

        var show_url = ($(this).attr('bsrc') != null) ? $(this).attr('bsrc') : $(this).attr('src');

        $("#show_pic_div_img_mouseover_show")[decodeURIComponent(encodeURIComponent('html'))]("<img src=\"" + show_url + "\" onLoad=\"$('#show_pic_div_img_mouseover_show').center();\" style='pointer-events: none;width:100%;height:100%;'>");
        $("#show_pic_div_img_mouseover_show").stop().fadeIn();
        $("#show_pic_div_img_mouseover_show").center();
        return true;
    });
}
function my_gc(obj) {
    if (typeof obj !== 'object' || obj === null) {
        return; // 傳入非物件或空值，直接返回
    }

    if (Array.isArray(obj)) {
        obj.length = 0; // 清空陣列元素
    } else {
        for (const prop in obj) {
            if (obj.hasOwnProperty(prop)) {
                if (typeof obj[prop] === 'object') {
                    my_gc(obj[prop]); // 遞迴處理子物件
                }
                obj[prop] = null; // 將屬性設置為 null
            }
        }
    }
}
function getGET() {
    var output = {};
    output['hash'] = location.hash;
    var _m = location.href.replace(output['hash'], '').split('?');
    _m.shift();
    var pa = _m.join('?');
    if (pa == "") return output;
    var map = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#039;': "'" };
    pa = pa.replace(/&amp;|&lt;|&gt;|&quot;|&#039;/g, function (m) { return map[m]; });
    var mpa = pa.split("&");
    for (var k = 0, max_k = mpa.length; k < max_k; k++) {
        //console.log(mpa[k]);
        var d = mpa[k].split("=");
        output[d[0]] = decodeURIComponent(d[1]);
    }
    return output;
}
function fb_date($datetime) {
    //類似 facebook的時間轉換方式
    //傳入日期　格式如 2011-01-19 04:12:12 
    //就會回傳 facebook 的幾秒、幾分鐘、幾小時的那種
    $week_array = new Array('星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日');
    $timestamp = strtotime($datetime);
    $distance = (time() - $timestamp);
    if ($distance < 60) {
        return sprintf("%d %s", $distance, ("秒前"));
    }
    else if ($distance >= 60 && $distance < 60 * 60) {
        return sprintf("%d %s", Math.floor($distance / 60), ("分鐘前"));
    }
    else if ($distance >= 60 * 60 && $distance < 60 * 60 * 24) {
        return sprintf("%d %s", Math.floor($distance / 60 / 60), ("小時前"));
    }
    else if ($distance >= 60 * 60 * 24 && $distance < 60 * 60 * 24 * 7) {
        return sprintf("%s %s", ($week_array[(date('N', $timestamp) - 1)]), date('H:i', $timestamp));
    }
    else {
        return sprintf("%s", date("Y/m/d H:i", $timestamp));
    }
}
//以後排序用這支
function array_sort(arr, field, order) {
    var array = arr.slice();
    //order = ='SORT_DESC'
    if (order == null) {
        order = 'ASC';
    }
    //From : https://davidwalsh.name/array-sort
    return array.sort(function (obj1, obj2) {
        // Ascending: first age less than the previous
        switch (order) {
            case 'ASC':
            case 'SORT_ASC':
                if (!isNaN(obj1[field]) && !isNaN(obj2[field])) {
                    return obj1[field] - obj2[field];
                }
                else {
                    return obj1[field].replace("一", "1").replace("二", "2").replace("三", "3").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9").localeCompare(obj2[field].replace("一", "1").replace("二", "2").replace("三", "3").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9"), "zh-Hant");
                }
                break;
            case 'DESC':
            case 'SORT_DESC':
                if (!isNaN(obj1[field]) && !isNaN(obj2[field])) {
                    return obj2[field] - obj1[field];
                }
                else {
                    return obj2[field].replace("一", "1").replace("二", "2").replace("三", "3").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9").localeCompare(obj1[field].replace("一", "1").replace("二", "2").replace("三", "3").replace("四", "4").replace("五", "5").replace("六", "6").replace("七", "7").replace("八", "8").replace("九", "9"), "zh-Hant");
                }
                break;
        }
    });
}
function isAllowChars(data, allowCharsString) {
    if (typeof (data) != "string" || typeof (allowCharsString) != "string") {
        console.log("Error use allowCharsString, wrong input type, not string...");
        return false;
    }
    var m = allowCharsString.split("");
    for (var i = 0, max_i = data.length; i < max_i; i++) {
        if (m.indexOf(data.charAt(i)) == -1) return false;
    }
    return true;
}
function arduino_map(x, in_min, in_max, out_min, out_max) {
    //x = 輸入值
    //in 如 0~255
    //out 如 0~1024
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}
function mytabs(dom, obj) {
    /*
      obj.head_css
      obj.head_li_focus_css
      obj.content_css
      obj.show = #div id
      //example:
  mytabs($("#tabs"),{
    head_li_focus_css:{
      'background-color':'#77ff77',
      'font-weight':'bold'
    },
    head_li_css:{
      'background-color':'#eeeeee',
      'font-weight':'normal'
    },
    head_a_css:{
      color:'#000'
    },  content_css:{
     
    },
    show : "#tabs-1"
  });
    */
    var li_a = dom.find("> ul li a");
    dom.find("> ul li a").css({
        "text-decoration": "none"
    });
    dom.find("> ul li").css({
        "padding": "8px",
        "border-top": "1px solid #fff",
        "border-left": "1px solid #fff",
        "border-right": "1px solid #fff",
        "border-bottom": "0px",
        "margin": "0px",
        "border-radius": "5px 5px 0px 0px"
    });
    dom.find("> ul li:visible").css({
        "display": "inline"
    });
    if (obj.head_li_css != null) {
        dom.find("> ul li").css(obj.head_li_css);
    }
    if (obj.head_a_css != null) {
        dom.find("> ul li a").css(obj.head_a_css);
    }
    if (obj.content_css != null) {
        for (var i = 0, max_i = li_a.length; i < max_i; i++) {
            var id = li_a.eq(i).attr('href');
            dom.find(id).css(obj.content_css);
        }
    }
    li_a.bind("click", { "dom": dom, "obj": obj, "li_a": li_a }, function (e) {
        e.data.li_a.attr('active', null);
        $(this).attr('active', "Y");
        var this_href = $(this).attr('href');
        var li_a = e.data.dom.find("> ul li a");
        var mids = [];
        for (var i = 0, max_i = li_a.length; i < max_i; i++) {
            var id = li_a.eq(i).attr('href');
            li_a.eq(i).closest("li").css({ 'background-color': 'transparent' });
            if (e.data.obj.head_li_css != null) {
                li_a.eq(i).closest("li").css(e.data.obj.head_li_css);
            }
            mids.push(id);
            e.data.dom.find(id).hide();
        }
        //li css
        $(this).closest("li").css({ 'background-color': '#006' });
        if (e.data.obj.head_li_focus_css != null) {
            $(this).closest("li").css(e.data.obj.head_li_focus_css);
        }

        e.data.dom.find(this_href).show();
        //div css
        e.data.dom.find(this_href).css({
            'border': '1px solid #fff',
            'padding': '10px',
            'display': 'block',
            'margin-top': '10px'
        });
        return false;
    }); //a click
    if (obj.show != null) {
        dom.find("> ul li a[href='" + obj.show + "']").trigger("click");
    }
    else {
        dom.find("> ul li a").eq(0).trigger("click");
    }
}
function str_replace_deep(search, replace, subject) {
    if (search === null || search === "") return subject;

    if (Array.isArray(subject)) {
        return subject.map(function (oneSubject) {
            return str_replace_deep(search, replace, oneSubject);
        });
    } else {
        return subject.replace(new RegExp(search, 'g'), replace);
    }
}

function secondtodhis($time) {
    // 秒數轉換成天時分秒
    // Create by 羽山 - Updated for better readability and logic
    // 2010-02-07, Updated: 2024-12-25

    $days = Math.floor($time / (24 * 60 * 60));
    $time %= (24 * 60 * 60); // 剩餘的時間

    $hours = Math.floor($time / (60 * 60));
    $time %= (60 * 60); // 剩餘的時間

    $mins = Math.floor($time / 60);
    $seconds = $time % 60;

    // 根據天、時、分、秒組合輸出
    $output = '';
    if ($days > 0) {
        $output += sprintf("%d天", $days);
    }
    if ($hours > 0 || $output !== '') {
        $output += sprintf("%02d時", $hours);
    }
    if ($mins > 0 || $output !== '') {
        $output += sprintf("%02d分", $mins);
    }
    $output += sprintf("%02d秒", $seconds);

    return $output;
}

function uuid() {
    let firstChar = "abcdef"[Math.floor(my_fix_random() * 6)]; // 確保第一碼是 a-f
    return (firstChar + 'xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx').replace(/[xy]/g, function (c) {
        let r = my_fix_random() * 16 | 0;
        let v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function my_table_page(jq_table_dom, page_cols = 10, options = null) {
    //var crypto = window.crypto /*native*/ || window.msCrypto /*IE11 native*/ || window.msrCrypto; /*polyfill*/
    //crypto.randomUUID
    var _options = {
        "output_dom": null, //輸出的page dom 要放在哪，如是 null 接在表格後
        "page_dom_uuid": (jq_table_dom.data('page_dom_uuid') == null) ? uuid() : jq_table_dom.data('page_dom_uuid'),
        "max_cols": 1, //一個畫面最多幾筆，此值建議為 5 7 9
        "first_btn": true, //是否顯示 回首頁
        "first_btn_txt": "&laquo;",
        "last_btn": true, //是否顯示 最末頁
        "last_btn_txt": "&raquo;&raquo;",
        "prev_txt": "&laquo;",
        "next_txt": "&raquo;",
        "css_class": "pages",
        "css_style": ``
    };

    jq_table_dom.data('page_dom_uuid', _options.page_dom_uuid);
    if (typeof (page_cols) == "undefined") {
        page_cols = 10;
    }
    if (options != null && typeof (options) == "object") {
        var ks = Object.keys(options);
        ks.map(function (kk) {
            _options[kk] = options[kk];
        });
    }

    var totals = jq_table_dom.find("tbody tr").length;
    var page_output = `
    <div reqk='my_table_page_div' page_dom_uuid='${_options["page_dom_uuid"]}' req_current_page='0' req_max_cols='${_options['max_cols']}'>
    <div class='pages float-lg-start'>    
    `;
    var is_need_add_one = ((totals % page_cols) > 0) ? 1 : 0;
    var total_pages = Math.floor(totals / page_cols) + is_need_add_one;
    if (_options['max_cols'] == -1) {
        for (var i = 1; i <= total_pages; i++) {
            //page_output += "<a href='javascript:;' reqk='thepage' req_page='" + (i - 1) + "'>" + i + "</a> ";
            page_output += "<input type='text' req_page='" + (i - 1) + "' value='" + i + "' class='form-control form-control-sm fc-auto text-end'>";
        }
    } else {
        //這是有上、下頁、分頁模式
        if (_options["first_btn"]) {
            page_output += `<a href="javascript:;" title="最首頁" reqk='page_first'><i class="fa fa-angle-double-left" aria-hidden="true"></i></a> `;
        }
        page_output += `<a href="javascript:;" title="上一頁" reqk='page_prev'><i class="fa fa-angle-left" aria-hidden="true"></i></a> `;
        page_output += `<div class="con"> 第 `;             
        for (var i = 1, max_i = total_pages; i <= max_i; i++) {
            page_output += "<a href='javascript:;' reqk='thepage' req_page='" + (i - 1) + "'>" + i + "</a> ";
        }
        page_output += `頁，共 ${total_pages} 頁 </div>`;
        page_output += `<a href="javascript:;" title="下一頁" reqk='page_next'><i class="fa fa-angle-right" aria-hidden="true"></i></a> `;

        if (_options["last_btn"]) {
            page_output += `<a href="javascript:;" title="最末頁" reqk='page_last'><i class="fa fa-angle-double-right" aria-hidden="true"></i></a>`;
        }

    }
    page_output += '</div>';
    page_output += `
    <span class="pagesTitle float-lg-end">
        <select class="form-select form-select-sm fc-auto me-2" reqk="page_cols">
            <!--<option value='1'>1</option>-->
            <option value='5'>5</option>
            <option value='10' selected>10</option>
            <option value='15'>15</option>
            <option value='20'>20</option>
            <option value='25'>25</option>
            <option value='30'>30</option>
        </select> 每頁筆數，共 ${total_pages} 頁，共 ${totals} 筆 
    </span>
    `;
    page_output += '</div>';
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").remove();
    if (_options.output_dom == null) {
        jq_table_dom.after(page_output);
    } else {
        _options.output_dom.html(page_output);
    }
    //預設只顯示 1~5 ?
    if (_options['max_cols'] != -1) {
        jq_table_dom.next("div[reqk='my_table_page_div'] a[reqk='thepage']").hide();
        for (var i = 0, max_i = (total_pages < _options['max_cols']) ? total_pages : _options['max_cols']; i < max_i; i++) {
            $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "'] a[reqk='thepage']").eq(i).show();
        }
    }
    // 每頁筆數
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "'] select[reqk='page_cols']").val(page_cols);
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "'] select[reqk='page_cols']").off().change({
        'jq_table_dom': jq_table_dom,
        'page_cols': page_cols,
        'options': options
    }, function (e) {        
        my_table_page(e.data.jq_table_dom, $(this).val(), e.data.options);
    });

    //首頁與末頁
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").eq(0).find("a[reqk='page_first']").off().click(function () {
        var p_dom = $(this).closest("div[reqk='my_table_page_div']").eq(0);
        var p = 0;
        p_dom.find("a[reqk='thepage'][req_page='" + p + "']").trigger("click");
        p_dom.attr('req_current_page', p);

    });
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").eq(0).find("a[reqk='page_last']").off().click(function () {
        var p_dom = $(this).closest("div[reqk='my_table_page_div']").eq(0);
        var p = total_pages - 1;
        p_dom.find("a[reqk='thepage'][req_page='" + p + "']").trigger("click");
        p_dom.attr('req_current_page', p);

    });
    //按上下頁
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").eq(0).find("a[reqk='page_prev']").off().click(function () {
        var p_dom = $(this).closest("div[reqk='my_table_page_div']").eq(0);
        var p = parseInt(p_dom.attr('req_current_page')) - 1;
        p = (p <= 0) ? 0 : p;
        p_dom.find("a[reqk='thepage'][req_page='" + p + "']").trigger("click");
        p_dom.attr('req_current_page', p);

    });
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").eq(0).find("a[reqk='page_next']").off().click(function () {
        var p_dom = $(this).closest("div[reqk='my_table_page_div']").eq(0);
        var p = parseInt(p_dom.attr('req_current_page')) + 1;
        p = (p > parseInt(p_dom.attr('req_total_pages')) - 1) ? parseInt(p_dom.attr('req_total_pages')) - 1 : p;
        p_dom.find("a[reqk='thepage'][req_page='" + p + "']").trigger("click");
        p_dom.attr('req_current_page', p);
    });

    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").attr('req_total_pages', total_pages);
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").eq(0).find("a[reqk='thepage']").unbind("click").click({
        'table': jq_table_dom,
        'page_cols': page_cols
    }, function (e) {
        e.data.table.find("tbody tr").hide();
        var p = parseInt($(this).attr('req_page'));
        //clear color
        
        //如果 req_max_cols 不是 -1 代表有分頁，顯示該 page 頭前後  N 頁
        var div_dom = $(this).closest("div[reqk='my_table_page_div']").eq(0);
        div_dom.attr('req_current_page', p);
        var max_cols = parseInt(div_dom.attr('req_max_cols'));
        
        if (max_cols != -1) {
            var half_max_cols = Math.floor(max_cols / 2.0);
            //每次按都全藏

            $(this).closest("div[reqk='my_table_page_div']").eq(0).find("a[reqk='thepage']").hide();
            //console.log(p + "," + half_max_cols);
            if (p < half_max_cols) {
                //顯示 1~N
                for (var i = 0, max_i = (total_pages < _options['max_cols']) ? total_pages : _options['max_cols']; i < max_i; i++) {
                    $(this).closest("div[reqk='my_table_page_div']").eq(0).find("a[reqk='thepage']").eq(i).show();
                }
            } else if (p >= total_pages - half_max_cols) {
                //顯示 最後 N 頁
                for (var i = total_pages - max_cols, max_i = total_pages; i < max_i; i++) {
                    $(this).closest("div[reqk='my_table_page_div']").eq(0).find("a[reqk='thepage']").eq(i).show();
                }
            } else {
                for (var i = p - half_max_cols, max_i = p + half_max_cols + 1; i < max_i; i++) {
                    $(this).closest("div[reqk='my_table_page_div']").eq(0).find("a[reqk='thepage']").eq(i).show();
                }

            }
        }

        //這是表格的值顯示

        for (var i = p * e.data.page_cols; i < p * e.data.page_cols + page_cols; i++) {
            e.data.table.find("tbody tr").eq(i).show();
        }

    });
    //trigger first page
    $("div[reqk='my_table_page_div'][page_dom_uuid='" + _options.page_dom_uuid + "']").eq(0).find("a[reqk='thepage']").eq(0).trigger("click");
}


// function end
function exceljs_adjustColumnWidths(worksheet) {
    worksheet.columns.forEach((column) => {
        let maxLength = 10; // 預設最小寬度
        column.eachCell({ includeEmpty: true }, (cell) => {
            if (cell.value) {
                const text = cell.value.toString();
                maxLength = Math.max(maxLength, text.length);
            }
        });
        column.width = maxLength + 2; // 額外加 2 增加間距
    });
}
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            // reader.result 會是類似 "data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,XXXXX"
            const base64data = reader.result.split(',')[1]; // 去掉前面的 mime type header，只取純 base64 字串
            resolve(base64data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}
function saveFile(content, filename) {
    // 創建一個 Blob 物件
    const blob = new Blob([content], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });

    if (!isMobile()) {

        // 創建一個 URL 對象，指向 Blob
        const url = window.URL.createObjectURL(blob);

        // 創建一個臨時的 <a> 元素
        const a = document.createElement('a');
        a.setAttribute('rel', 'noopener noreferrer');
        a.href = url;
        a.download = filename;  // 設置下載的文件名

        // 模擬點擊以觸發下載
        document.body.appendChild(a);  // 必須先將元素加入 DOM 中
        a.click();

        // 清理工作：刪除臨時元素並釋放 URL
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
    else {
        // content 轉換為 Base64 字串, 送給App下載
        blobToBase64(blob).then(base64 => {
            window.flutter_inappwebview.callHandler('callFlutterW4', {
                'method': 'downloadFromBase64',
                'filename': filename,
                'base64': base64
            });
        });
    }
}
function checkbox_multiselect_init(dom) {
    // 讓 checkbox 按著 shift 可以複選
    // Author : 羽山
    // Version : 1.2
    // Release date: 2021-01-05 16:20
    // Release date: 2023-07-31 14:58 修正 trigger change 問題
    // Release date: 2025-01-14 13:44 只針對看得見的 dom 處理
    dom.data('last_click', -1);
    dom.data('which_down', false);
    $(window).bind("keydown", { dom: dom }, function (e) {
        e.data.dom.data('which_down', (e.which == 16));
    });
    $(window).bind("keyup", { dom: dom }, function (e) {
        if (e.which == 16) {
            e.data.dom.data('which_down', false);
        }
    });
    $(dom).bind("mousedown", { dom: dom }, function (e) {
        e.data.dom.data('target_prop', $(this).prop("checked"));
    });
    $(dom).closest("label").bind("mouseup", { dom: dom }, function (e) {
        e.data.dom.data('target_prop', $(this).find("input[type='checkbox']").prop("checked"));
    });

    $(dom).bind("change", { dom: dom }, function (e) {
        var index = e.data.dom.index(this);
        var tf = e.data.dom.data("target_prop");
        //var label_click = ($(dom).data("label_click")==true)?true:false;
        if (e.data.dom.data('last_click') != -1 && e.data.dom.data('which_down')) {
            var ss = 0;
            var ee = 0;
            //var is_reverse = false;
            if (index <= e.data.dom.data('last_click')) {
                ss = index;
                ee = e.data.dom.data('last_click');
                //is_reverse = true;       
            }
            else {
                ss = e.data.dom.data('last_click');
                ee = index;
            }
            e.data.dom.data('which_down', false);

            for (var i = ss; i <= ee; i++) {
                if (e.data.dom.eq(i).is(":visible")) { // 只操作可見的 checkbox
                    e.data.dom.eq(i).prop("checked", !tf).trigger("change");
                }
            }
        }
        e.data.dom.data('last_click', index);
    });
}
