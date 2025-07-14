getAnswerClass(answer) {
    if(answer.category == 'Objetiva') {
        if(answer.answer)
            return answer.is_correct ? 'question-correct' : 'question-wrong'
        else
            return 'question-blank'
    } else {
        if (answer.teacher_grade === '') {
            return 'question-blank'
        }

        const teacherGrade = parseFloat(answer.teacher_grade)
        const questionWeight = parseFloat(answer.question_weight)
        return teacherGrade == questionWeight ? 'question-correct' : (teacherGrade === 0 ? 'question-wrong' : 'question-partial')
    }
},

getOptionClass(alternative, answer) {
    let selectedOption = alternative.id == answer

    if (alternative.is_correct)
        return 'alternative-correct'
    else if( selectedOption && !answer.is_correct )
        return 'alternative-incorrect'
    
    return ''
},

openQuestionModal(question) {
    this.selectedQuestion = {}
    $('#questionModal').modal('show')
    $('[href="#questionDetails"]').click()
    
    let questionUrl = "{% url 'questions:questions_api_detail' pk='00000000-0000-0000-0000-000000000000' %}"
    
    let questionFileAnswerUrl = "{% url 'questions:question_fileanswer_student_api' pk='00000000-0000-0000-0000-000000000000' student_application='11111111-1111-1111-1111-111111111111' %}"
    if(question.file_answer && question.file_answer != 'None') {
        axios.get(questionFileAnswerUrl.replace('00000000-0000-0000-0000-000000000000', question.pk).replace('11111111-1111-1111-1111-111111111111', '{{object.pk}}'))
        .then((response) => question['img_annotations'] = response.data.img_annotations)
        .catch((e) => e)
    }

    questionUrl = questionUrl.replace('00000000-0000-0000-0000-000000000000', question.pk)
    axios.get(questionUrl).then(response => {
        this.selectedQuestion = response.data
        this.selectedQuestion.alternatives.forEach(element => {
            element.text = element.text.replaceAll('\\\\', '\\')
        })
        this.selectedQuestion.answer = question.answer
        this.selectedQuestion.textual_answer = question.textual_answer
        this.selectedQuestion.file_answer = question.file_answer
        this.selectedQuestion.teacher_feedback = question.teacher_feedback
        this.selectedQuestion.teacher_grade = question.teacher_grade
        this.selectedQuestion.category = question.category
        this.selectedQuestion.question_weight = question.question_weight
        this.selectedQuestion.img_annotations = question.img_annotations
    })
},
