(function (window) {
    if (window == null) return;

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
        if (typeof window.XMLHttpRequest == 'function') return new window.XMLHttpRequest();
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

    function installAjaxMethods() {
        if (window.Easymap == null || window.Easymap.prototype == null) return false;
        var proto = window.Easymap.prototype;
        if (typeof proto.myAjax_async != 'function') {
            proto.myAjax_async = function (url, post, successFunc, failFunc) {
                return sendAjaxRequest(url, post, successFunc, failFunc);
            };
        }
        if (typeof proto.myAjax_async_json != 'function') {
            proto.myAjax_async_json = function (url, post, successFunc, failFunc) {
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
            };
        }
        return true;
    }

    installAjaxMethods();
})(window);
