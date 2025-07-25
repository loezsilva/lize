! function(e) {
    var t = {};

    function n(o) { if (t[o]) return t[o].exports; var r = t[o] = { i: o, l: !1, exports: {} }; return e[o].call(r.exports, r, r.exports, n), r.l = !0, r.exports }
    n.m = e, n.c = t, n.d = function(e, t, o) { n.o(e, t) || Object.defineProperty(e, t, { configurable: !1, enumerable: !0, get: o }) }, n.r = function(e) { Object.defineProperty(e, "__esModule", { value: !0 }) }, n.n = function(e) { var t = e && e.__esModule ? function() { return e.default } : function() { return e }; return n.d(t, "a", t), t }, n.o = function(e, t) { return Object.prototype.hasOwnProperty.call(e, t) }, n.p = "", n(n.s = 8)
}([function(e, t, n) {
    "use strict";
    Object.defineProperty(t, "__esModule", { value: !0 }), t.OneSignalStub = void 0;
    var o = function() {
        function e(t) {
            var n = this;
            this.VERSION = Number(151513), this.log = { setLevel: function(e) { n.currentLogLevel = e } }, this.setupStubFunctions(e.FUNCTION_LIST_TO_STUB, this.stubFunction, t), this.setupStubFunctions(e.FUNCTION_LIST_WITH_PROMISE_TO_STUB, this.stubPromiseFunction, t)
        }
        return e.prototype.setupStubFunctions = function(e, t, n) {
            for (var o = this, r = function(e) {
                    if (n.indexOf(e) > -1) return "continue";
                    Object.defineProperty(i, e, { value: function() { for (var n = [], r = 0; r < arguments.length; r++) n[r] = arguments[r]; return t(o, e, n) } })
                }, i = this, a = 0, u = e; a < u.length; a++) { r(u[a]) }
        }, e
    }();
    t.OneSignalStub = o, o.FUNCTION_LIST_TO_STUB = ["on", "off", "once", "push"], o.FUNCTION_LIST_WITH_PROMISE_TO_STUB = ["init", "_initHttp", "isPushNotificationsEnabled", "showHttpPrompt", "registerForPushNotifications", "setDefaultNotificationUrl", "setDefaultTitle", "syncHashedEmail", "getTags", "sendTag", "sendTags", "deleteTag", "deleteTags", "addListenerForNotificationOpened", "getIdsAvailable", "setSubscription", "showHttpPermissionRequest", "showNativePrompt", "showSlidedownPrompt", "showCategorySlidedown", "showSmsSlidedown", "showEmailSlidedown", "showSmsAndEmailSlidedown", "getNotificationPermission", "getUserId", "getRegistrationId", "getSubscription", "sendSelfNotification", "setEmail", "setSMSNumber", "logoutEmail", "logoutSMS", "setExternalUserId", "removeExternalUserId", "getExternalUserId", "provideUserConsent", "isOptedOut", "getEmailId", "getSMSId", "sendOutcome"]
}, function(e, t, n) {
    "use strict";
    Object.defineProperty(t, "__esModule", { value: !0 });
    var o = function() {
        function e() {}
        return e.shouldLog = function() { try { if ("undefined" == typeof window || void 0 === window.localStorage) return !1; var e = window.localStorage.getItem("loglevel"); return !(!e || "trace" !== e.toLowerCase()) } catch (e) { return !1 } }, e.setLevel = function(t) { if ("undefined" != typeof window && void 0 !== window.localStorage) try { window.localStorage.setItem("loglevel", t), e.proxyMethodsCreated = void 0, e.createProxyMethods() } catch (e) { return } }, e.createProxyMethods = function() {
            if (void 0 === e.proxyMethodsCreated) {
                e.proxyMethodsCreated = !0;
                for (var t = { log: "debug", trace: "trace", info: "info", warn: "warn", error: "error" }, n = 0, o = Object.keys(t); n < o.length; n++) {
                    var r = o[n],
                        i = void 0 !== console[r],
                        a = t[r],
                        u = i && (e.shouldLog() || "error" === a);
                    e[a] = u ? console[r].bind(console) : function() {}
                }
            }
        }, e
    }();
    t.default = o, o.createProxyMethods()
}, function(e, t, n) {
    "use strict";
    var o, r = this && this.__extends || (o = function(e, t) {
        return (o = Object.setPrototypeOf || { __proto__: [] }
            instanceof Array && function(e, t) { e.__proto__ = t } || function(e, t) { for (var n in t) Object.prototype.hasOwnProperty.call(t, n) && (e[n] = t[n]) })(e, t)
    }, function(e, t) {
        function n() { this.constructor = e }
        o(e, t), e.prototype = null === t ? Object.create(t) : (n.prototype = t.prototype, new n)
    });
    Object.defineProperty(t, "__esModule", { value: !0 });
    var i = function(e) {
        function t(n) { void 0 === n && (n = ""); var o = e.call(this, n) || this; return Object.defineProperty(o, "message", { configurable: !0, enumerable: !1, value: n, writable: !0 }), Object.defineProperty(o, "name", { configurable: !0, enumerable: !1, value: o.constructor.name, writable: !0 }), Error.hasOwnProperty("captureStackTrace") ? (Error.captureStackTrace(o, o.constructor), o) : (Object.defineProperty(o, "stack", { configurable: !0, enumerable: !1, value: new Error(n).stack, writable: !0 }), Object.setPrototypeOf(o, t.prototype), o) }
        return r(t, e), t
    }(Error);
    t.default = i
}, function(e, t, n) {
    "use strict";
    var o = this && this.__importDefault || function(e) { return e && e.__esModule ? e : { default: e } };
    Object.defineProperty(t, "__esModule", { value: !0 }), t.ProcessOneSignalPushCalls = void 0;
    var r = o(n(2)),
        i = function() {
            function e() {}
            return e.processItem = function(e, t) {
                if ("function" == typeof t) t();
                else {
                    if (!Array.isArray(t)) throw new r.default("Only accepts function and Array types!");
                    if (0 == t.length) throw new r.default("Empty array is not valid!");
                    var n = t.shift();
                    if (null == n || void 0 === n) throw new r.default("First element in array must be the OneSignal function name");
                    var o = e[n.toString()];
                    if ("function" != typeof o) throw new r.default("No OneSignal function with the name '" + n + "'");
                    o.apply(e, t)
                }
            }, e
        }();
    t.ProcessOneSignalPushCalls = i
}, function(e, t, n) {
    "use strict";
    var o, r = this && this.__extends || (o = function(e, t) {
            return (o = Object.setPrototypeOf || { __proto__: [] }
                instanceof Array && function(e, t) { e.__proto__ = t } || function(e, t) { for (var n in t) Object.prototype.hasOwnProperty.call(t, n) && (e[n] = t[n]) })(e, t)
        }, function(e, t) {
            function n() { this.constructor = e }
            o(e, t), e.prototype = null === t ? Object.create(t) : (n.prototype = t.prototype, new n)
        }),
        i = this && this.__importDefault || function(e) { return e && e.__esModule ? e : { default: e } };
    Object.defineProperty(t, "__esModule", { value: !0 }), t.OneSignalStubES5 = void 0;
    var a = n(0),
        u = n(3),
        s = i(n(1)),
        c = function(e) {
            function t(n) { var o = e.call(this, Object.getOwnPropertyNames(t.prototype)) || this; return window.OneSignal = o, o.playPushes(n), o }
            return r(t, e), t.prototype.isPushNotificationsSupported = function() { return !1 }, t.prototype.isPushNotificationsEnabled = function() { return t.newPromiseIfDefined(function(e) { e(!1) }) }, t.prototype.push = function(e) { u.ProcessOneSignalPushCalls.processItem(this, e) }, t.prototype.stubFunction = function(e, t, n) {}, t.prototype.stubPromiseFunction = function(e, n, o) { return t.newPromiseIfDefined(function(e, t) {}) }, t.newPromiseIfDefined = function(e) { return "undefined" == typeof Promise ? void 0 : new Promise(e) }, t.prototype.playPushes = function(e) {
                if (e)
                    for (var t = 0, n = e; t < n.length; t++) { var o = n[t]; try { this.push(o) } catch (e) { s.default.error(e) } }
            }, t
        }(a.OneSignalStub);
    t.OneSignalStubES5 = c
}, function(e, t, n) {
    "use strict";
    var o, r = this && this.__extends || (o = function(e, t) {
        return (o = Object.setPrototypeOf || { __proto__: [] }
            instanceof Array && function(e, t) { e.__proto__ = t } || function(e, t) { for (var n in t) Object.prototype.hasOwnProperty.call(t, n) && (e[n] = t[n]) })(e, t)
    }, function(e, t) {
        function n() { this.constructor = e }
        o(e, t), e.prototype = null === t ? Object.create(t) : (n.prototype = t.prototype, new n)
    });
    Object.defineProperty(t, "__esModule", { value: !0 }), t.OneSignalStubES6 = void 0;
    var OneSignalStubES6 = function(e) {
        function OneSignalStubES6(t) { var n = e.call(this, Object.getOwnPropertyNames(OneSignalStubES6.prototype)) || this; return n.directFunctionCallsArray = new Array, n.preExistingArray = t, n }
        return r(OneSignalStubES6, e), OneSignalStubES6.prototype.isPushNotificationsSupported = function() { return !0 }, OneSignalStubES6.prototype.stubFunction = function(e, t, n) { e.directFunctionCallsArray.push({ functionName: t, args: n, delayedPromise: void 0 }) }, OneSignalStubES6.prototype.stubPromiseFunction = function(e, t, n) {
            var o = void 0,
                r = new Promise(function(e, t) { o = { resolve: e, reject: t } });
            return e.directFunctionCallsArray.push({ functionName: t, delayedPromise: o, args: n }), r
        }, OneSignalStubES6
    }(n(0).OneSignalStub);
    t.OneSignalStubES6 = OneSignalStubES6
}, function(e, t, n) {
    "use strict";

    function o() { return window.top !== window && "Apple Computer, Inc." === navigator.vendor && "MacIntel" === navigator.platform }
    Object.defineProperty(t, "__esModule", { value: !0 }), t.isMacOSSafariInIframe = t.isPushNotificationsSupported = void 0, t.isPushNotificationsSupported = function() { return "undefined" != typeof PushSubscriptionOptions && PushSubscriptionOptions.prototype.hasOwnProperty("applicationServerKey") || window.safari && void 0 !== window.safari.pushNotification || o() }, t.isMacOSSafariInIframe = o
}, function(e, t, n) {
    "use strict";
    Object.defineProperty(t, "__esModule", { value: !0 }), t.OneSignalShimLoader = void 0;
    var o = n(6),
        r = n(5),
        i = n(4),
        a = function() {
            function e() {}
            return e.addScriptToPage = function(e) {
                var t = document.createElement("script");
                t.src = e, t.async = !0, document.head.appendChild(t)
            }, e.getPathAndPrefix = function() { return "https://cdn.onesignal.com/sdks/" }, e.isServiceWorkerRuntime = function() { return "undefined" == typeof window }, e.addOneSignalPageES6SDKStub = function() {
                var e = window.OneSignal,
                    t = Array.isArray(e);
                !e || t ? window.OneSignal = new r.OneSignalStubES6(e) : console.error("window.OneSignal already defined as '" + typeof OneSignal + "'!\n         Please make sure to define as 'window.OneSignal = window.OneSignal || [];'", OneSignal)
            }, e.addOneSignalPageES5SDKStub = function() {
                console.log("OneSignal: Using fallback ES5 Stub for backwards compatibility.");
                var e = window.OneSignal;
                window.OneSignal = new i.OneSignalStubES5(e)
            }, e.start = function() { e.isServiceWorkerRuntime() ? self.importScripts(e.getPathAndPrefix() + "OneSignalSDKWorker.js?v=" + e.VERSION) : o.isPushNotificationsSupported() ? (e.addScriptToPage(e.getPathAndPrefix() + "OneSignalPageSDKES6.js?v=" + e.VERSION), e.addOneSignalPageES6SDKStub()) : e.addOneSignalPageES5SDKStub() }, e
        }();
    t.OneSignalShimLoader = a, a.VERSION = Number(151513)
}, function(e, t, n) {
    "use strict";
    Object.defineProperty(t, "__esModule", { value: !0 }), n(7).OneSignalShimLoader.start()
}]);
//# sourceMappingURL=OneSignalSDK.js.map