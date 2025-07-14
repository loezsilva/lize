'use strict';

{
  function initTinyMCE(el) {
    if (el.closest('.empty-form') === null) {  // Don't do empty inlines
      var mce_conf = JSON.parse(el.dataset.mceConf);

      // There is no way to pass a JavaScript function as an option
      // because all options are serialized as JSON.
      const fns = [
        'color_picker_callback',
        'file_browser_callback',
        'file_picker_callback',
        'images_dataimg_filter',
        'images_upload_handler',
        'paste_postprocess',
        'paste_preprocess',
        // 'setup',
        'urlconverter_callback',
      ];
      fns.forEach((fn_name) => {
        if (typeof mce_conf[fn_name] != 'undefined') {
          if (mce_conf[fn_name].includes('(')) {
            mce_conf[fn_name] = eval('(' + mce_conf[fn_name] + ')');
          }
          else {
            mce_conf[fn_name] = window[mce_conf[fn_name]];
          }
        }
      });

    mce_conf['setup'] = function (editor) {
        editor.addShortcut(
          'f1', 'Muda tab de dados de questão.', function () {
          $('.nav-tabs a[href="#question-data"]').tab('show')
        }),
        editor.addShortcut(
          'f2', 'Muda tab de assuntos.', function () {
          $('.nav-tabs a[href="#question-subject"]').tab('show')
        }),
        editor.addShortcut(
          'f3', 'Muda tab de bncc.', function () {
          $('.nav-tabs a[href="#question-bncc"]').tab('show')
        }),
        editor.addShortcut(
          'f4', 'Muda tab para dados pedagógicos.', function () {
          $('.nav-tabs a[href="#question-print"]').tab('show')
        }),
        editor.addShortcut(
          'f5', 'Muda tab de mudanças na questão', function () {
          $('.nav-tabs a[href="#question-history"]').tab('show')
        }),
        editor.addShortcut(
          'f6', 'Muda tab de histórico.', function () {
          $('.nav-tabs a[href="#history-ult-tab"]').tab('show')
        }),
        editor.addShortcut(
          "Ctrl+l", 'Abre modal de atalhos', function () {
          $('[data-target="#shortcutFunction"]').click()
        }),
        editor.addShortcut(
          'Ctrl+i', 'Ver resumo da questão', function () {
          $('#view-question').click();
        }),
        editor.addShortcut(
          'Ctrl+s', 'Salva questão', function () {
          $('#submitModal').click()
        })
    }

    const id = el.id;
    if ('elements' in mce_conf && mce_conf['mode'] == 'exact') {
        mce_conf['elements'] = id;
    }
    
    if (!tinyMCE.editors[id]) {
            tinyMCE.init(mce_conf);
        }
    }
  }

  // Call function fn when the DOM is loaded and ready. If it is already
  // loaded, call the function now.
  // http://youmightnotneedjquery.com/#ready
  function ready(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  ready(function() {
    // initialize the TinyMCE editors on load
    document.querySelectorAll('.tinymce').forEach(function(el) {
      initTinyMCE(el);
    });

    // initialize the TinyMCE editor after adding an inline
    document.body.addEventListener("click", function(ev) {
      if (!ev.target.parentNode ||
          !ev.target.parentNode.getAttribute("class") ||
          !ev.target.parentNode.getAttribute("class").includes("add-row")) {
        return;
      }
      const addRow = ev.target.parentNode;
      setTimeout(function() {  // We have to wait until the inline is added
        addRow.parentNode.querySelectorAll('textarea.tinymce').forEach(function(el) {
          initTinyMCE(el);
        });
      }, 0);
    }, true);
  });
}
