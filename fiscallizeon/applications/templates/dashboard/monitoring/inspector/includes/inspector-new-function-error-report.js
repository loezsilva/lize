{% load static %}

confirmBroadcastQuestionUpdate(question){
    let self = this
    Swal.fire({
        title: 'Enviar atualização de questão para os alunos?',
        text: "Todos os alunos que já fizeram essa questão receberão uma notificação de atualização",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Enviar',
        cancelButtonText: 'Cancelar',
    }).then(result => {
        if (result.isConfirmed) {
            self.broadcastQuestionUpdate(question)
        }
    })
},
broadcastQuestionUpdate(question) {
    const self = this

    let url = "{% url 'questions:questions_api_detail_no_answer' pk='00000000-0000-0000-0000-000000000000'  %}"
    url = url.replace('00000000-0000-0000-0000-000000000000', question.pk)
    axios.get(url).then(response => {
        self.students.forEach(student => {
            var content = {
                "message": JSON.stringify(response.data),
                "type":"broadcastQuestionUpdate"
            }
    
            var message = {
                textroom: "message",
                transaction: Janus.randomString(12),
                room: student.roomId,
                text: JSON.stringify(content),
            };
            
            student.pluginHandle.data({
                text: JSON.stringify(message),
                error: function(reason) { console.log('Error', reason) },
                success: function() { }
            });
        });
    })
},
openQuestionEdit: function(questionPk){
    let url = "{% url 'questions:questions_update' pk='00000000-0000-0000-0000-000000000000' %}"
    url = url.replace("00000000-0000-0000-0000-000000000000", questionPk)
    window.open(url,'_blank')
},