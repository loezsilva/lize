fetchAnswers(examQuestionId) {
    let answersUrl = "{% url 'exams:exam_question_answers_detail_v2' pk='00000000-0000-0000-0000-000000000000' %}"
    
    answersUrl = answersUrl.replace('00000000-0000-0000-0000-000000000000', examQuestionId)
    answersUrl += `?class=${this.schoolClass}`

    axios.get(answersUrl).then(response => {
        this.selectedQuestion = response.data
        this.loadingAnswers = false
        this.selectApplicationStudent(this.selectedQuestion.applications_student.at(0))
        applicationStudent = this.selectedQuestion.applications_student.at(0)
 
    }).finally(() => {
        this.handlerApplicationsStudent()
        this.changeStudent(0)
    })
},
getOptionClass(alternative, answer) {
    let selectedOption = alternative.id == answer
    if (alternative.is_correct)
        return 'alternative-correct'
    else if( selectedOption && !answer.is_correct )
        return 'alternative-incorrect'
    
    return ''
},
updateChoiceAnswer(index) {
    let alternativeID = $(`[name="${'alternatives-' + index}"]:checked`).val()
    data = {
        "student_application": this.selectedApplicationStudent.id,
        "question_option": alternativeID,
    }
    this.loadingSaveApplicationStudent.push(this.selectedApplicationStudent.id)
    axios.post("{% url 'answers:create_option_coordination' %}", data)
    .then((response) => {
        answer = this.selectedApplicationStudent.answers[0] || {}
        answer['id'] = response.data.id
        answer['is_correct'] = response.data.is_correct
        answer['option_answer'] = response.data.question_option
        answer['created_by_name'] = response.data.created_by_name
        answer['created_at'] = response.data.created_at
        answer['teacher_grade'] = response.data.teacher_grade
        if (!this.selectedApplicationStudent.answers.length) {
            this.selectedApplicationStudent.answers.push(answer)
        }
        this.handlerChangeOption(index, answer.option_answer)
        this.changeStudent()
        this.$forceUpdate()
    }).finally(() => {
        this.loadingSaveApplicationStudent.splice(this.selectedApplicationStudent.id, 1)
    })
},
updateSumQuestionAnswer(sumValue, questionToUpdate) {
    this.loadingSaveApplicationStudent.push(this.selectedApplicationStudent.id)

    data = {
        "application_student": this.selectedApplicationStudent.id,
        "question": questionToUpdate.id,
        "sum_value": sumValue,
    }

    axios.post("{% url 'answers:sum_question_update' %}", data)
    .then((response) => {
        answer = this.selectedApplicationStudent.answers[0] || {}
        answer['id'] = response.data.id
        answer['sum_value'] = response.data.sum_question_sum_value
        answer['checked_options'] = response.data.checked_answers
        answer['created_by_name'] = response.data.created_by_name
        answer['created_at'] = response.data.created_at
        answer['teacher_grade'] = response.data.grade
        if (!this.selectedApplicationStudent.answers.length) {
            this.selectedApplicationStudent.answers.push(answer)
        }
        this.changeStudent()
        this.$forceUpdate()
    }).finally(() => {
        this.loadingSaveApplicationStudent.splice(this.selectedApplicationStudent.id, 1)
    })
},
setGrade(grade, index) {
    this.handleApplicationStudentStatus('unsaved')
    let answer = this.selectedApplicationStudent.answers.at(0) || { } 
    answer['teacher_grade'] = grade
    if(!this.selectedApplicationStudent.answers.at(0)) {
        this.selectedApplicationStudent.answers.push(answer)
    }
    this.sendTeacherFeedback()
    this.$forceUpdate()
},
removeGradeAlert(isOption, index) {
    Swal.fire({
        title: isOption ? 'Você confirma que quer remover a resposta do aluno?':'O que você deseja fazer?',
        showDenyButton: true,
        showConfirmButton: isOption,
        showCancelButton: true,
        confirmButtonText: 'Apagar nota',
        denyButtonText: isOption ? 'Sim, confirmo':'Apagar resposta',
        cancelButtonText: `Cancelar`,
    }).then((result) => {
        if (result.isConfirmed) {
            this.removeGrade(removeAnswer = false, index = index)
        } else if (result.isDenied) {
            this.removeGrade(removeAnswer = true, index = index)
        }
    })
},
removeGrade(removeAnswer, index) {

    let id = this.selectedApplicationStudent.answers[0].id
    let url = ''
    if(this.selectedQuestion.question.category == "Arquivo anexado") {
        url = removeAnswer ? this.urls.fileAnswerDelete : this.urls.fileAnswerUpdate
    } else if(this.selectedQuestion.question.category == "Objetiva") {
        url = this.urls.optionAnswerDelete
    } else {
        url = removeAnswer ? this.urls.textualAnswerDelete : this.urls.textualAnswerUpdate        
    }
    
    if (removeAnswer) {
        axios.delete(this.getUrl(url, id)).then((response) => {
            this.resetDataSelectedQuestion(response.data, removeAnswer, index)
        })
    } else {
        object = { 
            teacher_grade: null,
            who_corrected: null,
            corrected_but_no_answer: false,
        }
        axios.patch(this.getUrl(url, id), object).then((response) => {
            this.resetDataSelectedQuestion(response.data, removeAnswer, index)
        }).catch((e) => {
            console.log(e)
        })
    }
},
getUrl(url, id1, id2 = '') {
    return url.replace('00000000-0000-0000-0000-000000000000', id1).replace('11111111-1111-1111-1111-111111111111', id2)
},
resetDataSelectedQuestion(data, removeAnswer, index) {
    if (removeAnswer) {
        this.selectedApplicationStudent.answers.pop()
    } else {
        this.selectedApplicationStudent.answers[0].teacher_grade = data.teacher_grade
    }
    $(`#inputSetGrade-${index}`).val('')
    this.$forceUpdate()
},
clearFeedbackMessage() {
    this.feedbackSaved = false
    this.feedbackError = false
},

