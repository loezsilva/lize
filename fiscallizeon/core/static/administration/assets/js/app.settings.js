
$(function(){
  'use strict'
  // Template Customizer
  $('body').on('click', '#dfSettingsShow', function(e){
    e.preventDefault()

    $('.df-settings').toggleClass('show');
  })
})
