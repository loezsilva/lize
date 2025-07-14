{% load static %}
{% load remove_line_break %}

regroupQuestions(){
  var self = this;

  const questionsByKnowledgeArea = _.groupBy(self.questions, "knowledge_area")
  self.knowledgeAreas = Object.keys(questionsByKnowledgeArea).map(knowledgeAreaName => {
    const localSubjects = _.groupBy(questionsByKnowledgeArea[knowledgeAreaName], "subject")
    return {
      name: knowledgeAreaName,
      subjects: Object.keys(localSubjects).map(subjectName => ({
      name: subjectName,
      questions: localSubjects[subjectName]
      }))
    }
  })
},
countDown() {
  // Se existir um tempo final customizado, usa o tempo final direto do object(application_student)
  // Se não existir, usa o tempo final do object.application 
  var customTimeFinish = "{{object.custom_time_finish}}"
  if (customTimeFinish) {
    var countDownDate = moment("{{object.date_time_end_tz|date:'Y-m-d H:i:s'}}", 'YYYY-MM-DD HH:mm:ss').toDate().getTime();
  } 
  else {
    var countDownDate = moment("{{object.application.date_time_end_tz|date:'Y-m-d H:i:s'}}", 'YYYY-MM-DD HH:mm:ss').toDate().getTime();
  }

  var now_datetime = moment("{% now 'Y-m-d H:i:s' %}", 'YYYY-MM-DD HH:mm:ss').toDate().getTime();
  var start = performance.now();
  var x = setInterval(function() {
      var now = now_datetime + (performance.now() - start);
      var distance = countDownDate - now;

      var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      var seconds = Math.floor((distance % (1000 * 60)) / 1000);

      self.time = ('0' + hours).slice(-2) + ":" + ('0' + minutes).slice(-2) + ":" + ('0' + seconds).slice(-2);

      if (self.time == "00:10:00") {
          Swal.fire({
              title: 'A Prova está terminando',
              text: 'Faltam apenas 10 minutos para encerrar o tempo de prova, após esse horário não será mais permitido responder.',
              imageUrl: "{% static 'stopwatch.png' %}",
              imageWidth: 150,
          });
      }

      if (distance < 0) {
          self.time = "Encerrada";
      }

      if (self.time == "Encerrada") {
          axios.get("{% url 'applications:application_check_end' pk=object.pk  %}", {}).then(function(response) {
              if (response.data.add_time) {
                  self.time = "Tempo adicionado";
                  countDownDate = moment(response.data.finish_time, 'YYYY-MM-DD HH:mm:ss').toDate().getTime();
                  start = performance.now(); // Resetar o tempo de início
              } else {
                  clearInterval(x);
                  axios.post("{% url 'applications:application_end' pk=object.pk  %}", {}).then(function(response) {
                      if (self.pluginHandle) {
                          self.state = 'finished';
                          var content = {
                              "message": self.state,
                              "type": "changeState"
                          };

                          var message = {
                              textroom: "message",
                              transaction: Janus.randomString(12),
                              room: self.textRoomId,
                              text: JSON.stringify(content)
                          };
                          if (self.pluginHandle) {
                              self.pluginHandle.data({
                                  text: JSON.stringify(message),
                                  error: function(reason) {},
                                  success: function() {},
                              });
                          }
                      }

                      Swal.fire({
                          title: 'Tempo de prova encerrado!',
                          imageUrl: "{% static 'stopwatch.png' %}",
                          imageWidth: 150,
                          text: 'Sua prova foi finalizada automaticamente, todas as suas respostas foram enviadas com sucesso!',
                          showConfirmButton: true,
                          allowOutsideClick: false,
                          allowEscapeKey: false,
                      }).then((result) => {
                          window.location.href = "{% url 'core:redirect_dashboard' %}";
                      });
                  }).catch(function(error) {
                      console.log(error);
                  });
              }
          }).catch(function(error) {
              console.log(error);
          });
      }

      self.$forceUpdate();
  }, 1000);
},
removeElement: function(array, element) {
    const index = array.indexOf(element);
    array.splice(index, 1);
},
getInspector: function(inspectorId){
    return this.inspectors.find(element => element.id == inspectorId)
},
isIos: function(){
    return [
      'iPad Simulator',
      'iPhone Simulator',
      'iPod Simulator',
      'iPad',
      'iPhone',
      'iPod'
    ].includes(navigator.platform)
    // iPad on iOS 13 detection
    || (navigator.userAgent.includes("Mac") && "ontouchend" in document)
  },
isChrome: function(){
return navigator.userAgent.match('CriOS')
},
isMob: function(){
return (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent))
},
checkPendingRequest(){
    self = this
    if (self.pendingRequest){        
    switch(self.pendingRequest.get_response_display){
        case "Aprovado":
            self.showAnswerRequest("Aprovado")
            break;
        case "Pendente":
            Swal.fire({
              title: 'Aguarde aprovação de um fiscal!',
              text: "Te informaremos assim que algum fiscal disponível responda sua solicitação.",
              icon: 'warning',
              showConfirmButton: true,
              confirmButtonText: "Ok"
            })
            break;
        default:
            break;
        }
    }
},
showNotice(data){
    Swal.fire({
      title: 'Aviso importante',
      text: data.notice,
      icon: "warning",
      showCancelButton: false,
      confirmButtonColor: '#3085d6',
      confirmButtonText: 'Ok, entendi',
      showConfirmButton: true,
    }).then(function(){
      self.notices.unshift(data)
      self.checkPendingRequest()
    })


},
showAnswerRequest(response_display){
  self = this
  var response = response_display == "Aprovado";

  if (!response)
    this.pendingRequest = null

  var title = response ? "aprovada" : "rejeitada";
  var icon = response ? "success" : "error";

  if (title == "aprovado")
    self.state = "paused"


  var text_approved = "Assim que voltar do banheiro aperte no botão abaixo."
  var text_rejected = "Faça sua solicitação novamente em breve."
  var text = response ? text_approved : text_rejected

  Swal.fire({
    title: 'Sua solicitação foi '+ title,
    text: text,
    icon: icon,
    showCancelButton: false,
    confirmButtonColor: '#3085d6',
    confirmButtonText: 'Já voltei do banheiro',
    showConfirmButton: response,
    allowEscapeKey : !response,
    allowOutsideClick: !response,
    allowEnterKey: !response,
  }).then((result) => {

    if (result.value) {
      if (response){
        self.saveFinishPendingRequest()
      }
    }
  })
},
saveFinishPendingRequest(){
  self = this

  if(self.pendingRequest !== null){
    url = "{% url 'events:event_finish' pk='00000000-0000-0000-0000-000000000000'  %}"
    axios.put(url.replace("00000000-0000-0000-0000-000000000000", self.pendingRequest.pk)).then(function(response){

      self.state = "started"
      self.pendingRequest = null
      
      var content = {
        "message": self.state,
        "type":"changeState"
      }

      var message = {
        textroom: "message",
        transaction: Janus.randomString(12),
        room: self.textRoomId,
        text: JSON.stringify(content)
      };
      if(self.pluginHandle){
        self.pluginHandle.data({
          text: JSON.stringify(message),
          error: function(reason) {
            
          },
          success: function() {},
        });
      }
    }).catch(function(error){
      
    console.error(" --- Comunicaão com a api ..." + error)
    Swal.fire(
      'Ocorreu algum problema!',
      'Tente novamente mais tarde',
      'error'
    )
  })
  }
}