const element_{{group_guide_name}} = document.getElementById('{{element_click_id}}');

element_{{group_guide_name}}.addEventListener('click', () =>{
  setTimeout(() => {
  const tg_{{group_guide_name}} = new tourguide.TourGuideClient({
      dialogZ: 9999,
      backdropColor: "rgba(20,20,21,0.6)",
      nextLabel: "Próximo",
      prevLabel: "Anterior",
      finishLabel: "Finalizar",
      completeOnFinish: true,
      dialogMaxWidth: 400,
      exitOnClickOutside: false,
      group: "{{group_guide_name}}",
      autoScroll: true,
      autoScrollSmooth: true,
      followScroll:true
    });

    var localStorageData = localStorage.getItem('tg_tours_complete')

    if (!localStorageData || (!localStorageData.split(',').includes("{{group_guide_name}}"))){
        tg_{{group_guide_name}}.start("{{group_guide_name}}")
        {% comment %} localStorage.setItem('tg_tours_complete', ',{{group_guide_name}}') {% endcomment %}
    }

    const divInterna = document.getElementById('app');
    divInterna.addEventListener("scroll", () => {
        if (tg_{{group_guide_name}}.isVisible) {
          tg_{{group_guide_name}}.updatePositions();
        }
    });
  }, 500)
   
})

