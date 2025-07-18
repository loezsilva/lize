(() => {
    "use strict";
    var __webpack_modules__ = {
            785: (e, t, n) => {
                function i(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var r = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, r;
                    return t = e, r = [{
                        key: "safeXmlCharactersEntities",
                        get: function() {
                            return {
                                tagOpener: "&laquo;",
                                tagCloser: "&raquo;",
                                doubleQuote: "&uml;",
                                realDoubleQuote: "&quot;"
                            }
                        }
                    }, {
                        key: "safeBadBlackboardCharacters",
                        get: function() {
                            return {
                                ltElement: "«mo»<«/mo»",
                                gtElement: "«mo»>«/mo»",
                                ampElement: "«mo»&«/mo»"
                            }
                        }
                    }, {
                        key: "safeGoodBlackboardCharacters",
                        get: function() {
                            return {
                                ltElement: "«mo»§lt;«/mo»",
                                gtElement: "«mo»§gt;«/mo»",
                                ampElement: "«mo»§amp;«/mo»"
                            }
                        }
                    }, {
                        key: "xmlCharacters",
                        get: function() {
                            return {
                                id: "xmlCharacters",
                                tagOpener: "<",
                                tagCloser: ">",
                                doubleQuote: '"',
                                ampersand: "&",
                                quote: "'"
                            }
                        }
                    }, {
                        key: "safeXmlCharacters",
                        get: function() {
                            return {
                                id: "safeXmlCharacters",
                                tagOpener: "«",
                                tagCloser: "»",
                                doubleQuote: "¨",
                                ampersand: "§",
                                quote: "`",
                                realDoubleQuote: "¨"
                            }
                        }
                    }], (n = null) && i(t.prototype, n), r && i(t, r), e
                }();

                function a(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var o = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "isMathmlInAttribute",
                        value: function(e, t) {
                            var n = "[\\s]*(".concat("\"[^\"]*\"|'[^']*'", ")[\\s]*=[\\s]*[\\w-]+[\\s]*"),
                                i = "('".concat(n, "')*"),
                                r = "^".concat("['\"][\\s]*=[\\s]*[\\w-]+").concat(i, "[\\s]+gmi<"),
                                a = new RegExp(r),
                                o = e.substring(0, t).split("").reverse().join("");
                            return a.test(o)
                        }
                    }, {
                        key: "safeXmlDecode",
                        value: function(e) {
                            var t = r.safeXmlCharactersEntities.tagOpener,
                                n = r.safeXmlCharactersEntities.tagCloser,
                                i = r.safeXmlCharactersEntities.doubleQuote,
                                a = r.safeXmlCharactersEntities.realDoubleQuote;
                            e = (e = (e = (e = e.split(t).join(r.safeXmlCharacters.tagOpener)).split(n).join(r.safeXmlCharacters.tagCloser)).split(i).join(r.safeXmlCharacters.doubleQuote)).split(a).join(r.safeXmlCharacters.realDoubleQuote);
                            var o = r.safeBadBlackboardCharacters.ltElement,
                                s = r.safeBadBlackboardCharacters.gtElement,
                                l = r.safeBadBlackboardCharacters.ampElement;
                            "_wrs_blackboard" in window && window._wrs_blackboard && (e = (e = (e = e.split(o).join(r.safeGoodBlackboardCharacters.ltElement)).split(s).join(r.safeGoodBlackboardCharacters.gtElement)).split(l).join(r.safeGoodBlackboardCharacters.ampElement)), t = r.safeXmlCharacters.tagOpener, n = r.safeXmlCharacters.tagCloser, i = r.safeXmlCharacters.doubleQuote, a = r.safeXmlCharacters.realDoubleQuote;
                            var c = r.safeXmlCharacters.ampersand,
                                d = r.safeXmlCharacters.quote;
                            e = (e = (e = (e = (e = e.split(t).join(r.xmlCharacters.tagOpener)).split(n).join(r.xmlCharacters.tagCloser)).split(i).join(r.xmlCharacters.doubleQuote)).split(c).join(r.xmlCharacters.ampersand)).split(d).join(r.xmlCharacters.quote);
                            for (var u = "", m = null, h = 0; h < e.length; h += 1) {
                                var g = e.charAt(h);
                                null == m ? "$" === g ? m = "" : u += g : ";" === g ? (u += "&".concat(m), m = null) : g.match(/([a-zA-Z0-9#._-] | '-')/) ? m += g : (u += "$".concat(m), m = null, h -= 1)
                            }
                            return u
                        }
                    }, {
                        key: "safeXmlEncode",
                        value: function(e) {
                            var t = r.xmlCharacters.tagOpener,
                                n = r.xmlCharacters.tagCloser,
                                i = r.xmlCharacters.doubleQuote,
                                a = r.xmlCharacters.ampersand,
                                o = r.xmlCharacters.quote;
                            return e = (e = (e = (e = (e = e.split(t).join(r.safeXmlCharacters.tagOpener)).split(n).join(r.safeXmlCharacters.tagCloser)).split(i).join(r.safeXmlCharacters.doubleQuote)).split(a).join(r.safeXmlCharacters.ampersand)).split(o).join(r.safeXmlCharacters.quote)
                        }
                    }, {
                        key: "mathMLEntities",
                        value: function(e) {
                            for (var t = "", n = 0; n < e.length; n += 1) {
                                var i = e.charAt(n);
                                if (e.codePointAt(n) > 128) t += "&#".concat(e.codePointAt(n), ";"), e.codePointAt(n) > 65535 && (n += 1);
                                else if ("&" === i) {
                                    var r = e.indexOf(";", n + 1);
                                    if (r >= 0) {
                                        var a = document.createElement("span");
                                        a.innerHTML = e.substring(n, r + 1), t += "&#".concat(w.fixedCharCodeAt(a.textContent || a.innerText, 0), ";"), n = r
                                    } else t += i
                                } else t += i
                            }
                            return t
                        }
                    }, {
                        key: "addCustomEditorClassAttribute",
                        value: function(e, t) {
                            var n = "",
                                i = e.indexOf("<math");
                            if (0 === i) {
                                var r = e.indexOf(">");
                                if (-1 === e.indexOf("class")) return n = "".concat(e.substr(i, r), ' class="wrs_').concat(t, '">'), n += e.substr(r + 1, e.length)
                            }
                            return e
                        }
                    }, {
                        key: "removeCustomEditorClassAttribute",
                        value: function(e, t) {
                            return -1 === e.indexOf("class") || -1 === e.indexOf("wrs_".concat(t)) ? e : -1 !== e.indexOf('class="wrs_'.concat(t, '"')) ? e.replace('class="wrs_'.concat(t, '"'), "") : e.replace("wrs_".concat(t), "")
                        }
                    }, {
                        key: "addAnnotation",
                        value: function(t, n, i) {
                            var r = "";
                            if (-1 !== t.indexOf("<annotation")) {
                                var a = t.indexOf("</semantics>");
                                r = "".concat(t.substring(0, a), '<annotation encoding="').concat(i, '">').concat(n, "</annotation>").concat(t.substring(a))
                            } else if (e.isEmpty(t)) {
                                var o = t.indexOf("/>"),
                                    s = t.indexOf(">"),
                                    l = s === o ? o : s;
                                r = "".concat(t.substring(0, l), '><semantics><annotation encoding="').concat(i, '">').concat(n, "</annotation></semantics></math>")
                            } else {
                                var c = t.indexOf(">") + 1,
                                    d = t.lastIndexOf("</math>"),
                                    u = t.substring(c, d);
                                r = "".concat(t.substring(0, c), "<semantics>").concat(u, '<annotation encoding="').concat(i, '">').concat(n, "</annotation></semantics></math>")
                            }
                            return r
                        }
                    }, {
                        key: "removeAnnotation",
                        value: function(t, n) {
                            var i = t,
                                r = '<annotation encoding="'.concat(n, '">'),
                                a = "</annotation>",
                                o = t.indexOf(r);
                            if (-1 !== o) {
                                for (var s = !1, l = t.indexOf("<annotation"); - 1 !== l;) l !== o && (s = !0), l = t.indexOf("<annotation", l + 1);
                                if (s) {
                                    var c = t.indexOf(a, o) + a.length;
                                    i = t.substring(0, o) + t.substring(c)
                                } else i = e.removeSemantics(t)
                            }
                            return i
                        }
                    }, {
                        key: "removeSemantics",
                        value: function(e) {
                            var t = "<semantics>",
                                n = e,
                                i = e.indexOf(t);
                            if (-1 !== i) {
                                var r = e.indexOf("<annotation", i + t.length); - 1 !== r && (n = e.substring(0, i) + e.substring(i + t.length, r) + "</math>")
                            }
                            return n
                        }
                    }, {
                        key: "removeSemanticsOcurrences",
                        value: function(e) {
                            for (var t = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : r.xmlCharacters, n = "".concat(t.tagOpener, "math"), i = "".concat(t.tagOpener, "/math").concat(t.tagCloser), a = "/".concat(t.tagCloser), o = t.tagCloser, s = "".concat(t.tagOpener, "semantics").concat(t.tagCloser), l = "".concat(t.tagOpener, "annotation encoding="), c = "", d = e.indexOf(n), u = 0; - 1 !== d;) {
                                c += e.substring(u, d);
                                var m = e.indexOf(i, d),
                                    h = e.indexOf(a, d),
                                    g = e.indexOf(o, d); - 1 !== m ? u = m : h === g - 1 && (u = h);
                                var p = e.indexOf(s, d);
                                if (-1 !== p) {
                                    var f = e.substring(d, p),
                                        _ = e.indexOf(l, d);
                                    if (-1 !== _) {
                                        var v = p + s.length,
                                            b = e.substring(v, _);
                                        c += f + b + i, d = e.indexOf(n, d + n.length), u += i.length
                                    } else u = d, d = e.indexOf(n, d + n.length)
                                } else u = d, d = e.indexOf(n, d + n.length)
                            }
                            return c += e.substring(u, e.length)
                        }
                    }, {
                        key: "containClass",
                        value: function(e, t) {
                            var n = e.indexOf("class");
                            if (-1 === n) return !1;
                            var i = e.indexOf(">", n);
                            return -1 !== e.substring(n, i).indexOf(t)
                        }
                    }, {
                        key: "isEmpty",
                        value: function(e) {
                            var t = e.indexOf(">"),
                                n = e.indexOf("/>"),
                                i = !1;
                            if (-1 !== n && n === t - 1 && (i = !0), !i) {
                                var r = new RegExp("</(.+:)?math>").exec(e);
                                r && (i = t + 1 === r.index)
                            }
                            return i
                        }
                    }, {
                        key: "encodeProperties",
                        value: function(e) {
                            return e.replace(/\w+=".*?"/g, (function(e) {
                                var t = e.indexOf('"'),
                                    n = e.substring(t + 1, e.length - 1),
                                    i = w.htmlEntities(n);
                                return "".concat(e.substring(0, t + 1)).concat(i, '"')
                            }))
                        }
                    }], (n = null) && a(t.prototype, n), i && a(t, i), e
                }();

                function s(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var l = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "addConfiguration",
                        value: function(t) {
                            Object.assign(e.properties, t)
                        }
                    }, {
                        key: "properties",
                        get: function() {
                            return e._properties
                        },
                        set: function(t) {
                            e._properties = t
                        }
                    }, {
                        key: "get",
                        value: function(t) {
                            return Object.prototype.hasOwnProperty.call(e.properties, t) ? e.properties[t] : !!Object.prototype.hasOwnProperty.call(e.properties, "_wrs_conf_") && e.properties["_wrs_conf_".concat(t)]
                        }
                    }, {
                        key: "set",
                        value: function(t, n) {
                            e.properties[t] = n
                        }
                    }, {
                        key: "update",
                        value: function(t, n) {
                            if (e.get(t)) {
                                var i = Object.assign(e.get(t), n);
                                e.set(t, i)
                            } else e.set(t, n)
                        }
                    }], (n = null) && s(t.prototype, n), i && s(t, i), e
                }();

                function c(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                l._properties = {};
                var d = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), this.cache = []
                    }
                    var t, n, i;
                    return t = e, (n = [{
                        key: "populate",
                        value: function(e, t) {
                            this.cache[e] = t
                        }
                    }, {
                        key: "get",
                        value: function(e) {
                            return !!Object.prototype.hasOwnProperty.call(this.cache, e) && this.cache[e]
                        }
                    }]) && c(t.prototype, n), i && c(t, i), e
                }();

                function u(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var m = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), this.listeners = []
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "newListener",
                        value: function(e, t) {
                            var n = {};
                            return n.eventName = e, n.callback = t, n
                        }
                    }], (n = [{
                        key: "add",
                        value: function(e) {
                            this.listeners.push(e)
                        }
                    }, {
                        key: "fire",
                        value: function(e, t) {
                            for (var n = 0; n < this.listeners.length && !t.cancelled; n += 1) this.listeners[n].eventName === e && this.listeners[n].callback(t);
                            return t.defaultPrevented
                        }
                    }]) && u(t.prototype, n), i && u(t, i), e
                }();

                function h(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var g = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "listeners",
                        get: function() {
                            return e._listeners
                        }
                    }, {
                        key: "addListener",
                        value: function(t) {
                            e.listeners.add(t)
                        }
                    }, {
                        key: "fireEvent",
                        value: function(t, n) {
                            e.listeners.fire(t, n)
                        }
                    }, {
                        key: "parameters",
                        get: function() {
                            return e._parameters
                        },
                        set: function(t) {
                            e._parameters = t
                        }
                    }, {
                        key: "servicePaths",
                        get: function() {
                            return e._servicePaths
                        },
                        set: function(t) {
                            e._servicePaths = t
                        }
                    }, {
                        key: "setServicePath",
                        value: function(t, n) {
                            e.servicePaths[t] = n
                        }
                    }, {
                        key: "getServicePath",
                        value: function(t) {
                            return e.servicePaths[t]
                        }
                    }, {
                        key: "integrationPath",
                        get: function() {
                            return e._integrationPath
                        },
                        set: function(t) {
                            e._integrationPath = t
                        }
                    }, {
                        key: "getServerURL",
                        value: function() {
                            var e = window.location.href.split("/");
                            return "".concat(e[0], "//").concat(e[2])
                        }
                    }, {
                        key: "init",
                        value: function(t) {
                            e.parameters = t;
                            var n = e.createServiceURI("configurationjs"),
                                i = e.createServiceURI("createimage"),
                                r = e.createServiceURI("showimage"),
                                a = e.createServiceURI("getmathml"),
                                o = e.createServiceURI("service");
                            if (0 === e.parameters.URI.indexOf("/")) {
                                var s = e.getServerURL();
                                n = s + n, r = s + r, i = s + i, a = s + a, o = s + o
                            }
                            e.setServicePath("configurationjs", n), e.setServicePath("showimage", r), e.setServicePath("createimage", i), e.setServicePath("service", o), e.setServicePath("getmathml", a), e.setServicePath("configurationjs", n), e.listeners.fire("onInit", {})
                        }
                    }, {
                        key: "getUrl",
                        value: function(e, t) {
                            var editorUrl = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/fiscallizeremote/static/js/math_editor.min.js"
                            if (e.endsWith('demo/plugins/app/configurationjs') && !t){
                                return JSON.stringify({"versionPlatform":"unknown","editorParameters":{},"imageFormat":"svg","CASEnabled":false,"parseModes":["latex"],"editorToolbar":"","editorAttributes":"width=570, height=450, scroll=no, resizable=yes","base64savemode":"default","modalWindow":true,"version":"7.31.0.1453","enableAccessibility":true,"saveMode":"xml","saveHandTraces":false,"editorUrl":editorUrl,"editorEnabled":true,"chemEnabled":true,"CASMathmlAttribute":"alt","CASAttributes":"width=640, height=480, scroll=no, resizable=yes","modalWindowFullScreen":false,"imageMathmlAttribute":"data-mathml","hostPlatform":"unknown","wirisPluginPerformance":true})
                            }

                            var n = window.location.toString().substr(0, window.location.toString().lastIndexOf("/") + 1),
                                i = w.createHttpRequest();
                            var result = i ? (void 0 === t || void 0 === t ? i.open("GET", e, !1) : "/" === e.substr(0, 1) || "http://" === e.substr(0, 7) || "https://" === e.substr(0, 8) ? i.open("POST", e, !1) : i.open("POST", n + e, !1), void 0 !== t && t ? (i.setRequestHeader("Content-type", "application/x-www-form-urlencoded; charset=UTF-8"), i.send(w.httpBuildQuery(t))) : i.send(null), i.responseText) : ""

                            return result
                        }
                    }, {
                        key: "getService",
                        value: function(t, n, i) {
                            var r;
                            if (!0 === i) {
                                var a = n ? "?".concat(n) : "",
                                    o = "".concat(e.getServicePath(t)).concat(a);
                                r = e.getUrl(o)
                            } else {
                                var s = e.getServicePath(t);
                                r = e.getUrl(s, n)
                            }
                            return r
                        }
                    }, {
                        key: "getServerLanguageFromService",
                        value: function(e) {
                            return -1 !== e.indexOf(".php") ? "php" : -1 !== e.indexOf(".aspx") ? "aspx" : -1 !== e.indexOf("wirispluginengine") ? "ruby" : "java"
                        }
                    }, {
                        key: "createServiceURI",
                        value: function(t) {
                            var n = e.serverExtension();
                            return w.concatenateUrl(e.parameters.URI, t) + n
                        }
                    }, {
                        key: "serverExtension",
                        value: function() {
                            return -1 !== e.parameters.server.indexOf("php") ? ".php" : -1 !== e.parameters.server.indexOf("aspx") ? ".aspx" : ""
                        }
                    }], (n = null) && h(t.prototype, n), i && h(t, i), e
                }();

                function p(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                g._servicePaths = {}, g._integrationPath = "", g._listeners = new m, g._parameters = {};
                var f = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "cache",
                        get: function() {
                            return e._cache
                        },
                        set: function(t) {
                            e._cache = t
                        }
                    }, {
                        key: "getLatexFromMathML",
                        value: function(t) {
                            var n = o.removeSemantics(t),
                                i = e.cache,
                                r = {
                                    service: "mathml2latex",
                                    mml: n
                                },
                                a = JSON.parse(g.getService("service", r)),
                                s = "";
                            if ("ok" === a.status) {
                                s = a.result.text;
                                var l = w.htmlEntities(s),
                                    c = o.addAnnotation(t, l, "LaTeX");
                                i.populate(s, c)
                            }
                            return s
                        }
                    }, {
                        key: "getMathMLFromLatex",
                        value: function(t, n) {
                            var i = e.cache;
                            if (e.cache.get(t)) return e.cache.get(t);
                            var r = {
                                service: "latex2mathml",
                                latex: t
                            };
                            n && (r.saveLatex = "");
                            var a, s = JSON.parse(g.getService("service", r));
                            if ("ok" === s.status) {
                                var l = s.result.text;
                                if (-1 === (l = l.split("\r").join("").split("\n").join(" ")).indexOf("semantics") && -1 === l.indexOf("annotation")) {
                                    var c = w.htmlEntities(t);
                                    a = l = o.addAnnotation(l, c, "LaTeX")
                                } else a = l;
                                i.get(t) || i.populate(t, l)
                            } else a = "$$".concat(t, "$$");
                            return a
                        }
                    }, {
                        key: "parseMathmlToLatex",
                        value: function(t, n) {
                            for (var i, a, s, l = "", c = "".concat(n.tagOpener, "math"), d = "".concat(n.tagOpener, "/math").concat(n.tagCloser), u = "".concat(n.tagOpener, "annotation encoding=").concat(n.doubleQuote, "LaTeX").concat(n.doubleQuote).concat(n.tagCloser), m = "".concat(n.tagOpener, "/annotation").concat(n.tagCloser), h = t.indexOf(c), g = 0; - 1 !== h;) {
                                if (l += t.substring(g, h), -1 === (g = t.indexOf(d, h)) ? g = t.length - 1 : g += d.length, -1 !== (a = (i = t.substring(h, g)).indexOf(u))) {
                                    a += u.length, s = i.indexOf(m);
                                    var p = i.substring(a, s);
                                    n === r.safeXmlCharacters && (p = o.safeXmlDecode(p)), l += "$$".concat(p, "$$"), e.cache.populate(p, i)
                                } else l += i;
                                h = t.indexOf(c, g)
                            }
                            return l += t.substring(g, t.length)
                        }
                    }, {
                        key: "getLatexFromTextNode",
                        value: function(e, t, n) {
                            void 0 !== n && null != n || (n = {
                                open: "$$",
                                close: "$$"
                            });
                            for (var i, r = e; r.previousSibling && 3 === r.previousSibling.nodeType;) r = r.previousSibling;

                            function a(e, t, i) {
                                for (var r = e.nodeValue.indexOf(i, t); - 1 === r;) {
                                    if (!(e = e.nextSibling)) return null;
                                    r = e.nodeValue ? e.nodeValue.indexOf(n.close) : -1
                                }
                                return {
                                    node: e,
                                    position: r
                                }
                            }

                            function o(e, t, n, i) {
                                if (e === n) return t <= i;
                                for (; e && e !== n;) e = e.nextSibling;
                                return e === n
                            }
                            var s, l = {
                                    node: r,
                                    position: 0
                                },
                                c = n.open.length;
                            do {
                                if (null == (i = a(l.node, l.position, n.open)) || o(e, t, i.node, i.position)) return null;
                                if (null == (l = a(i.node, i.position + c, n.close))) return null;
                                l.position += c
                            } while (o(l.node, l.position, e, t));
                            if (i.node === l.node) s = i.node.nodeValue.substring(i.position + c, l.position - c);
                            else {
                                var d = i.position + c;
                                s = i.node.nodeValue.substring(d, i.node.nodeValue.length);
                                var u = i.node;
                                do {
                                    (u = u.nextSibling) === l.node ? s += l.node.nodeValue.substring(0, l.position - c) : s += u.nodeValue ? u.nodeValue : ""
                                } while (u !== l.node)
                            }
                            return {
                                latex: s,
                                startNode: i.node,
                                startPosition: i.position,
                                endNode: l.node,
                                endPosition: l.position
                            }
                        }
                    }], (n = null) && p(t.prototype, n), i && p(t, i), e
                }();
                f._cache = new d;
                const _ = JSON.parse('{"ar":{"latex":"LaTeX","cancel":"إلغاء","accept":"إدراج","manual":"الدليل","insert_math":"إدراج صيغة رياضية - MathType","insert_chem":"إدراج صيغة كيميائية - ChemType","minimize":"تصغير","maximize":"تكبير","fullscreen":"ملء الشاشة","exit_fullscreen":"الخروج من ملء الشاشة","close":"إغلاق","mathtype":"MathType","title_modalwindow":"نافذة MathType مشروطة","close_modal_warning":"هل تريد المغادرة بالتأكيد؟ ستُفقد التغييرات التي أجريتها.","latex_name_label":"صيغة Latex","browser_no_compatible":"المستعرض غير متوافق مع تقنية AJAX. الرجاء استخدام أحدث إصدار من Mozilla Firefox.","error_convert_accessibility":"حدث خطأ أثناء التحويل من MathML إلى نص قابل للاستخدام.","exception_cross_site":"البرمجة النصية للمواقع المشتركة مسموح بها لـ HTTP فقط.","exception_high_surrogate":"المركّب المرتفع غير متبوع بمركّب منخفض في fixedCharCodeAt()‎","exception_string_length":"سلسلة غير صالحة. يجب أن يكون الطول من مضاعفات العدد 4","exception_key_nonobject":"Object.keys مستدعاة على غير كائن","exception_null_or_undefined":" هذا فارغ أو غير محدد","exception_not_function":" ليست دالة","exception_invalid_date_format":"تنسيق تاريخ غير صالح: ","exception_casting":"لا يمكن الصياغة ","exception_casting_to":" إلى "},"ca":{"latex":"LaTeX","cancel":"Cancel·lar","accept":"Inserir","manual":"Manual","insert_math":"Inserir fórmula matemàtica - MathType","insert_chem":"Inserir fórmula química - ChemType","minimize":"Minimitza","maximize":"Maximitza","fullscreen":"Pantalla completa","exit_fullscreen":"Sortir de la pantalla complera","close":"Tanca","mathtype":"MathType","title_modalwindow":" Finestra modal de MathType","close_modal_warning":"N\'estàs segur que vols sortir? Es perdran els canvis que has fet.","latex_name_label":"Fórmula en Latex","browser_no_compatible":"El teu navegador no és compatible amb AJAX. Si us plau, usa la darrera versió de Mozilla Firefox.","error_convert_accessibility":"Error en convertir de MathML a text accessible.","exception_cross_site":"Els scripts de llocs creuats només estan permesos per HTTP.","exception_high_surrogate":"Subrogat alt no seguit de subrogat baix a fixedCharCodeAt()","exception_string_length":"Cadena invàlida. La longitud ha de ser un múltiple de 4","exception_key_nonobject":"Object.keys anomenat a non-object","exception_null_or_undefined":" això és null o no definit","exception_not_function":" no és una funció","exception_invalid_date_format":"Format de data invàlid : ","exception_casting":"No es pot emetre ","exception_casting_to":" a "},"cs":{"latex":"LaTeX","cancel":"Storno","accept":"Vložit","manual":"Příručka","insert_math":"Vložit matematický vzorec - MathType","insert_chem":"Vložení chemického vzorce – ChemType","minimize":"Minimalizovat","maximize":"Maximalizovat","fullscreen":"Celá obrazovka","exit_fullscreen":"Opustit režim celé obrazovky","close":"Zavřít","mathtype":"MathType","title_modalwindow":"Modální okno MathType","close_modal_warning":"Opravdu chcete okno zavřít? Provedené změny budou ztraceny.","latex_name_label":"Vzorec v LaTeXu","browser_no_compatible":"Váš prohlížeč nepodporuje technologii AJAX. Použijte nejnovější verzi prohlížeče Mozilla Firefox.","error_convert_accessibility":"Při převodu kódu MathML na čitelný text došlo k chybě.","exception_cross_site":"Skriptování mezi více servery je povoleno jen v HTTP.","exception_high_surrogate":"Ve funkci fixedCharCodeAt() nenásleduje po první části kódu znaku druhá část","exception_string_length":"Neplatný řetězec. Délka musí být násobkem 4.","exception_key_nonobject":"Funkce Object.keys byla použita pro prvek, který není objektem","exception_null_or_undefined":" hodnota je null nebo není definovaná","exception_not_function":" není funkce","exception_invalid_date_format":"Neplatný formát data: ","exception_casting":"Nelze přetypovat ","exception_casting_to":" na "},"da":{"latex":"LaTeX","cancel":"Annuller","accept":"Indsæt","manual":"Brugervejledning","insert_math":"Indsæt matematisk formel - MathType","insert_chem":"Indsæt en kemisk formel - ChemType","minimize":"Minimer","maximize":"Maksimer","fullscreen":"Fuld skærm","exit_fullscreen":"Afslut Fuld skærm","close":"Luk","mathtype":"MathType","title_modalwindow":"MathType-modalvindue","close_modal_warning":"Er du sikker på, du vil lukke? Dine ændringer går tabt.","latex_name_label":"LaTex-formel","browser_no_compatible":"Din browser er ikke kompatibel med AJAX-teknologi. Brug den nyeste version af Mozilla Firefox.","error_convert_accessibility":"Fejl under konvertering fra MathML til tilgængelig tekst.","exception_cross_site":"Scripts på tværs af websteder er kun tilladt for HTTP.","exception_high_surrogate":"Et højt erstatningstegn er ikke fulgt af et lavt erstatningstegn i fixedCharCodeAt()","exception_string_length":"Ugyldig streng. Længden skal være et multiplum af 4","exception_key_nonobject":"Object.keys kaldet ved ikke-objekt","exception_null_or_undefined":" dette er nul eller ikke defineret","exception_not_function":" er ikke en funktion","exception_invalid_date_format":"Ugyldigt datoformat: ","exception_casting":"Kan ikke beregne ","exception_casting_to":" til "},"de":{"latex":"LaTeX","cancel":"Abbrechen","accept":"Einfügen","manual":"Handbuch","insert_math":"Mathematische Formel einfügen - MathType","insert_chem":"Eine chemische Formel einfügen – ChemType","minimize":"Verkleinern","maximize":"Vergrößern","fullscreen":"Vollbild","exit_fullscreen":"Vollbild schließen","close":"Schließen","mathtype":"MathType","title_modalwindow":"Modales MathType-Fenster","close_modal_warning":"Bist du sicher, dass du das Programm verlassen willst? Alle vorgenommenen Änderungen gehen damit verloren.","latex_name_label":"Latex-Formel","browser_no_compatible":"Dein Browser ist nicht mit der AJAX-Technologie kompatibel. Verwende bitte die neueste Version von Mozilla Firefox.","error_convert_accessibility":"Fehler beim Konvertieren von MathML in barrierefreien Text.","exception_cross_site":"Cross-Site-Scripting ist nur bei HTTP zulässig.","exception_high_surrogate":"Hoher Ersatz bei bei festerZeichenkodierungbei() nicht von niedrigem Ersatz befolgt.","exception_string_length":"Ungültige Zeichenfolge. Länge muss ein Vielfaches von 4 sein.","exception_key_nonobject":"Object.keys wurde für ein Nicht-Objekt aufgerufen.","exception_null_or_undefined":" Das ist Null oder nicht definiert.","exception_not_function":" ist keine Funktion","exception_invalid_date_format":"Ungültiges Datumsformat: ","exception_casting":"Umwandlung nicht möglich ","exception_casting_to":" zu "},"el":{"latex":"LaTeX","cancel":"Άκυρο","accept":"Εισαγωγή","manual":"Χειροκίνητα","insert_math":"Εισαγωγή μαθηματικού τύπου - MathType","insert_chem":"Εισαγωγή χημικού τύπου - ChemType","minimize":"Ελαχιστοποίηση","maximize":"Μεγιστοποίηση","fullscreen":"Πλήρης οθόνη","exit_fullscreen":"Έξοδος από πλήρη οθόνη","close":"Κλείσιμο","mathtype":"MathType","title_modalwindow":"Τροπικό παράθυρο MathType","close_modal_warning":"Επιθυμείτε σίγουρα αποχώρηση; Θα χαθούν οι αλλαγές που έχετε κάνει.","latex_name_label":"Τύπος LaTeX","browser_no_compatible":"Το πρόγραμμα περιήγησής σας δεν είναι συμβατό με την τεχνολογία AJAX. Χρησιμοποιήστε την πιο πρόσφατη έκδοση του Mozilla Firefox.","error_convert_accessibility":"Σφάλμα κατά τη μετατροπή από MathML σε προσβάσιμο κείμενο.","exception_cross_site":"Το XSS (Cross site scripting) επιτρέπεται μόνο για HTTP.","exception_high_surrogate":"Το υψηλό υποκατάστατο δεν ακολουθείται από χαμηλό υποκατάστατο στο fixedCharCodeAt()","exception_string_length":"Μη έγκυρη συμβολοσειρά. Το μήκος πρέπει να είναι πολλαπλάσιο του 4","exception_key_nonobject":"Έγινε κλήση του Object.keys σε μη αντικείμενο","exception_null_or_undefined":" αυτό είναι μηδενικό ή δεν έχει οριστεί","exception_not_function":" δεν είναι συνάρτηση","exception_invalid_date_format":"Μη έγκυρη μορφή ημερομηνίας: ","exception_casting":"Δεν είναι δυνατή η μετατροπή ","exception_casting_to":" σε "},"en":{"latex":"LaTeX","cancel":"Cancel","accept":"Insert","manual":"Manual","insert_math":"Insert a math equation - MathType","insert_chem":"Insert a chemistry formula - ChemType","minimize":"Minimize","maximize":"Maximize","fullscreen":"Full-screen","exit_fullscreen":"Exit full-screen","close":"Close","mathtype":"MathType","title_modalwindow":"MathType modal window","close_modal_warning":"Are you sure you want to leave? The changes you made will be lost.","latex_name_label":"Latex Formula","browser_no_compatible":"Your browser is not compatible with AJAX technology. Please, use the latest version of Mozilla Firefox.","error_convert_accessibility":"Error converting from MathML to accessible text.","exception_cross_site":"Cross site scripting is only allowed for HTTP.","exception_high_surrogate":"High surrogate not followed by low surrogate in fixedCharCodeAt()","exception_string_length":"Invalid string. Length must be a multiple of 4","exception_key_nonobject":"Object.keys called on non-object","exception_null_or_undefined":" this is null or not defined","exception_not_function":" is not a function","exception_invalid_date_format":"Invalid date format : ","exception_casting":"Cannot cast ","exception_casting_to":" to "},"es":{"latex":"LaTeX","cancel":"Cancelar","accept":"Insertar","manual":"Manual","insert_math":"Insertar fórmula matemática - MathType","insert_chem":"Insertar fórmula química - ChemType","minimize":"Minimizar","maximize":"Maximizar","fullscreen":"Pantalla completa","exit_fullscreen":"Salir de pantalla completa","close":"Cerrar","mathtype":"MathType","title_modalwindow":"Ventana modal de MathType","close_modal_warning":"Seguro que quieres cerrar? Los cambios que has hecho se perderán","latex_name_label":"Formula en Latex","browser_no_compatible":"Tu navegador no es complatible con AJAX. Por favor, usa la última version de Mozilla Firefox.","error_convert_accessibility":"Error conviertiendo una fórmula MathML a texto accesible.","exception_cross_site":"Cross site scripting solo está permitido para HTTP.","exception_high_surrogate":"Subrogado alto no seguido por subrogado bajo en fixedCharCodeAt()","exception_string_length":"Cadena no válida. La longitud debe ser múltiplo de 4","exception_key_nonobject":"Object.keys called on non-object","exception_null_or_undefined":" esto es null o no definido","exception_not_function":" no es una función","exception_invalid_date_format":"Formato de fecha inválido: ","exception_casting":"No se puede emitir","exception_casting_to":" a "},"et":{"latex":"LaTeX","cancel":"Loobu","accept":"Lisa","manual":"Käsiraamat","insert_math":"Lisa matemaatiline valem – WIRIS","insert_chem":"Lisa keemiline valem – ChemType","minimize":"Minimeeri","maximize":"Maksimeeri","fullscreen":"Täiskuva","exit_fullscreen":"Välju täiskuvalt","close":"Sule","mathtype":"MathType","title_modalwindow":"MathType\'i modaalaken","close_modal_warning":"Kas soovite kindlasti lahkuda? Tehtud muudatused lähevad kaduma.","latex_name_label":"Latexi valem","browser_no_compatible":"Teie brauser ei ühildu AJAXi tehnoloogiaga. Palun kasutage Mozilla Firefoxi uusimat versiooni.","error_convert_accessibility":"Tõrge teisendamisel MathML-ist muudetavaks tekstiks.","exception_cross_site":"Ristskriptimine on lubatud ainult HTTP kasutamisel.","exception_high_surrogate":"Funktsioonis fixedCharCodeAt() ei järgne kõrgemale asendusliikmele madalam asendusliige.","exception_string_length":"Vigane string. Pikkus peab olema 4 kordne.","exception_key_nonobject":"Protseduur Object.keys kutsuti mitteobjekti korral.","exception_null_or_undefined":" see on null või määramata","exception_not_function":" ei ole funktsioon","exception_invalid_date_format":"Sobimatu kuupäeva kuju: ","exception_casting":"Esitamine ei õnnestu ","exception_casting_to":" – "},"eu":{"latex":"LaTeX","cancel":"Ezeztatu","accept":"Txertatu","manual":"Gida","insert_math":"Txertatu matematikako formula - MathType","insert_chem":"Txertatu formula kimiko bat - ChemType","minimize":"Ikonotu","maximize":"Maximizatu","fullscreen":"Pantaila osoa","exit_fullscreen":"Irten pantaila osotik","close":"Itxi","mathtype":"MathType","title_modalwindow":"MathType leiho modala","close_modal_warning":"Ziur irten nahi duzula? Egiten dituzun aldaketak galdu egingo dira.","latex_name_label":"LaTex Formula","browser_no_compatible":"Zure arakatzailea ez da bateragarria AJAX teknologiarekin. Erabili Mozilla Firefoxen azken bertsioa.","error_convert_accessibility":"Errorea MathMLtik testu irisgarrira bihurtzean.","exception_cross_site":"Gune arteko scriptak HTTPrako soilik onartzen dira.","exception_high_surrogate":"Ordezko baxuak ez dio ordezko altuari jarraitzen, hemen: fixedCharCodeAt()","exception_string_length":"Kate baliogabea. Luzerak 4ren multiploa izan behar du","exception_key_nonobject":"Object.keys deitu zaio objektua ez den zerbaiti","exception_null_or_undefined":" nulua edo definitu gabea da","exception_not_function":" ez da funtzio bat","exception_invalid_date_format":"Data-formatu baliogabea : ","exception_casting":"Ezin da igorri ","exception_casting_to":" honi "},"fi":{"latex":"LaTeX","cancel":"Peruuta","accept":"Lisää","manual":"Manual","insert_math":"Liitä matemaattinen kaava - MathType","insert_chem":"Lisää kemian kaava - ChemType","minimize":"Pienennä","maximize":"Suurenna","fullscreen":"Koko ruutu","exit_fullscreen":"Poistu koko ruudun tilasta","close":"Sulje","mathtype":"MathType","title_modalwindow":"MathTypen modaalinen ikkuna","close_modal_warning":"Oletko varma, että haluat poistua? Menetät tekemäsi muutokset.","latex_name_label":"Latex-kaava","browser_no_compatible":"Selaimesi ei tue AJAX-tekniikkaa. Ole hyvä ja käytä uusinta Firefox-versiota.","error_convert_accessibility":"Virhe muunnettaessa MathML:stä tekstiksi.","exception_cross_site":"Cross site scripting sallitaan vain HTTP:llä.","exception_high_surrogate":"fixedCharCodeAt(): yläsijaismerkkiä ei seurannut alasijaismerkki","exception_string_length":"Epäkelpo merkkijono. Pituuden on oltava 4:n kerrannainen","exception_key_nonobject":"Object.keys kutsui muuta kuin oliota","exception_null_or_undefined":" tämä on null tai ei määritelty","exception_not_function":" ei ole funktio","exception_invalid_date_format":"Virheellinen päivämäärämuoto : ","exception_casting":"Ei voida muuntaa tyyppiä ","exception_casting_to":" tyyppiin "},"fr":{"latex":"LaTeX","cancel":"Annuler","accept":"Insérer","manual":"Manuel","insert_math":"Insérer une formule mathématique - MathType","insert_chem":"Insérer une formule chimique - ChemType","minimize":"Minimiser","maximize":"Maximiser","fullscreen":"Plein écran","exit_fullscreen":"Quitter le plein écran","close":"Fermer","mathtype":"MathType","title_modalwindow":"Fenêtre modale MathType","close_modal_warning":"Confirmez-vous vouloir fermer ? Les changements effectués seront perdus.","latex_name_label":"Formule LaTeX","browser_no_compatible":"Votre navigateur n’est pas compatible avec la technologie AJAX. Veuillez utiliser la dernière version de Mozilla Firefox.","error_convert_accessibility":"Une erreur de conversion du format MathML en texte accessible est survenue.","exception_cross_site":"Le cross-site scripting n’est autorisé que pour HTTP.","exception_high_surrogate":"Substitut élevé non suivi d’un substitut inférieur dans fixedCharCodeAt()","exception_string_length":"Chaîne non valide. Longueur limitée aux multiples de 4","exception_key_nonobject":"Object.keys appelé sur un non-objet","exception_null_or_undefined":" nul ou non défini","exception_not_function":" n’est pas une fonction","exception_invalid_date_format":"Format de date non valide : ","exception_casting":"Impossible de convertir ","exception_casting_to":" sur "},"gl":{"latex":"LaTeX","cancel":"Cancelar","accept":"Inserir","manual":"Manual","insert_math":"Inserir unha fórmula matemática - MathType","insert_chem":"Inserir unha fórmula química - ChemType","minimize":"Minimizar","maximize":"Maximizar","fullscreen":"Pantalla completa","exit_fullscreen":"Saír da pantalla completa","close":"Pechar","mathtype":"MathType","title_modalwindow":"Ventá modal de MathType","close_modal_warning":"Seguro que quere saír? Perderanse os cambios realizados.","latex_name_label":"Fórmula Latex","browser_no_compatible":"O seu explorador non é compatible coa tecnoloxía AJAX. Use a versión máis recente de Mozilla Firefox.","error_convert_accessibility":"Erro ao converter de MathML a texto accesible.","exception_cross_site":"Os scripts de sitios só se permiten para HTTP.","exception_high_surrogate":"Suplente superior non seguido por suplente inferior en fixedCharCodeAt()","exception_string_length":"Cadea non válida. A lonxitude debe ser un múltiplo de 4","exception_key_nonobject":"Claves de obxecto chamadas en non obxecto","exception_null_or_undefined":" nulo ou non definido","exception_not_function":" non é unha función","exception_invalid_date_format":"Formato de data non válido: ","exception_casting":"Non se pode converter ","exception_casting_to":" a "},"he":{"latex":"LaTeX","cancel":"ביטול","accept":"עדכון","manual":"ידני","insert_math":"הוספת נוסחה מתמטית - MathType","insert_chem":"הוספת כתיבה כימית - ChemType","minimize":"מזערי","maximize":"מרבי","fullscreen":"מסך מלא","exit_fullscreen":"יציאה ממצב מסך מלא","close":"סגירה","mathtype":"MathType","title_modalwindow":"חלון מודאלי של MathType","close_modal_warning":"האם לצאת? שינויים אשר בוצעו ימחקו.","latex_name_label":"נוסחת Latex","browser_no_compatible":"הדפדפן שלך אינו תואם לטכנולוגיית AJAX. יש להשתמש בגרסה העדכנית ביותר של Mozilla Firefox.","error_convert_accessibility":"שגיאה בהמרה מ-MathML לטקסט נגיש.","exception_cross_site":"סקריפטינג חוצה-אתרים מורשה עבור HTTP בלבד.","exception_high_surrogate":"ערך ממלא מקום גבוה אינו מופיע אחרי ערך ממלא מקום נמוך ב-fixedCharCodeAt()‎","exception_string_length":"מחרוזת לא חוקית. האורך חייב להיות כפולה של 4","exception_key_nonobject":"בוצעה קריאה אל Object.keys ברכיב שאינו אובייקט","exception_null_or_undefined":" הוא Null או לא מוגדר","exception_not_function":"איננה פונקציה","exception_invalid_date_format":"תסדיר תאריך אינו תקין : ","exception_casting":"לא ניתן להמיר ","exception_casting_to":" ל "},"hr":{"latex":"LaTeX","cancel":"Poništi","accept":"Umetni","manual":"Priručnik","insert_math":"Umetnite matematičku formulu - MathType","insert_chem":"Umetnite kemijsku formulu - ChemType","minimize":"Minimiziraj","maximize":"Maksimiziraj","fullscreen":"Cijeli zaslon","exit_fullscreen":"Izlaz iz prikaza na cijelom zaslonu","close":"Zatvori","mathtype":"MathType","title_modalwindow":"MathType modalni prozor","close_modal_warning":"Sigurno želite zatvoriti? Izgubit će se unesene promjene.","latex_name_label":"Latex formula","browser_no_compatible":"Vaš preglednik nije kompatibilan s AJAX tehnologijom. Upotrijebite najnoviju verziju Mozilla Firefoxa.","error_convert_accessibility":"Pogreška konverzije iz MathML-a u dostupni tekst.","exception_cross_site":"Skriptiranje na različitim web-mjestima dopušteno je samo za HTTP.","exception_high_surrogate":"Iza visoke zamjene ne slijedi niska zamjena u fixedCharCodeAt()","exception_string_length":"Nevažeći niz. Duljina mora biti višekratnik broja 4","exception_key_nonobject":"Object.keys pozvano na ne-objekt","exception_null_or_undefined":" ovo je nula ili nije definirano","exception_not_function":" nije funkcija","exception_invalid_date_format":"Nevažeći format datuma : ","exception_casting":"Ne može se poslati ","exception_casting_to":" na "},"hu":{"latex":"LaTeX","cancel":"Mégsem","accept":"Beszúrás","manual":"Kézikönyv","insert_math":"Matematikai képlet beszúrása - MathType","insert_chem":"Kémiai képet beillesztése - ChemType","minimize":"Kis méret","maximize":"Nagy méret","fullscreen":"Teljes képernyő","exit_fullscreen":"Teljes képernyő elhagyása","close":"Bezárás","mathtype":"MathType","title_modalwindow":"MathType modális ablak","close_modal_warning":"Biztosan kilép? A módosítások el fognak veszni.","latex_name_label":"Latex képlet","browser_no_compatible":"A böngészője nem kompatibilis az AJAX technológiával. Használja a Mozilla Firefox legújabb verzióját.","error_convert_accessibility":"Hiba lépett fel a MathML szöveggé történő konvertálása során.","exception_cross_site":"Az oldalak közti scriptelés csak HTTP esetén engedélyezett.","exception_high_surrogate":"A magas helyettesítő karaktert nem alacsony helyettesítő karakter követi a fixedCharCodeAt() esetében","exception_string_length":"Érvénytelen karakterlánc. A hossznak a 4 többszörösének kell lennie","exception_key_nonobject":"Az Object.keys egy nem objektumra került meghívásra","exception_null_or_undefined":" null vagy nem definiált","exception_not_function":" nem függvény","exception_invalid_date_format":"Érvénytelen dátumformátum: ","exception_casting":"Nem alkalmazható ","exception_casting_to":" erre "},"id":{"latex":"LaTeX","cancel":"Membatalkan","accept":"Masukkan","manual":"Manual","insert_math":"Masukkan rumus matematika - MathType","insert_chem":"Masukkan rumus kimia - ChemType","minimize":"Minikan","maximize":"Perbesar","fullscreen":"Layar penuh","exit_fullscreen":"Keluar layar penuh","close":"Tutup","mathtype":"MathType","title_modalwindow":"Jendela modal MathType","close_modal_warning":"Anda yakin ingin keluar? Anda akan kehilangan perubahan yang Anda buat.","latex_name_label":"Rumus Latex","browser_no_compatible":"Penjelajah Anda tidak kompatibel dengan teknologi AJAX. Harap gunakan Mozilla Firefox versi terbaru.","error_convert_accessibility":"Kesalahan konversi dari MathML menjadi teks yang dapat diakses.","exception_cross_site":"Skrip lintas situs hanya diizinkan untuk HTTP.","exception_high_surrogate":"Pengganti tinggi tidak diikuti oleh pengganti rendah di fixedCharCodeAt()","exception_string_length":"String tidak valid. Panjang harus kelipatan 4","exception_key_nonobject":"Object.keys meminta nonobjek","exception_null_or_undefined":" ini tidak berlaku atau tidak didefinisikan","exception_not_function":" bukan sebuah fungsi","exception_invalid_date_format":"Format tanggal tidak valid : ","exception_casting":"Tidak dapat mentransmisikan ","exception_casting_to":" untuk "},"it":{"latex":"LaTeX","cancel":"Annulla","accept":"Inserisci","manual":"Manuale","insert_math":"Inserisci una formula matematica - MathType","insert_chem":"Inserisci una formula chimica - ChemType","minimize":"Riduci a icona","maximize":"Ingrandisci","fullscreen":"Schermo intero","exit_fullscreen":"Esci da schermo intero","close":"Chiudi","mathtype":"MathType","title_modalwindow":"Finestra modale di MathType","close_modal_warning":"Confermi di voler uscire? Le modifiche effettuate andranno perse.","latex_name_label":"Formula LaTeX","browser_no_compatible":"Il tuo browser non è compatibile con la tecnologia AJAX. Utilizza la versione più recente di Mozilla Firefox.","error_convert_accessibility":"Errore durante la conversione da MathML in testo accessibile.","exception_cross_site":"Lo scripting tra siti è consentito solo per HTTP.","exception_high_surrogate":"Surrogato alto non seguito da surrogato basso in fixedCharCodeAt()","exception_string_length":"Stringa non valida. La lunghezza deve essere un multiplo di 4","exception_key_nonobject":"Metodo Object.keys richiamato in un elemento non oggetto","exception_null_or_undefined":" questo è un valore null o non definito","exception_not_function":" non è una funzione","exception_invalid_date_format":"Formato di data non valido: ","exception_casting":"Impossibile eseguire il cast ","exception_casting_to":" a "},"ja":{"latex":"LaTeX","cancel":"キャンセル","accept":"挿入","manual":"マニュアル","insert_math":"数式を挿入 - MathType","insert_chem":"化学式を挿入 - ChemType","minimize":"最小化","maximize":"最大化","fullscreen":"全画面表示","exit_fullscreen":"全画面表示を解除","close":"閉じる","mathtype":"MathType","title_modalwindow":"MathType モードウィンドウ","close_modal_warning":"このページから移動してもよろしいですか？変更内容は失われます。","latex_name_label":"LaTeX 数式","browser_no_compatible":"お使いのブラウザは、AJAX 技術と互換性がありません。Mozilla Firefox の最新バージョンをご使用ください。","error_convert_accessibility":"MathML からアクセシブルなテキストへの変換中にエラーが発生しました。","exception_cross_site":"クロスサイトスクリプティングは、HTTP のみに許可されています。","exception_high_surrogate":"fixedCharCodeAt（）で上位サロゲートの後に下位サロゲートがありません","exception_string_length":"無効な文字列です。長さは4の倍数である必要があります","exception_key_nonobject":"Object.keys が非オブジェクトで呼び出されました","exception_null_or_undefined":" null であるか、定義されていません","exception_not_function":" は関数ではありません","exception_invalid_date_format":"無効な日付形式: ","exception_casting":"次にキャスト ","exception_casting_to":" できません "},"ko":{"latex":"LaTeX","cancel":"취소","accept":"삽입","manual":"설명서","insert_math":"수학 공식 삽입 - MathType","insert_chem":"화학 공식 입력하기 - ChemType","minimize":"최소화","maximize":"최대화","fullscreen":"전체 화면","exit_fullscreen":"전체 화면 나가기","close":"닫기","mathtype":"MathType","title_modalwindow":"MathType 모달 창","close_modal_warning":"정말로 나가시겠습니까? 변경 사항이 손실됩니다.","latex_name_label":"Latex 공식","browser_no_compatible":"사용자의 브라우저는 AJAX 기술과 호환되지 않습니다. Mozilla Firefox 최신 버전을 사용하십시오.","error_convert_accessibility":"MathML로부터 접근 가능한 텍스트로 오류 변환.","exception_cross_site":"사이트 교차 스크립팅은 HTTP 환경에서만 사용할 수 있습니다.","exception_high_surrogate":"fixedCharCodeAt()에서는 상위 서러게이트 뒤에 하위 서러게이트가 붙지 않습니다","exception_string_length":"유효하지 않은 스트링입니다. 길이는 4의 배수여야 합니다","exception_key_nonobject":"Object.keys가 non-object를 요청하였습니다","exception_null_or_undefined":" Null값이거나 정의되지 않았습니다","exception_not_function":" 함수가 아닙니다","exception_invalid_date_format":"유효하지 않은 날짜 포맷 : ","exception_casting":"캐스팅할 수 없습니다 ","exception_casting_to":" (으)로 "},"nl":{"latex":"LaTeX","cancel":"Annuleren","insert_chem":"Een scheikundige formule invoegen - ChemType","minimize":"Minimaliseer","maximize":"Maximaliseer","fullscreen":"Schermvullend","exit_fullscreen":"Verlaat volledig scherm","close":"Sluit","mathtype":"MathType","title_modalwindow":"Modaal venster MathType","close_modal_warning":"Weet je zeker dat je de app wilt sluiten? De gemaakte wijzigingen gaan verloren.","latex_name_label":"LaTeX-formule","browser_no_compatible":"Je browser is niet compatibel met AJAX-technologie. Gebruik de meest recente versie van Mozilla Firefox.","error_convert_accessibility":"Fout bij conversie van MathML naar toegankelijke tekst.","exception_cross_site":"Cross-site scripting is alleen toegestaan voor HTTP.","exception_high_surrogate":"Hoog surrogaat niet gevolgd door laag surrogaat in fixedCharCodeAt()","exception_string_length":"Ongeldige tekenreeks. Lengte moet een veelvoud van 4 zijn","exception_key_nonobject":"Object.keys opgeroepen voor niet-object","exception_null_or_undefined":" dit is nul of niet gedefinieerd","exception_not_function":" is geen functie","exception_invalid_date_format":"Ongeldige datumnotatie: ","exception_casting":"Kan niet weergeven ","exception_casting_to":" op "},"no":{"latex":"LaTeX","cancel":"Avbryt","accept":"Set inn","manual":"Håndbok","insert_math":"Sett inn matematikkformel - MathType","insert_chem":"Set inn ein kjemisk formel – ChemType","minimize":"Minimer","maximize":"Maksimer","fullscreen":"Fullskjerm","exit_fullscreen":"Avslutt fullskjerm","close":"Lukk","mathtype":"MathType","title_modalwindow":"Modalt MathType-vindu","close_modal_warning":"Er du sikker på at du vil gå ut? Endringane du har gjort, vil gå tapt.","latex_name_label":"LaTeX-formel","browser_no_compatible":"Nettlesaren er ikkje kompatibel med AJAX-teknologien. Bruk den nyaste versjonen av Mozilla Firefox.","error_convert_accessibility":"Feil under konvertering frå MathML til tilgjengeleg tekst.","exception_cross_site":"Skripting på tvers av nettstadar er bere tillaten med HTTP.","exception_high_surrogate":"Høgt surrogat er ikkje etterfølgt av lågt surrogat i fixedCharCodeAt()","exception_string_length":"Ugyldig streng. Lengda må vera deleleg på 4","exception_key_nonobject":"Object.keys kalla på eit ikkje-objekt","exception_null_or_undefined":" dette er null eller ikkje definert","exception_not_function":" er ikkje ein funksjon","exception_invalid_date_format":"Ugyldig datoformat: ","exception_casting":"Kan ikkje bruka casting ","exception_casting_to":" til "},"nb":{"latex":"LaTeX","cancel":"Avbryt","accept":"Insert","manual":"Håndbok","insert_math":"Sett inn matematikkformel - MathType","insert_chem":"Sett inn en kjemisk formel – ChemType","minimize":"Minimer","maximize":"Maksimer","fullscreen":"Fullskjerm","exit_fullscreen":"Avslutt fullskjerm","close":"Lukk","mathtype":"MathType","title_modalwindow":"Modalt MathType-vindu","close_modal_warning":"Er du sikker på at du vil gå ut? Endringene du har gjort, vil gå tapt.","latex_name_label":"LaTeX-formel","browser_no_compatible":"Nettleseren er ikke kompatibel med AJAX-teknologien. Bruk den nyeste versjonen av Mozilla Firefox.","error_convert_accessibility":"Feil under konvertering fra MathML til tilgjengelig tekst.","exception_cross_site":"Skripting på tvers av nettsteder er bare tillatt med HTTP.","exception_high_surrogate":"Høyt surrogat etterfølges ikke av lavt surrogat i fixedCharCodeAt()","exception_string_length":"Ugyldig streng. Lengden må være delelig på 4","exception_key_nonobject":"Object.keys kalte på et ikke-objekt","exception_null_or_undefined":" dette er null eller ikke definert","exception_not_function":" er ikke en funksjon","exception_invalid_date_format":"Ugyldig datoformat: ","exception_casting":"Kan ikke bruke casting ","exception_casting_to":" til "},"nn":{"latex":"LaTeX","cancel":"Avbryt","accept":"Set inn","manual":"Håndbok","insert_math":"Sett inn matematikkformel - MathType","insert_chem":"Set inn ein kjemisk formel – ChemType","minimize":"Minimer","maximize":"Maksimer","fullscreen":"Fullskjerm","exit_fullscreen":"Avslutt fullskjerm","close":"Lukk","mathtype":"MathType","title_modalwindow":"Modalt MathType-vindu","close_modal_warning":"Er du sikker på at du vil gå ut? Endringane du har gjort, vil gå tapt.","latex_name_label":"LaTeX-formel","browser_no_compatible":"Nettlesaren er ikkje kompatibel med AJAX-teknologien. Bruk den nyaste versjonen av Mozilla Firefox.","error_convert_accessibility":"Feil under konvertering frå MathML til tilgjengeleg tekst.","exception_cross_site":"Skripting på tvers av nettstadar er bere tillaten med HTTP.","exception_high_surrogate":"Høgt surrogat er ikkje etterfølgt av lågt surrogat i fixedCharCodeAt()","exception_string_length":"Ugyldig streng. Lengda må vera deleleg på 4","exception_key_nonobject":"Object.keys kalla på eit ikkje-objekt","exception_null_or_undefined":" dette er null eller ikkje definert","exception_not_function":" er ikkje ein funksjon","exception_invalid_date_format":"Ugyldig datoformat: ","exception_casting":"Kan ikkje bruka casting ","exception_casting_to":" til "},"pl":{"latex":"LaTeX","cancel":"Anuluj","accept":"Wstaw","manual":"Instrukcja","insert_math":"Wstaw formułę matematyczną - MathType","insert_chem":"Wstaw wzór chemiczny — ChemType","minimize":"Minimalizuj","maximize":"Maksymalizuj","fullscreen":"Pełny ekran","exit_fullscreen":"Opuść tryb pełnoekranowy","close":"Zamknij","mathtype":"MathType","title_modalwindow":"Okno modalne MathType","close_modal_warning":"Czy na pewno chcesz zamknąć? Wprowadzone zmiany zostaną utracone.","latex_name_label":"Wzór Latex","browser_no_compatible":"Twoja przeglądarka jest niezgodna z technologią AJAX Użyj najnowszej wersji Mozilla Firefox.","error_convert_accessibility":"Błąd podczas konwertowania z formatu MathML na dostępny tekst.","exception_cross_site":"Krzyżowanie skryptów witryny jest dozwolone tylko dla HTTP.","exception_high_surrogate":"Brak niskiego surogatu po wysokim surogacie w fixedCharCodeAt()","exception_string_length":"Niewłaściwy ciąg znaków. Długość musi być wielokrotnością liczby 4.","exception_key_nonobject":"Argumentem wywołanej funkcji Object.key nie jest obiekt.","exception_null_or_undefined":" jest zerowy lub niezdefiniowany","exception_not_function":" nie jest funkcją","exception_invalid_date_format":"Nieprawidłowy format daty: ","exception_casting":"Nie można rzutować ","exception_casting_to":" na "},"pt":{"latex":"LaTeX","cancel":"Cancelar","accept":"Inserir","manual":"Manual","insert_math":"Inserir fórmula matemática - MathType","insert_chem":"Inserir uma fórmula química - ChemType","minimize":"Minimizar","maximize":"Maximizar","fullscreen":"Ecrã completo","exit_fullscreen":"Sair do ecrã completo","close":"Fechar","mathtype":"MathType","title_modalwindow":"Janela modal do MathType","close_modal_warning":"Pretende sair? As alterações efetuadas serão perdidas.","latex_name_label":"Fórmula Latex","browser_no_compatible":"O seu navegador não é compatível com a tecnologia AJAX. Utilize a versão mais recente do Mozilla Firefox.","error_convert_accessibility":"Erro ao converter de MathML para texto acessível.","exception_cross_site":"O processamento de scripts em vários sites só é permitido para HTTP.","exception_high_surrogate":"Substituto alto não seguido por um substituto baixo em fixedCharCodeAt()","exception_string_length":"Cadeia inválida. O comprimento tem de ser um múltiplo de 4","exception_key_nonobject":"Object.keys chamou um não-objeto","exception_null_or_undefined":" é nulo ou não está definido","exception_not_function":" não é uma função","exception_invalid_date_format":"Formato de data inválido: ","exception_casting":"Não é possível adicionar ","exception_casting_to":" até "},"pt_br":{"latex":"LaTeX","cancel":"Cancelar","accept":"Inserir","manual":"Manual","insert_math":"Inserir fórmula matemática - MathType","insert_chem":"Insira uma fórmula química - ChemType","minimize":"Minimizar","maximize":"Maximizar","fullscreen":"Tela cheia","exit_fullscreen":"Sair de tela cheia","close":"Fechar","mathtype":"MathType","title_modalwindow":"Janela modal do MathType","close_modal_warning":"Tem certeza de que deseja sair? Todas as alterações serão perdidas.","latex_name_label":"Fórmula LaTeX","browser_no_compatible":"O navegador não é compatível com a tecnologia AJAX. Use a versão mais recente do Mozilla Firefox.","error_convert_accessibility":"Erro ao converter de MathML para texto acessível.","exception_cross_site":"O uso de scripts entre sites só é permitido para HTTP.","exception_high_surrogate":"High surrogate não seguido de low surrogate em fixedCharCodeAt()","exception_string_length":"String inválida. O comprimento deve ser um múltiplo de 4","exception_key_nonobject":"Object.keys chamados em não objeto","exception_null_or_undefined":" isto é nulo ou não definido","exception_not_function":" não é uma função","exception_invalid_date_format":"Formato de data inválido: ","exception_casting":"Não é possível transmitir ","exception_casting_to":" para "},"ro":{"latex":"LaTeX","cancel":"Anulare","accept":"Inserați","manual":"Ghid","insert_math":"Inserați o formulă matematică - MathType","insert_chem":"Inserați o formulă chimică - ChemType","minimize":"Minimizați","maximize":"Maximizați","fullscreen":"Afișați pe tot ecranul","exit_fullscreen":"Opriți afișarea pe tot ecranul","close":"Închideți","mathtype":"MathType","title_modalwindow":"Fereastră modală MathType","close_modal_warning":"Sigur doriți să ieșiți? Modificările realizate se vor pierde.","latex_name_label":"Formulă Latex","browser_no_compatible":"Browserul dvs. nu este compatibil cu tehnologia AJAX. Utilizați cea mai recentă versiune de Mozilla Firefox.","error_convert_accessibility":"Eroare la convertirea din MathML în text accesibil.","exception_cross_site":"Scriptarea între site‑uri este permisă doar pentru HTTP.","exception_high_surrogate":"Surogatul superior nu este urmat de un surogat inferior în fixedCharCodeAt()","exception_string_length":"Șir nevalid. Lungimea trebuie să fie multiplu de 4","exception_key_nonobject":"Object.keys a apelat un non-obiect","exception_null_or_undefined":" este null sau nu este definit","exception_not_function":" nu este funcție","exception_invalid_date_format":"Format de dată nevalid: ","exception_casting":"nu se poate difuza ","exception_casting_to":" către "},"ru":{"latex":"LaTeX","cancel":"отмена","accept":"Вставка","manual":"вручную","insert_math":"Вставить математическую формулу: WIRIS","insert_chem":"Вставить химическую формулу — ChemType","minimize":"Свернуть","maximize":"Развернуть","fullscreen":"На весь экран","exit_fullscreen":"Выйти из полноэкранного режима","close":"Закрыть","mathtype":"MathType","title_modalwindow":"Режимное окно MathType","close_modal_warning":"Вы уверены, что хотите выйти? Все внесенные изменения будут утрачены.","latex_name_label":"Формула Latex","browser_no_compatible":"Ваш браузер несовместим с технологией AJAX. Используйте последнюю версию Mozilla Firefox.","error_convert_accessibility":"При преобразовании формулы в текст допустимого формата произошла ошибка.","exception_cross_site":"Межсайтовые сценарии доступны только для HTTP.","exception_high_surrogate":"Младший символ-заместитель не сопровождает старший символ-заместитель в исправленном методе CharCodeAt()","exception_string_length":"Недопустимая строка. Длинна должна быть кратной 4.","exception_key_nonobject":"Метод Object.keys вызван не для объекта","exception_null_or_undefined":" значение пустое или не определено","exception_not_function":" не функция","exception_invalid_date_format":"Недопустимый формат даты: ","exception_casting":"Не удается привести ","exception_casting_to":" к "},"sv":{"latex":"LaTeX","cancel":"Avbryt","accept":"Infoga","manual":"Bruksanvisning","insert_math":"Infoga matematisk formel - MathType","insert_chem":"Infoga en kemiformel – ChemType","minimize":"Minimera","maximize":"Maximera","fullscreen":"Helskärm","exit_fullscreen":"Stäng helskärm","close":"Stäng","mathtype":"MathType","title_modalwindow":"MathType modulfönster","close_modal_warning":"Vill du avsluta? Inga ändringar kommer att sparas.","latex_name_label":"Latex-formel","browser_no_compatible":"Din webbläsare är inte kompatibel med AJAX-teknik. Använd den senaste versionen av Mozilla Firefox.","error_convert_accessibility":"Det uppstod ett fel vid konvertering från MathML till åtkomlig text.","exception_cross_site":"Skriptkörning över flera sajter är endast tillåtet för HTTP.","exception_high_surrogate":"Hög surrogat följs inte av låg surrogat i fixedCharCodeAt()","exception_string_length":"Ogiltig sträng. Längden måste vara en multipel av 4","exception_key_nonobject":"Object.keys anropade icke-objekt","exception_null_or_undefined":" det är null eller inte definierat","exception_not_function":" är inte en funktion","exception_invalid_date_format":"Ogiltigt datumformat: ","exception_casting":"Går inte att konvertera ","exception_casting_to":" till "},"tr":{"latex":"LaTeX","cancel":"Vazgeç","accept":"Ekle","manual":"Kılavuz","insert_math":"Matematik formülü ekle - MathType","insert_chem":"Kimya formülü ekleyin - ChemType","minimize":"Simge Durumuna Küçült","maximize":"Ekranı Kapla","fullscreen":"Tam Ekran","exit_fullscreen":"Tam Ekrandan Çık","close":"Kapat","mathtype":"MathType","title_modalwindow":"MathType kalıcı penceresi","close_modal_warning":"Çıkmak istediğinizden emin misiniz? Yaptığınız değişiklikler kaybolacak.","latex_name_label":"Latex Formülü","browser_no_compatible":"Tarayıcınız AJAX teknolojisiyle uyumlu değil. Lütfen en güncel Mozilla Firefox sürümünü kullanın.","error_convert_accessibility":"MathML biçiminden erişilebilir metne dönüştürme hatası.","exception_cross_site":"Siteler arası komut dosyası yazma işlemine yalnızca HTTP için izin verilir.","exception_high_surrogate":"fixedCharCodeAt() fonksiyonunda üst vekilin ardından alt vekil gelmiyor","exception_string_length":"Geçersiz dizgi. Uzunluk, 4\'ün katlarından biri olmalıdır","exception_key_nonobject":"Nesne olmayan öğe üzerinde Object.keys çağrıldı","exception_null_or_undefined":" bu değer boş veya tanımlanmamış","exception_not_function":" bir fonksiyon değil","exception_invalid_date_format":"Geçersiz tarih biçimi: ","exception_casting":"Tür dönüştürülemiyor ","exception_casting_to":" hedef: "},"zh":{"latex":"LaTeX","cancel":"取消","accept":"插入","manual":"手册","insert_math":"插入数学公式 - MathType","insert_chem":"插入化学分子式 - ChemType","minimize":"最小化","maximize":"最大化","fullscreen":"全屏幕","exit_fullscreen":"退出全屏幕","close":"关闭","mathtype":"MathType","title_modalwindow":"MathType 模式窗口","close_modal_warning":"您确定要离开吗？您所做的修改将丢失。","latex_name_label":"Latex 分子式","browser_no_compatible":"您的浏览器不兼容 AJAX 技术。请使用最新版 Mozilla Firefox。","error_convert_accessibility":"将 MathML 转换为可访问文本时出错。","exception_cross_site":"仅 HTTP 允许跨站脚本。","exception_high_surrogate":"fixedCharCodeAt() 中的高位代理之后未跟随低位代理","exception_string_length":"无效字符串。长度必须是 4 的倍数","exception_key_nonobject":"非对象调用了 Object.keys","exception_null_or_undefined":" 该值为空或未定义","exception_not_function":" 不是一个函数","exception_invalid_date_format":"无效日期格式： ","exception_casting":"无法转换 ","exception_casting_to":" 为 "},"":{}}');

                function v(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var b = function() {
                    function e() {
                        throw function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), new Error("Static class StringManager can not be instantiated.")
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "get",
                        value: function(e) {
                            var t = this.language;
                            return t && t.length > 2 && (t = t.slice(0, 2)), this.strings.hasOwnProperty(t) || (console.warn("Unknown language ".concat(t, " set in StringManager.")), t = "en"), this.strings[t].hasOwnProperty(e) ? this.strings[t][e] : (console.warn("Unknown key ".concat(e, " for language ").concat(t, " in StringManager.")), e)
                        }
                    }], (n = null) && v(t.prototype, n), i && v(t, i), e
                }();

                function y(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                b.strings = _, b.language = "en";
                var w = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "fireEvent",
                        value: function(e, t) {
                            if (document.createEvent) {
                                var n = document.createEvent("HTMLEvents");
                                return n.initEvent(t, !0, !0), !e.dispatchEvent(n)
                            }
                            var i = document.createEventObject();
                            return e.fireEvent("on".concat(t), i)
                        }
                    }, {
                        key: "addEvent",
                        value: function(e, t, n) {
                            e.addEventListener ? e.addEventListener(t, n, !0) : e.attachEvent && e.attachEvent("on".concat(t), n)
                        }
                    }, {
                        key: "removeEvent",
                        value: function(e, t, n) {
                            e.removeEventListener ? e.removeEventListener(t, n, !0) : e.detachEvent && e.detachEvent("on".concat(t), n)
                        }
                    }, {
                        key: "addElementEvents",
                        value: function(t, n, i, r) {
                            if (n && e.addEvent(t, "dblclick", (function(e) {
                                    var t = e || window.event,
                                        i = t.srcElement ? t.srcElement : t.target;
                                    n(i, t)
                                })), i && e.addEvent(t, "mousedown", (function(e) {
                                    var t = e || window.event,
                                        n = t.srcElement ? t.srcElement : t.target;
                                    i(n, t)
                                })), r) {
                                var a = function(e) {
                                    var t = e || window.event,
                                        n = t.srcElement ? t.srcElement : t.target;
                                    r(n, t)
                                };
                                e.addEvent(document, "mouseup", a), e.addEvent(t, "mouseup", a)
                            }
                        }
                    }, {
                        key: "addClass",
                        value: function(t, n) {
                            e.containsClass(t, n) || (t.className += " ".concat(n))
                        }
                    }, {
                        key: "containsClass",
                        value: function(e, t) {
                            if (null == e || !("className" in e)) return !1;
                            for (var n = e.className.split(" "), i = n.length - 1; i >= 0; i -= 1)
                                if (n[i] === t) return !0;
                            return !1
                        }
                    }, {
                        key: "removeClass",
                        value: function(e, t) {
                            for (var n = "", i = e.className.split(" "), r = 0; r < i.length; r += 1) i[r] !== t && (n += "".concat(i[r], " "));
                            e.className = n.trim()
                        }
                    }, {
                        key: "convertOldXmlinitialtextAttribute",
                        value: function(e) {
                            var t = "value=",
                                n = e.indexOf("xmlinitialtext"),
                                i = e.indexOf(t, n),
                                r = e.charAt(i + t.length),
                                a = i + t.length + 1,
                                o = e.indexOf(r, a),
                                s = e.substring(a, o),
                                l = s.split("«").join("§lt;");
                            return l = (l = (l = l.split("»").join("§gt;")).split("&").join("§")).split("¨").join("§quot;"), e = e.split(s).join(l)
                        }
                    }, {
                        key: "createElement",
                        value: function(t, n, i) {
                            var r;
                            void 0 === n && (n = {}), void 0 === i && (i = document);
                            try {
                                var a = "<".concat(t);
                                Object.keys(n).forEach((function(t) {
                                    a += " ".concat(t, '="').concat(e.htmlEntities(n[t]), '"')
                                })), a += ">", r = i.createElement(a)
                            } catch (e) {
                                r = i.createElement(t), Object.keys(n).forEach((function(e) {
                                    r.setAttribute(e, n[e])
                                }))
                            }
                            return r
                        }
                    }, {
                        key: "createObject",
                        value: function(t, n) {
                            void 0 === n && (n = document), t = (t = (t = (t = t.split("<applet ").join('<span wirisObject="WirisApplet" ').split("<APPLET ").join('<span wirisObject="WirisApplet" ')).split("</applet>").join("</span>").split("</APPLET>").join("</span>")).split("<param ").join('<br wirisObject="WirisParam" ').split("<PARAM ").join('<br wirisObject="WirisParam" ')).split("</param>").join("</br>").split("</PARAM>").join("</br>");
                            var i = e.createElement("div", {}, n);
                            return i.innerHTML = t,
                                function t(i) {
                                    if (i.getAttribute && "WirisParam" === i.getAttribute("wirisObject")) {
                                        for (var r = {}, a = 0; a < i.attributes.length; a += 1) null !== i.attributes[a].nodeValue && (r[i.attributes[a].nodeName] = i.attributes[a].nodeValue);
                                        var o = e.createElement("param", r, n);
                                        o.NAME && (o.name = o.NAME, o.value = o.VALUE), o.removeAttribute("wirisObject"), i.parentNode.replaceChild(o, i)
                                    } else if (i.getAttribute && "WirisApplet" === i.getAttribute("wirisObject")) {
                                        for (var s = {}, l = 0; l < i.attributes.length; l += 1) null !== i.attributes[l].nodeValue && (s[i.attributes[l].nodeName] = i.attributes[l].nodeValue);
                                        var c = e.createElement("applet", s, n);
                                        c.removeAttribute("wirisObject");
                                        for (var d = 0; d < i.childNodes.length; d += 1) t(i.childNodes[d]), "param" === i.childNodes[d].nodeName.toLowerCase() && (c.appendChild(i.childNodes[d]), d -= 1);
                                        i.parentNode.replaceChild(c, i)
                                    } else
                                        for (var u = 0; u < i.childNodes.length; u += 1) t(i.childNodes[u])
                                }(i), i.firstChild
                        }
                    }, {
                        key: "createObjectCode",
                        value: function(t) {
                            if (null == t) return null;
                            if (1 === t.nodeType) {
                                for (var n = "<".concat(t.tagName), i = 0; i < t.attributes.length; i += 1) t.attributes[i].specified && (n += " ".concat(t.attributes[i].name, '="').concat(e.htmlEntities(t.attributes[i].value), '"'));
                                if (t.childNodes.length > 0) {
                                    n += ">";
                                    for (var r = 0; r < t.childNodes.length; r += 1) n += e.createObject(t.childNodes[r]);
                                    n += "</".concat(t.tagName, ">")
                                } else "DIV" === t.nodeName || "SCRIPT" === t.nodeName ? n += "></".concat(t.tagName, ">") : n += "/>";
                                return n
                            }
                            return 3 === t.nodeType ? e.htmlEntities(t.nodeValue) : ""
                        }
                    }, {
                        key: "concatenateUrl",
                        value: function(e, t) {
                            var n = "";
                            return e.indexOf("/") !== e.length && 0 !== t.indexOf("/") && (n = "/"), (e + n + t).replace(/([^:]\/)\/+/g, "$1")
                        }
                    }, {
                        key: "htmlEntities",
                        value: function(e) {
                            return e.split("&").join("&amp;").split("<").join("&lt;").split(">").join("&gt;").split('"').join("&quot;")
                        }
                    }, {
                        key: "htmlEntitiesDecode",
                        value: function(e) {
                            var t = document.createElement("textarea");
                            return t.innerHTML = e, t.value
                        }
                    }, {
                        key: "createHttpRequest",
                        value: function() {
                            if ("file://" === window.location.toString().substr(0, window.location.toString().lastIndexOf("/") + 1).substr(0, 7)) throw b.get("exception_cross_site");
                            if ("undefined" != typeof XMLHttpRequest) return new XMLHttpRequest;
                            try {
                                return new ActiveXObject("Msxml2.XMLHTTP")
                            } catch (e) {
                                try {
                                    return new ActiveXObject("Microsoft.XMLHTTP")
                                } catch (e) {
                                    return null
                                }
                            }
                        }
                    }, {
                        key: "httpBuildQuery",
                        value: function(t) {
                            var n = "";
                            return Object.keys(t).forEach((function(i) {
                                null != t[i] && (n += "".concat(e.urlEncode(i), "=").concat(e.urlEncode(t[i]), "&"))
                            })), "&" === n.substring(n.length - 1) && (n = n.substring(0, n.length - 1)), n
                        }
                    }, {
                        key: "propertiesToString",
                        value: function(t) {
                            var n = [];
                            Object.keys(t).forEach((function(e) {
                                Object.prototype.hasOwnProperty.call(t, e) && n.push(e)
                            }));
                            for (var i = n.length, r = 0; r < i; r += 1)
                                for (var a = r + 1; a < i; a += 1) {
                                    var o = n[r],
                                        s = n[a];
                                    e.compareStrings(o, s) > 0 && (n[r] = s, n[a] = o)
                                }
                            for (var l = "", c = 0; c < i; c += 1) {
                                var d = n[c];
                                l += d, l += "=";
                                var u = t[d];
                                l += u = (u = (u = (u = u.replace("\\", "\\\\")).replace("\n", "\\n")).replace("\r", "\\r")).replace("\t", "\\t"), l += "\n"
                            }
                            return l
                        }
                    }, {
                        key: "compareStrings",
                        value: function(t, n) {
                            var i, r = t.length,
                                a = n.length,
                                o = r > a ? a : r;
                            for (i = 0; i < o; i += 1) {
                                var s = e.fixedCharCodeAt(t, i) - e.fixedCharCodeAt(n, i);
                                if (0 !== s) return s
                            }
                            return t.length - n.length
                        }
                    }, {
                        key: "fixedCharCodeAt",
                        value: function(e, t) {
                            t = t || 0;
                            var n, i, r = e.charCodeAt(t);
                            if (r >= 55296 && r <= 56319) {
                                if (n = r, i = e.charCodeAt(t + 1), Number.isNaN(i)) throw b.get("exception_high_surrogate");
                                return 1024 * (n - 55296) + (i - 56320) + 65536
                            }
                            return !(r >= 56320 && r <= 57343) && r
                        }
                    }, {
                        key: "urlToAssArray",
                        value: function(e) {
                            var t;
                            if ((t = e.indexOf("?")) > 0) {
                                var n = e.substring(t + 1).split("&"),
                                    i = {};
                                for (t = 0; t < n.length; t += 1) {
                                    var r = n[t].split("=");
                                    r.length > 1 && (i[r[0]] = decodeURIComponent(r[1].replace(/\+/g, " ")))
                                }
                                return i
                            }
                            return {}
                        }
                    }, {
                        key: "urlEncode",
                        value: function(e) {
                            return encodeURIComponent(e)
                        }
                    }, {
                        key: "getWIRISImageOutput",
                        value: function(t, n, i) {
                            var r = e.createObject(t);
                            if (r && (r.className === l.get("imageClassName") || r.getAttribute(l.get("imageMathmlAttribute")))) {
                                if (!n) return t;
                                var a = r.getAttribute(l.get("imageMathmlAttribute")),
                                    s = o.safeXmlDecode(a);
                                return l.get("saveHandTraces") || (s = o.removeAnnotation(s, "application/json")), null == s && (s = r.getAttribute("alt")), i ? o.safeXmlEncode(s) : s
                            }
                            return t
                        }
                    }, {
                        key: "getNodeLength",
                        value: function(t) {
                            if (3 === t.nodeType) return t.nodeValue.length;
                            if (1 === t.nodeType) {
                                var n = {
                                    IMG: 1,
                                    BR: 1
                                } [t.nodeName.toUpperCase()];
                                void 0 === n && (n = 0);
                                for (var i = 0; i < t.childNodes.length; i += 1) n += e.getNodeLength(t.childNodes[i]);
                                return n
                            }
                            return 0
                        }
                    }, {
                        key: "getSelectedItem",
                        value: function(t, n, i) {
                            var r;
                            if (n ? (r = t.contentWindow).focus() : (r = window, t.focus()), document.selection && !i) {
                                var a = r.document.selection.createRange();
                                if (a.parentElement) {
                                    if (a.htmlText.length > 0) return 0 === a.text.length ? e.getSelectedItem(t, n, !0) : null;
                                    r.document.execCommand("InsertImage", !1, "#");
                                    var o, s, l = a.parentElement();
                                    return "IMG" !== l.nodeName.toUpperCase() && (a.pasteHTML('<span id="wrs_openEditorWindow_temporalObject"></span>'), l = r.document.getElementById("wrs_openEditorWindow_temporalObject")), l.nextSibling && 3 === l.nextSibling.nodeType ? (o = l.nextSibling, s = 0) : l.previousSibling && 3 === l.previousSibling.nodeType ? s = (o = l.previousSibling).nodeValue.length : (o = r.document.createTextNode(""), l.parentNode.insertBefore(o, l), s = 0), l.parentNode.removeChild(l), {
                                        node: o,
                                        caretPosition: s
                                    }
                                }
                                return a.length > 1 ? null : {
                                    node: a.item(0)
                                }
                            }
                            if (r.getSelection) {
                                var c, d = r.getSelection();
                                try {
                                    c = d.getRangeAt(0)
                                } catch (e) {
                                    c = r.document.createRange()
                                }
                                var u = c.startContainer;
                                if (3 === u.nodeType) return {
                                    node: u,
                                    caretPosition: c.startOffset
                                };
                                if (u !== c.endContainer) return null;
                                if (1 === u.nodeType) {
                                    var m = c.startOffset;
                                    if (u.childNodes[m]) return {
                                        node: u.childNodes[m]
                                    }
                                }
                            }
                            return null
                        }
                    }, {
                        key: "getSelectedItemOnTextarea",
                        value: function(e) {
                            var t = document.createTextNode(e.value),
                                n = f.getLatexFromTextNode(t, e.selectionStart);
                            return null === n ? null : {
                                node: t,
                                caretPosition: e.selectionStart,
                                startPosition: n.startPosition,
                                endPosition: n.endPosition
                            }
                        }
                    }, {
                        key: "getElementsByNameFromString",
                        value: function(e, t, n) {
                            var i = [];
                            e = e.toLowerCase(), t = t.toLowerCase();
                            for (var r = e.indexOf("<".concat(t, " ")); - 1 !== r;) {
                                var a = void 0;
                                a = n ? ">" : "</".concat(t, ">");
                                var o = e.indexOf(a, r); - 1 !== o ? (o += a.length, i.push({
                                    start: r,
                                    end: o
                                })) : o = r + 1, r = e.indexOf("<".concat(t, " "), o)
                            }
                            return i
                        }
                    }, {
                        key: "decode64",
                        value: function(e) {
                            var t = "+".charCodeAt(0),
                                n = "/".charCodeAt(0),
                                i = "0".charCodeAt(0),
                                r = "a".charCodeAt(0),
                                a = "A".charCodeAt(0),
                                o = "-".charCodeAt(0),
                                s = "_".charCodeAt(0),
                                l = e.charCodeAt(0);
                            return l === t || l === o ? 62 : l === n || l === s ? 63 : l < i ? -1 : l < i + 10 ? l - i + 26 + 26 : l < a + 26 ? l - a : l < r + 26 ? l - r + 26 : null
                        }
                    }, {
                        key: "b64ToByteArray",
                        value: function(t, n) {
                            var i;
                            if (t.length % 4 > 0) throw new Error("Invalid string. Length must be a multiple of 4");
                            var r, a, o, s = [];
                            for (r = n || ((a = "=" === t.charAt(t.length - 2) ? 2 : "=" === t.charAt(t.length - 1) ? 1 : 0) > 0 ? t.length - 4 : t.length), o = 0; o < r; o += 4) i = e.decode64(t.charAt(o)) << 18 | e.decode64(t.charAt(o + 1)) << 12 | e.decode64(t.charAt(o + 2)) << 6 | e.decode64(t.charAt(o + 3)), s.push(i >> 16 & 255), s.push(i >> 8 & 255), s.push(255 & i);
                            return a && (2 === a ? (i = e.decode64(t.charAt(o)) << 2 | e.decode64(t.charAt(o + 1)) >> 4, s.push(255 & i)) : 1 === a && (i = e.decode64(t.charAt(o)) << 10 | e.decode64(t.charAt(o + 1)) << 4 | e.decode64(t.charAt(o + 2)) >> 2, s.push(i >> 8 & 255), s.push(255 & i))), s
                        }
                    }, {
                        key: "readInt32",
                        value: function(e) {
                            if (e.length < 4) return !1;
                            var t = e.splice(0, 4);
                            return t[0] << 24 | t[1] << 16 | t[2] << 8 | t[3] << 0
                        }
                    }, {
                        key: "readByte",
                        value: function(e) {
                            return e.shift() << 0
                        }
                    }, {
                        key: "readBytes",
                        value: function(e, t, n) {
                            return e.splice(t, n)
                        }
                    }, {
                        key: "updateTextArea",
                        value: function(e, t) {
                            if (e && t)
                                if (e.focus(), null != e.selectionStart) {
                                    var n = e.selectionEnd,
                                        i = e.value.substring(0, e.selectionStart),
                                        r = e.value.substring(n, e.value.length);
                                    e.value = i + t + r, e.selectionEnd = n + t.length
                                } else document.selection.createRange().text = t
                        }
                    }, {
                        key: "updateExistingTextOnTextarea",
                        value: function(e, t, n, i) {
                            e.focus();
                            var r = e.value.substring(0, n);
                            e.value = r + t + e.value.substring(i, e.value.length), e.selectionEnd = n + t.length
                        }
                    }, {
                        key: "addArgument",
                        value: function(e, t, n) {
                            var i;
                            return i = e.indexOf("?") > 0 ? "&" : "?", "".concat(e + i + t, "=").concat(n)
                        }
                    }], (n = null) && y(t.prototype, n), i && y(t, i), e
                }();

                function x(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var k = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "removeImgDataAttributes",
                        value: function(e) {
                            var t = [],
                                n = e.attributes;
                            Object.keys(n).forEach((function(e) {
                                var i = n[e];
                                void 0 !== i && void 0 !== i.name && 0 === i.name.indexOf("data-") && t.push(i.name)
                            })), t.forEach((function(t) {
                                e.removeAttribute(t)
                            }))
                        }
                    }, {
                        key: "clone",
                        value: function(e, t) {
                            var n = l.get("imageCustomEditorName");
                            e.hasAttribute(n) || t.removeAttribute(n), [l.get("imageMathmlAttribute"), n, "alt", "height", "width", "style", "src", "role"].forEach((function(n) {
                                var i = e.getAttribute(n);
                                i && t.setAttribute(n, i)
                            }))
                        }
                    }, {
                        key: "setImgSize",
                        value: function(t, n, i) {
                            var r, a, o, s;
                            if (i)
                                if ("svg" === l.get("imageFormat"))
                                    if ("base64" !== l.get("saveMode")) r = e.getMetricsFromSvgString(n);
                                    else {
                                        a = t.src.substr(t.src.indexOf("base64,") + 7, t.src.length), s = "", o = w.b64ToByteArray(a, a.length);
                                        for (var c = 0; c < o.length; c += 1) s += String.fromCharCode(o[c]);
                                        r = e.getMetricsFromSvgString(s)
                                    }
                            else a = t.src.substr(t.src.indexOf("base64,") + 7, t.src.length), o = w.b64ToByteArray(a, 88), r = e.getMetricsFromBytes(o);
                            else r = w.urlToAssArray(n);
                            var d = r.cw;
                            if (d) {
                                var u = r.ch,
                                    m = r.cb,
                                    h = r.dpi;
                                h && (d = 96 * d / h, u = 96 * u / h, m = 96 * m / h), t.width = d, t.height = u, t.style.verticalAlign = "-".concat(u - m, "px")
                            }
                        }
                    }, {
                        key: "fixAfterResize",
                        value: function(t) {
                            if (t.removeAttribute("style"), t.removeAttribute("width"), t.removeAttribute("height"), t.style.maxWidth = "none", -1 !== t.src.indexOf("data:image"))
                                if ("svg" === l.get("imageFormat")) {
                                    var n = decodeURIComponent(t.src.substring(32, t.src.length));
                                    e.setImgSize(t, n, !0)
                                } else {
                                    var i = t.src.substring(22, t.src.length);
                                    e.setImgSize(t, i, !0)
                                }
                            else e.setImgSize(t, t.src)
                        }
                    }, {
                        key: "getMetricsFromSvgString",
                        value: function(e) {
                            var t = e.indexOf('height="'),
                                n = e.indexOf('"', t + 8, e.length),
                                i = e.substring(t + 8, n);
                            t = e.indexOf('width="'), n = e.indexOf('"', t + 7, e.length);
                            var r = e.substring(t + 7, n);
                            t = e.indexOf('wrs:baseline="'), n = e.indexOf('"', t + 14, e.length);
                            var a = e.substring(t + 14, n);
                            if (void 0 !== r) {
                                var o = [];
                                return o.cw = r, o.ch = i, void 0 !== a && (o.cb = a), o
                            }
                            return []
                        }
                    }, {
                        key: "getMetricsFromBytes",
                        value: function(e) {
                            var t, n, i, r, a;
                            for (w.readBytes(e, 0, 8); e.length >= 4;) 1229472850 === (i = w.readInt32(e)) ? (t = w.readInt32(e), n = w.readInt32(e), w.readInt32(e), w.readByte(e)) : 1650545477 === i ? r = w.readInt32(e) : 1883789683 === i && (a = w.readInt32(e), a = Math.round(a / 39.37), w.readInt32(e), w.readByte(e)), w.readInt32(e);
                            if (void 0 !== t) {
                                var o = [];
                                return o.cw = t, o.ch = n, o.dpi = a, r && (o.cb = r), o
                            }
                            return []
                        }
                    }], (n = null) && x(t.prototype, n), i && x(t, i), e
                }();

                function A(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var C = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "cache",
                        get: function() {
                            return e._cache
                        },
                        set: function(t) {
                            e._cache = t
                        }
                    }, {
                        key: "mathMLToAccessible",
                        value: function(t, n, i) {
                            void 0 === n && (n = "en"), o.containClass(t, "wrs_chemistry") && (i.mode = "chemistry");
                            var r = "";
                            if (e.cache.get(t)) r = e.cache.get(t);
                            else {
                                i.service = "mathml2accessible", i.lang = n;
                                var a = JSON.parse(g.getService("service", i));
                                "error" !== a.status ? (r = a.result.text, e.cache.populate(t, r)) : r = b.get("error_convert_accessibility")
                            }
                            return r
                        }
                    }], (n = null) && A(t.prototype, n), i && A(t, i), e
                }();
                C._cache = new d;
                n(646);

                function T(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var E = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "mathmlToImgObject",
                        value: function(t, n, i, r) {
                            var a = t.createElement("img");
                            a.align = "middle", a.style.maxWidth = "none";
                            var s = i || {};
                            if (s.mml = n, s.lang = r, s.metrics = "true", s.centerbaseline = "false", "base64" === l.get("saveMode") && "default" === l.get("base64savemode") && (s.base64 = !0), a.className = l.get("imageClassName"), -1 !== n.indexOf('class="')) {
                                var c = n.substring(n.indexOf('class="') + 'class="'.length, n.length);
                                c = (c = c.substring(0, c.indexOf('"'))).substring(4, c.length), a.setAttribute(l.get("imageCustomEditorName"), c)
                            }
                            if (!l.get("wirisPluginPerformance") || "xml" !== l.get("saveMode") && "safeXml" !== l.get("saveMode")) {
                                var d = e.createImageSrc(n, s);
                                a.setAttribute(l.get("imageMathmlAttribute"), o.safeXmlEncode(n)), a.src = d, k.setImgSize(a, d, "base64" === l.get("saveMode") && "default" === l.get("base64savemode")), l.get("enableAccessibility") && (a.alt = C.mathMLToAccessible(n, r, s))
                            } else {
                                var u = JSON.parse(e.createShowImageSrc(s, r));
                                if ("warning" === u.status) try {
                                    u = JSON.parse(g.getService("showimage", s))
                                } catch (e) {
                                    return null
                                }
                                "png" === (u = u.result).format ? a.src = "data:image/png;base64,".concat(u.content) : a.src = "data:image/svg+xml;charset=utf8,".concat(w.urlEncode(u.content)), a.setAttribute(l.get("imageMathmlAttribute"), o.safeXmlEncode(n)), k.setImgSize(a, u.content, !0), l.get("enableAccessibility") && (void 0 === u.alt ? a.alt = C.mathMLToAccessible(n, r, s) : a.alt = u.alt)
                            }
                            return void 0 !== e.observer && e.observer.observe(a), a.setAttribute("role", "math"), a
                        }
                    }, {
                        key: "createImageSrc",
                        value: function(e, t) {
                            "base64" === l.get("saveMode") && "default" === l.get("base64savemode") && (t.base64 = !0);
                            var n = g.getService("createimage", t);
                            if (-1 !== n.indexOf("@BASE@")) {
                                var i = g.getServicePath("createimage").split("/");
                                i.pop(), n = n.split("@BASE@").join(i.join("/"))
                            }
                            return n
                        }
                    }, {
                        key: "initParse",
                        value: function(t, n) {
                            return t = e.initParseSaveMode(t, n), e.initParseEditMode(t)
                        }
                    }, {
                        key: "initParseSaveMode",
                        value: function(t, n) {
                            return l.get("saveMode") && (t = f.parseMathmlToLatex(t, r.safeXmlCharacters), t = f.parseMathmlToLatex(t, r.xmlCharacters), t = e.parseMathmlToImg(t, r.safeXmlCharacters, n), t = e.parseMathmlToImg(t, r.xmlCharacters, n), "base64" === l.get("saveMode") && "image" === l.get("base64savemode") && (t = e.codeImgTransform(t, "base642showimage"))), t
                        }
                    }, {
                        key: "initParseEditMode",
                        value: function(e) {
                            if (-1 !== l.get("parseModes").indexOf("latex"))
                                for (var t = w.getElementsByNameFromString(e, "img", !0), n = 'encoding="LaTeX">', i = 0, r = 0; r < t.length; r += 1) {
                                    var a = e.substring(t[r].start + i, t[r].end + i);
                                    if (-1 !== a.indexOf(' class="'.concat(l.get("imageClassName"), '"'))) {
                                        var s = " ".concat(l.get("imageMathmlAttribute"), '="'),
                                            c = a.indexOf(s);
                                        if (-1 === c && (s = ' alt="', c = a.indexOf(s)), -1 !== c) {
                                            c += s.length;
                                            var d = a.indexOf('"', c),
                                                u = o.safeXmlDecode(a.substring(c, d)),
                                                m = u.indexOf(n);
                                            if (-1 !== m) {
                                                m += n.length;
                                                var h = u.indexOf("</annotation>", m),
                                                    g = u.substring(m, h),
                                                    p = "$$".concat(w.htmlEntitiesDecode(g), "$$"),
                                                    f = e.substring(0, t[r].start + i),
                                                    _ = e.substring(t[r].end + i);
                                                e = f + p + _, i += p.length - (t[r].end - t[r].start)
                                            }
                                        }
                                    }
                                }
                            return e
                        }
                    }, {
                        key: "endParse",
                        value: function(t) {
                            var n = e.endParseEditMode(t);
                            return e.endParseSaveMode(n)
                        }
                    }, {
                        key: "endParseEditMode",
                        value: function(e) {
                            if (-1 !== l.get("parseModes").indexOf("latex")) {
                                for (var t = "", n = 0, i = e.indexOf("$$"); - 1 !== i;) {
                                    if (t += e.substring(n, i), -1 !== (n = e.indexOf("$$", i + 2))) {
                                        var r = e.substring(i + 2, n),
                                            a = w.htmlEntitiesDecode(r),
                                            s = f.getMathMLFromLatex(a, !0);
                                        l.get("saveHandTraces") || (s = o.removeAnnotation(s, "application/json")), t += s, n += 2
                                    } else t += "$$", n = i + 2;
                                    i = e.indexOf("$$", n)
                                }
                                t += e.substring(n, e.length), e = t
                            }
                            return e
                        }
                    }, {
                        key: "endParseSaveMode",
                        value: function(t) {
                            return l.get("saveMode") && ("safeXml" === l.get("saveMode") || "xml" === l.get("saveMode") ? t = e.codeImgTransform(t, "img2mathml") : "base64" === l.get("saveMode") && "image" === l.get("base64savemode") && (t = e.codeImgTransform(t, "img264"))), t
                        }
                    }, {
                        key: "createShowImageSrc",
                        value: function(e, t) {
                            var n = {};
                            ["mml", "color", "centerbaseline", "zoom", "dpi", "fontSize", "fontFamily", "defaultStretchy", "backgroundColor", "format"].forEach((function(t) {
                                void 0 !== e[t] && (n[t] = e[t])
                            }));
                            var i = {};
                            return Object.keys(e).forEach((function(t) {
                                "mml" !== t && (i[t] = e[t])
                            })), i.formula = com.wiris.js.JsPluginTools.md5encode(w.propertiesToString(n)), i.lang = void 0 === t ? "en" : t, i.version = l.get("version"), g.getService("showimage", w.httpBuildQuery(i), !0)
                        }
                    }, {
                        key: "codeImgTransform",
                        value: function(t, n) {
                            for (var i = "", r = 0, a = /<img/gi, s = a.source.length; a.test(t);) {
                                var c = a.lastIndex - s;
                                i += t.substring(r, c);
                                for (var d = c + 1; d < t.length && r <= c;) {
                                    var u = t.charAt(d);
                                    if ('"' === u || "'" === u) {
                                        var m = t.indexOf(u, d + 1);
                                        d = -1 === m ? t.length : m
                                    } else ">" === u && (r = d + 1);
                                    d += 1
                                }
                                if (r < c) return i += t.substring(c, t.length);
                                var h = t.substring(c, r),
                                    g = w.createObject(h),
                                    p = g.getAttribute(l.get("imageMathmlAttribute")),
                                    f = void 0,
                                    _ = void 0;
                                if ("base642showimage" === n) null == p && (p = g.getAttribute("alt")), p = o.safeXmlDecode(p), h = e.mathmlToImgObject(document, p, null, null), i += w.createObjectCode(h);
                                else if ("img2mathml" === n) l.get("saveMode") && ("safeXml" === l.get("saveMode") ? (f = !0, _ = !0) : "xml" === l.get("saveMode") && (f = !0, _ = !1)), i += w.getWIRISImageOutput(h, f, _);
                                else if ("img264" === n) {
                                    null === p && (p = g.getAttribute("alt")), p = o.safeXmlDecode(p);
                                    var v = {
                                        base64: "true"
                                    };
                                    h = e.mathmlToImgObject(document, p, v, null), k.setImgSize(h, h.src, !0), i += w.createObjectCode(h)
                                }
                            }
                            return i += t.substring(r, t.length)
                        }
                    }, {
                        key: "parseMathmlToImg",
                        value: function(t, n, i) {
                            for (var a = "", s = "".concat(n.tagOpener, "math"), c = "".concat(n.tagOpener, "/math").concat(n.tagCloser), d = t.indexOf(s), u = 0; - 1 !== d;) {
                                a += t.substring(u, d);
                                var m = t.indexOf(l.get("imageMathmlAttribute"));
                                if (-1 === (u = t.indexOf(c, d)) ? u = t.length - 1 : u += -1 !== m ? t.indexOf("/>", d) : c.length, o.isMathmlInAttribute(t, d) || -1 !== m) a += t.substring(d, u);
                                else {
                                    var h = t.substring(d, u);
                                    h = n.id === r.safeXmlCharacters.id ? o.safeXmlDecode(h) : o.mathMLEntities(h), a += w.createObjectCode(e.mathmlToImgObject(document, h, null, i))
                                }
                                d = t.indexOf(s, u)
                            }
                            return a += t.substring(u, t.length)
                        }
                    }], (n = null) && T(t.prototype, n), i && T(t, i), e
                }();
                if ("undefined" != typeof MutationObserver) {
                    var j = new MutationObserver((function(e) {
                        e.forEach((function(e) {
                            e.oldValue === l.get("imageClassName") && "class" === e.attributeName && -1 === e.target.className.indexOf(l.get("imageClassName")) && (e.target.className = l.get("imageClassName"))
                        }))
                    }));
                    E.observer = Object.create(j), E.observer.Config = {
                        attributes: !0,
                        attributeOldValue: !0
                    }, E.observer.observe = function(e) {
                        Object.getPrototypeOf(this).observe(e, this.Config)
                    }
                }

                function P(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var S = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), this.isContentChanged = !1, this.waitingForChanges = !1
                    }
                    var t, n, i;
                    return t = e, (n = [{
                        key: "setIsContentChanged",
                        value: function(e) {
                            this.isContentChanged = e
                        }
                    }, {
                        key: "getIsContentChanged",
                        value: function() {
                            return this.isContentChanged
                        }
                    }, {
                        key: "setWaitingForChanges",
                        value: function(e) {
                            this.waitingForChanges = e
                        }
                    }, {
                        key: "caretPositionChanged",
                        value: function(e) {}
                    }, {
                        key: "clipboardChanged",
                        value: function(e) {}
                    }, {
                        key: "contentChanged",
                        value: function(e) {
                            !0 === this.waitingForChanges && !1 === this.isContentChanged && (this.isContentChanged = !0)
                        }
                    }, {
                        key: "styleChanged",
                        value: function(e) {}
                    }, {
                        key: "transformationReceived",
                        value: function(e) {}
                    }]) && P(t.prototype, n), i && P(t, i), e
                }();

                function I(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var O = function() {
                    function e(t) {
                        if (function(e, t) {
                                if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                            }(this, e), this.editorAttributes = {}, !("editorAttributes" in t)) throw new Error("ContentManager constructor error: editorAttributes property missed.");
                        if (this.editorAttributes = t.editorAttributes, this.customEditors = null, "customEditors" in t && (this.customEditors = t.customEditors), this.environment = {}, !("environment" in t)) throw new Error("ContentManager constructor error: environment property missed");
                        if (this.environment = t.environment, this.language = "", !("language" in t)) throw new Error("ContentManager constructor error: language property missed");
                        this.language = t.language, this.editorListener = new S, this.editor = null, this.ua = navigator.userAgent.toLowerCase(), this.deviceProperties = {}, this.deviceProperties.isAndroid = this.ua.indexOf("android") > -1, this.deviceProperties.isIOS = e.isIOS(), this.toolbar = null, this.modalDialogInstance = null, this.listeners = new m, this.mathML = null, this.isNewElement = !0, this.integrationModel = null
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "setHrefToAnchorElement",
                        value: function(e, t) {
                            e.href = t
                        }
                    }, {
                        key: "setProtocolToAnchorElement",
                        value: function(e) {
                            0 === window.location.href.indexOf("https://") && "http:" === e.protocol && (e.protocol = "https:")
                        }
                    }, {
                        key: "getURLFromAnchorElement",
                        value: function(e) {
                            var t = "80" === e.port || "443" === e.port || "" === e.port;
                            return "".concat(e.protocol, "//").concat(e.hostname).concat(t ? "" : ":".concat(e.port)).concat(e.pathname.startsWith("/") ? e.pathname : "/".concat(e.pathname))
                        }
                    }, {
                        key: "isIOS",
                        value: function() {
                            return ["iPad Simulator", "iPhone Simulator", "iPod Simulator", "iPad", "iPhone", "iPod"].includes(navigator.platform) || navigator.userAgent.includes("Mac") && "ontouchend" in document
                        }
                    }, {
                        key: "isEditorLoaded",
                        value: function() {
                            return window.com && window.com.wiris && window.com.wiris.jsEditor && window.com.wiris.jsEditor.JsEditor && window.com.wiris.jsEditor.JsEditor.newInstance
                        }
                    }], (n = [{
                        key: "addListener",
                        value: function(e) {
                            this.listeners.add(e)
                        }
                    }, {
                        key: "setIntegrationModel",
                        value: function(e) {
                            this.integrationModel = e
                        }
                    }, {
                        key: "setModalDialogInstance",
                        value: function(e) {
                            this.modalDialogInstance = e
                        }
                    }, {
                        key: "insert",
                        value: function() {
                            this.updateTitle(this.modalDialogInstance), this.insertEditor(this.modalDialogInstance)
                        }
                    }, {
                        key: "insertEditor",
                        value: function() {
                            if (e.isEditorLoaded()) {
                                if (this.editor = window.com.wiris.jsEditor.JsEditor.newInstance(this.editorAttributes), this.editor.insertInto(this.modalDialogInstance.contentContainer), this.editor.focus(), this.modalDialogInstance.rtl && this.editor.action("rtl"), this.editor.getEditorModel().isRTL() && (this.editor.element.style.direction = "rtl"), this.editor.getEditorModel().addEditorListener(this.editorListener), this.modalDialogInstance.deviceProperties.isIOS) {
                                    setTimeout((function() {
                                        this.hasOwnProperty("modalDialogInstance") && this.modalDialogInstance.hideKeyboard()
                                    }), 400);
                                    var t = document.getElementsByClassName("wrs_formulaDisplay")[0];
                                    w.addEvent(t, "focus", this.modalDialogInstance.handleOpenedIosSoftkeyboard), w.addEvent(t, "blur", this.modalDialogInstance.handleClosedIosSoftkeyboard)
                                }
                                this.listeners.fire("onLoad", {})
                            } else setTimeout(e.prototype.insertEditor.bind(this), 100)
                        }
                    }, {
                        key: "init",
                        value: function() {
                            e.isEditorLoaded() || this.addEditorAsExternalDependency()
                        }
                    }, {
                        key: "addEditorAsExternalDependency",
                        value: function() {
                            var t = document.createElement("script");
                            t.type = "text/javascript";
                            var n = l.get("editorUrl"),
                                i = document.createElement("a");
                            e.setHrefToAnchorElement(i, n), e.setProtocolToAnchorElement(i), n = e.getURLFromAnchorElement(i);
                            var r = this.getEditorStats();
                            t.src = "".concat(n, "?lang=").concat(this.language, "&stats-editor=").concat(r.editor, "&stats-mode=").concat(r.mode, "&stats-version=").concat(r.version), document.getElementsByTagName("head")[0].appendChild(t)
                        }
                    }, {
                        key: "getEditorStats",
                        value: function() {
                            var e = {};
                            return "editor" in this.environment ? e.editor = this.environment.editor : e.editor = "unknown", "mode" in this.environment ? e.mode = this.environment.mode : e.mode = l.get("saveMode"), "version" in this.environment ? e.version = this.environment.version : e.version = l.get("version"), e
                        }
                    }, {
                        key: "setInitialContent",
                        value: function() {
                            this.isNewElement || this.setMathML(this.mathML)
                        }
                    }, {
                        key: "setMathML",
                        value: function(e, t) {
                            var n = this;
                            void 0 === t && (t = !1), this.editor.setMathMLWithCallback(e, (function() {
                                n.editorListener.setWaitingForChanges(!0)
                            })), setTimeout((function() {
                                n.editorListener.setIsContentChanged(!1)
                            }), 500), t || this.onFocus()
                        }
                    }, {
                        key: "onFocus",
                        value: function() {
                            void 0 !== this.editor && null != this.editor && this.editor.focus()
                        }
                    }, {
                        key: "submitAction",
                        value: function() {
                            if (this.editor.isFormulaEmpty()) this.integrationModel.updateFormula(null);
                            else {
                                var e = this.editor.getMathMLWithSemantics();
                                if (null !== this.customEditors.getActiveEditor()) {
                                    var t = this.customEditors.getActiveEditor().toolbar;
                                    e = o.addCustomEditorClassAttribute(e, t)
                                } else Object.keys(this.customEditors.editors).forEach((function(t) {
                                    e = o.removeCustomEditorClassAttribute(e, t)
                                }));
                                var n = o.mathMLEntities(e);
                                this.integrationModel.updateFormula(n)
                            }
                            this.customEditors.disable(), this.integrationModel.notifyWindowClosed(), this.setEmptyMathML(), this.customEditors.disable()
                        }
                    }, {
                        key: "setEmptyMathML",
                        value: function() {
                            this.deviceProperties.isAndroid || this.deviceProperties.isIOS ? this.editor.getEditorModel().isRTL() ? this.setMathML('<math dir="rtl"><semantics><annotation encoding="application/json">[]</annotation></semantics></math>', !0) : this.setMathML('<math><semantics><annotation encoding="application/json">[]</annotation></semantics></math>', !0) : this.editor.getEditorModel().isRTL() ? this.setMathML('<math dir="rtl"/>', !0) : this.setMathML("<math/>", !0)
                        }
                    }, {
                        key: "onOpen",
                        value: function() {
                            this.isNewElement ? this.setEmptyMathML() : this.setMathML(this.mathML), this.updateToolbar(), this.onFocus()
                        }
                    }, {
                        key: "updateToolbar",
                        value: function() {
                            this.updateTitle(this.modalDialogInstance);
                            var e = this.customEditors.getActiveEditor();
                            if (e) {
                                var t = e.toolbar ? e.toolbar : _wrs_int_wirisProperties.toolbar;
                                null != this.toolbar && this.toolbar === t || this.setToolbar(t)
                            } else {
                                var n = this.getToolbar();
                                null != this.toolbar && this.toolbar === n || (this.setToolbar(n), this.customEditors.disable())
                            }
                        }
                    }, {
                        key: "updateTitle",
                        value: function() {
                            var e = this.customEditors.getActiveEditor();
                            e ? this.modalDialogInstance.setTitle(e.title) : this.modalDialogInstance.setTitle("MathType")
                        }
                    }, {
                        key: "getToolbar",
                        value: function() {
                            var e = "general";
                            return "toolbar" in this.editorAttributes && (e = this.editorAttributes.toolbar), "general" === e && (e = "undefined" == typeof _wrs_int_wirisProperties || void 0 === _wrs_int_wirisProperties.toolbar ? "general" : _wrs_int_wirisProperties.toolbar), e
                        }
                    }, {
                        key: "setToolbar",
                        value: function(e) {
                            this.toolbar = e, this.editor.setParams({
                                toolbar: this.toolbar
                            })
                        }
                    }, {
                        key: "hasChanges",
                        value: function() {
                            return !this.editor.isFormulaEmpty() && this.editorListener.getIsContentChanged()
                        }
                    }, {
                        key: "onKeyDown",
                        value: function(e) {
                            if (void 0 !== e.key && !1 === e.repeat)
                                if ("Escape" === e.key || "Esc" === e.key) {
                                    var t = document.getElementsByClassName("wrs_expandButton wrs_expandButtonFor3RowsLayout wrs_pressed");
                                    0 === t.length && 0 === (t = document.getElementsByClassName("wrs_expandButton wrs_expandButtonFor2RowsLayout wrs_pressed")).length && 0 === (t = document.getElementsByClassName("wrs_select wrs_pressed")).length && (this.modalDialogInstance.cancelAction(), e.stopPropagation(), e.preventDefault())
                                } else if (e.shiftKey && "Tab" === e.key)
                                if (document.activeElement === this.modalDialogInstance.submitButton) this.editor.focus(), e.stopPropagation(), e.preventDefault();
                                else {
                                    var n = document.querySelector('[title="Manual"]');
                                    document.activeElement === n && (this.modalDialogInstance.cancelButton.focus(), e.stopPropagation(), e.preventDefault())
                                }
                            else "Tab" === e.key && (document.activeElement === this.modalDialogInstance.cancelButton ? (document.querySelector('[title="Manual"]').focus(), e.stopPropagation(), e.preventDefault()) : "wrs_formulaDisplay wrs_focused" === document.getElementsByClassName("wrs_formulaDisplay")[0].getAttribute("class") && (this.modalDialogInstance.submitButton.focus(), e.stopPropagation(), e.preventDefault()))
                        }
                    }]) && I(t.prototype, n), i && I(t, i), e
                }();

                function z(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var L = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), this.editors = [], this.activeEditor = "default"
                    }
                    var t, n, i;
                    return t = e, (n = [{
                        key: "addEditor",
                        value: function(e, t) {
                            var n = {};
                            n.name = t.name, n.toolbar = t.toolbar, n.icon = t.icon, n.confVariable = t.confVariable, n.title = t.title, n.tooltip = t.tooltip, this.editors[e] = n
                        }
                    }, {
                        key: "enable",
                        value: function(e) {
                            this.activeEditor = e
                        }
                    }, {
                        key: "disable",
                        value: function() {
                            this.activeEditor = "default"
                        }
                    }, {
                        key: "getActiveEditor",
                        value: function() {
                            return "default" !== this.activeEditor ? this.editors[this.activeEditor] : null
                        }
                    }]) && z(t.prototype, n), i && z(t, i), e
                }();
                const B = {
                    imageCustomEditorName: "data-custom-editor",
                    imageClassName: "Wirisformula",
                    CASClassName: "Wiriscas"
                };

                function N(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var D = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), this.cancelled = !1, this.defaultPrevented = !1
                    }
                    var t, n, i;
                    return t = e, (n = [{
                        key: "cancel",
                        value: function() {
                            this.cancelled = !0
                        }
                    }, {
                        key: "preventDefault",
                        value: function() {
                            this.defaultPrevented = !0
                        }
                    }]) && N(t.prototype, n), i && N(t, i), e
                }();

                function F(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var R, U = function() {
                        function e(t) {
                            ! function(e, t) {
                                if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                            }(this, e), this.overlayElement = t.overlayElement, this.callbacks = t.callbacks, this.overlayWrapper = this.overlayElement.appendChild(document.createElement("div")), this.overlayWrapper.setAttribute("class", "wrs_popupmessage_overlay_envolture"), this.message = this.overlayWrapper.appendChild(document.createElement("div")), this.message.id = "wrs_popupmessage", this.message.setAttribute("class", "wrs_popupmessage_panel"), this.message.setAttribute("role", "dialog"), this.message.setAttribute("aria-describedby", "description_txt");
                            var n = document.createElement("p"),
                                i = document.createTextNode(t.strings.message);
                            n.appendChild(i), n.id = "description_txt", this.message.appendChild(n);
                            var r = this.overlayWrapper.appendChild(document.createElement("div"));
                            r.setAttribute("class", "wrs_popupmessage_overlay"), r.addEventListener("click", this.cancelAction.bind(this)), this.buttonArea = this.message.appendChild(document.createElement("div")), this.buttonArea.setAttribute("class", "wrs_popupmessage_button_area"), this.buttonArea.id = "wrs_popup_button_area";
                            var a = {
                                class: "wrs_button_accept",
                                innerHTML: t.strings.submitString,
                                id: "wrs_popup_accept_button"
                            };
                            this.closeButton = this.createButton(a, this.closeAction.bind(this)), this.buttonArea.appendChild(this.closeButton);
                            var o = {
                                class: "wrs_button_cancel",
                                innerHTML: t.strings.cancelString,
                                id: "wrs_popup_cancel_button"
                            };
                            this.cancelButton = this.createButton(o, this.cancelAction.bind(this)), this.buttonArea.appendChild(this.cancelButton)
                        }
                        var t, n, i;
                        return t = e, (n = [{
                            key: "createButton",
                            value: function(e, t) {
                                var n = {};
                                return (n = document.createElement("button")).setAttribute("id", e.id), n.setAttribute("class", e.class), n.innerHTML = e.innerHTML, n.addEventListener("click", t), n
                            }
                        }, {
                            key: "show",
                            value: function() {
                                "block" !== this.overlayWrapper.style.display ? (document.activeElement.blur(), this.overlayWrapper.style.display = "block", this.closeButton.focus()) : this.overlayWrapper.style.display = "none"
                            }
                        }, {
                            key: "cancelAction",
                            value: function() {
                                this.overlayWrapper.style.display = "none", void 0 !== this.callbacks.cancelCallback && this.callbacks.cancelCallback()
                            }
                        }, {
                            key: "closeAction",
                            value: function() {
                                this.cancelAction(), void 0 !== this.callbacks.closeCallback && this.callbacks.closeCallback()
                            }
                        }, {
                            key: "onKeyDown",
                            value: function(e) {
                                void 0 !== e.key && ("Escape" === e.key || "Esc" === e.key ? (this.cancelAction(), e.stopPropagation(), e.preventDefault()) : "Tab" === e.key && (document.activeElement === this.closeButton ? this.cancelButton.focus() : this.closeButton.focus(), e.stopPropagation(), e.preventDefault()))
                            }
                        }]) && F(t.prototype, n), i && F(t, i), e
                    }(),
                    X = new Uint8Array(16);

                function H() {
                    if (!R && !(R = "undefined" != typeof crypto && crypto.getRandomValues && crypto.getRandomValues.bind(crypto) || "undefined" != typeof msCrypto && "function" == typeof msCrypto.getRandomValues && msCrypto.getRandomValues.bind(msCrypto))) throw new Error("crypto.getRandomValues() not supported. See https://github.com/uuidjs/uuid#getrandomvalues-not-supported");
                    return R(X)
                }
                const W = /^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}|00000000-0000-0000-0000-000000000000)$/i;
                const V = function(e) {
                    return "string" == typeof e && W.test(e)
                };
                for (var J = [], K = 0; K < 256; ++K) J.push((K + 256).toString(16).substr(1));
                const Q = function(e) {
                    var t = arguments.length > 1 && void 0 !== arguments[1] ? arguments[1] : 0,
                        n = (J[e[t + 0]] + J[e[t + 1]] + J[e[t + 2]] + J[e[t + 3]] + "-" + J[e[t + 4]] + J[e[t + 5]] + "-" + J[e[t + 6]] + J[e[t + 7]] + "-" + J[e[t + 8]] + J[e[t + 9]] + "-" + J[e[t + 10]] + J[e[t + 11]] + J[e[t + 12]] + J[e[t + 13]] + J[e[t + 14]] + J[e[t + 15]]).toLowerCase();
                    if (!V(n)) throw TypeError("Stringified UUID is invalid");
                    return n
                };
                const Y = function(e, t, n) {
                    var i = (e = e || {}).random || (e.rng || H)();
                    if (i[6] = 15 & i[6] | 64, i[8] = 63 & i[8] | 128, t) {
                        n = n || 0;
                        for (var r = 0; r < 16; ++r) t[n + r] = i[r];
                        return t
                    }
                    return Q(i)
                };

                function q(e, t) {
                    return function(e) {
                        if (Array.isArray(e)) return e
                    }(e) || function(e, t) {
                        var n = null == e ? null : "undefined" != typeof Symbol && e[Symbol.iterator] || e["@@iterator"];
                        if (null == n) return;
                        var i, r, a = [],
                            o = !0,
                            s = !1;
                        try {
                            for (n = n.call(e); !(o = (i = n.next()).done) && (a.push(i.value), !t || a.length !== t); o = !0);
                        } catch (e) {
                            s = !0, r = e
                        } finally {
                            try {
                                o || null == n.return || n.return()
                            } finally {
                                if (s) throw r
                            }
                        }
                        return a
                    }(e, t) || Z(e, t) || function() {
                        throw new TypeError("Invalid attempt to destructure non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.")
                    }()
                }

                function Z(e, t) {
                    if (e) {
                        if ("string" == typeof e) return G(e, t);
                        var n = Object.prototype.toString.call(e).slice(8, -1);
                        return "Object" === n && e.constructor && (n = e.constructor.name), "Map" === n || "Set" === n ? Array.from(e) : "Arguments" === n || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n) ? G(e, t) : void 0
                    }
                }

                function G(e, t) {
                    (null == t || t > e.length) && (t = e.length);
                    for (var n = 0, i = new Array(t); n < t; n++) i[n] = e[n];
                    return i
                }

                function $(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var ee = "wiris_telemetry_mathtype_web_senderid",
                    te = function() {
                        function e() {
                            throw function(e, t) {
                                if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                            }(this, e), new Error("Static class StringManager can not be instantiated.")
                        }
                        var t, n, i;
                        return t = e, i = [{
                            key: "senderId",
                            get: function() {
                                if (!this._senderId) {
                                    var t, n = function(e, t) {
                                        var n = "undefined" != typeof Symbol && e[Symbol.iterator] || e["@@iterator"];
                                        if (!n) {
                                            if (Array.isArray(e) || (n = Z(e)) || t && e && "number" == typeof e.length) {
                                                n && (e = n);
                                                var i = 0,
                                                    r = function() {};
                                                return {
                                                    s: r,
                                                    n: function() {
                                                        return i >= e.length ? {
                                                            done: !0
                                                        } : {
                                                            done: !1,
                                                            value: e[i++]
                                                        }
                                                    },
                                                    e: function(e) {
                                                        throw e
                                                    },
                                                    f: r
                                                }
                                            }
                                            throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.")
                                        }
                                        var a, o = !0,
                                            s = !1;
                                        return {
                                            s: function() {
                                                n = n.call(e)
                                            },
                                            n: function() {
                                                var e = n.next();
                                                return o = e.done, e
                                            },
                                            e: function(e) {
                                                s = !0, a = e
                                            },
                                            f: function() {
                                                try {
                                                    o || null == n.return || n.return()
                                                } finally {
                                                    if (s) throw a
                                                }
                                            }
                                        }
                                    }(document.cookie.split(";").map((function(e) {
                                        return e.trim().split("=")
                                    })));
                                    try {
                                        for (n.s(); !(t = n.n()).done;) {
                                            var i = q(t.value, 2),
                                                r = i[0],
                                                a = i[1];
                                            if (r === ee) {
                                                this._senderId = a;
                                                break
                                            }
                                        }
                                    } catch (e) {
                                        n.e(e)
                                    } finally {
                                        n.f()
                                    }
                                    this._senderId || (this._senderId = e.composeUUID(), document.cookie = this.composeCookie(ee, this._senderId, 31536e4))
                                }
                                return this._senderId
                            }
                        }, {
                            key: "sessionId",
                            get: function() {
                                return this._sessionId || (this._sessionId = e.composeUUID()), this._sessionId
                            }
                        }, {
                            key: "send",
                            value: function(t) {
                                var n = {
                                    method: "POST",
                                    cache: "no-cache",
                                    headers: {
                                        "Content-Type": "application/json",
                                        "X-Api-Key": "CJ20op1pOx2LAUjPFP7kB2UPveHZRidG51UJE26m",
                                        "Accept-Version": "1"
                                    },
                                    body: JSON.stringify(e.composeBody(t))
                                };
                                return fetch(e.endpoint, n).then((function(e) {
                                    return e
                                })).catch((function(e) {
                                    console.warn(e)
                                }))
                            }
                        }, {
                            key: "session",
                            get: function() {
                                return {
                                    id: e.sessionId,
                                    page: 0
                                }
                            }
                        }, {
                            key: "sender",
                            get: function() {
                                return {
                                    id: e.senderId,
                                    os: navigator.oscpu,
                                    user_agent: window.navigator.userAgent,
                                    domain: "localhost",
                                    deployment: e.deployment,
                                    editor_version: WirisPlugin.currentInstance.environment.editorVersion ? WirisPlugin.currentInstance.environment.editorVersion : "",
                                    language: WirisPlugin.currentInstance.language,
                                    product_version: WirisPlugin.currentInstance.version,
                                    backend: WirisPlugin.currentInstance.serviceProviderProperties.server ? WirisPlugin.currentInstance.serviceProviderProperties.server : ""
                                }
                            }
                        }, {
                            key: "deployment",
                            get: function() {
                                var e = WirisPlugin.currentInstance.environment.editor,
                                    t = "";
                                return /Generic/.test(e) ? t = "generic" : /Froala/.test(e) ? t = "froala" : /CKEditor/.test(e) ? t = "ckeditor" : /TinyMCE/.test(e) && (t = "tinymce"), "".concat("mathtype-web-plugin-").concat(t)
                            }
                        }, {
                            key: "composeBody",
                            value: function(t) {
                                return {
                                    messages: t,
                                    sender: e.sender,
                                    session: e.session
                                }
                            }
                        }, {
                            key: "composeUUID",
                            value: function() {
                                return Y()
                            }
                        }, {
                            key: "composeSenderUUID",
                            value: function() {
                                return this.composeUUID()
                            }
                        }, {
                            key: "composeCookie",
                            value: function(e, t, n) {
                                var i = null == n ? "" : "; max-age=".concat(n);
                                return "".concat(e, "=").concat(t).concat(i)
                            }
                        }], (n = null) && $(t.prototype, n), i && $(t, i), e
                    }();

                function ne(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                te.endpoint = "https://tl.nvppndw.lizeedu.com.br", te._senderId = "", te._sessionId = "";
                var ie = function() {
                    function e(t) {
                        var n = this;
                        if (function(e, t) {
                                if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                            }(this, e), this.language = "en", this.serviceProviderProperties = {}, "serviceProviderProperties" in t && (this.serviceProviderProperties = t.serviceProviderProperties), this.configurationService = "", "configurationService" in t && (this.serviceProviderProperties.URI = t.configurationService, console.warn("Deprecated property configurationService. Use serviceParameters on instead.", [t.configurationService])), this.version = "version" in t ? t.version : "", this.target = null, !("target" in t)) throw new Error("IntegrationModel constructor error: target property missed.");
                        this.target = t.target, "scriptName" in t && (this.scriptName = t.scriptName), this.callbackMethodArguments = {}, "callbackMethodArguments" in t && (this.callbackMethodArguments = t.callbackMethodArguments), this.environment = {}, "environment" in t && (this.environment = t.environment), this.isIframe = !1, null != this.target && (this.isIframe = "IFRAME" === this.target.tagName.toUpperCase()), this.editorObject = null, "editorObject" in t && (this.editorObject = t.editorObject), this.rtl = !1, "rtl" in t && (this.rtl = t.rtl), this.managesLanguage = !1, "managesLanguage" in t && (this.managesLanguage = t.managesLanguage), this.temporalImageResizing = !1, this.core = null, this.listeners = new m, "integrationParameters" in t && e.integrationParameters.forEach((function(e) {
                            if (e in t.integrationParameters) {
                                var i = t.integrationParameters[e];
                                0 !== Object.keys(i).length && (n[e] = i)
                            }
                        }))
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "setTemporalImageToNull",
                        value: function() {
                            WirisPlugin.currentInstance && (WirisPlugin.currentInstance.core.editionProperties.temporalImage = null);
                            var e = WirisPlugin.currentInstance,
                                t = e.getSelection();
                            if (t.removeAllRanges(), e.core.editionProperties.range) {
                                var n = e.core.editionProperties.range;
                                e.core.editionProperties.range = null, t.addRange(n)
                            }
                        }
                    }], (n = [{
                        key: "init",
                        value: function() {
                            var e = this;
                            this.language = this.getLanguage();
                            var t = m.newListener("onLoad", (function() {
                                e.callbackFunction(e.callbackMethodArguments)
                            }));
                            if (-1 !== this.serviceProviderProperties.URI.indexOf("configuration")) {
                                var n = this.serviceProviderProperties.URI,
                                    i = g.getServerLanguageFromService(n);
                                this.serviceProviderProperties.server = i;
                                var r = this.serviceProviderProperties.URI.indexOf("configuration"),
                                    a = this.serviceProviderProperties.URI.substring(0, r);
                                this.serviceProviderProperties.URI = a
                            }
                            var o = this.serviceProviderProperties.URI;
                            o = 0 === o.indexOf("/") || 0 === o.indexOf("http") ? o : w.concatenateUrl(this.getPath(), o), this.serviceProviderProperties.URI = o;
                            var s = {};
                            s.serviceProviderProperties = this.serviceProviderProperties, this.setCore(new fe(s)), this.core.addListener(t), this.core.language = this.language, this.core.init(), this.core.setEnvironment(this.environment)
                        }
                    }, {
                        key: "getPath",
                        value: function() {
                            if (void 0 === this.scriptName) throw new Error("scriptName property needed for getPath.");
                            for (var e = document.getElementsByTagName("script"), t = "", n = 0; n < e.length; n += 1) {
                                var i = e[n].src.lastIndexOf(this.scriptName);
                                i >= 0 && (t = e[n].src.substr(0, i - 1))
                            }
                            return t
                        }
                    }, {
                        key: "getVersion",
                        value: function() {
                            return this.version
                        }
                    }, {
                        key: "setLanguage",
                        value: function(e) {
                            this.language = e
                        }
                    }, {
                        key: "setCore",
                        value: function(e) {
                            this.core = e, e.setIntegrationModel(this)
                        }
                    }, {
                        key: "getCore",
                        value: function() {
                            return this.core
                        }
                    }, {
                        key: "setTarget",
                        value: function(e) {
                            this.target = e, this.isIframe = "IFRAME" === this.target.tagName.toUpperCase()
                        }
                    }, {
                        key: "setEditorObject",
                        value: function(e) {
                            this.editorObject = e
                        }
                    }, {
                        key: "openNewFormulaEditor",
                        value: function() {
                            this.core.editionProperties.isNewElement = !0, this.core.openModalDialog(this.target, this.isIframe)
                        }
                    }, {
                        key: "openExistingFormulaEditor",
                        value: function() {
                            this.core.editionProperties.isNewElement = !1, this.core.openModalDialog(this.target, this.isIframe)
                        }
                    }, {
                        key: "updateFormula",
                        value: function(e) {
                            var t, n;
                            this.editorParameters && (e = com.wiris.editor.util.EditorUtils.addAnnotation(e, "application/vnd.wiris.mtweb-params+json", JSON.stringify(this.editorParameters))), this.isIframe ? (t = this.target.contentWindow, n = this.target.contentWindow) : (t = this.target, n = window);
                            var i = this.core.beforeUpdateFormula(e, null);
                            return i && (i = this.insertFormula(t, n, i.mathml, i.wirisProperties)) ? this.core.afterUpdateFormula(i.focusElement, i.windowTarget, i.node, i.latex) : ""
                        }
                    }, {
                        key: "insertFormula",
                        value: function(e, t, n, i) {
                            return this.core.insertFormula(e, t, n, i)
                        }
                    }, {
                        key: "getSelection",
                        value: function() {
                            return this.isIframe ? (this.target.contentWindow.focus(), this.target.contentWindow.getSelection()) : (this.target.focus(), window.getSelection())
                        }
                    }, {
                        key: "addEvents",
                        value: function() {
                            var e = this,
                                t = this.isIframe ? this.target.contentWindow.document : this.target;
                            w.addElementEvents(t, (function(t, n) {
                                e.doubleClickHandler(t, n)
                            }), (function(t, n) {
                                e.mousedownHandler(t, n)
                            }), (function(t, n) {
                                e.mouseupHandler(t, n)
                            }))
                        }
                    }, {
                        key: "doubleClickHandler",
                        value: function(e) {
                            if ("img" === e.nodeName.toLowerCase()) {
                                this.core.getCustomEditors().disable();
                                var t = l.get("imageCustomEditorName");
                                if (e.hasAttribute(t)) {
                                    var n = e.getAttribute(t);
                                    this.core.getCustomEditors().enable(n)
                                }
                                w.containsClass(e, l.get("imageClassName")) && (this.core.editionProperties.temporalImage = e, this.core.editionProperties.isNewElement = !0, this.openExistingFormulaEditor())
                            }
                        }
                    }, {
                        key: "mouseupHandler",
                        value: function() {
                            var e = this;
                            this.temporalImageResizing && setTimeout((function() {
                                k.fixAfterResize(e.temporalImageResizing)
                            }), 10)
                        }
                    }, {
                        key: "mousedownHandler",
                        value: function(e) {
                            "img" === e.nodeName.toLowerCase() && w.containsClass(e, l.get("imageClassName")) && (this.temporalImageResizing = e)
                        }
                    }, {
                        key: "getLanguage",
                        value: function() {
                            return this.getBrowserLanguage()
                        }
                    }, {
                        key: "getBrowserLanguage",
                        value: function() {
                            return navigator.userLanguage ? navigator.userLanguage.substring(0, 2) : navigator.language ? navigator.language.substring(0, 2) : "en"
                        }
                    }, {
                        key: "callbackFunction",
                        value: function() {
                            var e = this,
                                t = m.newListener("onTargetReady", (function() {
                                    e.addEvents(e.target)
                                }));
                            this.listeners.add(t)
                        }
                    }, {
                        key: "notifyWindowClosed",
                        value: function() {}
                    }, {
                        key: "getMathmlFromTextNode",
                        value: function(e, t) {}
                    }, {
                        key: "fillNonLatexNode",
                        value: function(e, t, n) {}
                    }, {
                        key: "getSelectedItem",
                        value: function(e, t) {}
                    }]) && ne(t.prototype, n), i && ne(t, i), e
                }();
                ie.prototype.getMathmlFromTextNode = void 0, ie.prototype.fillNonLatexNode = void 0, ie.prototype.getSelectedItem = void 0, ie.integrationParameters = ["serviceProviderProperties", "editorParameters"];
                const re = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg3813"\n   version="1.1">\n  <metadata\n     id="metadata3819">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs3817" />\n  <image\n     y="0"\n     x="0"\n     id="image3821"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAACXBIWXMAAC4jAAAuIwF4pT92AAAA\nnUlEQVRYw+3Z0QnCMBSF4T/FATqCG1g3cISO0NE6iiPoCE5gneD40ohPvgkJ/AcC9/EjHELgliT0\nkoGOIlasWLFixYoVK1asWLFixYoVK1bsjxy+5hlYgLEx47ofSEKSJW1nTUJJMgLPDlpwHoCpk8rO\nvgZixf4Zu3Vi3cq+WroBp4ahL+BYa3AB7o1CH7vvc7M1U4N/g2sdSk8bxjfDaMNdr+hmAQAAAABJ\nRU5ErkJggg==\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n',
                    ae = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg32"\n   version="1.1">\n  <metadata\n     id="metadata38">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs36" />\n  <image\n     y="0"\n     x="0"\n     id="image40"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAACXBIWXMAAC4jAAAuIwF4pT92AAAA\npklEQVRYw+3ZLQ4CMRCG4bcbFOvXg99T7FG4BafAw1VALx7dWyy2mIoGgSOZJu/n6p70ZybppFIK\nvWSgo4gVK1asWLFixYoVK1asWLFixYoV+yO7r/UMHIAxiO8FZGBrsUfgDEwBN/QNXIA11S/PW1Bo\nCz4N9ein4Nd1Dyw9PbDR0iVW7J+xudax6HkOtZVdg0MfQE7N0G4GlmANYgNW4A6QepowfgDMXB26\nb1V6LAAAAABJRU5ErkJggg==\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n';

                function oe(e, t) {
                    if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                }

                function se(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }

                function le(e, t, n) {
                    return t && se(e.prototype, t), n && se(e, n), e
                }
                var ce = function() {
                    function e(t) {
                        var n = this;
                        oe(this, e), this.attributes = t;
                        var i = navigator.userAgent.toLowerCase(),
                            r = i.indexOf("android") > -1,
                            a = O.isIOS();
                        this.iosSoftkeyboardOpened = !1, this.iosMeasureUnit = -1 === i.indexOf("crios") ? "%" : "vh", this.iosDivHeight = "100%".concat(this.iosMeasureUnit);
                        var o = window.outerWidth,
                            s = window.outerHeight,
                            l = o > s,
                            c = o < s,
                            d = l && this.attributes.height > s,
                            u = c && this.attributes.width > o,
                            m = d || u;
                        this.instanceId = document.getElementsByClassName("wrs_modal_dialogContainer").length, this.deviceProperties = {
                            orientation: l ? "landscape" : "portait",
                            isAndroid: r,
                            isIOS: a,
                            isMobile: m,
                            isDesktop: !m && !a && !r
                        }, this.properties = {
                            created: !1,
                            state: "",
                            previousState: "",
                            position: {
                                bottom: 0,
                                right: 10
                            },
                            size: {
                                height: 338,
                                width: 580
                            }
                        }, this.websiteBeforeLockParameters = null;
                        var h = {
                            class: "wrs_modal_overlay"
                        };
                        h.id = this.getElementId(h.class), this.overlay = w.createElement("div", h), (h = {}).class = "wrs_modal_title_bar", h.id = this.getElementId(h.class), this.titleBar = w.createElement("div", h), (h = {}).class = "wrs_modal_title", h.id = this.getElementId(h.class), this.title = w.createElement("div", h), this.title.innerHTML = "", (h = {}).class = "wrs_modal_close_button", h.id = this.getElementId(h.class), h.title = b.get("close"), h.style = {}, this.closeDiv = w.createElement("a", h), this.closeDiv.setAttribute("role", "button");
                        var g = "background-size: 10px; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg3783"\n   version="1.1">\n  <metadata\n     id="metadata3789">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs3787" />\n  <image\n     y="0"\n     x="0"\n     id="image3791"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAACXBIWXMAAC4jAAAuIwF4pT92AAAB\nvklEQVRYw83Z23GDMBAF0AsNhBIowSVQgjuISnAJKSEdZNOBS6CDOBUkqSC4gs2PyGhAQg92se4M\n4w8bccYW2hVumBmRdAB6ADfopQcw2SOYNoIkAL8APgB8AzgLI0/2S/iy1xkt3B9m9h0dM9/YHxM4\nJ/c4MfPkGX+y763OyYVKgUPQTXAJdC84Bg2CS6Gl4FSoF7wHmgvOhbrgzsW+8L4YJegccrEj749R\ngs7ZXGdz8wbAeNbREcDTzrHvblEgBbAUFACuy6JALJeL0E/P9sbvmBnNojcgAM+oJ58AhrlnWM5Z\nA+C9RmiokakBvIJuNTLSc7hojqY0Mo8EB6Ep2CPBm9BU7BHgKDQHqwlOguZiNcDJ0JLe4FV4iaLY\nJjF16dLqnoob+EdDs8A1QJPBtUCTwDVBo+DaoJvgNvBIR6rDl9wirbA1QIPgVgl6VwHb+dAr7Jkk\nS/Pg3mCkVOslxxV9yBFqSqTA/3N2Utkzye3pftw5OxzQ5tHeddcdzGj3o4VgClUwowgtAVOs3BpF\naA6YUnsDowhNAVNu12UUoVtgCn2+ifxp1wO42Ner4KPR5dJ2tsse2ZLvTQxbVf4AmC2z7WnSvpIA\nAAAASUVORK5CYII=\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n'), ")"),
                            p = "background-size: 10px; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg2"\n   version="1.1">\n  <metadata\n     id="metadata8">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs6" />\n  <image\n     y="0"\n     x="0"\n     id="image10"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAACXBIWXMAAC4jAAAuIwF4pT92AAAB\n2ElEQVRYw9XZoXPCMBTH8S+5KfDzQ29606CH3/SmQTO96aGHHn/F0Himh8eDZSblQknSJH2F0DtE\nQw8+12vyfulr7XY7LuW4qvj+DugD18AC+AE2woa+/mz07y9cF7Y8d7YPDEtjK2AsCB4BvdLYHPi0\nXawioAA3wAfQaQiKHhuFYl1QSbAL6gWrSKgEuArqBKsEaB1wKNQKVsasHybcpRhwLNQED0zsoMbz\nFwJOhWL6Cmzd2e0D14Wi1/k9di2wFNnAEtBifd9jv4GtIPgaeBOCAkzLFayr/6idWSSY6DJ8sHT9\n6VK6zRFqKwo5gQ+grnKbA/gI6gsy5wRboT7sucBOaBX21GAvNAR7KnAlNBTbNDgIGoMtwO/C0Gko\nNBZbN525tk+dJrAj4F4YGxXgVQS019DkCgarM0OjwCoDaDBYZQINAquMoJVglRnUC1YZQp1g1RB0\nJryn65jYJ0HoRGPHguDX8hsZ6VAiGX4eUrJBbHqSArdN7LLBmCcBnpvYWfHWo6E8Wge8Ar7Kj8E4\nARwcnBPBB20BE7uJBMdAU8BH/YvyBAsFp0BjwNZGi201qALXgYaAnR0hX2upAzwDj/p8raFL5I4u\n8ALc6vNfvc+ztq5al9Rh/AfwZZ/LmlMllAAAAABJRU5ErkJggg==\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n'), ")");
                        this.closeDiv.setAttribute("style", g), this.closeDiv.setAttribute("onmouseover", 'this.style = "'.concat(p, '";')), this.closeDiv.setAttribute("onmouseout", 'this.style = "'.concat(g, '";')), (h = {}).class = "wrs_modal_stack_button", h.id = this.getElementId(h.class), h.title = b.get("exit_fullscreen"), this.stackDiv = w.createElement("a", h), this.stackDiv.setAttribute("role", "button"), g = "background-size: 10px; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg3823"\n   version="1.1">\n  <metadata\n     id="metadata3829">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs3827" />\n  <image\n     y="0"\n     x="0"\n     id="image3831"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAAAXNSR0IArs4c6QAAAARnQU1BAACx\njwv8YQUAAAAJcEhZcwAALiMAAC4jAXilP3YAAAHOSURBVFhH1ZiLUcMwEEQNDcQl0AEuISVABZhO\nUkroICVAB6ECoINQgdmVfR5FlmQrkZzjzezEzsc8NPqcdNd1XfVfuB9ec3NAmv4yiRo5ImzBlm+c\nwZYtEHJCGsT3eSgHxKZFxs/tL+aMkCK8R3yMwu4PcsVmiXBIVDDCvh/miEtMeE5UaEsNMJcN8o64\ng26PvPSXs9S+/zRHQtgtvLRFCb9blZpnYw/9Rb6RR3M3zxtiprFbyKYwipK1+uwlnIkSrbITUaJR\n1itKtMkGRYk2WRZAQbTNBpzWtggrrwnaWja00hk0DrCgsEZZ4hXWKksmwjLAHobkgOv+V3+ZhXHQ\niWxKqXYLKNyILDdqbPKlldASPhA+Mxc7uwatkSOSix1iP//q2APshLBvfJo7hbizgQj/mDtl+KYu\nCj8h7NSqCM2zXJvZwqqEY4uCOuGYLKEwJ3kVzMlyscg5915FTFbdqhaSVbn8+mTV1gmurOqCxpZN\nEeUu9BlZd1obioTkQ7IhPGTjYZuPIoUMK/GUFrX39asuHJTlH3w1d3FCBxCrCUufZX+NCUdPSsAq\nwu4A8wnPiQrFhW1Z4govFRWKCoeOjzjoZF92CdwpZy6AquoPvJRHJxB8bJ8AAAAASUVORK5CYII=\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n'), ")"), p = "background-size: 10px; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg42"\n   version="1.1">\n  <metadata\n     id="metadata48">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs46" />\n  <image\n     y="0"\n     x="0"\n     id="image50"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAAAXNSR0IArs4c6QAAAARnQU1BAACx\njwv8YQUAAAAJcEhZcwAALiMAAC4jAXilP3YAAAG/SURBVFhH1ZgxUsMwEEUNJRyAGmp6qKGn5xRQ\nQ08NNfRQQw11DpAaanIAWrMv8WaELSlexhLLm/mRnImiF48jr7zVtm3zX9ju2ik5llxLdpdHNg4k\nT5I7yWB8Cdl9yZHkRmIRRpQxOxK+YzC+hKwSnTBBKKoMxpeUBSbkksgRE1V+CJeWhUPJ5ao7ICeq\nrIVryMKJpC88RlTZk1SThVDYIvoluZIsSqyz511SfEg4UxbRdw5qnlmFa9AsCn8hO4aBKHiUjYqC\nN9mkKHiSzYqCJ9lPSVIUPMmySqTudEu8XbOxO90ab7KQFPYoC1Fhr7IwENbagMLCUtXnoCTM1QZW\n3iS3dFT2mRfHvEjuVfZUckFnQh67dgqo1GYqC1MLn3XtZIR/sFcJW2C39FcD18KxpcutcGqddSmc\nuykg/LDq+iAnC/OudUFOVrfLbkjJWvb11YjJuhSFvqxbUQhlXYuCylpE2YXy2SkLlVEgaxVluzyT\nIEutWQ1kKZYtouF2maK4mjCyFN6bJsw9gKgmrNdsbsKNT0qEKsIqC7EJx4gqxYVDWQgntIgqRYXD\nbY3CLpcVgmdPC974BYy3/MgRNM03hR9ubFTHT48AAAAASUVORK5CYII=\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n'), ")"), this.stackDiv.setAttribute("style", g), this.stackDiv.setAttribute("onmouseover", 'this.style = "'.concat(p, '";')), this.stackDiv.setAttribute("onmouseout", 'this.style = "'.concat(g, '";')), (h = {}).class = "wrs_modal_maximize_button", h.id = this.getElementId(h.class), h.title = b.get("fullscreen"), this.maximizeDiv = w.createElement("a", h), this.maximizeDiv.setAttribute("role", "button"), g = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg3793"\n   version="1.1">\n  <metadata\n     id="metadata3799">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs3797" />\n  <image\n     y="0"\n     x="0"\n     id="image3801"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAAAXNSR0IArs4c6QAAAARnQU1BAACx\njwv8YQUAAAAJcEhZcwAALiMAAC4jAXilP3YAAAG4SURBVFhHvZnhUYNAEEbRBkwH2oGUkA40FWgJ\nKSEdaAmxA0vQDmIHKSFWgPuAHZkEAnd8y5v5kuNHMm+WY1mSm6qqCiGlZdUspXzxopY9Wu6bpZQf\nSxlRWapwVx9p2dy2CxUHy9ryWx9pKdWyECYcIQshwlGyIBeOlAWpcLQsyISXkAWEX5tlPkvJwnP7\nns1SsnvLS7PMZwlZiShEy8pEIVJWKgpRsnJRiJBNFf2wbCzjfZgRUZi9JYWDxT9bWk6WIXbKym4t\nKRVloObO5oze6ZClWX9a5jyOcOrfmuUkXPRUH/1zVRhZpvsnCxN+jnDqHh0SdQaFu9vg0ZIqrBZ1\neoXP92yKcJSocyHcd4FNEY4WdbrCR1rGrukMF9BWVhZvLZ7U9rS2nH9HVvoq63iFu+RUlOpIuCYL\nCCPIqVjq1A9j5R3aBnMY2kKzMlbZHPQVbVHLhomCUjZUFFSy35ZQUVDIMo+Gi4JCltFwERSy75Y5\n4+VkFLLcKHLHyyRUF1jOeJmMShbChZWy0Df8yFDLgg8/cpCN6I9cdHJhZHmy7X2anAnCtDUZ/j/Y\ng2X2j709MHhTDAFF8QdK9SRpUl2yFgAAAABJRU5ErkJggg==\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n'), ")"), p = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.76 13.76"\n   height="13.76"\n   width="13.76"\n   id="svg12"\n   version="1.1">\n  <metadata\n     id="metadata18">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs16" />\n  <image\n     y="0"\n     x="0"\n     id="image20"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAArCAYAAADhXXHAAAAAAXNSR0IArs4c6QAAAARnQU1BAACx\njwv8YQUAAAAJcEhZcwAALiMAAC4jAXilP3YAAAGMSURBVFhHvdk7TsNAFIVhQ0l6elLDJqCGngXQ\nU7MA6rALahZATQ81C6APrXP/jEaKHD/i8TnzS1eaICF/2I4f4qxt20bYOmaVlrK2Mb8s1Nj3mIu0\nlPYZszlPa1kvMf9pKe02Zq3Gcrhc4JUaSzawA0sWsAtLcrATS1KwG0sycA0sAd6kZXm1sNzVHtOy\nvBpYoK8xV/tPC3JjZVByYqVQcmHlUHJgLVBSY0ugPP7xO5PXYSW2FMr19ytm8sahxD7ElEBzk3c6\nsFysn/afymKPvsXMueh3oblRMNibmPuYZ34wsyWHfqhB8OFpwKvDHLADmusFd8/ZU8FOaO4I3PcF\nmwLXgOYOwVtexdnwdUy3vg2UQPnD2eji+vZsrruHS/eoBEpjWMpgrhi1Dv1gY6fBkuRQmtqzJVmg\npMbaoKTEWqGkwtqhpMBWgZICWwVKCuwpzxKSFNi5T2vFqb5gVcAqLNnBSixZwWos2cBg/9JSmgUM\n9iMt5QFe8tZ8VP6n3WXMHQtxPzHfabm0ptkBwWhpthzMp7YAAAAASUVORK5CYII=\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.76" />\n</svg>\n'), ")"), this.maximizeDiv.setAttribute("style", g), this.maximizeDiv.setAttribute("onmouseover", 'this.style = "'.concat(p, '";')), this.maximizeDiv.setAttribute("onmouseout", 'this.style = "'.concat(g, '";')), (h = {}).class = "wrs_modal_minimize_button", h.id = this.getElementId(h.class), h.title = b.get("minimize"), this.minimizeDiv = w.createElement("a", h), this.minimizeDiv.setAttribute("role", "button"), g = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa(re), ")"), p = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa(ae), ")"), this.minimizeDiv.setAttribute("style", g), this.minimizeDiv.setAttribute("onmouseover", 'this.style = "'.concat(p, '";')), this.minimizeDiv.setAttribute("onmouseout", 'this.style = "'.concat(g, '";')), (h = {}).class = "wrs_modal_dialogContainer", h.id = this.getElementId(h.class), h.role = "dialog", this.container = w.createElement("div", h), this.container.setAttribute("aria-labeledby", "wrs_modal_title[0]"), (h = {}).class = "wrs_modal_wrapper", h.id = this.getElementId(h.class), this.wrapper = w.createElement("div", h), (h = {}).class = "wrs_content_container", h.id = this.getElementId(h.class), this.contentContainer = w.createElement("div", h), (h = {}).class = "wrs_modal_controls", h.id = this.getElementId(h.class), this.controls = w.createElement("div", h), (h = {}).class = "wrs_modal_buttons_container", h.id = this.getElementId(h.class), this.buttonContainer = w.createElement("div", h), this.submitButton = this.createSubmitButton({
                            id: this.getElementId("wrs_modal_button_accept"),
                            class: "wrs_modal_button_accept",
                            innerHTML: b.get("accept")
                        }, this.submitAction.bind(this)), this.cancelButton = this.createSubmitButton({
                            id: this.getElementId("wrs_modal_button_cancel"),
                            class: "wrs_modal_button_cancel",
                            innerHTML: b.get("cancel")
                        }, this.cancelAction.bind(this)), this.contentManager = null;
                        var f = {
                                cancelString: b.get("cancel"),
                                submitString: b.get("close"),
                                message: b.get("close_modal_warning")
                            },
                            _ = {
                                closeCallback: function() {
                                    n.close()
                                },
                                cancelCallback: function() {
                                    n.focus()
                                }
                            },
                            v = {
                                overlayElement: this.container,
                                callbacks: _,
                                strings: f
                            };
                        this.popup = new U(v), this.rtl = !1, "rtl" in this.attributes && (this.rtl = this.attributes.rtl), this.handleOpenedIosSoftkeyboard = this.handleOpenedIosSoftkeyboard.bind(this), this.handleClosedIosSoftkeyboard = this.handleClosedIosSoftkeyboard.bind(this)
                    }
                    return le(e, [{
                        key: "setContentManager",
                        value: function(e) {
                            this.contentManager = e
                        }
                    }, {
                        key: "getContentManager",
                        value: function() {
                            return this.contentManager
                        }
                    }, {
                        key: "submitAction",
                        value: function() {
                            void 0 !== this.contentManager.submitAction && this.contentManager.submitAction(), this.close()
                        }
                    }, {
                        key: "cancelAction",
                        value: function() {
                            ie.setTemporalImageToNull(), void 0 === this.contentManager.hasChanges ? this.close() : this.contentManager.hasChanges() ? this.showPopUpMessage() : this.close()
                        }
                    }, {
                        key: "createSubmitButton",
                        value: function(e, t) {
                            return new(function() {
                                function n() {
                                    oe(this, n), this.element = document.createElement("button"), this.element.id = e.id, this.element.className = e.class, this.element.innerHTML = e.innerHTML, w.addEvent(this.element, "click", t)
                                }
                                return le(n, [{
                                    key: "getElement",
                                    value: function() {
                                        return this.element
                                    }
                                }]), n
                            }())(e, t).getElement()
                        }
                    }, {
                        key: "create",
                        value: function() {
                            this.titleBar.appendChild(this.closeDiv), this.titleBar.appendChild(this.stackDiv), this.titleBar.appendChild(this.maximizeDiv), this.titleBar.appendChild(this.minimizeDiv), this.titleBar.appendChild(this.title), this.deviceProperties.isDesktop && this.container.appendChild(this.titleBar), this.wrapper.appendChild(this.contentContainer), this.wrapper.appendChild(this.controls), this.controls.appendChild(this.buttonContainer), this.buttonContainer.appendChild(this.submitButton), this.buttonContainer.appendChild(this.cancelButton), this.container.appendChild(this.wrapper), this.recalculateScrollBar(), document.body.appendChild(this.container), document.body.appendChild(this.overlay), this.deviceProperties.isDesktop ? (this.createModalWindowDesktop(), this.createResizeButtons(), this.addListeners(), l.get("modalWindowFullScreen") && this.maximize()) : this.deviceProperties.isAndroid ? this.createModalWindowAndroid() : this.deviceProperties.isIOS && this.createModalWindowIos(), null != this.contentManager && this.contentManager.insert(this), this.properties.open = !0, this.properties.created = !0, this.isRTL() && (this.container.style.right = "".concat(window.innerWidth - this.scrollbarWidth - this.container.offsetWidth, "px"), this.container.className += " wrs_modal_rtl")
                        }
                    }, {
                        key: "createResizeButtons",
                        value: function() {
                            this.resizerBR = document.createElement("div"), this.resizerBR.className = "wrs_bottom_right_resizer", this.resizerBR.innerHTML = "◢", this.resizerTL = document.createElement("div"), this.resizerTL.className = "wrs_bottom_left_resizer", this.container.appendChild(this.resizerBR), this.titleBar.appendChild(this.resizerTL), w.addEvent(this.resizerBR, "mousedown", this.activateResizeStateBR.bind(this)), w.addEvent(this.resizerTL, "mousedown", this.activateResizeStateTL.bind(this))
                        }
                    }, {
                        key: "activateResizeStateBR",
                        value: function(e) {
                            this.initializeResizeProperties(e, !1)
                        }
                    }, {
                        key: "activateResizeStateTL",
                        value: function(e) {
                            this.initializeResizeProperties(e, !0)
                        }
                    }, {
                        key: "initializeResizeProperties",
                        value: function(e, t) {
                            w.addClass(document.body, "wrs_noselect"), w.addClass(this.overlay, "wrs_overlay_active"), this.resizeDataObject = {
                                x: this.eventClient(e).X,
                                y: this.eventClient(e).Y
                            }, this.initialWidth = parseInt(this.container.style.width, 10), this.initialHeight = parseInt(this.container.style.height, 10), t ? this.leftScale = !0 : (this.initialRight = parseInt(this.container.style.right, 10), this.initialBottom = parseInt(this.container.style.bottom, 10)), this.initialRight || (this.initialRight = 0), this.initialBottom || (this.initialBottom = 0), document.body.style["user-select"] = "none"
                        }
                    }, {
                        key: "open",
                        value: function() {
                            var e = this;
                            // try {
                            //     te.send([{
                            //         timestamp: (new Date).toJSON(),
                            //         topic: "0",
                            //         level: "info",
                            //         message: "HELO tl.nvppndw.lizeedu.com.br"
                            //     }]).then((function(e) {}))
                            // } catch (e) {}
                            this.removeClass("wrs_closed");
                            var t = this.deviceProperties.isIOS,
                                n = this.deviceProperties.isAndroid,
                                i = this.deviceProperties.isMobile;
                            if ((t || n || i) && (this.restoreWebsiteScale(), this.lockWebsiteScroll(), setTimeout((function() {
                                    e.hideKeyboard()
                                }), 400)), this.properties.created ? (this.properties.open || (this.properties.open = !0, this.deviceProperties.isAndroid || this.deviceProperties.isIOS || this.restoreState()), this.deviceProperties.isDesktop && l.get("modalWindowFullScreen") && this.maximize(), this.deviceProperties.isIOS && (this.iosSoftkeyboardOpened = !1, this.setContainerHeight("".concat(100 + this.iosMeasureUnit)))) : this.create(), O.isEditorLoaded()) this.contentManager.onOpen(this);
                            else {
                                var r = m.newListener("onLoad", (function() {
                                    e.contentManager.onOpen(e)
                                }));
                                this.contentManager.addListener(r)
                            }
                        }
                    }, {
                        key: "close",
                        value: function() {
                            this.removeClass("wrs_maximized"), this.removeClass("wrs_minimized"), this.removeClass("wrs_stack"), this.addClass("wrs_closed"), this.saveModalProperties(), this.unlockWebsiteScroll(), this.properties.open = !1
                        }
                    }, {
                        key: "restoreWebsiteScale",
                        value: function() {
                            var e = document.querySelector("meta[name=viewport]"),
                                t = ["initial-scale=", "minimum-scale=", "maximum-scale="],
                                n = ["1.0", "1.0", "1.0"],
                                i = function(e, t) {
                                    var i = e.getAttribute("content");
                                    if (i) {
                                        for (var r = i.split(","), a = "", o = [], s = 0; s < r.length; s += 1) {
                                            for (var l = !1, c = 0; !l && c < t.length;) r[s].indexOf(t[c]) && (l = !0), c += 1;
                                            l || o.push(r[s])
                                        }
                                        for (var d = 0; d < t.length; d += 1) {
                                            var u = t[d] + n[d];
                                            a += 0 === d ? u : ",".concat(u)
                                        }
                                        for (var m = 0; m < o.length; m += 1) a += ",".concat(o[m]);
                                        e.setAttribute("content", a), e.setAttribute("content", ""), e.setAttribute("content", i)
                                    } else e.setAttribute("content", "initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0"), e.removeAttribute("content")
                                };
                            e ? i(e, t) : (e = document.createElement("meta"), document.getElementsByTagName("head")[0].appendChild(e), i(e, t), e.remove())
                        }
                    }, {
                        key: "lockWebsiteScroll",
                        value: function() {
                            this.websiteBeforeLockParameters = {
                                bodyStylePosition: document.body.style.position ? document.body.style.position : "",
                                bodyStyleOverflow: document.body.style.overflow ? document.body.style.overflow : "",
                                htmlStyleOverflow: document.documentElement.style.overflow ? document.documentElement.style.overflow : "",
                                windowScrollX: window.scrollX,
                                windowScrollY: window.scrollY
                            }
                        }
                    }, {
                        key: "unlockWebsiteScroll",
                        value: function() {
                            if (this.websiteBeforeLockParameters) {
                                document.body.style.position = this.websiteBeforeLockParameters.bodyStylePosition, document.body.style.overflow = this.websiteBeforeLockParameters.bodyStyleOverflow, document.documentElement.style.overflow = this.websiteBeforeLockParameters.htmlStyleOverflow;
                                var e = this.websiteBeforeLockParameters.windowScrollX,
                                    t = this.websiteBeforeLockParameters.windowScrollY;
                                window.scrollTo(e, t), this.websiteBeforeLockParameters = null
                            }
                        }
                    }, {
                        key: "isIE11",
                        value: function() {
                            return navigator.userAgent.search("Msie/") >= 0 || navigator.userAgent.search("Trident/") >= 0 || navigator.userAgent.search("Edge/") >= 0
                        }
                    }, {
                        key: "isRTL",
                        value: function() {
                            return "ar" === this.attributes.language || "he" === this.attributes.language || this.rtl
                        }
                    }, {
                        key: "addClass",
                        value: function(e) {
                            w.addClass(this.overlay, e), w.addClass(this.titleBar, e), w.addClass(this.overlay, e), w.addClass(this.container, e), w.addClass(this.contentContainer, e), w.addClass(this.stackDiv, e), w.addClass(this.minimizeDiv, e), w.addClass(this.maximizeDiv, e), w.addClass(this.wrapper, e)
                        }
                    }, {
                        key: "removeClass",
                        value: function(e) {
                            w.removeClass(this.overlay, e), w.removeClass(this.titleBar, e), w.removeClass(this.overlay, e), w.removeClass(this.container, e), w.removeClass(this.contentContainer, e), w.removeClass(this.stackDiv, e), w.removeClass(this.minimizeDiv, e), w.removeClass(this.maximizeDiv, e), w.removeClass(this.wrapper, e)
                        }
                    }, {
                        key: "createModalWindowDesktop",
                        value: function() {
                            this.addClass("wrs_modal_desktop"), this.stack()
                        }
                    }, {
                        key: "createModalWindowAndroid",
                        value: function() {
                            this.addClass("wrs_modal_android"), window.addEventListener("resize", this.orientationChangeAndroidSoftkeyboard.bind(this))
                        }
                    }, {
                        key: "createModalWindowIos",
                        value: function() {
                            this.addClass("wrs_modal_ios"), window.addEventListener("resize", this.orientationChangeIosSoftkeyboard.bind(this))
                        }
                    }, {
                        key: "restoreState",
                        value: function() {
                            "maximized" === this.properties.state ? this.maximize() : "minimized" === this.properties.state ? (this.properties.state = this.properties.previousState, this.properties.previousState = "", this.minimize()) : this.stack()
                        }
                    }, {
                        key: "stack",
                        value: function() {
                            this.properties.previousState = this.properties.state, this.properties.state = "stack", this.removeClass("wrs_maximized"), this.minimizeDiv.title = b.get("minimize"), this.removeClass("wrs_minimized"), this.addClass("wrs_stack");
                            var e = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa(re), ")"),
                                t = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa(ae), ")");
                            this.minimizeDiv.setAttribute("style", e), this.minimizeDiv.setAttribute("onmouseover", 'this.style = "'.concat(t, '";')), this.minimizeDiv.setAttribute("onmouseout", 'this.style = "'.concat(e, '";')), this.restoreModalProperties(), void 0 !== this.resizerBR && void 0 !== this.resizerTL && this.setResizeButtonsVisibility(), this.recalculateScrollBar(), this.recalculatePosition(), this.recalculateScale(), this.focus()
                        }
                    }, {
                        key: "minimize",
                        value: function() {
                            if (this.saveModalProperties(), this.title.style.cursor = "pointer", "minimized" === this.properties.state && "stack" === this.properties.previousState) this.stack();
                            else if ("minimized" === this.properties.state && "maximized" === this.properties.previousState) this.maximize();
                            else {
                                this.container.style.height = "30px", this.container.style.width = "250px", this.container.style.bottom = "0px", this.container.style.right = "10px", this.removeListeners(), this.properties.previousState = this.properties.state, this.properties.state = "minimized", this.setResizeButtonsVisibility(), this.minimizeDiv.title = b.get("maximize"), w.containsClass(this.overlay, "wrs_stack") ? this.removeClass("wrs_stack") : this.removeClass("wrs_maximized"), this.addClass("wrs_minimized");
                                var e = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.44 13.76"\n   height="13.76"\n   width="13.44"\n   id="svg3803"\n   version="1.1">\n  <metadata\n     id="metadata3809">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs3807" />\n  <image\n     y="0"\n     x="0"\n     id="image3811"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAArCAYAAAAOnxr+AAAACXBIWXMAAC4jAAAuIwF4pT92AAAA\nvElEQVRYw+3ZSw0CMRSF4b8T9iAFB4wDkDAWcICEkTA4GAeAA3AADurgsCkbAgsSMrmFczZNd1/a\n3vSVJFFDGipJNdBZaRdAB2wC2TIwAgNAkrQEjsA86GBegDZJGoF18JnfJtVR9idXvaGGGmrod/b6\nV9kD14k9LbD6FDqUM8CU2b2Deo0aaqihhhpqqKGGGhr1hH/wiP469FaBMzflEhc9PZKQ1CtmsqRO\nEunpHbeNNN3A+dFJ/mf6V+gduGPIoUgKLbAAAAAASUVORK5CYII=\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.44" />\n</svg>\n'), ")"),
                                    t = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<svg\n   xmlns:dc="http://purl.org/dc/elements/1.1/"\n   xmlns:cc="http://creativecommons.org/ns#"\n   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n   xmlns:svg="http://www.w3.org/2000/svg"\n   xmlns="http://www.w3.org/2000/svg"\n   xmlns:xlink="http://www.w3.org/1999/xlink"\n   viewBox="0 0 13.44 13.76"\n   height="13.76"\n   width="13.44"\n   id="svg22"\n   version="1.1">\n  <metadata\n     id="metadata28">\n    <rdf:RDF>\n      <cc:Work\n         rdf:about="">\n        <dc:format>image/svg+xml</dc:format>\n        <dc:type\n           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />\n        <dc:title></dc:title>\n      </cc:Work>\n    </rdf:RDF>\n  </metadata>\n  <defs\n     id="defs26" />\n  <image\n     y="0"\n     x="0"\n     id="image30"\n     xlink:href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAArCAYAAAAOnxr+AAAACXBIWXMAAC4jAAAuIwF4pT92AAAA\nvUlEQVRYw+3ZsQ3CMBCF4d8WFekZgBqWIDUDZACmYBQWYIn0pGYAegZIexROERHRIBTdhXeVy08+\nyT4/JzMjQmWCVBjoarSugK0z3/0degKODjeyBy5Am8ysARrnnT8nM7sCa+fQLgdAAlQ6ngQVVFBB\nfzeUTK6t8VAwU328ztV6QQUVVFBBBRVUUEG9Ds41sJvZs/8GelDrlw7tAjhvmZLo9o6RD4bEGUp+\nX1My/I0T4HN4rrcASf9M/wp9ASNzIKYYz2hAAAAAAElFTkSuQmCC\n"\n     style="image-rendering:optimizeQuality"\n     preserveAspectRatio="none"\n     height="13.76"\n     width="13.44" />\n</svg>\n'), ")");
                                this.minimizeDiv.setAttribute("style", e), this.minimizeDiv.setAttribute("onmouseover", 'this.style = "'.concat(t, '";')), this.minimizeDiv.setAttribute("onmouseout", 'this.style = "'.concat(e, '";'))
                            }
                        }
                    }, {
                        key: "maximize",
                        value: function() {
                            this.saveModalProperties(), "maximized" !== this.properties.state && (this.properties.previousState = this.properties.state, this.properties.state = "maximized"), this.setResizeButtonsVisibility(), w.containsClass(this.overlay, "wrs_minimized") ? (this.minimizeDiv.title = b.get("minimize"), this.removeClass("wrs_minimized")) : w.containsClass(this.overlay, "wrs_stack") && (this.container.style.left = null, this.container.style.top = null, this.removeClass("wrs_stack")), this.addClass("wrs_maximized");
                            var e = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa(re), ")"),
                                t = "background-size: 10px; background-repeat: no-repeat; background-image: url(data:image/svg+xml;base64,".concat(window.btoa(ae), ")");
                            this.minimizeDiv.setAttribute("style", e), this.minimizeDiv.setAttribute("onmouseover", 'this.style = "'.concat(t, '";')), this.minimizeDiv.setAttribute("onmouseout", 'this.style = "'.concat(e, '";')), this.setSize(parseInt(.8 * window.innerHeight, 10), parseInt(.8 * window.innerWidth, 10)), this.container.clientHeight > 700 && (this.container.style.height = "700px"), this.container.clientWidth > 1200 && (this.container.style.width = "1200px");
                            var n = window.innerHeight,
                                i = window.innerWidth,
                                r = n / 2 - this.container.offsetHeight / 2,
                                a = i / 2 - this.container.offsetWidth / 2;
                            this.setPosition(r, a), this.recalculateScale(), this.recalculatePosition(), this.recalculateSize(), this.focus()
                        }
                    }, {
                        key: "reExpand",
                        value: function() {
                            "minimized" === this.properties.state && ("maximized" === this.properties.previousState ? this.maximize() : this.stack(), this.title.style.cursor = "")
                        }
                    }, {
                        key: "setSize",
                        value: function(e, t) {
                            this.container.style.height = "".concat(e, "px"), this.container.style.width = "".concat(t, "px"), this.recalculateSize()
                        }
                    }, {
                        key: "setPosition",
                        value: function(e, t) {
                            this.container.style.bottom = "".concat(e, "px"), this.container.style.right = "".concat(t, "px")
                        }
                    }, {
                        key: "saveModalProperties",
                        value: function() {
                            "stack" === this.properties.state && (this.properties.position.bottom = parseInt(this.container.style.bottom, 10), this.properties.position.right = parseInt(this.container.style.right, 10), this.properties.size.width = parseInt(this.container.style.width, 10), this.properties.size.height = parseInt(this.container.style.height, 10))
                        }
                    }, {
                        key: "restoreModalProperties",
                        value: function() {
                            "stack" === this.properties.state && (this.setPosition(this.properties.position.bottom, this.properties.position.right), this.setSize(this.properties.size.height, this.properties.size.width))
                        }
                    }, {
                        key: "recalculateSize",
                        value: function() {
                            this.wrapper.style.width = "".concat(this.container.clientWidth - 12, "px"), this.wrapper.style.height = "".concat(this.container.clientHeight - 38, "px"), this.contentContainer.style.height = "".concat(parseInt(this.wrapper.offsetHeight - 50, 10), "px")
                        }
                    }, {
                        key: "setResizeButtonsVisibility",
                        value: function() {
                            "stack" === this.properties.state ? (this.resizerTL.style.visibility = "visible", this.resizerBR.style.visibility = "visible") : (this.resizerTL.style.visibility = "hidden", this.resizerBR.style.visibility = "hidden")
                        }
                    }, {
                        key: "addListeners",
                        value: function() {
                            this.maximizeDiv.addEventListener("click", this.maximize.bind(this), !0), this.stackDiv.addEventListener("click", this.stack.bind(this), !0), this.minimizeDiv.addEventListener("click", this.minimize.bind(this), !0), this.closeDiv.addEventListener("click", this.cancelAction.bind(this)), this.title.addEventListener("click", this.reExpand.bind(this)), this.overlay.addEventListener("click", this.cancelAction.bind(this)), w.addEvent(window, "mousedown", this.startDrag.bind(this)), w.addEvent(window, "mouseup", this.stopDrag.bind(this)), w.addEvent(window, "mousemove", this.drag.bind(this)), w.addEvent(window, "resize", this.onWindowResize.bind(this)), w.addEvent(this.container, "keydown", this.onKeyDown.bind(this))
                        }
                    }, {
                        key: "removeListeners",
                        value: function() {
                            w.removeEvent(window, "mousedown", this.startDrag), w.removeEvent(window, "mouseup", this.stopDrag), w.removeEvent(window, "mousemove", this.drag), w.removeEvent(window, "resize", this.onWindowResize), w.removeEvent(this.container, "keydown", this.onKeyDown)
                        }
                    }, {
                        key: "eventClient",
                        value: function(e) {
                            return void 0 === e.clientX && e.changedTouches ? {
                                X: e.changedTouches[0].clientX,
                                Y: e.changedTouches[0].clientY
                            } : {
                                X: e.clientX,
                                Y: e.clientY
                            }
                        }
                    }, {
                        key: "startDrag",
                        value: function(e) {
                            "minimized" !== this.properties.state && e.target === this.title && (void 0 !== this.dragDataObject && null !== this.dragDataObject || (this.dragDataObject = {
                                x: this.eventClient(e).X,
                                y: this.eventClient(e).Y
                            }, this.lastDrag = {
                                x: "0px",
                                y: "0px"
                            }, "" === this.container.style.right && (this.container.style.right = "0px"), "" === this.container.style.bottom && (this.container.style.bottom = "0px"), this.isIE11(), w.addClass(document.body, "wrs_noselect"), w.addClass(this.overlay, "wrs_overlay_active"), this.limitWindow = this.getLimitWindow()))
                        }
                    }, {
                        key: "drag",
                        value: function(e) {
                            if (this.dragDataObject) {
                                e.preventDefault();
                                var t = Math.min(this.eventClient(e).Y, this.limitWindow.minPointer.y);
                                t = Math.max(this.limitWindow.maxPointer.y, t);
                                var n = Math.min(this.eventClient(e).X, this.limitWindow.minPointer.x);
                                n = Math.max(this.limitWindow.maxPointer.x, n);
                                var i = "".concat(n - this.dragDataObject.x, "px"),
                                    r = "".concat(t - this.dragDataObject.y, "px");
                                this.lastDrag = {
                                    x: i,
                                    y: r
                                }, this.container.style.transform = "translate3d(".concat(i, ",").concat(r, ",0)")
                            }
                            if (this.resizeDataObject) {
                                var a, o = window.innerWidth,
                                    s = window.innerHeight,
                                    l = Math.min(this.eventClient(e).X, o - this.scrollbarWidth - 7),
                                    c = Math.min(this.eventClient(e).Y, s - 7);
                                l < 0 && (l = 0), c < 0 && (c = 0), a = this.leftScale ? -1 : 1, this.container.style.width = "".concat(this.initialWidth + a * (l - this.resizeDataObject.x), "px"), this.container.style.height = "".concat(this.initialHeight + a * (c - this.resizeDataObject.y), "px"), this.leftScale || (this.resizeDataObject.x - l - this.initialWidth < -580 ? this.container.style.right = "".concat(this.initialRight - (l - this.resizeDataObject.x), "px") : (this.container.style.right = "".concat(this.initialRight + this.initialWidth - 580, "px"), this.container.style.width = "580px"), this.resizeDataObject.y - c < this.initialHeight - 338 ? this.container.style.bottom = "".concat(this.initialBottom - (c - this.resizeDataObject.y), "px") : (this.container.style.bottom = "".concat(this.initialBottom + this.initialHeight - 338, "px"), this.container.style.height = "338px")), this.recalculateScale(), this.recalculatePosition()
                            }
                        }
                    }, {
                        key: "getLimitWindow",
                        value: function() {
                            var e = window.innerWidth,
                                t = window.innerHeight,
                                n = this.container.offsetHeight,
                                i = parseInt(this.container.style.bottom, 10),
                                r = parseInt(this.container.style.right, 10),
                                a = window.pageXOffset,
                                o = this.dragDataObject.y,
                                s = this.dragDataObject.x,
                                l = n + i - (t - (o - a)),
                                c = e - this.scrollbarWidth - (s - a) - r,
                                d = t - this.container.offsetHeight + l,
                                u = this.title.offsetHeight - (this.title.offsetHeight - l);
                            return {
                                minPointer: {
                                    x: e - c - this.scrollbarWidth,
                                    y: d
                                },
                                maxPointer: {
                                    x: this.container.offsetWidth - c,
                                    y: u
                                }
                            }
                        }
                    }, {
                        key: "getScrollBarWidth",
                        value: function() {
                            var e = document.createElement("p");
                            e.style.width = "100%", e.style.height = "200px";
                            var t = document.createElement("div");
                            t.style.position = "absolute", t.style.top = "0px", t.style.left = "0px", t.style.visibility = "hidden", t.style.width = "200px", t.style.height = "150px", t.style.overflow = "hidden", t.appendChild(e), document.body.appendChild(t);
                            var n = e.offsetWidth;
                            t.style.overflow = "scroll";
                            var i = e.offsetWidth;
                            return n === i && (i = t.clientWidth), document.body.removeChild(t), n - i
                        }
                    }, {
                        key: "stopDrag",
                        value: function() {
                            (this.dragDataObject || this.resizeDataObject) && (this.container.style.transform = "", this.dragDataObject && (this.container.style.right = "".concat(parseInt(this.container.style.right, 10) - parseInt(this.lastDrag.x, 10), "px"), this.container.style.bottom = "".concat(parseInt(this.container.style.bottom, 10) - parseInt(this.lastDrag.y, 10), "px")), this.focus(), document.body.style["user-select"] = "", this.isIE11(), w.removeClass(document.body, "wrs_noselect"), w.removeClass(this.overlay, "wrs_overlay_active")), this.dragDataObject = null, this.resizeDataObject = null, this.initialWidth = null, this.leftScale = null
                        }
                    }, {
                        key: "onWindowResize",
                        value: function() {
                            this.recalculateScrollBar(), this.recalculatePosition(), this.recalculateScale()
                        }
                    }, {
                        key: "onKeyDown",
                        value: function(e) {
                            void 0 !== e.key && ("block" !== this.popup.overlayWrapper.style.display ? "Escape" === e.key || "Esc" === e.key ? this.properties.open && this.contentManager.onKeyDown(e) : e.shiftKey && "Tab" === e.key ? document.activeElement === this.cancelButton ? (this.submitButton.focus(), e.stopPropagation(), e.preventDefault()) : this.contentManager.onKeyDown(e) : "Tab" === e.key && (document.activeElement === this.submitButton ? (this.cancelButton.focus(), e.stopPropagation(), e.preventDefault()) : this.contentManager.onKeyDown(e)) : this.popup.onKeyDown(e))
                        }
                    }, {
                        key: "recalculatePosition",
                        value: function() {
                            this.container.style.right = "".concat(Math.min(parseInt(this.container.style.right, 10), window.innerWidth - this.scrollbarWidth - this.container.offsetWidth), "px"), parseInt(this.container.style.right, 10) < 0 && (this.container.style.right = "0px"), this.container.style.bottom = "".concat(Math.min(parseInt(this.container.style.bottom, 10), window.innerHeight - this.container.offsetHeight), "px"), parseInt(this.container.style.bottom, 10) < 0 && (this.container.style.bottom = "0px")
                        }
                    }, {
                        key: "recalculateScale",
                        value: function() {
                            var e = !1;
                            parseInt(this.container.style.width, 10) > 580 ? (this.container.style.width = "".concat(Math.min(parseInt(this.container.style.width, 10), window.innerWidth - this.scrollbarWidth), "px"), e = !0) : (this.container.style.width = "580px", e = !0), parseInt(this.container.style.height, 10) > 338 ? (this.container.style.height = "".concat(Math.min(parseInt(this.container.style.height, 10), window.innerHeight), "px"), e = !0) : (this.container.style.height = "338px", e = !0), e && this.recalculateSize()
                        }
                    }, {
                        key: "recalculateScrollBar",
                        value: function() {
                            this.hasScrollBar = window.innerWidth > document.documentElement.clientWidth, this.hasScrollBar ? this.scrollbarWidth = this.getScrollBarWidth() : this.scrollbarWidth = 0
                        }
                    }, {
                        key: "hideKeyboard",
                        value: function() {
                            var e = document.createElement("input");
                            this.container.appendChild(e), e.focus(), e.blur(), e.remove()
                        }
                    }, {
                        key: "focus",
                        value: function() {
                            null != this.contentManager && void 0 !== this.contentManager.onFocus && this.contentManager.onFocus()
                        }
                    }, {
                        key: "portraitMode",
                        value: function() {
                            return window.innerHeight > window.innerWidth
                        }
                    }, {
                        key: "handleOpenedIosSoftkeyboard",
                        value: function() {
                            this.iosSoftkeyboardOpened || null == this.iosDivHeight || this.iosDivHeight !== "100".concat(this.iosMeasureUnit) || (this.portraitMode() ? this.setContainerHeight("63".concat(this.iosMeasureUnit)) : this.setContainerHeight("40".concat(this.iosMeasureUnit))), this.iosSoftkeyboardOpened = !0
                        }
                    }, {
                        key: "handleClosedIosSoftkeyboard",
                        value: function() {
                            this.iosSoftkeyboardOpened = !1, this.setContainerHeight("100".concat(this.iosMeasureUnit))
                        }
                    }, {
                        key: "orientationChangeIosSoftkeyboard",
                        value: function() {
                            this.iosSoftkeyboardOpened ? this.portraitMode() ? this.setContainerHeight("63".concat(this.iosMeasureUnit)) : this.setContainerHeight("40".concat(this.iosMeasureUnit)) : this.setContainerHeight("100".concat(this.iosMeasureUnit))
                        }
                    }, {
                        key: "orientationChangeAndroidSoftkeyboard",
                        value: function() {
                            this.setContainerHeight("100%")
                        }
                    }, {
                        key: "setContainerHeight",
                        value: function(e) {
                            this.iosDivHeight = e, this.wrapper.style.height = e
                        }
                    }, {
                        key: "showPopUpMessage",
                        value: function() {
                            "minimized" === this.properties.state && this.stack(), this.popup.show()
                        }
                    }, {
                        key: "setTitle",
                        value: function(e) {
                            this.title.innerHTML = e
                        }
                    }, {
                        key: "getElementId",
                        value: function(e) {
                            return "".concat(e, "[").concat(this.instanceId, "]")
                        }
                    }]), e
                }();
                var de;
                String.prototype.codePointAt || (de = function(e) {
                    if (null == this) throw TypeError();
                    var t = String(this),
                        n = t.length,
                        i = e ? Number(e) : 0;
                    if (i != i && (i = 0), !(i < 0 || i >= n)) {
                        var r, a = t.charCodeAt(i);
                        return a >= 55296 && a <= 56319 && n > i + 1 && (r = t.charCodeAt(i + 1)) >= 56320 && r <= 57343 ? 1024 * (a - 55296) + r - 56320 + 65536 : a
                    }
                }, Object.defineProperty ? Object.defineProperty(String.prototype, "codePointAt", {
                    value: de,
                    configurable: !0,
                    writable: !0
                }) : String.prototype.codePointAt = de), "function" != typeof Object.assign && Object.defineProperty(Object, "assign", {
                    value: function(e, t) {
                        if (null == e) throw new TypeError("Cannot convert undefined or null to object");
                        for (var n = Object(e), i = 1; i < arguments.length; i++) {
                            var r = arguments[i];
                            if (null != r)
                                for (var a in r) Object.prototype.hasOwnProperty.call(r, a) && (n[a] = r[a])
                        }
                        return n
                    },
                    writable: !0,
                    configurable: !0
                }), Array.prototype.includes || Object.defineProperty(Array.prototype, "includes", {
                    value: function(e, t) {
                        if (null == this) throw new TypeError('"this" s null or is not defined');
                        var n = Object(this),
                            i = n.length >>> 0;
                        if (0 === i) return !1;
                        var r, a, o = 0 | t,
                            s = Math.max(o >= 0 ? o : i - Math.abs(o), 0);
                        for (; s < i;) {
                            if ((r = n[s]) === (a = e) || "number" == typeof r && "number" == typeof a && isNaN(r) && isNaN(a)) return !0;
                            s++
                        }
                        return !1
                    }
                }), String.prototype.includes || (String.prototype.includes = function(e, t) {
                    if (e instanceof RegExp) throw TypeError("first argument must not be a RegExp");
                    return void 0 === t && (t = 0), -1 !== this.indexOf(e, t)
                }), String.prototype.startsWith || Object.defineProperty(String.prototype, "startsWith", {
                    value: function(e, t) {
                        var n = t > 0 ? 0 | t : 0;
                        return this.substring(n, n + e.length) === e
                    }
                });
                var ue = n(379),
                    me = n.n(ue),
                    he = n(775),
                    ge = {
                        insert: "head",
                        singleton: !1
                    };
                me()(he.Z, ge);
                he.Z.locals;

                function pe(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                var fe = function() {
                    function e(t) {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e), this.language = "en", this.editMode = "images", this.modalDialog = null, this.customEditors = new L;
                        var n, i;
                        if (this.customEditors.addEditor("chemistry", {
                                name: "Chemistry",
                                toolbar: "chemistry",
                                icon: "chem.png",
                                confVariable: "chemEnabled",
                                title: "ChemType",
                                tooltip: "Insert a chemistry formula - ChemType"
                            }), this.environment = {}, this.editionProperties = {}, this.editionProperties.isNewElement = !0, this.editionProperties.temporalImage = null, this.editionProperties.latexRange = null, this.editionProperties.range = null, this.integrationModel = null, this.contentManager = null, this.browser = (n = navigator.userAgent, i = "none", n.search("Edge/") >= 0 ? i = "EDGE" : n.search("Chrome/") >= 0 ? i = "CHROME" : n.search("Trident/") >= 0 ? i = "IE" : n.search("Firefox/") >= 0 ? i = "FIREFOX" : n.search("Safari/") >= 0 && (i = "SAFARI"), i), this.listeners = new m, this.serviceProviderProperties = {}, !("serviceProviderProperties" in t)) throw new Error("serviceProviderProperties property missing.");
                        this.serviceProviderProperties = t.serviceProviderProperties
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "globalListeners",
                        get: function() {
                            return e._globalListeners
                        },
                        set: function(t) {
                            e._globalListeners = t
                        }
                    }, {
                        key: "initialized",
                        get: function() {
                            return e._initialized
                        },
                        set: function(t) {
                            e._initialized = t
                        }
                    }, {
                        key: "addGlobalListener",
                        value: function(t) {
                            e.globalListeners.add(t)
                        }
                    }], (n = [{
                        key: "setIntegrationModel",
                        value: function(e) {
                            this.integrationModel = e
                        }
                    }, {
                        key: "setEnvironment",
                        value: function(e) {
                            "editor" in e && (this.environment.editor = e.editor), "mode" in e && (this.environment.mode = e.mode), "version" in e && (this.environment.version = e.version)
                        }
                    }, {
                        key: "getModalDialog",
                        value: function() {
                            return this.modalDialog
                        }
                    }, {
                        key: "init",
                        value: function() {
                            var t = this;
                            if (e.initialized) this.listeners.fire("onLoad", {});
                            else {
                                var n = m.newListener("onInit", (function() {
                                    var e = g.getService("configurationjs", "", "get"),
                                        n = JSON.parse(e);
                                    l.addConfiguration(n), l.addConfiguration(B), b.language = t.language, t.listeners.fire("onLoad", {})
                                }));
                                g.addListener(n), g.init(this.serviceProviderProperties), e.initialized = !0
                            }
                        }
                    }, {
                        key: "addListener",
                        value: function(e) {
                            this.listeners.add(e)
                        }
                    }, {
                        key: "beforeUpdateFormula",
                        value: function(t, n) {
                            var i = new D;
                            return i.mathml = t, i.wirisProperties = {}, null != n && Object.keys(n).forEach((function(e) {
                                i.wirisProperties[e] = n[e]
                            })), i.language = this.language, i.editMode = this.editMode, this.listeners.fire("onBeforeFormulaInsertion", i) || e.globalListeners.fire("onBeforeFormulaInsertion", i) ? {} : {
                                mathml: i.mathml,
                                wirisProperties: i.wirisProperties
                            }
                        }
                    }, {
                        key: "insertFormula",
                        value: function(e, t, n, i) {
                            var r = {};
                            if (n)
                                if ("latex" === this.editMode) {
                                    if (r.latex = f.getLatexFromMathML(n), this.integrationModel.fillNonLatexNode && !r.latex) {
                                        var a = new D;
                                        a.editMode = this.editMode, a.windowTarget = t, a.focusElement = e, a.latex = r.latex, this.integrationModel.fillNonLatexNode(a, t, n)
                                    } else r.node = t.document.createTextNode("$$".concat(r.latex, "$$"));
                                    this.insertElementOnSelection(r.node, e, t)
                                } else r.node = E.mathmlToImgObject(t.document, n, i, this.language), this.insertElementOnSelection(r.node, e, t);
                            else this.insertElementOnSelection(null, e, t);
                            return r
                        }
                    }, {
                        key: "afterUpdateFormula",
                        value: function(t, n, i, r) {
                            var a = new D;
                            return a.editMode = this.editMode, a.windowTarget = n, a.focusElement = t, a.node = i, a.latex = r, this.listeners.fire("onAfterFormulaInsertion", a) || e.globalListeners.fire("onAfterFormulaInsertion", a), {}
                        }
                    }, {
                        key: "placeCaretAfterNode",
                        value: function(e) {
                            this.integrationModel.getSelection();
                            var t = e.ownerDocument;
                            if (void 0 !== t.getSelection && e.parentElement) {
                                var n = t.createRange();
                                n.setStartAfter(e), n.collapse(!0);
                                var i = t.getSelection();
                                i.removeAllRanges(), i.addRange(n), t.body.focus()
                            }
                        }
                    }, {
                        key: "insertElementOnSelection",
                        value: function(e, t, n) {
                            if (this.editionProperties.isNewElement)
                                if (e)
                                    if ("textarea" === t.type) w.updateTextArea(t, e.textContent);
                                    else if (document.selection && 0 === document.getSelection) {
                                var i = n.document.selection.createRange();
                                if (n.document.execCommand("InsertImage", !1, e.src), "parentElement" in i || (n.document.execCommand("delete", !1), i = n.document.selection.createRange(), n.document.execCommand("InsertImage", !1, e.src)), "parentElement" in i) {
                                    var r = i.parentElement();
                                    "IMG" === r.nodeName.toUpperCase() ? r.parentNode.replaceChild(e, r) : i.pasteHTML(w.createObjectCode(e))
                                }
                            } else {
                                var a = this.integrationModel.getSelection(),
                                    o = null;
                                this.editionProperties.range ? (o = this.editionProperties.range, this.editionProperties.range = null) : o = a.getRangeAt(0), o.deleteContents();
                                var s = o.startContainer,
                                    l = o.startOffset;
                                3 === s.nodeType ? (s = s.splitText(l)).parentNode.insertBefore(e, s) : 1 === s.nodeType && s.insertBefore(e, s.childNodes[l]), this.placeCaretAfterNode(e)
                            } else if ("textarea" === t.type) t.focus();
                            else {
                                var c = this.integrationModel.getSelection();
                                if (c.removeAllRanges(), this.editionProperties.range) {
                                    var d = this.editionProperties.range;
                                    this.editionProperties.range = null, c.addRange(d)
                                }
                            } else if (this.editionProperties.latexRange) document.selection && 0 === document.getSelection ? (this.editionProperties.isNewElement = !0, this.editionProperties.latexRange.select(), this.insertElementOnSelection(e, t, n)) : (this.editionProperties.latexRange.deleteContents(), this.editionProperties.latexRange.insertNode(e), this.placeCaretAfterNode(e));
                            else if ("textarea" === t.type) {
                                var u;
                                u = void 0 !== this.integrationModel.getSelectedItem ? this.integrationModel.getSelectedItem(t, !1) : w.getSelectedItemOnTextarea(t), w.updateExistingTextOnTextarea(t, e.textContent, u.startPosition, u.endPosition)
                            } else e && "img" === e.nodeName.toLowerCase() ? (k.removeImgDataAttributes(this.editionProperties.temporalImage), k.clone(e, this.editionProperties.temporalImage)) : this.editionProperties.temporalImage.remove(), this.placeCaretAfterNode(this.editionProperties.temporalImage)
                        }
                    }, {
                        key: "openModalDialog",
                        value: function(e, t) {
                            var n, i = this;
                            this.editMode = "images";
                            try {
                                if (t) {
                                    e.contentWindow.focus();
                                    var r = e.contentWindow.getSelection();
                                    this.editionProperties.range = r.getRangeAt(0)
                                } else {
                                    e.focus();
                                    var a = getSelection();
                                    this.editionProperties.range = a.getRangeAt(0)
                                }
                            } catch (e) {
                                this.editionProperties.range = null
                            }
                            if (void 0 === t && (t = !0), this.editionProperties.latexRange = null, e)
                                if (n = void 0 !== this.integrationModel.getSelectedItem ? this.integrationModel.getSelectedItem(e, t) : w.getSelectedItem(e, t)) {
                                    if (!n.caretPosition && w.containsClass(n.node, l.get("imageClassName"))) this.editionProperties.temporalImage = n.node, this.editionProperties.isNewElement = !1;
                                    else if (3 === n.node.nodeType)
                                        if (this.integrationModel.getMathmlFromTextNode) {
                                            var s = this.integrationModel.getMathmlFromTextNode(n.node, n.caretPosition);
                                            s && (this.editMode = "latex", this.editionProperties.isNewElement = !1, this.editionProperties.temporalImage = document.createElement("img"), this.editionProperties.temporalImage.setAttribute(l.get("imageMathmlAttribute"), o.safeXmlEncode(s)))
                                        } else {
                                            var c = f.getLatexFromTextNode(n.node, n.caretPosition);
                                            if (c) {
                                                var d = f.getMathMLFromLatex(c.latex);
                                                this.editMode = "latex", this.editionProperties.isNewElement = !1, this.editionProperties.temporalImage = document.createElement("img"), this.editionProperties.temporalImage.setAttribute(l.get("imageMathmlAttribute"), o.safeXmlEncode(d));
                                                var u = t ? e.contentWindow : window;
                                                if ("textarea" !== e.tagName.toLowerCase())
                                                    if (document.selection) {
                                                        for (var h = 0, g = c.startNode.previousSibling; g;) h += w.getNodeLength(g), g = g.previousSibling;
                                                        this.editionProperties.latexRange = u.document.selection.createRange(), this.editionProperties.latexRange.moveToElementText(c.startNode.parentNode), this.editionProperties.latexRange.move("character", h + c.startPosition), this.editionProperties.latexRange.moveEnd("character", c.latex.length + 4)
                                                    } else this.editionProperties.latexRange = u.document.createRange(), this.editionProperties.latexRange.setStart(c.startNode, c.startPosition), this.editionProperties.latexRange.setEnd(c.endNode, c.endPosition)
                                            }
                                        }
                                } else "textarea" === e.tagName.toLowerCase() && (this.editMode = "latex");
                            for (var p = l.get("editorAttributes").split(", "), _ = {}, v = 0, b = p.length; v < b; v += 1) {
                                var y = p[v].split("="),
                                    x = y[0],
                                    k = y[1];
                                _[x] = k
                            }
                            var A = {},
                                C = l.get("editorParameters"),
                                M = this.integrationModel.editorParameters;
                            Object.assign(A, _, C), Object.assign(A, _, M), A.language = this.language, A.rtl = this.integrationModel.rtl;
                            var T = {};
                            if (T.editorAttributes = A, T.language = this.language, T.customEditors = this.customEditors, T.environment = this.environment, null == this.modalDialog) {
                                this.modalDialog = new ce(A), this.contentManager = new O(T);
                                var E = m.newListener("onLoad", (function() {
                                    if (i.contentManager.isNewElement = i.editionProperties.isNewElement, null != i.editionProperties.temporalImage) {
                                        var e = o.safeXmlDecode(i.editionProperties.temporalImage.getAttribute(l.get("imageMathmlAttribute")));
                                        i.contentManager.mathML = e
                                    }
                                }));
                                this.contentManager.addListener(E), this.contentManager.init(), this.modalDialog.setContentManager(this.contentManager), this.contentManager.setModalDialogInstance(this.modalDialog)
                            } else if (this.contentManager.isNewElement = this.editionProperties.isNewElement, null != this.editionProperties.temporalImage) {
                                var j = o.safeXmlDecode(this.editionProperties.temporalImage.getAttribute(l.get("imageMathmlAttribute")));
                                this.contentManager.mathML = j
                            }
                            this.contentManager.setIntegrationModel(this.integrationModel), this.modalDialog.open()
                        }
                    }, {
                        key: "getCustomEditors",
                        value: function() {
                            return this.customEditors
                        }
                    }]) && pe(t.prototype, n), i && pe(t, i), e
                }();
                fe._globalListeners = new m, fe._initialized = !1;

                function _e(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }
                window.wrs_addPluginListener = function(e) {
                    var t, n;
                    console.warn("Deprecated method"), n = e[t = Object.keys(e)[0]];
                    var i = m.newListener(t, n);
                    fe.addGlobalListener(i)
                }, window.wrs_initParse = function(e, t) {
                    return console.warn("Deprecated method. Use Parser.endParse instead."), E.initParse(e, t)
                }, window.wrs_endParse = function(e, t, n) {
                    return console.warn("Deprecated method. Use Parser.endParse instead."), E.endParse(e, t, n)
                };
                var ve = function() {
                    function e() {
                        ! function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, e)
                    }
                    var t, n, i;
                    return t = e, i = [{
                        key: "init",
                        value: function() {
                            e.testServices()
                        }
                    }, {
                        key: "testServices",
                        value: function() {
                            var e;
                            console.log("Testing configuration service..."), console.log(g.getService("configurationjs", "", "get")), console.log("Testing showimage service..."), (e = []).mml = '<math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mi>x</mi><mn>2</mn></msup></math>', console.log(g.getService("showimage", e)), console.log("Testing createimage service..."), (e = []).mml = '<math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mi>x</mi><mn>2</mn></msup></math>', console.log(g.getService("createimage", e, "post")), console.log("Testing MathML2Latex service..."), (e = []).service = "mathml2latex", e.mml = '<math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mi>x</mi><mn>2</mn></msup></math>', console.log(g.getService("service", e)), console.log("Testing Latex2MathML service..."), (e = []).service = "latex2mathml", e.latex = "x^2", console.log(g.getService("service", e)), console.log("Testing Mathml2Accesible service..."), (e = []).service = "mathml2accessible", e.mml = '<math xmlns="http://www.w3.org/1998/Math/MathML"><msup><mi>x</mi><mn>2</mn></msup></math>', console.log(g.getService("service", e))
                        }
                    }], (n = null) && _e(t.prototype, n), i && _e(t, i), e
                }();
                const be = "7.27.0";

                function ye(e) {
                    return (ye = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(e) {
                        return typeof e
                    } : function(e) {
                        return e && "function" == typeof Symbol && e.constructor === Symbol && e !== Symbol.prototype ? "symbol" : typeof e
                    })(e)
                }

                function we(e, t) {
                    for (var n = 0; n < t.length; n++) {
                        var i = t[n];
                        i.enumerable = i.enumerable || !1, i.configurable = !0, "value" in i && (i.writable = !0), Object.defineProperty(e, i.key, i)
                    }
                }

                function xe(e, t, n) {
                    return (xe = "undefined" != typeof Reflect && Reflect.get ? Reflect.get : function(e, t, n) {
                        var i = function(e, t) {
                            for (; !Object.prototype.hasOwnProperty.call(e, t) && null !== (e = Me(e)););
                            return e
                        }(e, t);
                        if (i) {
                            var r = Object.getOwnPropertyDescriptor(i, t);
                            return r.get ? r.get.call(n) : r.value
                        }
                    })(e, t, n || e)
                }

                function ke(e, t) {
                    return (ke = Object.setPrototypeOf || function(e, t) {
                        return e.__proto__ = t, e
                    })(e, t)
                }

                function Ae(e) {
                    var t = function() {
                        if ("undefined" == typeof Reflect || !Reflect.construct) return !1;
                        if (Reflect.construct.sham) return !1;
                        if ("function" == typeof Proxy) return !0;
                        try {
                            return Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], (function() {}))), !0
                        } catch (e) {
                            return !1
                        }
                    }();
                    return function() {
                        var n, i = Me(e);
                        if (t) {
                            var r = Me(this).constructor;
                            n = Reflect.construct(i, arguments, r)
                        } else n = i.apply(this, arguments);
                        return Ce(this, n)
                    }
                }

                function Ce(e, t) {
                    return !t || "object" !== ye(t) && "function" != typeof t ? function(e) {
                        if (void 0 === e) throw new ReferenceError("this hasn't been initialised - super() hasn't been called");
                        return e
                    }(e) : t
                }

                function Me(e) {
                    return (Me = Object.setPrototypeOf ? Object.getPrototypeOf : function(e) {
                        return e.__proto__ || Object.getPrototypeOf(e)
                    })(e)
                }
                var Te = function(e) {
                    ! function(e, t) {
                        if ("function" != typeof t && null !== t) throw new TypeError("Super expression must either be null or a function");
                        e.prototype = Object.create(t && t.prototype, {
                            constructor: {
                                value: e,
                                writable: !0,
                                configurable: !0
                            }
                        }), t && ke(e, t)
                    }(a, e);
                    var t, n, i, r = Ae(a);

                    function a(e) {
                        var t;
                        return function(e, t) {
                            if (!(e instanceof t)) throw new TypeError("Cannot call a class as a function")
                        }(this, a), (t = r.call(this, e)).initParsed = e.initParsed, t.isMoodle = e.isMoodle, t.isExternal = e.isExternal, t
                    }
                    return t = a, (n = [{
                        key: "getPath",
                        value: function() {
                            if (this.isMoodle) {
                                var e = "lib/editor/tinymce",
                                    t = tinymce.baseURL.indexOf(e),
                                    n = tinymce.baseURL.substr(0, t + e.length);
                                return "".concat(n, "/plugins/tiny_mce_wiris/tinymce/")
                            }
                            if (this.isExternal) {
                                var i = this.editorObject.getParam("external_plugins").tiny_mce_wiris;
                                return i.substring(0, i.lastIndexOf("/") + 1)
                            }
                            return "".concat(tinymce.baseURL, "/plugins/tiny_mce_wiris/")
                        }
                    }, {
                        key: "getIconsPath",
                        value: function() {
                            return this.isMoodle && l.get("versionPlatform") < 2013111800 ? "".concat(this.getPath(), "icons/tinymce3/") : "".concat(this.getPath(), "icons/")
                        }
                    }, {
                        key: "getLanguage",
                        value: function() {
                            var e = this.editorObject.settings;
                            try {
                                return e.mathTypeParameters.editorParameters.language
                            } catch (e) {
                                console.error()
                            }
                            return e.wirisformulaeditorlang ? (console.warn("Deprecated property wirisformulaeditorlang. Use mathTypeParameters on instead."), e.wirisformulaeditorlang) : this.editorObject.getParam("language") || xe(Me(a.prototype), "getLanguage", this).call(this)
                        }
                    }, {
                        key: "callbackFunction",
                        value: function() {
                            var e = this,
                                t = [];
                            xe(Me(a.prototype), "callbackFunction", this).call(this);
                            var n = l.get("imageClassName");
                            this.isIframe ? void 0 !== E.observer && Array.prototype.forEach.call(this.target.contentDocument.getElementsByClassName(n), (function(e) {
                                E.observer.observe(e)
                            })) : Array.prototype.forEach.call(document.getElementsByClassName(n), (function(e) {
                                E.observer.observe(e)
                            }));
                            var i = m.newListener("onAfterFormulaInsertion", (function() {
                                void 0 !== e.editorObject.fire && e.editorObject.fire("Change")
                            }));
                            this.getCore().addListener(i), t[this.editorObject.id] = this.editorObject.settings.images_dataimg_filter, this.editorObject.settings.images_dataimg_filter = function(n) {
                                return n.hasAttribute("class") && -1 !== n.getAttribute("class").indexOf(l.get("imageClassName")) ? n.hasAttribute("internal-blob") : void 0 === t[e.editorObject.id] || t[e.editorObject.id](n)
                            }
                        }
                    }, {
                        key: "updateFormula",
                        value: function(e) {
                            void 0 !== this.editorObject.fire && this.editorObject.fire("ExecCommand", {
                                command: "updateFormula",
                                value: e
                            }), xe(Me(a.prototype), "updateFormula", this).call(this, e)
                        }
                    }]) && we(t.prototype, n), i && we(t, i), a
                }(ie);
                tinymce.create("tinymce.plugins.tiny_mce_wiris", {
                    init: function(e) {
                        e.settings.extended_valid_elements += ",".concat(["math[*]", "maction[*]]", "malignmark[*]", "maligngroup[*]", "menclose[*]", "merror[*]", "mfenced[*]", "mfrac[*]", "mglyph[*]", "mi[*]", "mlabeledtr[*]", "mlongdiv[*]", "mmultiscripts[*]", "mn[*]", "mo[*]", "mover[*]", "mpadded[*]", "mphantom[*]", "mprescripts[*]", "none[*]", "mroot[*]", "mrow[*]", "ms[*]", "mscarries[*]", "mscarry[*]", "msgroup[*]", "msline[*]", "mspace[*]", "msqrt[*]", "msrow[*]", "mstack[*]", "mstyle[*]", "msub[*]", "msubsup[*]", "msup[*]", "mtable[*]", "mtd[*]", "mtext[*]", "mtr[*]", "munder[*]", "munderover[*]", "semantics[*]", "annotation[*]"].join());
                        var t = {
                            serviceProviderProperties: {}
                        };
                        t.serviceProviderProperties.URI = "https://nvppndw.lizeedu.com.br/demo/plugins/app", t.serviceProviderProperties.server = "java", t.version = be, t.isMoodle = !("object" !== ("undefined" == typeof M ? "undefined" : ye(M)) || null === M), t.isMoodle && (t.configurationService = M.cfg.wwwroot + "/filter/wiris/integration/configurationjs.php"), void 0 !== e.getParam("wiriscontextpath") && (t.configurationService = w.concatenateUrl(e.getParam("wiriscontextpath"), t.configurationService), "".concat(e.getParam("wiriscontextpath"), "/").concat(t.configurationService), console.warn("Deprecated property wiriscontextpath. Use mathTypeParameters on instead.", e.opts.wiriscontextpath)), void 0 !== e.getParam("mathTypeParameters") && (t.integrationParameters = e.getParam("mathTypeParameters")), t.scriptName = "plugin.min.js", t.environment = {};
                        var n = "4";
                        "5" === tinymce.majorVersion && (n = "5"), t.environment.editor = "TinyMCE ".concat(n, ".x"), t.environment.editorVersion = "".concat(tinymce.majorVersion, ".").concat(tinymce.minorVersion), t.callbackMethodArguments = {}, t.editorObject = e, t.initParsed = !1, t.target = null;
                        var i = void 0 !== e.getParam("external_plugins") && "tiny_mce_wiris" in e.getParam("external_plugins");
                        t.isExternal = i, t.rtl = "rtl" === e.getParam("directionality");
                        var r = new Te(t);
                        r.init(), WirisPlugin.instances[r.editorObject.id] = r, WirisPlugin.currentInstance = r;
                        var a = function(e) {
                            var t = WirisPlugin.instances[r.editorObject.id];
                            e.inline ? t.setTarget(e.getElement()) : t.setTarget(e.getContentAreaContainer().firstChild), t.setEditorObject(e), t.listeners.fire("onTargetReady", {}), "wiriseditorparameters" in e.settings && l.update("editorParameters", e.settings.wiriseditorparameters), new MutationObserver(function(e, t) {
                                Array.prototype.forEach.call(t, function(e, t) {
                                    Array.prototype.forEach.call(t.addedNodes, function(e, t) {
                                        1 === t.nodeType && Array.prototype.forEach.call(t.querySelectorAll(".".concat(WirisPlugin.Configuration.get("imageClassName"))), function(e, t) {
                                            t.removeAttribute("data-mce-src"), t.removeAttribute("data-mce-style")
                                        }.bind(this, e))
                                    }.bind(this, e))
                                }.bind(this, e))
                            }.bind(this, e)).observe(e.getBody(), {
                                attributes: !0,
                                childList: !0,
                                characterData: !0,
                                subtree: !0
                            });
                            var n = e.getContent();
                            e.setContent(E.initParse(n, e.getParam("language")), {
                                format: "html"
                            }), e.undoManager.clear(), WirisPlugin.instances[e.id].initParsed = !0
                        };
                        "onInit" in e ? e.onInit.add(a) : e.on("init", (function() {
                            a(e)
                        })), "onActivate" in e ? e.onActivate.add((function(e) {
                            WirisPlugin.currentInstance = WirisPlugin.instances[tinymce.activeEditor.id]
                        })) : e.on("focus", (function(e) {
                            WirisPlugin.currentInstance = WirisPlugin.instances[tinymce.activeEditor.id]
                        }));
                        var o, s = function(e, t) {
                            t.content = E.endParse(t.content, e.getParam("language"))
                        };

                        function c() {
                            var t = WirisPlugin.instances[e.id];
                            t.core.getCustomEditors().disable(), t.openNewFormulaEditor()
                        }
                        "onSaveContent" in e ? e.onSaveContent.add(s) : e.on("saveContent", (function(t) {
                            s(e, t)
                        })), "onGetContent" in e ? e.onGetContent.add(s) : e.on("getContent", (function(t) {
                            s(e, t)
                        })), "onBeforeSetContent" in e ? e.onBeforeSetContent.add((function(t, n) {
                            WirisPlugin.instances[e.id].initParsed && (n.content = E.initParse(n.content, e.getParam("language")))
                        })) : e.on("beforeSetContent", (function(t) {
                            WirisPlugin.instances[e.id].initParsed && (t.content = E.initParse(t.content, e.getParam("language")))
                        }));
                        var d = "mathtypeicon",
                            u = "chemtypeicon";
                        if ("5" === tinymce.majorVersion) {
                            (o = e.ui.registry).addIcon(d, '<svg width="16" height="16" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px"viewBox="0 0 300 261.7" style="enable-background:new 0 0 300 261.7;" xml:space="preserve"><g id=icon-wirisformula stroke="none" stroke-width="1" fill-rule="evenodd"><g><path class="st1" d="M90.2,257.7c-11.4,0-21.9-6.4-27-16.7l-60-119.9c-7.5-14.9-1.4-33.1,13.5-40.5c14.9-7.5,33.1-1.4,40.5,13.5l27.3,54.7L121.1,39c5.3-15.8,22.4-24.4,38.2-19.1c15.8,5.3,24.4,22.4,19.1,38.2l-59.6,179c-3.9,11.6-14.3,19.7-26.5,20.6C91.6,257.7,90.9,257.7,90.2,257.7"/></g></g><g><g><path class="st2" d="M300,32.8c0-16.4-13.4-29.7-29.9-29.7c-2.9,0-7.2,0.8-7.2,0.8c-37.9,9.1-71.3,14-112,14c-0.3,0-0.6,0-1,0c-16.5,0-29.9,13.3-29.9,29.7c0,16.4,13.4,29.7,29.9,29.7l0,0c45.3,0,83.1-5.3,125.3-15.3h0C289.3,59.5,300,47.4,300,32.8"/></g></g></svg>'), o.addIcon(u, '<svg width="16" height="16" version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" width="16px" height="16px" viewBox="0 0 16 16" enable-background="new 0 0 16 16" xml:space="preserve">  <image id="image0" width="16" height="16" x="0" y="0"href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAQAAAC1+jfqAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAAmJLR0QA/4ePzL8AAAAHdElNRQfiChwSIwERK9BGAAABfklEQVQoz12RvUtbcRiFn/uRXKNJNCJSokFFqoKDIjHEqKA4WRAc/AsUKl2Ck5ODIKKDm4v+BbqIEr8WQ+hgQSgOElGJgkPTih+3tUabeL3353A1CX3Hcx7OC+dIAIL3CwXEmJU6XBHWuyIVgIjrOcoUblCTrolE/D+gc0QsUJePEtrGh+jajzcg1GQu0W87ldl7zZQAtPP9Dh5lADNm25rx+Xb7ZdWMCAARyHXhVQD8iwAD+qLV61B++U4Hb5pKS9Tx3w05Umr+K3Mlsk6SfY7x9oX7OvDiwlEEoLPLNkdc4yRJG9WkuCoCxBV7JMhg8cgRl7h44m9xwhM3PLyVYnBni3LBX64p4MHGYLSzOV9UWDd8AO608iW+2eP5NyVN4JR/7rRU2T0MzVRmATI197FIInsmTeIErcwTxqcAxHPDFdLHE4cJmPV4AAKZ+XStyrkCMC00K8Qnj+6+kAFKjfE/sw6/zAXf7bFUqmill+5v7es+vzVqlhukOWCLr6/ZMH/PRaOKYwAAACV0RVh0ZGF0ZTpjcmVhdGUAMjAxOC0xMC0yOVQwMTozNTowMS0wNzowMOC+eEAAAAAldEVYdGRhdGU6bW9kaWZ5ADIwMTgtMTAtMjlUMDE6MzU6MDEtMDc6MDCR48D8AAAAAElFTkSuQmCC" /></svg>'), o.addMenuItem("tiny_mce_wiris_formulaEditor", {
                                text: "MathType",
                                icon: d,
                                onAction: c
                            });
                            var m = WirisPlugin.instances[e.id].getCore().getCustomEditors();
                            Object.keys(m.editors).forEach((function(t) {
                                m.editors[t].confVariable && o.addMenuItem("tiny_mce_wiris_formulaEditor".concat(m.editors[t].name), {
                                    text: m.editors[t].title,
                                    icon: u,
                                    onAction: function() {
                                        m.enable(t), WirisPlugin.instances[e.id].openNewFormulaEditor()
                                    }
                                })
                            }))
                        } else(o = e).addCommand("tiny_mce_wiris_openFormulaEditor", c);
                        o.addButton("tiny_mce_wiris_formulaEditor", {
                            tooltip: "Insert a math equation - MathType",
                            title: "Insert a math equation - MathType",
                            cmd: "tiny_mce_wiris_openFormulaEditor",
                            image: "".concat(WirisPlugin.instances[e.id].getIconsPath(), "formula.png"),
                            onAction: c,
                            icon: d
                        });
                        var h = WirisPlugin.instances[e.id].getCore().getCustomEditors(),
                            g = function(t) {
                                if (h.editors[t].confVariable) {
                                    var n = function() {
                                            h.enable(t), WirisPlugin.instances[e.id].openNewFormulaEditor()
                                        },
                                        i = "tiny_mce_wiris_openFormulaEditor".concat(h.editors[t].name);
                                    e.addCommand(i, n), o.addButton("tiny_mce_wiris_formulaEditor".concat(h.editors[t].name), {
                                        title: h.editors[t].tooltip,
                                        tooltip: h.editors[t].tooltip,
                                        onAction: n,
                                        cmd: i,
                                        image: WirisPlugin.instances[e.id].getIconsPath() + h.editors[t].icon,
                                        icon: u
                                    })
                                }
                            };
                        for (var p in h.editors) g(p)
                    },
                    getInfo: function() {
                        return {
                            longname: "tiny_mce_wiris",
                            author: "Nvppnw",
                            authorurl: "http://www.nvppnw.com",
                            infourl: "http://www.nvppnw.com",
                            version: be
                        }
                    }
                }), tinymce.PluginManager.add("tiny_mce_wiris", tinymce.plugins.tiny_mce_wiris), window.WirisPlugin = {
                    Core: fe,
                    Parser: E,
                    Image: k,
                    Util: w,
                    Configuration: l,
                    Listeners: m,
                    IntegrationModel: ie,
                    currentInstance: null,
                    instances: {},
                    TinyMceIntegration: Te,
                    Latex: f,
                    Test: ve
                }
            },
            646: () => {
                function _typeof(e) {
                    return (_typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(e) {
                        return typeof e
                    } : function(e) {
                        return e && "function" == typeof Symbol && e.constructor === Symbol && e !== Symbol.prototype ? "symbol" : typeof e
                    })(e)
                }
                var md5, __WEBPACK_DEFAULT_EXPORT__ = md5;
                (function() {
                    var HxOverrides = function() {};
                    HxOverrides.__name__ = !0, HxOverrides.dateStr = function(e) {
                        var t = e.getMonth() + 1,
                            n = e.getDate(),
                            i = e.getHours(),
                            r = e.getMinutes(),
                            a = e.getSeconds();
                        return e.getFullYear() + "-" + (t < 10 ? "0" + t : "" + t) + "-" + (n < 10 ? "0" + n : "" + n) + " " + (i < 10 ? "0" + i : "" + i) + ":" + (r < 10 ? "0" + r : "" + r) + ":" + (a < 10 ? "0" + a : "" + a)
                    }, HxOverrides.strDate = function(e) {
                        switch (e.length) {
                            case 8:
                                var t = e.split(":"),
                                    n = new Date;
                                return n.setTime(0), n.setUTCHours(t[0]), n.setUTCMinutes(t[1]), n.setUTCSeconds(t[2]), n;
                            case 10:
                                t = e.split("-");
                                return new Date(t[0], t[1] - 1, t[2], 0, 0, 0);
                            case 19:
                                var i = (t = e.split(" "))[0].split("-"),
                                    r = t[1].split(":");
                                return new Date(i[0], i[1] - 1, i[2], r[0], r[1], r[2]);
                            default:
                                throw "Invalid date format : " + e
                        }
                    }, HxOverrides.cca = function(e, t) {
                        var n = e.charCodeAt(t);
                        if (n == n) return n
                    }, HxOverrides.substr = function(e, t, n) {
                        return null != t && 0 != t && null != n && n < 0 ? "" : (null == n && (n = e.length), t < 0 ? (t = e.length + t) < 0 && (t = 0) : n < 0 && (n = e.length + n - t), e.substr(t, n))
                    }, HxOverrides.remove = function(e, t) {
                        for (var n = 0, i = e.length; n < i;) {
                            if (e[n] == t) return e.splice(n, 1), !0;
                            n++
                        }
                        return !1
                    }, HxOverrides.iter = function(e) {
                        return {
                            cur: 0,
                            arr: e,
                            hasNext: function() {
                                return this.cur < this.arr.length
                            },
                            next: function() {
                                return this.arr[this.cur++]
                            }
                        }
                    };
                    var IntIter = function(e, t) {
                        this.min = e, this.max = t
                    };
                    IntIter.__name__ = !0, IntIter.prototype = {
                        next: function() {
                            return this.min++
                        },
                        hasNext: function() {
                            return this.min < this.max
                        },
                        __class__: IntIter
                    };
                    var Std = function() {};
                    Std.__name__ = !0, Std.is = function(e, t) {
                        return js.Boot.__instanceof(e, t)
                    }, Std.string = function(e) {
                        return js.Boot.__string_rec(e, "")
                    }, Std.int = function(e) {
                        return 0 | e
                    }, Std.parseInt = function(e) {
                        var t = parseInt(e, 10);
                        return 0 != t || 120 != HxOverrides.cca(e, 1) && 88 != HxOverrides.cca(e, 1) || (t = parseInt(e)), isNaN(t) ? null : t
                    }, Std.parseFloat = function(e) {
                        return parseFloat(e)
                    }, Std.random = function(e) {
                        return Math.floor(Math.random() * e)
                    };
                    var com = com || {};
                    com.wiris || (com.wiris = {}), com.wiris.js || (com.wiris.js = {}), com.wiris.js.JsPluginTools = function() {
                        this.tryReady()
                    }, com.wiris.js.JsPluginTools.__name__ = !0, com.wiris.js.JsPluginTools.main = function() {
                        var e;
                        e = com.wiris.js.JsPluginTools.getInstance(), haxe.Timer.delay($bind(e, e.tryReady), 100)
                    }, com.wiris.js.JsPluginTools.getInstance = function() {
                        return null == com.wiris.js.JsPluginTools.instance && (com.wiris.js.JsPluginTools.instance = new com.wiris.js.JsPluginTools), com.wiris.js.JsPluginTools.instance
                    }, com.wiris.js.JsPluginTools.bypassEncapsulation = function() {
                        null == window.com && (window.com = {}), null == window.com.wiris && (window.com.wiris = {}), null == window.com.wiris.js && (window.com.wiris.js = {}), null == window.com.wiris.js.JsPluginTools && (window.com.wiris.js.JsPluginTools = com.wiris.js.JsPluginTools.getInstance())
                    }, com.wiris.js.JsPluginTools.prototype = {
                        md5encode: function(e) {
                            return haxe.Md5.encode(e)
                        },
                        doLoad: function() {
                            this.ready = !0, com.wiris.js.JsPluginTools.instance = this, com.wiris.js.JsPluginTools.bypassEncapsulation()
                        },
                        tryReady: function() {
                            this.ready = !1, js.Lib.document.readyState && (this.doLoad(), this.ready = !0), this.ready || haxe.Timer.delay($bind(this, this.tryReady), 100)
                        },
                        __class__: com.wiris.js.JsPluginTools
                    };
                    var haxe = haxe || {};
                    haxe.Log = function() {}, haxe.Log.__name__ = !0, haxe.Log.trace = function(e, t) {
                        js.Boot.__trace(e, t)
                    }, haxe.Log.clear = function() {
                        js.Boot.__clear_trace()
                    }, haxe.Md5 = function() {}, haxe.Md5.__name__ = !0, haxe.Md5.encode = function(e) {
                        return (new haxe.Md5).doEncode(e)
                    }, haxe.Md5.prototype = {
                        doEncode: function(e) {
                            for (var t = this.str2blks(e), n = 1732584193, i = -271733879, r = -1732584194, a = 271733878, o = 0; o < t.length;) {
                                var s = n,
                                    l = i,
                                    c = r,
                                    d = a;
                                0, n = this.ff(n, i, r, a, t[o], 7, -680876936), a = this.ff(a, n, i, r, t[o + 1], 12, -389564586), r = this.ff(r, a, n, i, t[o + 2], 17, 606105819), i = this.ff(i, r, a, n, t[o + 3], 22, -1044525330), n = this.ff(n, i, r, a, t[o + 4], 7, -176418897), a = this.ff(a, n, i, r, t[o + 5], 12, 1200080426), r = this.ff(r, a, n, i, t[o + 6], 17, -1473231341), i = this.ff(i, r, a, n, t[o + 7], 22, -45705983), n = this.ff(n, i, r, a, t[o + 8], 7, 1770035416), a = this.ff(a, n, i, r, t[o + 9], 12, -1958414417), r = this.ff(r, a, n, i, t[o + 10], 17, -42063), i = this.ff(i, r, a, n, t[o + 11], 22, -1990404162), n = this.ff(n, i, r, a, t[o + 12], 7, 1804603682), a = this.ff(a, n, i, r, t[o + 13], 12, -40341101), r = this.ff(r, a, n, i, t[o + 14], 17, -1502002290), i = this.ff(i, r, a, n, t[o + 15], 22, 1236535329), n = this.gg(n, i, r, a, t[o + 1], 5, -165796510), a = this.gg(a, n, i, r, t[o + 6], 9, -1069501632), r = this.gg(r, a, n, i, t[o + 11], 14, 643717713), i = this.gg(i, r, a, n, t[o], 20, -373897302), n = this.gg(n, i, r, a, t[o + 5], 5, -701558691), a = this.gg(a, n, i, r, t[o + 10], 9, 38016083), r = this.gg(r, a, n, i, t[o + 15], 14, -660478335), i = this.gg(i, r, a, n, t[o + 4], 20, -405537848), n = this.gg(n, i, r, a, t[o + 9], 5, 568446438), a = this.gg(a, n, i, r, t[o + 14], 9, -1019803690), r = this.gg(r, a, n, i, t[o + 3], 14, -187363961), i = this.gg(i, r, a, n, t[o + 8], 20, 1163531501), n = this.gg(n, i, r, a, t[o + 13], 5, -1444681467), a = this.gg(a, n, i, r, t[o + 2], 9, -51403784), r = this.gg(r, a, n, i, t[o + 7], 14, 1735328473), i = this.gg(i, r, a, n, t[o + 12], 20, -1926607734), n = this.hh(n, i, r, a, t[o + 5], 4, -378558), a = this.hh(a, n, i, r, t[o + 8], 11, -2022574463), r = this.hh(r, a, n, i, t[o + 11], 16, 1839030562), i = this.hh(i, r, a, n, t[o + 14], 23, -35309556), n = this.hh(n, i, r, a, t[o + 1], 4, -1530992060), a = this.hh(a, n, i, r, t[o + 4], 11, 1272893353), r = this.hh(r, a, n, i, t[o + 7], 16, -155497632), i = this.hh(i, r, a, n, t[o + 10], 23, -1094730640), n = this.hh(n, i, r, a, t[o + 13], 4, 681279174), a = this.hh(a, n, i, r, t[o], 11, -358537222), r = this.hh(r, a, n, i, t[o + 3], 16, -722521979), i = this.hh(i, r, a, n, t[o + 6], 23, 76029189), n = this.hh(n, i, r, a, t[o + 9], 4, -640364487), a = this.hh(a, n, i, r, t[o + 12], 11, -421815835), r = this.hh(r, a, n, i, t[o + 15], 16, 530742520), i = this.hh(i, r, a, n, t[o + 2], 23, -995338651), n = this.ii(n, i, r, a, t[o], 6, -198630844), a = this.ii(a, n, i, r, t[o + 7], 10, 1126891415), r = this.ii(r, a, n, i, t[o + 14], 15, -1416354905), i = this.ii(i, r, a, n, t[o + 5], 21, -57434055), n = this.ii(n, i, r, a, t[o + 12], 6, 1700485571), a = this.ii(a, n, i, r, t[o + 3], 10, -1894986606), r = this.ii(r, a, n, i, t[o + 10], 15, -1051523), i = this.ii(i, r, a, n, t[o + 1], 21, -2054922799), n = this.ii(n, i, r, a, t[o + 8], 6, 1873313359), a = this.ii(a, n, i, r, t[o + 15], 10, -30611744), r = this.ii(r, a, n, i, t[o + 6], 15, -1560198380), i = this.ii(i, r, a, n, t[o + 13], 21, 1309151649), n = this.ii(n, i, r, a, t[o + 4], 6, -145523070), a = this.ii(a, n, i, r, t[o + 11], 10, -1120210379), r = this.ii(r, a, n, i, t[o + 2], 15, 718787259), i = this.ii(i, r, a, n, t[o + 9], 21, -343485551), n = this.addme(n, s), i = this.addme(i, l), r = this.addme(r, c), a = this.addme(a, d), o += 16
                            }
                            return this.rhex(n) + this.rhex(i) + this.rhex(r) + this.rhex(a)
                        },
                        ii: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitXOR(n, this.bitOR(t, ~i)), e, t, r, a, o)
                        },
                        hh: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitXOR(this.bitXOR(t, n), i), e, t, r, a, o)
                        },
                        gg: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitOR(this.bitAND(t, i), this.bitAND(n, ~i)), e, t, r, a, o)
                        },
                        ff: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitOR(this.bitAND(t, n), this.bitAND(~t, i)), e, t, r, a, o)
                        },
                        cmn: function(e, t, n, i, r, a) {
                            return this.addme(this.rol(this.addme(this.addme(t, e), this.addme(i, a)), r), n)
                        },
                        rol: function(e, t) {
                            return e << t | e >>> 32 - t
                        },
                        str2blks: function(e) {
                            for (var t = 1 + (e.length + 8 >> 6), n = new Array, i = 0, r = 16 * t; i < r;) {
                                n[a = i++] = 0
                            }
                            for (var a = 0; a < e.length;) n[a >> 2] |= HxOverrides.cca(e, a) << (8 * e.length + a) % 4 * 8, a++;
                            n[a >> 2] |= 128 << (8 * e.length + a) % 4 * 8;
                            var o = 8 * e.length,
                                s = 16 * t - 2;
                            return n[s] = 255 & o, n[s] |= (o >>> 8 & 255) << 8, n[s] |= (o >>> 16 & 255) << 16, n[s] |= (o >>> 24 & 255) << 24, n
                        },
                        rhex: function(e) {
                            for (var t = "", n = "0123456789abcdef", i = 0; i < 4;) {
                                var r = i++;
                                t += n.charAt(e >> 8 * r + 4 & 15) + n.charAt(e >> 8 * r & 15)
                            }
                            return t
                        },
                        addme: function(e, t) {
                            var n = (65535 & e) + (65535 & t);
                            return (e >> 16) + (t >> 16) + (n >> 16) << 16 | 65535 & n
                        },
                        bitAND: function(e, t) {
                            return (e >>> 1 & t >>> 1) << 1 | 1 & e & t
                        },
                        bitXOR: function(e, t) {
                            return (e >>> 1 ^ t >>> 1) << 1 | 1 & e ^ 1 & t
                        },
                        bitOR: function(e, t) {
                            return (e >>> 1 | t >>> 1) << 1 | (1 & e | 1 & t)
                        },
                        __class__: haxe.Md5
                    }, haxe.Timer = function(e) {
                        var t = this;
                        this.id = window.setInterval((function() {
                            t.run()
                        }), e)
                    }, haxe.Timer.__name__ = !0, haxe.Timer.delay = function(e, t) {
                        var n = new haxe.Timer(t);
                        return n.run = function() {
                            n.stop(), e()
                        }, n
                    }, haxe.Timer.measure = function(e, t) {
                        var n = haxe.Timer.stamp(),
                            i = e();
                        return haxe.Log.trace(haxe.Timer.stamp() - n + "s", t), i
                    }, haxe.Timer.stamp = function() {
                        return (new Date).getTime() / 1e3
                    }, haxe.Timer.prototype = {
                        run: function() {},
                        stop: function() {
                            null != this.id && (window.clearInterval(this.id), this.id = null)
                        },
                        __class__: haxe.Timer
                    };
                    var js = js || {},
                        $_;

                    function $bind(e, t) {
                        var n = function e() {
                            return e.method.apply(e.scope, arguments)
                        };
                        return n.scope = e, n.method = t, n
                    }
                    js.Boot = function() {}, js.Boot.__name__ = !0, js.Boot.__unhtml = function(e) {
                        return e.split("&").join("&amp;").split("<").join("&lt;").split(">").join("&gt;")
                    }, js.Boot.__trace = function(e, t) {
                        var n, i = null != t ? t.fileName + ":" + t.lineNumber + ": " : "";
                        i += js.Boot.__string_rec(e, ""), "undefined" != typeof document && null != (n = document.getElementById("haxe:trace")) ? n.innerHTML += js.Boot.__unhtml(i) + "<br/>" : "undefined" != typeof console && null != console.log && console.log(i)
                    }, js.Boot.__clear_trace = function() {
                        var e = document.getElementById("haxe:trace");
                        null != e && (e.innerHTML = "")
                    }, js.Boot.isClass = function(e) {
                        return e.__name__
                    }, js.Boot.isEnum = function(e) {
                        return e.__ename__
                    }, js.Boot.getClass = function(e) {
                        return e.__class__
                    }, js.Boot.__string_rec = function(e, t) {
                        if (null == e) return "null";
                        if (t.length >= 5) return "<...>";
                        var n = _typeof(e);
                        switch ("function" == n && (e.__name__ || e.__ename__) && (n = "object"), n) {
                            case "object":
                                if (e instanceof Array) {
                                    if (e.__enum__) {
                                        if (2 == e.length) return e[0];
                                        var i = e[0] + "(";
                                        t += "\t";
                                        for (var r = 2, a = e.length; r < a;) {
                                            i += 2 != (o = r++) ? "," + js.Boot.__string_rec(e[o], t) : js.Boot.__string_rec(e[o], t)
                                        }
                                        return i + ")"
                                    }
                                    var o, s = e.length;
                                    i = "[";
                                    t += "\t";
                                    for (a = 0; a < s;) {
                                        var l = a++;
                                        i += (l > 0 ? "," : "") + js.Boot.__string_rec(e[l], t)
                                    }
                                    return i += "]"
                                }
                                var c;
                                try {
                                    c = e.toString
                                } catch (e) {
                                    return "???"
                                }
                                if (null != c && c != Object.toString) {
                                    var d = e.toString();
                                    if ("[object Object]" != d) return d
                                }
                                var u = null;
                                i = "{\n";
                                t += "\t";
                                var m = null != e.hasOwnProperty;
                                for (var u in e) m && !e.hasOwnProperty(u) || "prototype" != u && "__class__" != u && "__super__" != u && "__interfaces__" != u && "__properties__" != u && (2 != i.length && (i += ", \n"), i += t + u + " : " + js.Boot.__string_rec(e[u], t));
                                return i += "\n" + (t = t.substring(1)) + "}";
                            case "function":
                                return "<function>";
                            case "string":
                                return e;
                            default:
                                return String(e)
                        }
                    }, js.Boot.__interfLoop = function(e, t) {
                        if (null == e) return !1;
                        if (e == t) return !0;
                        var n = e.__interfaces__;
                        if (null != n)
                            for (var i = 0, r = n.length; i < r;) {
                                var a = n[i++];
                                if (a == t || js.Boot.__interfLoop(a, t)) return !0
                            }
                        return js.Boot.__interfLoop(e.__super__, t)
                    }, js.Boot.__instanceof = function(e, t) {
                        try {
                            if (e instanceof t) return t != Array || null == e.__enum__;
                            if (js.Boot.__interfLoop(e.__class__, t)) return !0
                        } catch (e) {
                            if (null == t) return !1
                        }
                        switch (t) {
                            case Int:
                                return Math.ceil(e % 2147483648) === e;
                            case Float:
                                return "number" == typeof e;
                            case Bool:
                                return !0 === e || !1 === e;
                            case String:
                                return "string" == typeof e;
                            case Dynamic:
                                return !0;
                            default:
                                return null != e && (t == Class && null != e.__name__ || (t == Enum && null != e.__ename__ || e.__enum__ == t))
                        }
                    }, js.Boot.__cast = function(e, t) {
                        if (js.Boot.__instanceof(e, t)) return e;
                        throw "Cannot cast " + Std.string(e) + " to " + Std.string(t)
                    }, js.Lib = function() {}, js.Lib.__name__ = !0, js.Lib.debug = function() {}, js.Lib.alert = function(e) {
                        alert(js.Boot.__string_rec(e, ""))
                    }, js.Lib.eval = function(code) {
                        return eval(code)
                    }, js.Lib.setErrorHandler = function(e) {
                        js.Lib.onerror = e
                    }, Array.prototype.indexOf && (HxOverrides.remove = function(e, t) {
                        var n = e.indexOf(t);
                        return -1 != n && (e.splice(n, 1), !0)
                    }), Math.__name__ = ["Math"], Math.NaN = Number.NaN, Math.NEGATIVE_INFINITY = Number.NEGATIVE_INFINITY, Math.POSITIVE_INFINITY = Number.POSITIVE_INFINITY, Math.isFinite = function(e) {
                        return isFinite(e)
                    }, Math.isNaN = function(e) {
                        return isNaN(e)
                    }, String.prototype.__class__ = String, String.__name__ = !0, Array.prototype.__class__ = Array, Array.__name__ = !0, Date.prototype.__class__ = Date, Date.__name__ = ["Date"];
                    var Int = {
                            __name__: ["Int"]
                        },
                        Dynamic = {
                            __name__: ["Dynamic"]
                        },
                        Float = Number;
                    Float.__name__ = ["Float"];
                    var Bool = Boolean;
                    Bool.__ename__ = ["Bool"];
                    var Class = {
                            __name__: ["Class"]
                        },
                        Enum = {},
                        Void = {
                            __ename__: ["Void"]
                        };
                    "undefined" != typeof document && (js.Lib.document = document), "undefined" != typeof window && (js.Lib.window = window, js.Lib.window.onerror = function(e, t, n) {
                        var i = js.Lib.onerror;
                        return null != i && i(e, [t + ":" + n])
                    }), com.wiris.js.JsPluginTools.main(), delete Array.prototype.__class__
                })(),
                function() {
                    var HxOverrides = function() {};
                    HxOverrides.__name__ = !0, HxOverrides.dateStr = function(e) {
                        var t = e.getMonth() + 1,
                            n = e.getDate(),
                            i = e.getHours(),
                            r = e.getMinutes(),
                            a = e.getSeconds();
                        return e.getFullYear() + "-" + (t < 10 ? "0" + t : "" + t) + "-" + (n < 10 ? "0" + n : "" + n) + " " + (i < 10 ? "0" + i : "" + i) + ":" + (r < 10 ? "0" + r : "" + r) + ":" + (a < 10 ? "0" + a : "" + a)
                    }, HxOverrides.strDate = function(e) {
                        switch (e.length) {
                            case 8:
                                var t = e.split(":"),
                                    n = new Date;
                                return n.setTime(0), n.setUTCHours(t[0]), n.setUTCMinutes(t[1]), n.setUTCSeconds(t[2]), n;
                            case 10:
                                t = e.split("-");
                                return new Date(t[0], t[1] - 1, t[2], 0, 0, 0);
                            case 19:
                                var i = (t = e.split(" "))[0].split("-"),
                                    r = t[1].split(":");
                                return new Date(i[0], i[1] - 1, i[2], r[0], r[1], r[2]);
                            default:
                                throw "Invalid date format : " + e
                        }
                    }, HxOverrides.cca = function(e, t) {
                        var n = e.charCodeAt(t);
                        if (n == n) return n
                    }, HxOverrides.substr = function(e, t, n) {
                        return null != t && 0 != t && null != n && n < 0 ? "" : (null == n && (n = e.length), t < 0 ? (t = e.length + t) < 0 && (t = 0) : n < 0 && (n = e.length + n - t), e.substr(t, n))
                    }, HxOverrides.remove = function(e, t) {
                        for (var n = 0, i = e.length; n < i;) {
                            if (e[n] == t) return e.splice(n, 1), !0;
                            n++
                        }
                        return !1
                    }, HxOverrides.iter = function(e) {
                        return {
                            cur: 0,
                            arr: e,
                            hasNext: function() {
                                return this.cur < this.arr.length
                            },
                            next: function() {
                                return this.arr[this.cur++]
                            }
                        }
                    };
                    var IntIter = function(e, t) {
                        this.min = e, this.max = t
                    };
                    IntIter.__name__ = !0, IntIter.prototype = {
                        next: function() {
                            return this.min++
                        },
                        hasNext: function() {
                            return this.min < this.max
                        },
                        __class__: IntIter
                    };
                    var Std = function() {};
                    Std.__name__ = !0, Std.is = function(e, t) {
                        return js.Boot.__instanceof(e, t)
                    }, Std.string = function(e) {
                        return js.Boot.__string_rec(e, "")
                    }, Std.int = function(e) {
                        return 0 | e
                    }, Std.parseInt = function(e) {
                        var t = parseInt(e, 10);
                        return 0 != t || 120 != HxOverrides.cca(e, 1) && 88 != HxOverrides.cca(e, 1) || (t = parseInt(e)), isNaN(t) ? null : t
                    }, Std.parseFloat = function(e) {
                        return parseFloat(e)
                    }, Std.random = function(e) {
                        return Math.floor(Math.random() * e)
                    };
                    var com = com || {};
                    com.wiris || (com.wiris = {}), com.wiris.js || (com.wiris.js = {}), com.wiris.js.JsPluginTools = function() {
                        this.tryReady()
                    }, com.wiris.js.JsPluginTools.__name__ = !0, com.wiris.js.JsPluginTools.main = function() {
                        var e;
                        e = com.wiris.js.JsPluginTools.getInstance(), haxe.Timer.delay($bind(e, e.tryReady), 100)
                    }, com.wiris.js.JsPluginTools.getInstance = function() {
                        return null == com.wiris.js.JsPluginTools.instance && (com.wiris.js.JsPluginTools.instance = new com.wiris.js.JsPluginTools), com.wiris.js.JsPluginTools.instance
                    }, com.wiris.js.JsPluginTools.bypassEncapsulation = function() {
                        null == window.com && (window.com = {}), null == window.com.wiris && (window.com.wiris = {}), null == window.com.wiris.js && (window.com.wiris.js = {}), null == window.com.wiris.js.JsPluginTools && (window.com.wiris.js.JsPluginTools = com.wiris.js.JsPluginTools.getInstance())
                    }, com.wiris.js.JsPluginTools.prototype = {
                        md5encode: function(e) {
                            return haxe.Md5.encode(e)
                        },
                        doLoad: function() {
                            this.ready = !0, com.wiris.js.JsPluginTools.instance = this, com.wiris.js.JsPluginTools.bypassEncapsulation()
                        },
                        tryReady: function() {
                            this.ready = !1, js.Lib.document.readyState && (this.doLoad(), this.ready = !0), this.ready || haxe.Timer.delay($bind(this, this.tryReady), 100)
                        },
                        __class__: com.wiris.js.JsPluginTools
                    };
                    var haxe = haxe || {};
                    haxe.Log = function() {}, haxe.Log.__name__ = !0, haxe.Log.trace = function(e, t) {
                        js.Boot.__trace(e, t)
                    }, haxe.Log.clear = function() {
                        js.Boot.__clear_trace()
                    }, haxe.Md5 = function() {}, haxe.Md5.__name__ = !0, haxe.Md5.encode = function(e) {
                        return (new haxe.Md5).doEncode(e)
                    }, haxe.Md5.prototype = {
                        doEncode: function(e) {
                            for (var t = this.str2blks(e), n = 1732584193, i = -271733879, r = -1732584194, a = 271733878, o = 0; o < t.length;) {
                                var s = n,
                                    l = i,
                                    c = r,
                                    d = a;
                                0, n = this.ff(n, i, r, a, t[o], 7, -680876936), a = this.ff(a, n, i, r, t[o + 1], 12, -389564586), r = this.ff(r, a, n, i, t[o + 2], 17, 606105819), i = this.ff(i, r, a, n, t[o + 3], 22, -1044525330), n = this.ff(n, i, r, a, t[o + 4], 7, -176418897), a = this.ff(a, n, i, r, t[o + 5], 12, 1200080426), r = this.ff(r, a, n, i, t[o + 6], 17, -1473231341), i = this.ff(i, r, a, n, t[o + 7], 22, -45705983), n = this.ff(n, i, r, a, t[o + 8], 7, 1770035416), a = this.ff(a, n, i, r, t[o + 9], 12, -1958414417), r = this.ff(r, a, n, i, t[o + 10], 17, -42063), i = this.ff(i, r, a, n, t[o + 11], 22, -1990404162), n = this.ff(n, i, r, a, t[o + 12], 7, 1804603682), a = this.ff(a, n, i, r, t[o + 13], 12, -40341101), r = this.ff(r, a, n, i, t[o + 14], 17, -1502002290), i = this.ff(i, r, a, n, t[o + 15], 22, 1236535329), n = this.gg(n, i, r, a, t[o + 1], 5, -165796510), a = this.gg(a, n, i, r, t[o + 6], 9, -1069501632), r = this.gg(r, a, n, i, t[o + 11], 14, 643717713), i = this.gg(i, r, a, n, t[o], 20, -373897302), n = this.gg(n, i, r, a, t[o + 5], 5, -701558691), a = this.gg(a, n, i, r, t[o + 10], 9, 38016083), r = this.gg(r, a, n, i, t[o + 15], 14, -660478335), i = this.gg(i, r, a, n, t[o + 4], 20, -405537848), n = this.gg(n, i, r, a, t[o + 9], 5, 568446438), a = this.gg(a, n, i, r, t[o + 14], 9, -1019803690), r = this.gg(r, a, n, i, t[o + 3], 14, -187363961), i = this.gg(i, r, a, n, t[o + 8], 20, 1163531501), n = this.gg(n, i, r, a, t[o + 13], 5, -1444681467), a = this.gg(a, n, i, r, t[o + 2], 9, -51403784), r = this.gg(r, a, n, i, t[o + 7], 14, 1735328473), i = this.gg(i, r, a, n, t[o + 12], 20, -1926607734), n = this.hh(n, i, r, a, t[o + 5], 4, -378558), a = this.hh(a, n, i, r, t[o + 8], 11, -2022574463), r = this.hh(r, a, n, i, t[o + 11], 16, 1839030562), i = this.hh(i, r, a, n, t[o + 14], 23, -35309556), n = this.hh(n, i, r, a, t[o + 1], 4, -1530992060), a = this.hh(a, n, i, r, t[o + 4], 11, 1272893353), r = this.hh(r, a, n, i, t[o + 7], 16, -155497632), i = this.hh(i, r, a, n, t[o + 10], 23, -1094730640), n = this.hh(n, i, r, a, t[o + 13], 4, 681279174), a = this.hh(a, n, i, r, t[o], 11, -358537222), r = this.hh(r, a, n, i, t[o + 3], 16, -722521979), i = this.hh(i, r, a, n, t[o + 6], 23, 76029189), n = this.hh(n, i, r, a, t[o + 9], 4, -640364487), a = this.hh(a, n, i, r, t[o + 12], 11, -421815835), r = this.hh(r, a, n, i, t[o + 15], 16, 530742520), i = this.hh(i, r, a, n, t[o + 2], 23, -995338651), n = this.ii(n, i, r, a, t[o], 6, -198630844), a = this.ii(a, n, i, r, t[o + 7], 10, 1126891415), r = this.ii(r, a, n, i, t[o + 14], 15, -1416354905), i = this.ii(i, r, a, n, t[o + 5], 21, -57434055), n = this.ii(n, i, r, a, t[o + 12], 6, 1700485571), a = this.ii(a, n, i, r, t[o + 3], 10, -1894986606), r = this.ii(r, a, n, i, t[o + 10], 15, -1051523), i = this.ii(i, r, a, n, t[o + 1], 21, -2054922799), n = this.ii(n, i, r, a, t[o + 8], 6, 1873313359), a = this.ii(a, n, i, r, t[o + 15], 10, -30611744), r = this.ii(r, a, n, i, t[o + 6], 15, -1560198380), i = this.ii(i, r, a, n, t[o + 13], 21, 1309151649), n = this.ii(n, i, r, a, t[o + 4], 6, -145523070), a = this.ii(a, n, i, r, t[o + 11], 10, -1120210379), r = this.ii(r, a, n, i, t[o + 2], 15, 718787259), i = this.ii(i, r, a, n, t[o + 9], 21, -343485551), n = this.addme(n, s), i = this.addme(i, l), r = this.addme(r, c), a = this.addme(a, d), o += 16
                            }
                            return this.rhex(n) + this.rhex(i) + this.rhex(r) + this.rhex(a)
                        },
                        ii: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitXOR(n, this.bitOR(t, ~i)), e, t, r, a, o)
                        },
                        hh: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitXOR(this.bitXOR(t, n), i), e, t, r, a, o)
                        },
                        gg: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitOR(this.bitAND(t, i), this.bitAND(n, ~i)), e, t, r, a, o)
                        },
                        ff: function(e, t, n, i, r, a, o) {
                            return this.cmn(this.bitOR(this.bitAND(t, n), this.bitAND(~t, i)), e, t, r, a, o)
                        },
                        cmn: function(e, t, n, i, r, a) {
                            return this.addme(this.rol(this.addme(this.addme(t, e), this.addme(i, a)), r), n)
                        },
                        rol: function(e, t) {
                            return e << t | e >>> 32 - t
                        },
                        str2blks: function(e) {
                            for (var t = 1 + (e.length + 8 >> 6), n = new Array, i = 0, r = 16 * t; i < r;) {
                                n[a = i++] = 0
                            }
                            for (var a = 0; a < e.length;) n[a >> 2] |= HxOverrides.cca(e, a) << (8 * e.length + a) % 4 * 8, a++;
                            n[a >> 2] |= 128 << (8 * e.length + a) % 4 * 8;
                            var o = 8 * e.length,
                                s = 16 * t - 2;
                            return n[s] = 255 & o, n[s] |= (o >>> 8 & 255) << 8, n[s] |= (o >>> 16 & 255) << 16, n[s] |= (o >>> 24 & 255) << 24, n
                        },
                        rhex: function(e) {
                            for (var t = "", n = "0123456789abcdef", i = 0; i < 4;) {
                                var r = i++;
                                t += n.charAt(e >> 8 * r + 4 & 15) + n.charAt(e >> 8 * r & 15)
                            }
                            return t
                        },
                        addme: function(e, t) {
                            var n = (65535 & e) + (65535 & t);
                            return (e >> 16) + (t >> 16) + (n >> 16) << 16 | 65535 & n
                        },
                        bitAND: function(e, t) {
                            return (e >>> 1 & t >>> 1) << 1 | 1 & e & t
                        },
                        bitXOR: function(e, t) {
                            return (e >>> 1 ^ t >>> 1) << 1 | 1 & e ^ 1 & t
                        },
                        bitOR: function(e, t) {
                            return (e >>> 1 | t >>> 1) << 1 | (1 & e | 1 & t)
                        },
                        __class__: haxe.Md5
                    }, haxe.Timer = function(e) {
                        var t = this;
                        this.id = window.setInterval((function() {
                            t.run()
                        }), e)
                    }, haxe.Timer.__name__ = !0, haxe.Timer.delay = function(e, t) {
                        var n = new haxe.Timer(t);
                        return n.run = function() {
                            n.stop(), e()
                        }, n
                    }, haxe.Timer.measure = function(e, t) {
                        var n = haxe.Timer.stamp(),
                            i = e();
                        return haxe.Log.trace(haxe.Timer.stamp() - n + "s", t), i
                    }, haxe.Timer.stamp = function() {
                        return (new Date).getTime() / 1e3
                    }, haxe.Timer.prototype = {
                        run: function() {},
                        stop: function() {
                            null != this.id && (window.clearInterval(this.id), this.id = null)
                        },
                        __class__: haxe.Timer
                    };
                    var js = js || {},
                        $_;

                    function $bind(e, t) {
                        var n = function e() {
                            return e.method.apply(e.scope, arguments)
                        };
                        return n.scope = e, n.method = t, n
                    }
                    js.Boot = function() {}, js.Boot.__name__ = !0, js.Boot.__unhtml = function(e) {
                        return e.split("&").join("&amp;").split("<").join("&lt;").split(">").join("&gt;")
                    }, js.Boot.__trace = function(e, t) {
                        var n, i = null != t ? t.fileName + ":" + t.lineNumber + ": " : "";
                        i += js.Boot.__string_rec(e, ""), "undefined" != typeof document && null != (n = document.getElementById("haxe:trace")) ? n.innerHTML += js.Boot.__unhtml(i) + "<br/>" : "undefined" != typeof console && null != console.log && console.log(i)
                    }, js.Boot.__clear_trace = function() {
                        var e = document.getElementById("haxe:trace");
                        null != e && (e.innerHTML = "")
                    }, js.Boot.isClass = function(e) {
                        return e.__name__
                    }, js.Boot.isEnum = function(e) {
                        return e.__ename__
                    }, js.Boot.getClass = function(e) {
                        return e.__class__
                    }, js.Boot.__string_rec = function(e, t) {
                        if (null == e) return "null";
                        if (t.length >= 5) return "<...>";
                        var n = _typeof(e);
                        switch ("function" == n && (e.__name__ || e.__ename__) && (n = "object"), n) {
                            case "object":
                                if (e instanceof Array) {
                                    if (e.__enum__) {
                                        if (2 == e.length) return e[0];
                                        var i = e[0] + "(";
                                        t += "\t";
                                        for (var r = 2, a = e.length; r < a;) {
                                            i += 2 != (o = r++) ? "," + js.Boot.__string_rec(e[o], t) : js.Boot.__string_rec(e[o], t)
                                        }
                                        return i + ")"
                                    }
                                    var o, s = e.length;
                                    i = "[";
                                    t += "\t";
                                    for (a = 0; a < s;) {
                                        var l = a++;
                                        i += (l > 0 ? "," : "") + js.Boot.__string_rec(e[l], t)
                                    }
                                    return i += "]"
                                }
                                var c;
                                try {
                                    c = e.toString
                                } catch (e) {
                                    return "???"
                                }
                                if (null != c && c != Object.toString) {
                                    var d = e.toString();
                                    if ("[object Object]" != d) return d
                                }
                                var u = null;
                                i = "{\n";
                                t += "\t";
                                var m = null != e.hasOwnProperty;
                                for (var u in e) m && !e.hasOwnProperty(u) || "prototype" != u && "__class__" != u && "__super__" != u && "__interfaces__" != u && "__properties__" != u && (2 != i.length && (i += ", \n"), i += t + u + " : " + js.Boot.__string_rec(e[u], t));
                                return i += "\n" + (t = t.substring(1)) + "}";
                            case "function":
                                return "<function>";
                            case "string":
                                return e;
                            default:
                                return String(e)
                        }
                    }, js.Boot.__interfLoop = function(e, t) {
                        if (null == e) return !1;
                        if (e == t) return !0;
                        var n = e.__interfaces__;
                        if (null != n)
                            for (var i = 0, r = n.length; i < r;) {
                                var a = n[i++];
                                if (a == t || js.Boot.__interfLoop(a, t)) return !0
                            }
                        return js.Boot.__interfLoop(e.__super__, t)
                    }, js.Boot.__instanceof = function(e, t) {
                        try {
                            if (e instanceof t) return t != Array || null == e.__enum__;
                            if (js.Boot.__interfLoop(e.__class__, t)) return !0
                        } catch (e) {
                            if (null == t) return !1
                        }
                        switch (t) {
                            case Int:
                                return Math.ceil(e % 2147483648) === e;
                            case Float:
                                return "number" == typeof e;
                            case Bool:
                                return !0 === e || !1 === e;
                            case String:
                                return "string" == typeof e;
                            case Dynamic:
                                return !0;
                            default:
                                return null != e && (t == Class && null != e.__name__ || (t == Enum && null != e.__ename__ || e.__enum__ == t))
                        }
                    }, js.Boot.__cast = function(e, t) {
                        if (js.Boot.__instanceof(e, t)) return e;
                        throw "Cannot cast " + Std.string(e) + " to " + Std.string(t)
                    }, js.Lib = function() {}, js.Lib.__name__ = !0, js.Lib.debug = function() {}, js.Lib.alert = function(e) {
                        alert(js.Boot.__string_rec(e, ""))
                    }, js.Lib.eval = function(code) {
                        return eval(code)
                    }, js.Lib.setErrorHandler = function(e) {
                        js.Lib.onerror = e
                    }, Array.prototype.indexOf && (HxOverrides.remove = function(e, t) {
                        var n = e.indexOf(t);
                        return -1 != n && (e.splice(n, 1), !0)
                    }), Math.__name__ = ["Math"], Math.NaN = Number.NaN, Math.NEGATIVE_INFINITY = Number.NEGATIVE_INFINITY, Math.POSITIVE_INFINITY = Number.POSITIVE_INFINITY, Math.isFinite = function(e) {
                        return isFinite(e)
                    }, Math.isNaN = function(e) {
                        return isNaN(e)
                    }, String.prototype.__class__ = String, String.__name__ = !0, Array.prototype.__class__ = Array, Array.__name__ = !0, Date.prototype.__class__ = Date, Date.__name__ = ["Date"];
                    var Int = {
                            __name__: ["Int"]
                        },
                        Dynamic = {
                            __name__: ["Dynamic"]
                        },
                        Float = Number;
                    Float.__name__ = ["Float"];
                    var Bool = Boolean;
                    Bool.__ename__ = ["Bool"];
                    var Class = {
                            __name__: ["Class"]
                        },
                        Enum = {},
                        Void = {
                            __ename__: ["Void"]
                        };
                    "undefined" != typeof document && (js.Lib.document = document), "undefined" != typeof window && (js.Lib.window = window, js.Lib.window.onerror = function(e, t, n) {
                        var i = js.Lib.onerror;
                        return null != i && i(e, [t + ":" + n])
                    }), com.wiris.js.JsPluginTools.main()
                }(), delete Array.prototype.__class__
            },
            775: (e, t, n) => {
                n.d(t, {
                    Z: () => a
                });
                var i = n(645),
                    r = n.n(i)()((function(e) {
                        return e[1]
                    }));
                r.push([e.id, ".wrs_modal_overlay {\n  position: fixed;\n  font-family: arial, sans-serif;\n  top: 0;\n  right: 0;\n  left: 0;\n  bottom: 0;\n  background: rgba(0, 0, 0, 0.8);\n  z-index: 999998;\n  opacity: 0.65;\n  pointer-events: auto;\n}\n\n.wrs_modal_overlay.wrs_modal_ios {\n  visibility: hidden;\n  display: none;\n}\n\n.wrs_modal_overlay.wrs_modal_android {\n  visibility: hidden;\n  display: none;\n}\n\n.wrs_modal_overlay.wrs_modal_ios.moodle {\n  position: fixed;\n}\n\n.wrs_modal_overlay.wrs_modal_desktop.wrs_stack {\n  background: rgba(0, 0, 0, 0);\n  display: none;\n}\n\n.wrs_modal_overlay.wrs_modal_desktop.wrs_maximized {\n  background: rgba(0, 0, 0, 0.8);\n}\n\n.wrs_modal_overlay.wrs_modal_desktop.wrs_minimized {\n  background: rgba(0, 0, 0, 0);\n  display: none;\n}\n\n.wrs_modal_overlay.wrs_modal_desktop.wrs_closed {\n  background: rgba(0, 0, 0, 0);\n  display: none;\n}\n\n.wrs_modal_title {\n  color: #fff;\n  padding: 5px 0 5px 10px;\n  -moz-user-select: none;\n  -webkit-user-select: none;\n  -ms-user-select: none;\n  user-select: none;\n  text-align: left;\n}\n\n.wrs_modal_close_button {\n  float: right;\n  cursor: pointer;\n  color: #fff;\n  padding: 5px 10px 5px 0;\n  margin: 10px 7px 0 0;\n  background-repeat: no-repeat;\n}\n\n.wrs_modal_minimize_button {\n  float: right;\n  cursor: pointer;\n  color: #fff;\n  padding: 5px 10px 5px 0;\n  top: inherit;\n  margin: 10px 7px 0 0;\n}\n\n.wrs_modal_stack_button {\n  float: right;\n  cursor: pointer;\n  color: #fff;\n  margin: 10px 7px 0 0;\n  padding: 5px 10px 5px 0;\n  top: inherit;\n}\n\n.wrs_modal_stack_button.wrs_stack {\n  visibility: hidden;\n  margin: 0;\n  padding: 0;\n}\n\n.wrs_modal_stack_button.wrs_minimized {\n  visibility: hidden;\n  margin: 0;\n  padding: 0;\n}\n\n.wrs_modal_maximize_button {\n  float: right;\n  cursor: pointer;\n  color: #fff;\n  margin: 10px 7px 0 0;\n  padding: 5px 10px 5px 0;\n  top: inherit;\n}\n\n.wrs_modal_maximize_button.wrs_maximized {\n  visibility: hidden;\n  margin: 0;\n  padding: 0;\n}\n\n.wrs_modal_title_bar {\n  display: block;\n  background-color: #778e9a;\n}\n\n.wrs_modal_dialogContainer {\n  border: none;\n  background: #fafafa;\n  z-index: 999999;\n}\n\n.wrs_modal_dialogContainer.wrs_modal_desktop {\n  font-size: 14px;\n}\n\n.wrs_modal_dialogContainer.wrs_modal_desktop.wrs_maximized {\n  position: fixed;\n}\n\n.wrs_modal_dialogContainer.wrs_modal_desktop.wrs_minimized {\n  position: fixed;\n  top: inherit;\n  margin: 0;\n  margin-right: 10px;\n}\n\n.wrs_modal_dialogContainer.wrs_closed {\n  visibility: hidden;\n  display: none;\n  opacity: 0;\n}\n\n/* Class that exists but hasn't got css properties defined\n.wrs_modal_dialogContainer.wrs_modal_desktop.wrs_minimized.wrs_drag {} */\n\n.wrs_modal_dialogContainer.wrs_modal_desktop.wrs_stack {\n  position: fixed;\n  bottom: 0;\n  right: 0;\n  box-shadow: rgba(0, 0, 0, 0.5) 0 2px 8px;\n}\n\n.wrs_modal_dialogContainer.wrs_drag {\n  box-shadow: rgba(0, 0, 0, 0.5) 0 2px 8px;\n}\n\n.wrs_modal_dialogContainer.wrs_modal_desktop.wrs_drag {\n  box-shadow: rgba(0, 0, 0, 0.5) 0 2px 8px;\n}\n\n.wrs_modal_dialogContainer.wrs_modal_android {\n  margin: auto;\n  position: fixed;\n  width: 99%;\n  height: 99%;\n  overflow: hidden;\n  transform: translate(50%, -50%);\n  top: 50%;\n  right: 50% !important;\n}\n\n.wrs_modal_dialogContainer.wrs_modal_ios {\n  margin: auto;\n  position: fixed;\n  width: 100%;\n  height: 100%;\n  overflow: hidden;\n  transform: translate(50%, -50%);\n  top: 50%;\n  right: 50% !important;\n}\n\n/* Class that exists but hasn't got css properties defined\n.wrs_content_container.wrs_maximized {} */\n\n.wrs_content_container.wrs_minimized {\n  display: none;\n}\n\n/* .wrs_editor {\n    flex-grow: 1;\n} */\n\n.wrs_content_container.wrs_modal_android {\n  width: 100%;\n  flex-grow: 1;\n  display: flex;\n  flex-direction: column;\n}\n\n.wrs_content_container.wrs_modal_android > div:first-child {\n  flex-grow: 1;\n}\n\n.wrs_content_container.wrs_modal_ios > div:first-child {\n  flex-grow: 1;\n}\n\n.wrs_content_container.wrs_modal_desktop > div:first-child {\n  flex-grow: 1;\n}\n\n.wrs_modal_wrapper.wrs_modal_android {\n  margin: auto;\n  display: flex;\n  flex-direction: column;\n  height: 100%;\n  width: 100%;\n}\n\n.wrs_content_container.wrs_modal_desktop {\n  width: 100%;\n  flex-grow: 1;\n  display: flex;\n  flex-direction: column;\n}\n\n.wrs_content_container.wrs_modal_ios {\n  width: 100%;\n  flex-grow: 1;\n  display: flex;\n  flex-direction: column;\n}\n\n.wrs_modal_wrapper.wrs_modal_ios {\n  margin: auto;\n  display: flex;\n  flex-direction: column;\n  height: 100%;\n  width: 100%;\n}\n\n.wrs_virtual_keyboard {\n  height: 100%;\n  width: 100%;\n  top: 0;\n  left: 50%;\n  transform: translate(-50%, 0%);\n}\n\n@media all and (orientation: portrait) {\n  .wrs_modal_dialogContainer.wrs_modal_mobile {\n    width: 100vmin;\n    height: 100vmin;\n    margin: auto;\n    border-width: 0;\n  }\n\n  .wrs_modal_wrapper.wrs_modal_mobile {\n    width: 100vmin;\n    height: 100vmin;\n    margin: auto;\n  }\n}\n\n@media all and (orientation: landscape) {\n  .wrs_modal_dialogContainer.wrs_modal_mobile {\n    width: 100vmin;\n    height: 100vmin;\n    margin: auto;\n    border-width: 0;\n  }\n\n  .wrs_modal_wrapper.wrs_modal_mobile {\n    width: 100vmin;\n    height: 100vmin;\n    margin: auto;\n  }\n}\n\n.wrs_modal_dialogContainer.wrs_modal_badStock {\n  width: 100%;\n  height: 280px;\n  margin: 0 auto;\n  border-width: 0;\n}\n\n.wrs_modal_wrapper.wrs_modal_badStock {\n  width: 100%;\n  height: 280px;\n  margin: 0 auto;\n  border-width: 0;\n}\n\n.wrs_noselect {\n  -moz-user-select: none;\n  -khtml-user-select: none;\n  -webkit-user-select: none;\n  -ms-user-select: none;\n  user-select: none;\n}\n\n.wrs_bottom_right_resizer {\n  width: 10px;\n  height: 10px;\n  color: #778e9a;\n  position: absolute;\n  right: 4px;\n  bottom: 8px;\n  cursor: se-resize;\n  -moz-user-select: none;\n  -webkit-user-select: none;\n  -ms-user-select: none;\n  user-select: none;\n}\n\n.wrs_bottom_left_resizer {\n  width: 15px;\n  height: 15px;\n  color: #778e9a;\n  position: absolute;\n  left: 0;\n  top: 0;\n  cursor: se-resize;\n}\n\n.wrs_modal_controls {\n  height: 42px;\n  margin: 3px 0;\n  overflow: hidden;\n  line-height: normal;\n}\n\n.wrs_modal_links {\n  margin: 10px auto;\n  margin-bottom: 0;\n  font-family: arial, sans-serif;\n  padding: 6px;\n  display: inline;\n  float: right;\n  text-align: right;\n}\n\n.wrs_modal_links > a {\n  text-decoration: none;\n  color: #778e9a;\n  font-size: 16px;\n}\n\n.wrs_modal_button_cancel,\n.wrs_modal_button_cancel:hover,\n.wrs_modal_button_cancel:visited,\n.wrs_modal_button_cancel:active,\n.wrs_modal_button_cancel:focus {\n  min-width: 80px;\n  font-size: 14px;\n  border-radius: 3px;\n  border: 1px solid #778e9a;\n  padding: 6px 8px;\n  margin: 10px auto;\n  margin-left: 5px;\n  margin-bottom: 0;\n  cursor: pointer;\n  font-family: arial, sans-serif;\n  background-color: #ddd;\n  height: 32px;\n}\n\n.wrs_modal_button_accept,\n.wrs_modal_button_accept:hover,\n.wrs_modal_button_accept:visited,\n.wrs_modal_button_accept:active,\n.wrs_modal_button_accept:focus {\n  min-width: 80px;\n  font-size: 14px;\n  border-radius: 3px;\n  border: 1px solid #778e9a;\n  padding: 6px 8px;\n  margin: 10px auto;\n  margin-right: 5px;\n  margin-bottom: 0;\n  color: #fff;\n  background: #778e9a;\n  cursor: pointer;\n  font-family: arial, sans-serif;\n  height: 32px;\n}\n\n.wrs_editor_vertical_bar {\n  height: 20px;\n  float: right;\n  background: none;\n  width: 20px;\n  cursor: pointer;\n}\n\n.wrs_modal_buttons_container {\n  display: inline;\n  float: left;\n}\n\n.wrs_modal_buttons_container.wrs_modalAndroid {\n  padding-left: 6px;\n}\n\n.wrs_modal_buttons_container.wrs_modalDesktop {\n  padding-left: 0;\n}\n\n.wrs_modal_buttons_container > button {\n  line-height: normal;\n  background-image: none;\n}\n\n.wrs_modal_wrapper {\n  margin: 6px;\n  display: flex;\n  flex-direction: column;\n}\n\n.wrs_modal_wrapper.wrs_modal_desktop.wrs_minimized {\n  display: none;\n}\n\n@media only screen and (max-device-width: 480px) and (orientation: portrait) {\n  #wrs_modal_wrapper {\n    width: 140%;\n  }\n}\n\n.wrs_popupmessage_overlay_envolture {\n  display: none;\n  width: 100%;\n}\n\n.wrs_popupmessage_overlay {\n  position: absolute;\n  width: 100%;\n  height: 100%;\n  top: 0;\n  left: 0;\n  right: 0;\n  bottom: 0;\n  background-color: rgba(0, 0, 0, 0.5);\n  z-index: 4;\n  cursor: pointer;\n}\n\n.wrs_popupmessage_panel {\n  top: 50%;\n  left: 50%;\n  transform: translate(-50%, -50%);\n  position: absolute;\n  background: white;\n  max-width: 500px;\n  width: 75%;\n  border-radius: 2px;\n  padding: 20px;\n  font-family: sans-serif;\n  font-size: 15px;\n  text-align: left;\n  color: #2e2e2e;\n  z-index: 5;\n  max-height: 75%;\n  overflow: auto;\n}\n\n.wrs_popupmessage_button_area {\n  margin: 10px 0 0 0;\n}\n\n.wrs_panelContainer * {\n  border: 0;\n}\n\n.wrs_button_cancel,\n.wrs_button_cancel:hover,\n.wrs_button_cancel:visited,\n.wrs_button_cancel:active,\n.wrs_button_cancel:focus {\n  min-width: 80px;\n  font-size: 14px;\n  border-radius: 3px;\n  border: 1px solid #778e9a;\n  padding: 6px 8px;\n  margin: 10px auto;\n  margin-left: 5px;\n  margin-bottom: 0;\n  cursor: pointer;\n  font-family: arial, sans-serif;\n  background-color: #ddd;\n  background-image: none;\n  height: 32px;\n}\n\n.wrs_button_accept,\n.wrs_button_accept:hover,\n.wrs_button_accept:visited,\n.wrs_button_accept:active,\n.wrs_button_accept:focus {\n  min-width: 80px;\n  font-size: 14px;\n  border-radius: 3px;\n  border: 1px solid #778e9a;\n  padding: 6px 8px;\n  margin: 10px auto;\n  margin-right: 5px;\n  margin-bottom: 0;\n  color: #fff;\n  background: #778e9a;\n  cursor: pointer;\n  font-family: arial, sans-serif;\n  height: 32px;\n}\n\n.wrs_editor button {\n  box-shadow: none;\n}\n\n.wrs_editor .wrs_header button {\n  border-bottom: none;\n  border-bottom-left-radius: 0;\n  border-bottom-right-radius: 0;\n}\n\n.wrs_modal_overlay.wrs_modal_desktop.wrs_stack.wrs_overlay_active {\n  display: block;\n}\n\n/* Fix selection in drupal style */\n.wrs_toolbar tr:focus {\n  background: none;\n}\n\n.wrs_toolbar tr:hover {\n  background: none;\n}\n\n/* End of fix drupal */\n.wrs_modal_rtl .wrs_modal_button_cancel {\n  margin-right: 5px;\n  margin-left: 0;\n}\n\n.wrs_modal_rtl .wrs_modal_button_accept {\n  margin-right: 0;\n  margin-left: 5px;\n}\n\n.wrs_modal_rtl .wrs_button_cancel {\n  margin-right: 5px;\n  margin-left: 0;\n}\n\n.wrs_modal_rtl .wrs_button_accept {\n  margin-right: 0;\n  margin-left: 5px;\n}\n", ""]);
                const a = r
            },
            645: e => {
                e.exports = function(e) {
                    var t = [];
                    return t.toString = function() {
                        return this.map((function(t) {
                            var n = e(t);
                            return t[2] ? "@media ".concat(t[2], " {").concat(n, "}") : n
                        })).join("")
                    }, t.i = function(e, n, i) {
                        "string" == typeof e && (e = [
                            [null, e, ""]
                        ]);
                        var r = {};
                        if (i)
                            for (var a = 0; a < this.length; a++) {
                                var o = this[a][0];
                                null != o && (r[o] = !0)
                            }
                        for (var s = 0; s < e.length; s++) {
                            var l = [].concat(e[s]);
                            i && r[l[0]] || (n && (l[2] ? l[2] = "".concat(n, " and ").concat(l[2]) : l[2] = n), t.push(l))
                        }
                    }, t
                }
            },
            379: (e, t, n) => {
                var i, r = function() {
                        return void 0 === i && (i = Boolean(window && document && document.all && !window.atob)), i
                    },
                    a = function() {
                        var e = {};
                        return function(t) {
                            if (void 0 === e[t]) {
                                var n = document.querySelector(t);
                                if (window.HTMLIFrameElement && n instanceof window.HTMLIFrameElement) try {
                                    n = n.contentDocument.head
                                } catch (e) {
                                    n = null
                                }
                                e[t] = n
                            }
                            return e[t]
                        }
                    }(),
                    o = [];

                function s(e) {
                    for (var t = -1, n = 0; n < o.length; n++)
                        if (o[n].identifier === e) {
                            t = n;
                            break
                        } return t
                }

                function l(e, t) {
                    for (var n = {}, i = [], r = 0; r < e.length; r++) {
                        var a = e[r],
                            l = t.base ? a[0] + t.base : a[0],
                            c = n[l] || 0,
                            d = "".concat(l, " ").concat(c);
                        n[l] = c + 1;
                        var u = s(d),
                            m = {
                                css: a[1],
                                media: a[2],
                                sourceMap: a[3]
                            }; - 1 !== u ? (o[u].references++, o[u].updater(m)) : o.push({
                            identifier: d,
                            updater: f(m, t),
                            references: 1
                        }), i.push(d)
                    }
                    return i
                }

                function c(e) {
                    var t = document.createElement("style"),
                        i = e.attributes || {};
                    if (void 0 === i.nonce) {
                        var r = n.nc;
                        r && (i.nonce = r)
                    }
                    if (Object.keys(i).forEach((function(e) {
                            t.setAttribute(e, i[e])
                        })), "function" == typeof e.insert) e.insert(t);
                    else {
                        var o = a(e.insert || "head");
                        if (!o) throw new Error("Couldn't find a style target. This probably means that the value for the 'insert' parameter is invalid.");
                        o.appendChild(t)
                    }
                    return t
                }
                var d, u = (d = [], function(e, t) {
                    return d[e] = t, d.filter(Boolean).join("\n")
                });

                function m(e, t, n, i) {
                    var r = n ? "" : i.media ? "@media ".concat(i.media, " {").concat(i.css, "}") : i.css;
                    if (e.styleSheet) e.styleSheet.cssText = u(t, r);
                    else {
                        var a = document.createTextNode(r),
                            o = e.childNodes;
                        o[t] && e.removeChild(o[t]), o.length ? e.insertBefore(a, o[t]) : e.appendChild(a)
                    }
                }

                function h(e, t, n) {
                    var i = n.css,
                        r = n.media,
                        a = n.sourceMap;
                    if (r ? e.setAttribute("media", r) : e.removeAttribute("media"), a && "undefined" != typeof btoa && (i += "\n/*# sourceMappingURL=data:application/json;base64,".concat(btoa(unescape(encodeURIComponent(JSON.stringify(a)))), " */")), e.styleSheet) e.styleSheet.cssText = i;
                    else {
                        for (; e.firstChild;) e.removeChild(e.firstChild);
                        e.appendChild(document.createTextNode(i))
                    }
                }
                var g = null,
                    p = 0;

                function f(e, t) {
                    var n, i, r;
                    if (t.singleton) {
                        var a = p++;
                        n = g || (g = c(t)), i = m.bind(null, n, a, !1), r = m.bind(null, n, a, !0)
                    } else n = c(t), i = h.bind(null, n, t), r = function() {
                        ! function(e) {
                            if (null === e.parentNode) return !1;
                            e.parentNode.removeChild(e)
                        }(n)
                    };
                    return i(e),
                        function(t) {
                            if (t) {
                                if (t.css === e.css && t.media === e.media && t.sourceMap === e.sourceMap) return;
                                i(e = t)
                            } else r()
                        }
                }
                e.exports = function(e, t) {
                    (t = t || {}).singleton || "boolean" == typeof t.singleton || (t.singleton = r());
                    var n = l(e = e || [], t);
                    return function(e) {
                        if (e = e || [], "[object Array]" === Object.prototype.toString.call(e)) {
                            for (var i = 0; i < n.length; i++) {
                                var r = s(n[i]);
                                o[r].references--
                            }
                            for (var a = l(e, t), c = 0; c < n.length; c++) {
                                var d = s(n[c]);
                                0 === o[d].references && (o[d].updater(), o.splice(d, 1))
                            }
                            n = a
                        }
                    }
                }
            }
        },
        __webpack_module_cache__ = {};

    function __webpack_require__(e) {
        var t = __webpack_module_cache__[e];
        if (void 0 !== t) return t.exports;
        var n = __webpack_module_cache__[e] = {
            id: e,
            exports: {}
        };
        return __webpack_modules__[e](n, n.exports, __webpack_require__), n.exports
    }
    __webpack_require__.n = e => {
        var t = e && e.__esModule ? () => e.default : () => e;
        return __webpack_require__.d(t, {
            a: t
        }), t
    }, __webpack_require__.d = (e, t) => {
        for (var n in t) __webpack_require__.o(t, n) && !__webpack_require__.o(e, n) && Object.defineProperty(e, n, {
            enumerable: !0,
            get: t[n]
        })
    }, __webpack_require__.o = (e, t) => Object.prototype.hasOwnProperty.call(e, t);
    var __webpack_exports__ = __webpack_require__(785)
})();