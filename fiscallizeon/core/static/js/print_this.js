!(function (e) {
  var t;
  function n(e, t) {
    t && e.append(t.jquery ? t.clone() : t);
  }
  (e.fn.printThis = function (i) {
    t = e.extend({}, e.fn.printThis.defaults, i);
    var a = this instanceof jQuery ? this : e(this),
      r = "printThis-" + new Date().getTime();
    if (
      window.location.hostname !== document.domain &&
      navigator.userAgent.match(/msie/i)
    ) {
      var o =
          'javascript:document.write("<head><script>document.domain=\\"' +
          document.domain +
          '\\";</script></head><body></body>")',
        s = document.createElement("iframe");
      (s.name = "printIframe"),
        (s.id = r),
        (s.className = "MSIE"),
        document.body.appendChild(s),
        (s.src = o);
    } else e("<iframe id='" + r + "' name='printIframe' />").appendTo("body");
    var c = e("#" + r);
    t.debug ||
      c.css({
        position: "absolute",
        width: "0px",
        height: "0px",
        left: "-600px",
        top: "-600px",
      }),
      "function" == typeof t.beforePrint && t.beforePrint(),
      setTimeout(function () {
        t.doctypeString &&
          ((f = c),
          (h = t.doctypeString),
          (u =
            (m = (m = f.get(0)).contentWindow || m.contentDocument || m)
              .document ||
            m.contentDocument ||
            m).open(),
          u.write(h),
          u.close());
        var i,
          r,
          o,
          s,
          d,
          l,
          p,
          f,
          h,
          m,
          u,
          y,
          v = c.contents(),
          $ = v.find("head"),
          b = v.find("body"),
          S = e("base");
        (y =
          !0 === t.base && S.length > 0
            ? S.attr("href")
            : "string" == typeof t.base
            ? t.base
            : document.location.protocol + "//" + document.location.host),
          $.append('<base href="' + y + '">'),
          t.importCSS &&
            e("link[rel=stylesheet]").each(function () {
              var t = e(this).attr("href");
              if (t) {
                var n = e(this).attr("media") || "all";
                $.append(
                  "<link type='text/css' rel='stylesheet' href='" +
                    t +
                    "' media='" +
                    n +
                    "'>"
                );
              }
            }),
          t.importStyle &&
            e("style").each(function () {
              $.append(this.outerHTML);
            }),
          t.pageTitle && $.append("<title>" + t.pageTitle + "</title>"),
          t.loadCSS &&
            (e.isArray(t.loadCSS)
              ? jQuery.each(t.loadCSS, function (e, t) {
                  $.append(
                    "<link type='text/css' rel='stylesheet' href='" +
                      this +
                      "'>"
                  );
                })
              : $.append(
                  "<link type='text/css' rel='stylesheet' href='" +
                    t.loadCSS +
                    "'>"
                ));
        var g = e("html")[0];
        v.find("html").prop("style", g.style.cssText);
        var T = t.copyTagClasses;
        if (
          (T &&
            (-1 !== (T = !0 === T ? "bh" : T).indexOf("b") &&
              b.addClass(e("body")[0].className),
            -1 !== T.indexOf("h") && v.find("html").addClass(g.className)),
          (T = t.copyTagStyles) &&
            (-1 !== (T = !0 === T ? "bh" : T).indexOf("b") &&
              b.attr("style", e("body")[0].style.cssText),
            -1 !== T.indexOf("h") &&
              v.find("html").attr("style", g.style.cssText)),
          n(b, t.header),
          t.canvas)
        ) {
          var C = 0;
          a.find("canvas")
            .addBack("canvas")
            .each(function () {
              e(this).attr("data-printthis", C++);
            });
        }
        if (
          ((i = b),
          (r = a),
          (o = t),
          (s = r.clone(o.formValues)),
          o.formValues &&
            (function t(n, i, a) {
              var r = n.find(a);
              i.find(a).each(function (t, n) {
                e(n).val(r.eq(t).val());
              });
            })(r, s, "select, textarea"),
          o.removeScripts && s.find("script").remove(),
          o.printContainer
            ? s.appendTo(i)
            : s.each(function () {
                e(this).children().appendTo(i);
              }),
          t.canvas &&
            b.find("canvas").each(function () {
              var t = e(this).data("printthis"),
                n = e('[data-printthis="' + t + '"]');
              this.getContext("2d").drawImage(n[0], 0, 0),
                e.isFunction(e.fn.removeAttr)
                  ? n.removeAttr("data-printthis")
                  : e.each(n, function (e, t) {
                      t.removeAttribute("data-printthis");
                    });
            }),
          t.removeInline)
        ) {
          var x = t.removeInlineSelector || "*";
          e.isFunction(e.removeAttr)
            ? b.find(x).removeAttr("style")
            : b.find(x).attr("style", "");
        }
        n(b, t.footer),
          (d = c),
          (l = t.beforePrintEvent),
          (p = (p = d.get(0)).contentWindow || p.contentDocument || p),
          "function" == typeof l &&
            ("matchMedia" in p
              ? p.matchMedia("print").addListener(function (e) {
                  e.matches && l();
                })
              : (p.onbeforeprint = l)),
          setTimeout(function () {
            c.hasClass("MSIE")
              ? (window.frames.printIframe.focus(),
                $.append("<script>  window.print(); </script>"))
              : document.queryCommandSupported("print")
              ? c[0].contentWindow.document.execCommand("print", !1, null)
              : (c[0].contentWindow.focus(), c[0].contentWindow.print()),
              t.debug ||
                setTimeout(function () {
                  c.remove();
                }, 1e3),
              "function" == typeof t.afterPrint && t.afterPrint();
          }, t.printDelay);
      }, 333);
  }),
    (e.fn.printThis.defaults = {
      debug: !1,
      importCSS: !0,
      importStyle: !0,
      printContainer: !0,
      loadCSS: "",
      pageTitle: "",
      removeInline: !1,
      removeInlineSelector: "*",
      printDelay: 1e3,
      header: null,
      footer: null,
      base: !1,
      formValues: !0,
      canvas: !0,
      doctypeString: "<!DOCTYPE html>",
      removeScripts: !1,
      copyTagClasses: !0,
      copyTagStyles: !0,
      beforePrintEvent: null,
      beforePrint: null,
      afterPrint: null,
    });
})(jQuery);