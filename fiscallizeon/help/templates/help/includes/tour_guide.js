const steps = [{
    title: "Novidades por aqui! 👋",
    content: "Iremos te explicar rapidinho como acessar os recursos existentes e o que há de novo, vamos lá?",
    order: 1,
    group: "{{group_guide_name}}"
},
{
    title: "Ficou com alguma dúvida?",
    content: "Fale com nosso suporte a qualquer momento para tirar suas dúvidas ou sugerir melhorias.",
    order: 99,
    group: "{{group_guide_name}}"
}]

const tg = new tourguide.TourGuideClient({
  dialogZ: 9999,
  backdropColor: "rgba(20,20,21,0.6)",
  nextLabel: "Próximo",
  prevLabel: "Anterior",
  finishLabel: "Finalizar",
  completeOnFinish: true,
  steps: steps,
  dialogMaxWidth: 400,
  exitOnClickOutside: false,
  group: "{{group_guide_name}}",
  autoScroll: true,
  autoScrollSmooth: true,
  followScroll:true
});

var localStorageData = localStorage.getItem('tg_tours_complete')

if (!localStorageData || (!localStorageData.split(',').includes("{{group_guide_name}}"))){
    tg.start("{{group_guide_name}}")
    localStorage.setItem('tg_tours_complete', localStorageData+',{{group_guide_name}}')
}

const divInterna = document.getElementById('app');
divInterna.addEventListener("scroll", () => {
    if (tg.isVisible) {
      tg.updatePositions();
    }
});