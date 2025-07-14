{% load static %}


openErrorReportModal(question){
    this.selectedQuestion = question
    question.answer_id = 'REPORTED'
    jQuery.noConflict()
    $('#errorReportModal').modal('show')
},
sendReportError() {
    $('#errorReportModal').modal('hide')

    eventData = {
        "question": this.selectedQuestion.id,
        "application": "{{object.application.pk}}",
        "content": this.errorDescription,
    }
      
    axios.post("{% url 'events:question_error_report_create'  %}", eventData)
    .then(function(response) {
        this.selectedQuestion = null
        this.errorDescription = ''
    
        Swal.fire({
          title: 'Obrigado!',
          text: "Analisaremos a sua solicitação de correção e informaremos o resultado, caso necessário",
          icon: 'warning',
          showConfirmButton: false,
        })
    
        var content = {
          "message": response.data,
          "type":"questionErrorReport"
        }    
    
      }).catch(function(error){
        
        Swal.fire(
          'Ocorreu um erro ao enviar sua mensagem. Informe ao fiscal da prova.',
        )
      })
}, 
findQuestion(_question){
  let oldQuestion = null
  this.knowledgeAreas.find(knowledgeArea => {
    knowledgeArea.subjects.find(subject => {
      subject.questions.find(question => {
        if(question.id == _question.id)
          oldQuestion = question
      })
    })
  })
  return oldQuestion
},
getEmptyQuestions() {
  var questions = []
  this.getAllQuestions().find(question => {
    if(this.attachments && question.category == "Arquivo anexado" && this.checkHasAttachment(question))  {
      return
    }

    if (question.category == "Somatório" && question.selectedIndexes.length == 0 ){
      questions.push(question)
    }
  
    if (question.answerId === "" && question.category != "Somatório") {
        questions.push(question)
    }
   
  })
  return questions
},
getAllQuestions(){
  var questions = []
  this.knowledgeAreas.find(knowledgeArea => {
    knowledgeArea.subjects.filter(subject => subject.foreignLanguageIndex === null || subject.foreignLanguageIndex === this.selectedLanguage).find(subject => {
      subject.questions.find(question => {
        questions.push(question)
      })
    })
  })
  return questions
},
updateQuestion(question){
  self = this
  let newQuestion = JSON.parse(question.message)
  let oldQuestion = self.findQuestion(newQuestion)

  if(oldQuestion){
    if (oldQuestion.updated_at >= newQuestion.updated_at)
      return

    oldQuestion.enunciation = newQuestion.enunciation
    oldQuestion.updated_at = newQuestion.updated_at
    
    newQuestion.alternatives.find(newAlternative => {
      oldQuestion.alternatives.find(alternative => {
        if (alternative.id == newAlternative.id)
          alternative.text = newAlternative.text
      })
    })

    if(oldQuestion.answer_id) {
      Swal.fire(
        'Atenção!',
        `A questão ${oldQuestion.number} foi retificada pela coordenação, verifique se a sua resposta ainda está consistente`,
      )
    }
  }
},