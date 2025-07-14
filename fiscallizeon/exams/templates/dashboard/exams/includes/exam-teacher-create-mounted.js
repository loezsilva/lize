self = this

$(document).ready(function() {
    $(window).keydown(function(event){
        if(event.keyCode == 13) {
            event.preventDefault();
            return false;
        }
    });
});
this.initializeSelect2()
$('.question').on('select2:select', (e) => {
    question = e.params.data
    if (this.getQuestion(question.pk, this.selectedQuestions)){
        Swal.fire(
            'Questão duplicada!',
            'A questão que você está tentando adicionar nessa prova já foi adicionada anteriormente.',
            'warning'
        )
        return
    }
    question['weight'] = "1.0000"
    const listOrder = this.selectedTeacherSubject.questions.map(question => question.order)
    if (listOrder.length > 0) {
        question['order'] = Math.max(...listOrder) + 1
    } else {
        question['order'] = 0
    }
    this.createExamQuestion(question).then((_response) => {
        icon = 'success'
        if(_response.status > 208) {
            icon = 'error'
        }
        Swal.fire({
            icon: icon,
            title: _response.message,
        })
    })
});
