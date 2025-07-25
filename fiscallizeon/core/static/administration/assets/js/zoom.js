! function(t, e) {
    "object" == typeof exports && "undefined" != typeof module ? module.exports = e() : "function" == typeof define && define.amd ? define(e) : (t = t || self).Zooming = e()
}(this, function() {
    "use strict";
    var t = "auto",
        n = "zoom-in",
        o = "zoom-out",
        r = "grab",
        a = "move";

    function l(t, e, i) {
        var n = {
            passive: !1
        };
        !(3 < arguments.length && void 0 !== arguments[3]) || arguments[3] ? t.addEventListener(e, i, n) : t.removeEventListener(e, i, n)
    }

    function h(t, e) {
        if (t) {
            var i = new Image;
            i.onload = function() {
                e && e(i)
            }, i.src = t
        }
    }

    function s(t) {
        return t.dataset.original ? t.dataset.original : "A" === t.parentNode.tagName ? t.parentNode.getAttribute("href") : null
    }

    function c(t, e, i) {
        if (e.transition) {
            var n = e.transition;
            delete e.transition, e.transition = n
        }
        if (e.transform) {
            var s = e.transform;
            delete e.transform, e.transform = s
        }
        var o = t.style,
            r = {};
        for (var a in e) i && (r[a] = o[a] || ""), o[a] = e[a];
        return r
    }
    var e = function() {},
        i = {
            enableGrab: !0,
            preloadImage: !1,
            closeOnWindowResize: !0,
            transitionDuration: .4,
            transitionTimingFunction: "cubic-bezier(0.4, 0, 0, 1)",
            bgColor: "rgb(255, 255, 255)",
            bgOpacity: 1,
            scaleBase: 1,
            scaleExtra: .5,
            scrollThreshold: 40,
            zIndex: 998,
            customSize: null,
            onOpen: e,
            onClose: e,
            onGrab: e,
            onMove: e,
            onRelease: e,
            onBeforeOpen: e,
            onBeforeClose: e,
            onBeforeGrab: e,
            onBeforeRelease: e,
            onImageLoading: e,
            onImageLoaded: e
        },
        u = {
            init: function(t) {
                var e, i;
                e = this, i = t, Object.getOwnPropertyNames(Object.getPrototypeOf(e)).forEach(function(t) {
                    e[t] = e[t].bind(i)
                })
            },
            click: function(t) {
                if (t.preventDefault(), f(t)) return window.open(this.target.srcOriginal || t.currentTarget.src, "_blank");
                this.shown ? this.released ? this.close() : this.release() : this.open(t.currentTarget)
            },
            scroll: function() {
                var t = document.documentElement || document.body.parentNode || document.body,
                    e = window.pageXOffset || t.scrollLeft,
                    i = window.pageYOffset || t.scrollTop;
                null === this.lastScrollPosition && (this.lastScrollPosition = {
                    x: e,
                    y: i
                });
                var n = this.lastScrollPosition.x - e,
                    s = this.lastScrollPosition.y - i,
                    o = this.options.scrollThreshold;
                (Math.abs(s) >= o || Math.abs(n) >= o) && (this.lastScrollPosition = null, this.close())
            },
            keydown: function(t) {
                var e;
                ("Escape" === ((e = t).key || e.code) || 27 === e.keyCode) && (this.released ? this.close() : this.release(this.close))
            },
            mousedown: function(t) {
                if (d(t) && !f(t)) {
                    t.preventDefault();
                    var e = t.clientX,
                        i = t.clientY;
                    this.pressTimer = setTimeout(function() {
                        this.grab(e, i)
                    }.bind(this), 200)
                }
            },
            mousemove: function(t) {
                this.released || this.move(t.clientX, t.clientY)
            },
            mouseup: function(t) {
                d(t) && !f(t) && (clearTimeout(this.pressTimer), this.released ? this.close() : this.release())
            },
            touchstart: function(t) {
                t.preventDefault();
                var e = t.touches[0],
                    i = e.clientX,
                    n = e.clientY;
                this.pressTimer = setTimeout(function() {
                    this.grab(i, n)
                }.bind(this), 200)
            },
            touchmove: function(t) {
                if (!this.released) {
                    var e = t.touches[0],
                        i = e.clientX,
                        n = e.clientY;
                    this.move(i, n)
                }
            },
            touchend: function(t) {
                void t.targetTouches.length || (clearTimeout(this.pressTimer), this.released ? this.close() : this.release())
            },
            clickOverlay: function() {
                this.close()
            },
            resizeWindow: function() {
                this.close()
            }
        };

    function d(t) {
        return 0 === t.button
    }

    function f(t) {
        return t.metaKey || t.ctrlKey
    }
    var p = {
            init: function(t) {
                this.el = document.createElement("div"), this.instance = t, this.parent = document.body, c(this.el, {
                    position: "fixed",
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    opacity: 0
                }), this.updateStyle(t.options), l(this.el, "click", t.handler.clickOverlay.bind(t))
            },
            updateStyle: function(t) {
                c(this.el, {
                    zIndex: t.zIndex,
                    backgroundColor: t.bgColor,
                    transition: "opacity\n        " + t.transitionDuration + "s\n        " + t.transitionTimingFunction
                })
            },
            insert: function() {
                this.parent.appendChild(this.el)
            },
            remove: function() {
                this.parent.removeChild(this.el)
            },
            fadeIn: function() {
                this.el.offsetWidth, this.el.style.opacity = this.instance.options.bgOpacity
            },
            fadeOut: function() {
                this.el.style.opacity = 0
            }
        },
        m = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(t) {
            return typeof t
        } : function(t) {
            return t && "function" == typeof Symbol && t.constructor === Symbol && t !== Symbol.prototype ? "symbol" : typeof t
        },
        y = function() {
            function n(t, e) {
                for (var i = 0; i < e.length; i++) {
                    var n = e[i];
                    n.enumerable = n.enumerable || !1, n.configurable = !0, "value" in n && (n.writable = !0), Object.defineProperty(t, n.key, n)
                }
            }
            return function(t, e, i) {
                return e && n(t.prototype, e), i && n(t, i), t
            }
        }(),
        g = Object.assign || function(t) {
            for (var e = 1; e < arguments.length; e++) {
                var i = arguments[e];
                for (var n in i) Object.prototype.hasOwnProperty.call(i, n) && (t[n] = i[n])
            }
            return t
        },
        v = {
            init: function(t, e) {
                this.el = t, this.instance = e, this.srcThumbnail = this.el.getAttribute("src"), this.srcset = this.el.getAttribute("srcset"), this.srcOriginal = s(this.el), this.rect = this.el.getBoundingClientRect(), this.translate = null, this.scale = null, this.styleOpen = null, this.styleClose = null
            },
            zoomIn: function() {
                var t = this.instance.options,
                    e = t.zIndex,
                    i = t.enableGrab,
                    n = t.transitionDuration,
                    s = t.transitionTimingFunction;
                this.translate = this.calculateTranslate(), this.scale = this.calculateScale(), this.styleOpen = {
                    position: "relative",
                    zIndex: e + 1,
                    cursor: i ? r : o,
                    transition: "transform\n        " + n + "s\n        " + s,
                    transform: "translate3d(" + this.translate.x + "px, " + this.translate.y + "px, 0px)\n        scale(" + Math.abs(this.scale.x) + "," + Math.abs(this.scale.y) + ")",
                    height: this.rect.height + "px",
                    width: this.rect.width + "px"
                }, this.el.offsetWidth, this.styleClose = c(this.el, this.styleOpen, !0)
            },
            zoomOut: function() {
                this.el.offsetWidth, c(this.el, {
                    transform: "none"
                })
            },
            grab: function(t, e, i) {
                var n = b(),
                    s = n.x - t,
                    o = n.y - e;
                c(this.el, {
                    cursor: a,
                    transform: "translate3d(\n        " + (this.translate.x + s) + "px, " + (this.translate.y + o) + "px, 0px)\n        scale(" + (Math.abs(this.scale.x) + i) + "," + (Math.abs(this.scale.y) + i) + ")"
                })
            },
            move: function(t, e, i) {
                var n = b(),
                    s = n.x - t,
                    o = n.y - e;
                c(this.el, {
                    transition: "transform",
                    transform: "translate3d(\n        " + (this.translate.x + s) + "px, " + (this.translate.y + o) + "px, 0px)\n        scale(" + (Math.abs(this.scale.x) + i) + "," + (Math.abs(this.scale.y) + i) + ")"
                })
            },
            restoreCloseStyle: function() {
                c(this.el, this.styleClose)
            },
            restoreOpenStyle: function() {
                c(this.el, this.styleOpen)
            },
            upgradeSource: function() {
                if (this.srcOriginal) {
                    var t = this.el.parentNode;
                    this.srcset && this.el.removeAttribute("srcset");
                    var e = this.el.cloneNode(!1);
                    e.setAttribute("src", this.srcOriginal), e.style.position = "fixed", e.style.visibility = "hidden", t.appendChild(e), setTimeout(function() {
                        this.el.setAttribute("src", this.srcOriginal), t.removeChild(e)
                    }.bind(this), 50)
                }
            },
            downgradeSource: function() {
                this.srcOriginal && (this.srcset && this.el.setAttribute("srcset", this.srcset), this.el.setAttribute("src", this.srcThumbnail))
            },
            calculateTranslate: function() {
                var t = b(),
                    e = this.rect.left + this.rect.width / 2,
                    i = this.rect.top + this.rect.height / 2;
                return {
                    x: t.x - e,
                    y: t.y - i
                }
            },
            calculateScale: function() {
                var t = this.el.dataset,
                    e = t.zoomingHeight,
                    i = t.zoomingWidth,
                    n = this.instance.options,
                    s = n.customSize,
                    o = n.scaleBase;
                if (!s && e && i) return {
                    x: i / this.rect.width,
                    y: e / this.rect.height
                };
                if (s && "object" === (void 0 === s ? "undefined" : m(s))) return {
                    x: s.width / this.rect.width,
                    y: s.height / this.rect.height
                };
                var r = this.rect.width / 2,
                    a = this.rect.height / 2,
                    l = b(),
                    h = (l.x - r) / r,
                    c = (l.y - a) / a,
                    u = o + Math.min(h, c);
                if (s && "string" == typeof s) {
                    var d = i || this.el.naturalWidth,
                        f = e || this.el.naturalHeight,
                        p = parseFloat(s) * d / (100 * this.rect.width),
                        y = parseFloat(s) * f / (100 * this.rect.height);
                    if (p < u || y < u) return {
                        x: p,
                        y: y
                    }
                }
                return {
                    x: u,
                    y: u
                }
            }
        };

    function b() {
        var t = document.documentElement;
        return {
            x: Math.min(t.clientWidth, window.innerWidth) / 2,
            y: Math.min(t.clientHeight, window.innerHeight) / 2
        }
    }

    function w(e, i, n) {
        ["mousedown", "mousemove", "mouseup", "touchstart", "touchmove", "touchend"].forEach(function(t) {
            l(e, t, i[t], n)
        })
    }
    return function() {
        function e(t) {
            ! function(t, e) {
                if (!(t instanceof e)) throw new TypeError("Cannot call a class as a function")
            }(this, e), this.target = Object.create(v), this.overlay = Object.create(p), this.handler = Object.create(u), this.body = document.body, this.shown = !1, this.lock = !1, this.released = !0, this.lastScrollPosition = null, this.pressTimer = null, this.options = g({}, i, t), this.overlay.init(this), this.handler.init(this)
        }
        return y(e, [{
            key: "listen",
            value: function(t) {
                if ("string" == typeof t)
                    for (var e = document.querySelectorAll(t), i = e.length; i--;) this.listen(e[i]);
                else "IMG" === t.tagName && (t.style.cursor = n, l(t, "click", this.handler.click), this.options.preloadImage && h(s(t)));
                return this
            }
        }, {
            key: "config",
            value: function(t) {
                return t ? (g(this.options, t), this.overlay.updateStyle(this.options), this) : this.options
            }
        }, {
            key: "open",
            value: function(t) {
                var e = this,
                    i = 1 < arguments.length && void 0 !== arguments[1] ? arguments[1] : this.options.onOpen;
                if (!this.shown && !this.lock) {
                    var n = "string" == typeof t ? document.querySelector(t) : t;
                    if ("IMG" === n.tagName) {
                        if (this.options.onBeforeOpen(n), this.target.init(n, this), !this.options.preloadImage) {
                            var s = this.target.srcOriginal;
                            null != s && (this.options.onImageLoading(n), h(s, this.options.onImageLoaded))
                        }
                        this.shown = !0, this.lock = !0, this.target.zoomIn(), this.overlay.insert(), this.overlay.fadeIn(), l(document, "scroll", this.handler.scroll), l(document, "keydown", this.handler.keydown), this.options.closeOnWindowResize && l(window, "resize", this.handler.resizeWindow);
                        return l(n, "transitionend", function t() {
                            l(n, "transitionend", t, !1), e.lock = !1, e.target.upgradeSource(), e.options.enableGrab && w(document, e.handler, !0), i(n)
                        }), this
                    }
                }
            }
        }, {
            key: "close",
            value: function() {
                var e = this,
                    i = 0 < arguments.length && void 0 !== arguments[0] ? arguments[0] : this.options.onClose;
                if (this.shown && !this.lock) {
                    var n = this.target.el;
                    this.options.onBeforeClose(n), this.lock = !0, this.body.style.cursor = t, this.overlay.fadeOut(), this.target.zoomOut(), l(document, "scroll", this.handler.scroll, !1), l(document, "keydown", this.handler.keydown, !1), this.options.closeOnWindowResize && l(window, "resize", this.handler.resizeWindow, !1);
                    return l(n, "transitionend", function t() {
                        l(n, "transitionend", t, !1), e.shown = !1, e.lock = !1, e.target.downgradeSource(), e.options.enableGrab && w(document, e.handler, !1), e.target.restoreCloseStyle(), e.overlay.remove(), i(n)
                    }), this
                }
            }
        }, {
            key: "grab",
            value: function(t, e) {
                var i = 2 < arguments.length && void 0 !== arguments[2] ? arguments[2] : this.options.scaleExtra,
                    n = 3 < arguments.length && void 0 !== arguments[3] ? arguments[3] : this.options.onGrab;
                if (this.shown && !this.lock) {
                    var s = this.target.el;
                    this.options.onBeforeGrab(s), this.released = !1, this.target.grab(t, e, i);
                    return l(s, "transitionend", function t() {
                        l(s, "transitionend", t, !1), n(s)
                    }), this
                }
            }
        }, {
            key: "move",
            value: function(t, e) {
                var i = 2 < arguments.length && void 0 !== arguments[2] ? arguments[2] : this.options.scaleExtra,
                    n = 3 < arguments.length && void 0 !== arguments[3] ? arguments[3] : this.options.onMove;
                if (this.shown && !this.lock) {
                    this.released = !1, this.body.style.cursor = a, this.target.move(t, e, i);
                    var s = this.target.el;
                    return l(s, "transitionend", function t() {
                        l(s, "transitionend", t, !1), n(s)
                    }), this
                }
            }
        }, {
            key: "release",
            value: function() {
                var e = this,
                    i = 0 < arguments.length && void 0 !== arguments[0] ? arguments[0] : this.options.onRelease;
                if (this.shown && !this.lock) {
                    var n = this.target.el;
                    this.options.onBeforeRelease(n), this.lock = !0, this.body.style.cursor = t, this.target.restoreOpenStyle();
                    return l(n, "transitionend", function t() {
                        l(n, "transitionend", t, !1), e.lock = !1, e.released = !0, i(n)
                    }), this
                }
            }
        }]), e
    }()
});