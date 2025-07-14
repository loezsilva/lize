$(function(){
  'use strict'

  // Initialize tooltip
  $('[data-toggle="tooltip"]').tooltip()

  // Initialize PerfectScrollbar
  const asideBody = new PerfectScrollbar('.aside-body', { suppressScrollX: true });

  // Add backdrop if it doesn't exist
  if ($('.aside-backdrop').length === 0) {
    $('<div class="aside-backdrop"></div>').appendTo('body');
  }

  // Minimize aside on media query change
  const mql = window.matchMedia('(min-width:992px) and (max-width: 1199px)');
  const minimizeAside = (e) => {
    const $aside = $('.aside');
    if (e.matches) {
      $aside.addClass('minimize');
      closeAllDisclosures();
    } else {
      $aside.removeClass('minimize');
    }
    asideBody.update();
  }
  mql.addEventListener('change', minimizeAside);
  minimizeAside(mql);

  // Toggle aside on menu link click
  $('.aside-menu-link').on('click', function(e) {
    e.preventDefault();
    const $aside = $(this).closest('.aside');
    if (window.matchMedia('(min-width: 992px)').matches) {
      if (!$aside.hasClass('minimize')) {
        closeAllDisclosures();
      }
      $aside.toggleClass('minimize');
    } else {
      $('body').toggleClass('show-aside');
    }
    asideBody.update();
  });

  // Toggle submenu on nav-link click
  $('.nav-aside .with-sub').on('click', '.nav-link', function(e) {
    e.preventDefault();
    const $parent = $(this).parent();
    $parent.siblings().removeClass('show');
    $parent.toggleClass('show');
    asideBody.update();
  });

  // Maximize aside on mouseenter
  $('body').on('mouseenter', '.minimize .aside-body', function(e) {
    $(this).parent().addClass('maximize');
  });

  // Restore aside on mouseleave
  $('body').on('mouseleave', '.minimize .aside-body', function(e) {
    $(this).parent().removeClass('maximize');
    closeAllDisclosures();
    asideBody.update();
  });

  // Hide aside on backdrop click
  $('body').on('click', '.aside-backdrop', function(e) {
    $('body').removeClass('show-aside');
  });

  function closeAllDisclosures() {
    const disclosureButtons = document.querySelectorAll('button[id^="headlessui-disclosure-button-"');
  
    disclosureButtons.forEach((button) => {
      const panel = document.querySelector(`#${button.getAttribute('aria-controls')}`);
      const svgs = button.querySelectorAll('svg');
      let svg;
      if (svgs.length === 2) {
        svg = svgs.item(1);
      } else {
        svg = svgs.item(0);
      }
  
      button.setAttribute('aria-expanded', 'false');
      panel.style.display = 'none';
      panel.setAttribute('data-headlessui-state', 'closed');
      svg.style.transform = 'rotate(0deg)';
    });
  }
});
