initializeSelect2() {
    self = this
    $('.question').select2({
        placeholder: 'Buscar pelo enunciado da questão...',
        minimumInputLength: 3,
        allowClear: true,
        closeOnSelect: false,
        escapeMarkup: function (text) { return text; },
        ajax: {
            url: '{% url "questions:questions_api_list" %}',
            delay: 250,
            data: function (params) {
                return {
                    search: params.term
                }
            },
            processResults: function(results) {
                let new_results = $.map(results, function(element) {
                    element.text = element.enunciation
                    element.id = element.pk
                    return element
                })

                return {
                    results: new_results,
                }
            }
        },
        templateResult: (data) => {
            return this.templateSelect(data)
        }
    })
    $('#id_grade_input').select2({
        placeholder: 'Selecione uma série',
        closeOnSelect: false
    })
    $('#id_subjects_input').select2({
        placeholder: 'Selecione uma disciplina',
        closeOnSelect: false
    })
},
templateSelect: function (data) {
    var used_times_text = data.used_times > 0 ? `<span class="badge badge-warning float-right">  ${data.used_times} vez(es)</span>` : `<span class="badge badge-primary float-right">Inédita</span>`

    var result = `
        <div class="row mb-0">
        <div class="col-10 mb-0">
            <div class="font-weight-bold" style="line-height: 15px; white-space: break-spaces; ">${data.enunciation}..</div>
        </div>
        <div class="col-2 mb-0">
            <span class="float-right text-muted font-weight-normal">
            ${data.get_level_display}
            </span>
            ${used_times_text}
        </div>
        </div>
        <div class="row"><div class="col-12">`

    if (data.topic_name)
        result += `<span class="badge badge-success">${data.topic_name}</span>`

    result += ` <span class="badge badge-success">${data.topic_name}</span>`

    result += '</div></div>'
    return result
},
sumWeight(questions) {
    if(questions) {  
        value_questions = questions.filter(elem => elem.last_status.status_display != 'Reprovada')
        return value_questions.reduce((total = 0, element) => total += Number(element.weight), 0)
    }
    return 0
},
openModal(url){
    let popupWidth = screen.width / 2
    var leftPos = screen.width - popupWidth;
    window.open(url, "DescriptiveWindowName", "width=" + popupWidth + ", height=1040, top=0, left=" + leftPos +", resizable,scrollbars,status");
},
selectBaseText(baseText) {
    this.selectedBaseText = baseText
},
removeSubject(teacherSubject, index) {
    {% if object %}
        Swal.fire({
            title: 'Confirmação?',
            text: "Você confirma que quer remover esta disciplina do caderno? todas as questões selecionadas também serão removidas?",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sim, Confirmo!',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                url  = "{% url 'exams:api-exam-delete-exam-teacher-subject' pk='00000000-0000-0000-0000-000000000000' %}"
                axios.post(url.replace('00000000-0000-0000-0000-000000000000', teacherSubject.id)).then((response) => {
                    this.alertTop('A disciplina removida com sucesso.')
                    this.exam.teacher_subjects.splice(index, 1)
                }).catch((error) => {
                    this.alertError('Ocorreu um erro ao remover a disciplina do caderno.')
                })
            }
        })
        return
    {% endif %}
    this.exam.teacher_subjects.splice(index, 1)
},
removeExamQuestion(question, index) {
    {% if object %}
        Swal.fire({
            title: 'Confirmação?',
            text: "Você confirma que quer remover esta questao do caderno?",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sim, Confirmo!',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                url  = "{% url 'exams:api-exam-delete-exam-question' pk='00000000-0000-0000-0000-000000000000' %}"
                this.recalculateWeights = true
                axios.post(url.replace('00000000-0000-0000-0000-000000000000', question.id)).then((response) => {
                    this.selectedTeacherSubject.questions.splice(index, 1)
                    this.alertTop('Questão removida do caderno.')
                    {% if object.exam.total_grade %}
                        this.getExamTeacherSubjectData()
                    {% endif %}
                }).catch((error) => {
                    if(error.response.status === 401) {
                        this.alertError(error.response.data)
                        return
                    }
                    this.alertError('Ocorreu um erro ao remover a questão do caderno, tente novamente e se o erro persistir entre em contato com o suporte.')
                })
            }
        })
        return
    
    {% endif %}

    this.exam.teacher_subjects.splice(index, 1)
},
getQuestion(id) {
    return this.selectedTeacherSubject.questions.find(exam_question => exam_question.question.pk == id || exam_question.question.id == id)
},
checkIfQuestionExist(id) {
    return this.getQuestion(id) || (this.examQuestionsAnotherTeachers && this.examQuestionsAnotherTeachers.includes(id))
},
call(result) {
    if (result.updated) {
        let examQuestion = this.getQuestion(result.pk || result.id, this.selectedTeacherSubject.questions)
        let question = examQuestion.question
        
        question.enunciation = result.enunciation
        question.get_category_display = result.get_category_display
        question.get_level_display = result.get_level_display
        question.used_times = result.used_times                    
        question.has_feedback = result.has_feedback
        if((question.pk === result.pk || question.id === result.pk) && examQuestion.last_status.status_display == "Aguardando correção") {
            this.createStatusQuestion(examQuestion, 4)
        }

    } else {
        if(!(this.getQuestion(result.pk || result.id, this.selectedTeacherSubject.questions))) {
            result['order'] = this.selectedTeacherSubject.questions.length
            result['weight'] = 1.0000
            return this.createExamQuestion(result)
        }
    }
},
distributeWeights(teacherSubject, examQuestion = '') {
    if(teacherSubject.weights > 0 || (examQuestion && examQuestion.weight > 0)) {
        teacherSubjectOrExamQuestion = {
            weights: teacherSubject.weights,
            question: examQuestion
        }
        url  = "{% url 'exams:api-exam-distribute-weights' pk='00000000-0000-0000-0000-000000000000' %}"
        axios.post(url.replace('00000000-0000-0000-0000-000000000000', teacherSubject.id), teacherSubjectOrExamQuestion).then((response) => {
            if(!examQuestion) {
                teacherSubject.questions.forEach(question => {
                    question.weight = (Object.assign(teacherSubject.weights) / teacherSubject.questions.length).toFixed(4)
                })
                this.alertTop('Os pesos foram distribuídos igualmente entre as questões do caderno!')
            } else {
                this.alertTop('As alterações foram salvas com sucesso!')
            }
            teacherSubject.weights = ''
        }).catch((error) => {
            this.alertError('Ocorreu um erro ao tentar distribuir os pontos, tente novamente e se o erro persistir entre em contato com o suporte.')
        })
    }
},
async createExamQuestion(question) {
    url = "{% url 'exams:api-exam-create-exam-question' pk='00000000-0000-0000-0000-000000000000' %}"
    return await axios.post(url.replace('00000000-0000-0000-0000-000000000000', this.selectedTeacherSubject.id), question).then((response) => {
        {% if object.exam.total_grade %}
            this.getExamTeacherSubjectData()
        {% else %}
            this.selectedTeacherSubject.questions.push(response.data)
        {% endif %}
        return {
            status: response.status,
            message: 'Questão adicionada com sucesso!',
            exam_question: response.data,
        }
    }).catch((error) => {
        errorMessage = 'Ocorreu um erro ao adicionar a questão ao caderno, tente novamente e se o erro persistir entre em contato com o suporte.'
        if(error.response.status == 401) {
            errorMessage = error.response.data
        }
        this.alertTop(errorMessage, 'error', 5000)
        return {
            status: error.response.status,
            message: errorMessage,
            exam_question: null,
        }
    })
},
save() {
    this.alertTop('As questões foram adicionadas com sucesso.')
    setTimeout(() => {
        window.location.href = "{% url 'core:redirect_dashboard' %}"
    }, 500)
},
changeObjectsOrder(teacherSubjects, examQuestions=null, showMessage=true, redirect_url="{% url 'core:redirect_dashboard' %}") {
    this.swaping = true
    object = {
        teacher_subjects: teacherSubjects,
        exam_questions: examQuestions
    }
    axios.put("{% url 'exams:api-exam-swap-position' %}", object).then((response) => {
        this.selectedTeacherSubject.questions = response.data.exam_questions
        if(showMessage) {
            this.alertTop('As alterações foram salvas.')
        } else {
            this.alertTop('Redirecionando para o início.')
            window.location.href = redirect_url
        }
    }).catch((error) => {
        this.alertError('Erro ao tentar modificar a ordem das questões, tente novamente, caso o erro persista entre em contato com o suporte.')
    }).finally(() => {
        this.swaping = false
    })
},
alertTop(text, icon = 'success', timer = 1500) {
    Swal.fire({
        position: 'top-end',
        text: text,
        icon: icon,
        showConfirmButton: false,
        timer: timer,
        timerProgressBar: true,
        toast: true,
    })
},
alertError(title = "Erro", text) {
    Swal.fire(
        title,
        text,
        'error'
    )
},