getAnswers(examQuestionId) {
    this.loadingAnswers = true
    this.clearFeedbackMessage()
    $('#detailModal').modal('show')
    this.fetchAnswers(examQuestionId)
},

setAnswerGrade(answer, grade) {
    answer.teacher_grade = grade
    answer.unsaved = true
},

setUnsaved(answer) {
    answer.unsaved = true
    this.$forceUpdate()
},

getCorrectPercentage(examQuestion) {
    if(examQuestion.correctedAnswers == 0) {
      return 0
    }
    const rate = examQuestion.correctAnswers / examQuestion.correctedAnswers * 100
    return rate.toFixed(2)
  },
  
getPercentageClass(percentage) {
    porcentage = parseFloat(percentage)
    if(porcentage > 80)
        return 'text-success'
    if (porcentage < 40)
        return 'text-danger'
    
    return 'text-warning'    
},
sendTeacherFeedback(hasCorrection = false) {
    let answer = this.selectedApplicationStudent.answers.at(0);
    let grade = answer.teacher_grade

    let requestBody = { 
        teacher_feedback: answer.teacher_feedback, 
        teacher_grade: grade, 
        who_corrected: '{{user.pk}}',
        question: this.selectedQuestion.question.id,
        student_application: this.selectedApplicationStudent.id,
        ai_suggestion_accepted: answer.ai_suggestion_accepted ? true : false,
    };

    this.handleApplicationStudentStatus('saving');
    let feedbackUrl = "{% url 'answers:file_update_feedback' pk='00000000-0000-0000-0000-000000000000' %}";
    if (this.selectedQuestion.question.category == 'Discursiva') {
        feedbackUrl = "{% url 'answers:text_update_feedback' pk='00000000-0000-0000-0000-000000000000' %}";
    }
    if (answer && answer.id) {

        feedbackUrl = feedbackUrl.replace('00000000-0000-0000-0000-000000000000', answer.id);
        try {
            axios.put(feedbackUrl, requestBody).then((response) => {
                let newPercentGrade = grade / this.selectedQuestion.weight
                if(newPercentGrade > 1) {
                    newPercentGrade = 1
                } else if(newPercentGrade < 0) {
                    newPercentGrade = 0
                }

                answer.percent_grade = newPercentGrade
                
                this.handleApplicationStudentStatus('saved');
    
                if (!hasCorrection && this.selectedQuestion.question.text_correction) {
                    this.saveUpdateCorrection(this.selectedApplicationStudent.id);
                }
    
                this.changeStudent();
                this.$forceUpdate();
            }).catch((e) => {
                this.handleApplicationStudentStatus('error');
            })
        } catch (error) {
            this.handleApplicationStudentStatus('error');
        }
    } else {
        requestBody['corrected_but_no_answer'] = true;
        requestBody['student_application'] = this.selectedApplicationStudent.id;
        requestBody['question'] = this.selectedQuestion.question.id;
        requestBody['teacher_feedback'] = $("#feedback-textarea").val();

        let createUrl = "{% url 'answers:file_create' %}";
        if (this.selectedQuestion.question.category == 'Discursiva') {
            createUrl = "{% url 'answers:text_create' %}";
        }

        try {
            axios.post(createUrl, requestBody).then((response) => {
                let newPercentGrade = grade / this.selectedQuestion.weight
                if(newPercentGrade > 1) {
                    newPercentGrade = 1
                } else if(newPercentGrade < 0) {
                    newPercentGrade = 0
                }

                answer = {
                    'id': response.data.id,
                    'file': response.data.arquivo,
                    'teacher_grade': response.data.teacher_grade,
                    'percent_grade': newPercentGrade,
                    'teacher_feedback': response.data.teacher_feedback,
                    'img_annotations': [],
                };

                this.selectedApplicationStudent.answers[0] = answer
                this.handleApplicationStudentStatus('saved');
                this.changeStudent();
                this.$forceUpdate();
            }).catch((e) => {
                this.handleApplicationStudentStatus('error');
            })
        } catch (error) {
            this.handleApplicationStudentStatus('error');
        }
    }
},
selectedCorrection(questionId, order, point, criterionId){ 
    let competence = this.selectPoint.find((item) => item.order == order)

    if(competence){
        competence.point = point;
    }else{
        this.selectPoint.push({'questionId': questionId, 'order': order ,'point': point, 'criterion_id': criterionId});
    }
    let sumMaximumScore = this.selectedQuestion.question.generate_correction_criterion.reduce((total = 0 , generate_correction_criterion) => total + parseFloat(generate_correction_criterion.maximum_score), 0);

    let sumPoints = this.selectPoint.reduce((total = 0 , competence) => total + competence.point, 0)

    let total = (sumPoints  / sumMaximumScore) * this.selectedQuestion.weight;
    this.totalPoints = total.toFixed(2)

    this.selectedQuestion.teacher_grade = this.totalPoints
    this.selectedApplicationStudent.answers.at(0).teacher_grade  =  this.totalPoints

},
setSuggestion(suggestion, setFeedback = false) {
    if (setFeedback) {
        this.selectedApplicationStudent.answers.at(0).teacher_feedback = suggestion.teacher_feedback
    }
    this.selectedApplicationStudent.answers.at(0).ai_suggestion_accepted = true
    this.setGrade(parseFloat(this.selectedQuestion.weight * suggestion.grade).toFixed(4))
}