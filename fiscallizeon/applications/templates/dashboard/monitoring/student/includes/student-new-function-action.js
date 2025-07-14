{% load static %}

beforeStartApplication(){
  self = this
  Swal.fire({
    title: 'Atraso no início da prova',
    text: 'Você está iniciando a prova após o período de tolerância. Por gentileza, justifique a razão pela qual você está atrasado:',
    input: 'text',
    inputAttributes: {
        autocapitalize: 'off'
    },
    showCancelButton: false,
    confirmButtonText: 'Enviar justificativa',
    showLoaderOnConfirm: true,
    allowOutsideClick: false,
    allowEscapeKey: false,
    preConfirm: (justifyText) => {
      if ($("input.swal2-input").val().trim()) {
        url = "{% url 'applications:application_student_justify_delay' pk='00000000-0000-0000-0000-000000000000'  %}"
        return axios.put(url.replace("00000000-0000-0000-0000-000000000000", "{{ object.pk }}"), { 'justification_delay': justifyText })
        .then(response => {
            if (!response.status == 200) {
                throw new Error(response.statusText)
            }
            return response.data
        })
        .catch(error => {
            
            Swal.showValidationMessage(`Falha no envio: ${error}`)
        })
      } else {
        $("input.swal2-input").val("")
        Swal.showValidationMessage('Preencha o campo acima')   
      }
    },
  }).then((result) => {
    
  })
  
},

requestApplicationPause(){
  self = this
  if (self.pendingRequest !== null){
    Swal.fire(
      'Solicitação em andamento',
      'Aguarde que um fiscal responda a sua solicitação em andamento',
      'warning'
    )
    return
  }

  data = {
    "event_type": "1",
    "student_application": "{{object.pk}}"
  }
  
  axios.post("{% url 'events:event_create'  %}", data
  ).then(function(response){

    Swal.fire({
      title: 'Aguarde aprovação de um fiscal!',
      text: "Te informaremos assim que algum fiscal disponível responda sua solicitação.",
      icon: 'warning',
      showConfirmButton: false,
    })

    var content = {
      "message": response.data,
      "type":"requestPause"
    }

    var message = {
      textroom: "message",
      transaction: Janus.randomString(12),
      room: self.textRoomId,
      text: JSON.stringify(content)
    };

    self.pendingRequest = response.data
    
    if(self.pluginHandle){
      self.pluginHandle.data({
        text: JSON.stringify(message),
        error: function(reason) {
          
        },
        success: function() {},
      });
    }


  }).catch(function(error){
    
    Swal.fire(
      'Horário não permitido',
      'error'
    )
  })

},
startApplication(){
  self = this
  axios.post("{% url 'applications:application_start' pk=object.pk  %}", {}
  ).then(function(response){
    self.state = 'started'

    var data = JSON.parse(response.data)

    var content = {
      "message": {
        "state": self.state,
        "device": data.device
      },
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
    data = JSON.parse(error.response.data)
    Swal.fire(
      'Problema ao iniciar',
      data.message,
      'error'
    )
  })
},
finishApplication(){
  self = this

  var emptyQuestions = self.getEmptyQuestions()

  if (emptyQuestions.length > 0){
    Swal.fire({
      title: 'Atenção, você deixou questões em branco!',
      text: `Revise sua prova, existem ${emptyQuestions.length} questões não respondidas!`,
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Finalizar prova mesmo assim!',
      cancelButtonText: 'Voltar para a prova'
    }).then((result) => {
      if(result.value){
       self.saveFinishApplication(emptyQuestions.length)
      }
    })
  }else{
    Swal.fire({
      title: 'Certeza que deseja finalizar a prova agora?',
      text: "Após confirmação não será possível voltar a este ambiente de fiscalização!",
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sim, finalizar prova!',
      cancelButtonText: 'Voltar para a prova'
    }).then((result) => {
      if (result.value) {
       self.saveFinishApplication(emptyQuestions.length)
      }
    })
  }
},
saveFinishApplication(emptyQuestions=0){
   axios.post("{% url 'applications:application_end' pk=object.pk  %}", {
     'empty_questions': emptyQuestions
   }
    ).then(function(response){

      localStorage.clear();
      localStorage.setItem('RECALCULATE_STUDENT_PERFORMANCE_{{object.student.pk}}', '{{object.student.pk}}')

      Swal.fire({
        icon: 'success',
        title: 'Prova finalizada. Boa sorte!',
        showConfirmButton: true,
      }).then((result) => {

        self.state = 'finished'

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

        window.location.replace("{% url 'core:redirect_dashboard' %}")
        
      })

    }).catch(function(error){
      
      Swal.fire(
        'Horário não permitido',
        "Você só pode finalizar a partir das {{object.application.min_time_end|date:'H:i'}} horas",
        'error'
      )
    })
},
showRequestShareScreen(){
  self = this

  Swal.fire({
    title: 'Autorize o compartilhamento de sua tela',
    html: "Um fiscal deseja visualizar a sua tela, confirme no botão abaixo! <b>Compartilhe a tela inteira!</b>",
    showCancelButton: false,
    imageUrl: "{% static  'share.png' %}",
    imageWidth: 120,
    confirmButtonColor: '#3085d6',
    cancelButtonColor: '#d33',
    confirmButtonText: 'Sim, compartilhar tela!',
    allowOutsideClick: false
  }).then((result) => {
    if (result.value) {
      self.checkPendingRequest()
      var unpublish = { request: "unpublish" };
      self.sfutest.send({ message: unpublish });
      self.publishOwnFeed(useAudio=false, useVideo=true, shareScreen=true)
    }
  })
}