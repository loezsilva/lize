fetchApplicationStudentData(student) {
    this.errors.forbidden = false
    this.errors.notQuestions = false
    this.spinnerVerification = true

    let studentUrl = "{% url 'applications:application_student_exam_api' pk='00000000-0000-0000-0000-000000000000' %}" 
    studentUrl = studentUrl.replace('00000000-0000-0000-0000-000000000000', typeof(student) == 'string' ? student : student.id ? student.id : student.pk)
    const subjectsParams = new URLSearchParams(this.selectedSubjects);
    axios.get(`${studentUrl}?${subjectsParams.toString()}`)
    .then(response => {
        this.applicationStudent = response.data
        let uniqueQuestions = []
        response.data.questions.forEach((question) => {
            if(!uniqueQuestions.find((_question) => _question.pk == question.pk)) {
                uniqueQuestions.push(question)
            }
            if(question.teacher_grade){
                question.formValid = 'is-valid'
            }
        })
        this.applicationStudent.questions = uniqueQuestions.map((question, index) => {
            return ({...question, order: index + 1})
        })
        student = this.applicationStudent
        this.selectedApplicationStudent = student
        if(!this.selectedApplicationStudent.can_be_corrected) {
            this.correctionFast = false
        }

        {% if object.group_attachments %}
            this.getAttachments(response.data)
        {% endif %}
        this.orderQuestions(this.ordering.category, false)
        if(this.applicationStudent.questions.length) {
            this.getEnunciation(this.applicationStudent.questions[0])
        } else {
            this.errors.notQuestions = true
        }
        this.spinnerVerification = false
    }).catch((error) => {
        if(error.response.status == 403) {
            this.errors.forbidden = true
        }
    })
},
getAttachments(applicationStudent) {
    axios.get(`{% url 'answers:api-attachments-get-teacher-attachments' %}?application_student=${applicationStudent.pk}`).then((response) => {
        let group = _.groupBy(response.data, 'exam_teacher_subject')
        this.groupExamTeacherAttachments = _.map(group, (value, key) => {
            object = {
                id: key,
                attachments: value,
            }
            return object
        })
    })
},
getAttachmentsExamTeacherSubject(examTeacherSubjectID) {
    return this.groupExamTeacherAttachments.find((group) => group.id == examTeacherSubjectID)
},
openStudentModal(student) {

    this.applicationStudent = { questions: [] }
    this.selectedQuestion = ""
    $('#detailModal').modal('show')
    this.fetchApplicationStudentData(student)
    this.selectedQuestion.text_correction_answer = []
    this.selectPoint = []
    this.totalPoints = 0

},

getAnswerClass(answer) {

    if(!answer.annuled && !answer.empty && !this.selectedApplicationStudent.empty_option_questions.includes(answer.pk)) {
        if(answer.category == 'Objetiva') {
            console.log(answer)
            console.log(answer.answer)
            if (answer.answer)
                return answer.is_correct ? 'bg-success' : 'bg-pink'
            return 'bg-gray'
        }

        if (answer.teacher_grade == null) {
            return 'bg-gray'
        }

        const teacherGrade = parseFloat(answer.percent_grade * answer.question_weight)
        const questionWeight = parseFloat(answer.question_weight)

        if(answer.category == 'Somatório') {
            return teacherGrade == 1 ? 'bg-success' : (teacherGrade === 0 ? 'bg-pink' : 'bg-warning')
        }
        return teacherGrade == questionWeight ? 'bg-success' : (teacherGrade === 0 ? 'bg-pink' : 'bg-warning')
    }
    return 'bg-gray'
},
getAnswerVariantClass(answer) {
  let grayVariant = 'gray'
  let greenVariant = 'green'
  let redVariant = 'red'
  let yellowVariant = 'yellow'
  if (
    !answer.annuled &&
    !answer.empty &&
    !this.selectedApplicationStudent.empty_option_questions.includes(answer.pk)
  ) {
    if (answer.category == 'Objetiva') {
      if (answer.answer) return answer.is_correct ? greenVariant : redVariant
      return grayVariant
    }

    if (answer.teacher_grade == null) return grayVariant
    let teacherGrade = parseFloat(answer.percent_grade * answer.question_weight)
    let questionWeight = parseFloat(answer.question_weight)
    return teacherGrade === questionWeight ? greenVariant : teacherGrade === 0 ? redVariant : yellowVariant
  }
  return grayVariant
},
getAnswerTwClass(answer, selectedQuestion) {
  let colorVariants = {
    gray: {
      base: 'tw-text-slate-500 tw-bg-slate-50',
      border: 'tw-border-gray-500',
    },
    green: {
      base: 'tw-text-mint-800 tw-bg-mint-200',
      border: 'tw-border-mint-600',
    },
    red: {
      base: 'tw-text-poppy-800 tw-bg-poppy-100',
      border: 'tw-border-poppy-600',
    },
    yellow: {
      base: 'tw-text-honey-800 tw-bg-honey-100',
      border: 'tw-border-honey-600',
    }
  }
  let variant = this.getAnswerVariantClass(answer)
  let { base, border } = colorVariants[variant]
  return answer.pk === selectedQuestion.pk ? `${base} tw-border ${border}` : base
},
getAnswerIcon(answer) {
  let icons = {
    'gray': '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1.3125 3C1.3125 2.85082 1.37176 2.70774 1.47725 2.60225C1.58274 2.49676 1.72582 2.4375 1.875 2.4375H10.125C10.2742 2.4375 10.4173 2.49676 10.5227 2.60225C10.6282 2.70774 10.6875 2.85082 10.6875 3C10.6875 3.14918 10.6282 3.29226 10.5227 3.39775C10.4173 3.50324 10.2742 3.5625 10.125 3.5625H1.875C1.72582 3.5625 1.58274 3.50324 1.47725 3.39775C1.37176 3.29226 1.3125 3.14918 1.3125 3ZM1.875 5.4375H7.875C8.02418 5.4375 8.16726 5.37824 8.27275 5.27275C8.37824 5.16726 8.4375 5.02418 8.4375 4.875C8.4375 4.72582 8.37824 4.58274 8.27275 4.47725C8.16726 4.37176 8.02418 4.3125 7.875 4.3125H1.875C1.72582 4.3125 1.58274 4.37176 1.47725 4.47725C1.37176 4.58274 1.3125 4.72582 1.3125 4.875C1.3125 5.02418 1.37176 5.16726 1.47725 5.27275C1.58274 5.37824 1.72582 5.4375 1.875 5.4375ZM10.125 6.1875H1.875C1.72582 6.1875 1.58274 6.24676 1.47725 6.35225C1.37176 6.45774 1.3125 6.60082 1.3125 6.75C1.3125 6.89918 1.37176 7.04226 1.47725 7.14775C1.58274 7.25324 1.72582 7.3125 1.875 7.3125H10.125C10.2742 7.3125 10.4173 7.25324 10.5227 7.14775C10.6282 7.04226 10.6875 6.89918 10.6875 6.75C10.6875 6.60082 10.6282 6.45774 10.5227 6.35225C10.4173 6.24676 10.2742 6.1875 10.125 6.1875ZM7.875 8.0625H1.875C1.72582 8.0625 1.58274 8.12176 1.47725 8.22725C1.37176 8.33274 1.3125 8.47582 1.3125 8.625C1.3125 8.77418 1.37176 8.91726 1.47725 9.02275C1.58274 9.12824 1.72582 9.1875 1.875 9.1875H7.875C8.02418 9.1875 8.16726 9.12824 8.27275 9.02275C8.37824 8.91726 8.4375 8.77418 8.4375 8.625C8.4375 8.47582 8.37824 8.33274 8.27275 8.22725C8.16726 8.12176 8.02418 8.0625 7.875 8.0625Z" fill="currentColor"/></svg>',
    'green': '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><g clip-path="url(#clip0_3692_7975)"><path d="M8.27297 4.47703C8.32541 4.52929 8.36702 4.59139 8.39541 4.65976C8.4238 4.72813 8.43841 4.80144 8.43841 4.87547C8.43841 4.9495 8.4238 5.02281 8.39541 5.09118C8.36702 5.15955 8.32541 5.22165 8.27297 5.27391L5.64797 7.89891C5.59571 7.95135 5.53362 7.99295 5.46524 8.02135C5.39687 8.04974 5.32357 8.06435 5.24953 8.06435C5.1755 8.06435 5.1022 8.04974 5.03382 8.02135C4.96545 7.99295 4.90335 7.95135 4.8511 7.89891L3.7261 6.77391C3.67377 6.72158 3.63227 6.65947 3.60395 6.5911C3.57563 6.52274 3.56106 6.44947 3.56106 6.37547C3.56106 6.30147 3.57563 6.2282 3.60395 6.15984C3.63227 6.09147 3.67377 6.02936 3.7261 5.97703C3.77842 5.92471 3.84054 5.8832 3.9089 5.85489C3.97726 5.82657 4.05054 5.81199 4.12453 5.81199C4.19853 5.81199 4.2718 5.82657 4.34017 5.85489C4.40853 5.8832 4.47065 5.92471 4.52297 5.97703L5.25 6.70312L7.47703 4.47563C7.52937 4.42342 7.59148 4.38204 7.65981 4.35385C7.72815 4.32566 7.80137 4.31122 7.87529 4.31135C7.94922 4.31148 8.02239 4.32618 8.09062 4.35461C8.15886 4.38304 8.22082 4.42464 8.27297 4.47703ZM11.0625 6C11.0625 7.00127 10.7656 7.98005 10.2093 8.81257C9.65304 9.6451 8.86239 10.294 7.93734 10.6771C7.01229 11.0603 5.99439 11.1606 5.01236 10.9652C4.03033 10.7699 3.12828 10.2877 2.42027 9.57973C1.71227 8.87173 1.23011 7.96967 1.03478 6.98764C0.839439 6.00562 0.939694 4.98772 1.32286 4.06266C1.70603 3.13761 2.3549 2.34696 3.18743 1.79069C4.01995 1.23441 4.99873 0.9375 6 0.9375C7.3422 0.938989 8.62901 1.47284 9.57809 2.42192C10.5272 3.371 11.061 4.6578 11.0625 6ZM9.9375 6C9.9375 5.22124 9.70657 4.45996 9.27391 3.81244C8.84126 3.16492 8.2263 2.66024 7.50682 2.36222C6.78733 2.0642 5.99563 1.98623 5.23183 2.13816C4.46803 2.29009 3.76644 2.6651 3.21577 3.21577C2.6651 3.76644 2.29009 4.46803 2.13816 5.23183C1.98623 5.99563 2.06421 6.78733 2.36223 7.50682C2.66025 8.2263 3.16493 8.84125 3.81244 9.27391C4.45996 9.70657 5.22124 9.9375 6 9.9375C7.04395 9.93638 8.04482 9.52118 8.783 8.783C9.52118 8.04482 9.93639 7.04395 9.9375 6Z" fill="currentColor"/></g><defs><clipPath id="clip0_3692_7975"><rect width="12" height="12" fill="white"/></clipPath></defs></svg>',
    'red': '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9.54555 2.93759L10.1666 2.25415C10.2649 2.14342 10.3155 1.99844 10.3075 1.85064C10.2996 1.70284 10.2337 1.56413 10.1242 1.46458C10.0146 1.36503 9.87026 1.31267 9.72237 1.31885C9.57449 1.32503 9.43499 1.38925 9.33414 1.49759L8.71351 2.18009C7.77933 1.52118 6.63656 1.22636 5.5002 1.35111C4.36385 1.47586 3.31225 2.01157 2.54326 2.85745C1.77427 3.70334 1.3409 4.80108 1.32469 5.94414C1.30848 7.08721 1.71054 8.1968 2.45523 9.06415L1.83414 9.74759C1.78342 9.80207 1.74402 9.86608 1.71822 9.9359C1.69242 10.0057 1.68074 10.08 1.68384 10.1543C1.68695 10.2287 1.70479 10.3017 1.73632 10.3692C1.76786 10.4366 1.81246 10.4971 1.86754 10.5471C1.92263 10.5972 1.98711 10.6358 2.05723 10.6608C2.12736 10.6858 2.20174 10.6965 2.27607 10.6925C2.3504 10.6885 2.4232 10.6698 2.49024 10.6375C2.55728 10.6052 2.61724 10.5598 2.66664 10.5042L3.28726 9.82165C4.22145 10.4806 5.36422 10.7754 6.50058 10.6506C7.63693 10.5259 8.68853 9.99017 9.45752 9.14429C10.2265 8.2984 10.6599 7.20066 10.6761 6.05759C10.6923 4.91453 10.2902 3.80494 9.54555 2.93759ZM2.43789 6.00087C2.43735 5.35862 2.61057 4.72819 2.93921 4.17639C3.26784 3.62459 3.73965 3.17198 4.30461 2.86653C4.86957 2.56108 5.50665 2.41417 6.14833 2.44137C6.79 2.46857 7.41236 2.66886 7.94945 3.02103L3.2193 8.22415C2.71282 7.5939 2.4371 6.8094 2.43789 6.00087ZM6.00039 9.56337C5.30769 9.56403 4.63001 9.36144 4.05133 8.98071L8.78148 3.77759C9.20114 4.30125 9.46424 4.93286 9.54041 5.5996C9.61659 6.26633 9.50275 6.94101 9.21203 7.54584C8.9213 8.15066 8.46553 8.66099 7.89729 9.01796C7.32904 9.37493 6.67146 9.564 6.00039 9.56337Z" fill="currentColor"/></svg>',
    'yellow': '<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1.3125 3C1.3125 2.85082 1.37176 2.70774 1.47725 2.60225C1.58274 2.49676 1.72582 2.4375 1.875 2.4375H10.125C10.2742 2.4375 10.4173 2.49676 10.5227 2.60225C10.6282 2.70774 10.6875 2.85082 10.6875 3C10.6875 3.14918 10.6282 3.29226 10.5227 3.39775C10.4173 3.50324 10.2742 3.5625 10.125 3.5625H1.875C1.72582 3.5625 1.58274 3.50324 1.47725 3.39775C1.37176 3.29226 1.3125 3.14918 1.3125 3ZM1.875 5.4375H7.875C8.02418 5.4375 8.16726 5.37824 8.27275 5.27275C8.37824 5.16726 8.4375 5.02418 8.4375 4.875C8.4375 4.72582 8.37824 4.58274 8.27275 4.47725C8.16726 4.37176 8.02418 4.3125 7.875 4.3125H1.875C1.72582 4.3125 1.58274 4.37176 1.47725 4.47725C1.37176 4.58274 1.3125 4.72582 1.3125 4.875C1.3125 5.02418 1.37176 5.16726 1.47725 5.27275C1.58274 5.37824 1.72582 5.4375 1.875 5.4375ZM10.125 6.1875H1.875C1.72582 6.1875 1.58274 6.24676 1.47725 6.35225C1.37176 6.45774 1.3125 6.60082 1.3125 6.75C1.3125 6.89918 1.37176 7.04226 1.47725 7.14775C1.58274 7.25324 1.72582 7.3125 1.875 7.3125H10.125C10.2742 7.3125 10.4173 7.25324 10.5227 7.14775C10.6282 7.04226 10.6875 6.89918 10.6875 6.75C10.6875 6.60082 10.6282 6.45774 10.5227 6.35225C10.4173 6.24676 10.2742 6.1875 10.125 6.1875ZM7.875 8.0625H1.875C1.72582 8.0625 1.58274 8.12176 1.47725 8.22725C1.37176 8.33274 1.3125 8.47582 1.3125 8.625C1.3125 8.77418 1.37176 8.91726 1.47725 9.02275C1.58274 9.12824 1.72582 9.1875 1.875 9.1875H7.875C8.02418 9.1875 8.16726 9.12824 8.27275 9.02275C8.37824 8.91726 8.4375 8.77418 8.4375 8.625C8.4375 8.47582 8.37824 8.33274 8.27275 8.22725C8.16726 8.12176 8.02418 8.0625 7.875 8.0625Z" fill="currentColor"/></svg>',
  }
  let variant = this.getAnswerVariantClass(answer)
  return icons[variant]
},
getOptionClass(alternative, answer) {
    let selectedOption = alternative.id == answer
    if (alternative.is_correct)
        return 'alternative-correct'
    else if( selectedOption && !answer.is_correct )
        return 'alternative-incorrect'
    
    return ''
},

getEnunciation(question) {
    this.expandedEnunciation = false
    this.currentAnswerTab = 'student-answer'
    this.selectPoint = []
    this.selectedQuestion = {}
    this.totalPoints = 0
    if (question && (question.pk || question.id)) {
        this.spinnerFeedbackSaved = true
        let questionUrl = `{% url 'questions:questions_api_detail' pk='00000000-0000-0000-0000-000000000000' %}?randomization_version_pk=${this.applicationStudent.randomization_version ? this.applicationStudent.randomization_version.id : ''}&application_student=${this.applicationStudent.pk}`
        questionUrl = questionUrl.replace('00000000-0000-0000-0000-000000000000', question.pk)
        axios.get(questionUrl).then(response => {

            this.selectedQuestion = response.data
            this.selectedQuestion['order'] = question.order
            this.selectedQuestion.alternatives.forEach(element => {
                element.text = element.text.replaceAll('\\\\', '\\')
            })
            this.selectedQuestion.pk = question.pk
            this.selectedQuestion.answer = question.answer
            this.selectedQuestion.empty = question.empty
            this.selectedQuestion.sum_question_sum_value = question.sum_question_sum_value
            this.selectedQuestion.sum_question_checked_answers = question.sum_question_checked_answers
    
            this.selectedQuestion.answer_created_by_id = question.answer_created_by_id
            this.selectedQuestion.answer_created_by_name = question.answer_created_by_name
            this.selectedQuestion.answer_created_at = question.answer_created_at
    
            this.alternativeUpdate = question.answer
            this.selectedQuestion.textual_answer = question.textual_answer
            this.selectedQuestion.textual_answer_content = question.textual_answer_content
            this.selectedQuestion.similar_answers = question.similar_answers
            this.selectedQuestion.file_answer = question.file_answer
            this.selectedQuestion.file_answer_url = question.file_answer_url
            this.selectedQuestion.option_answer = question.option_answer
            this.selectedQuestion.corrected_but_no_answer = question.corrected_but_no_answer
            this.selectedQuestion.category = question.category
            this.selectedQuestion.teacher_feedback = question.teacher_feedback
            this.selectedQuestion.percent_grade = question.percent_grade
            this.selectedQuestion.teacher_grade = question.teacher_grade
            this.selectedQuestion.question_weight = question.question_weight
            this.selectedQuestion.img_annotations = question.img_annotations
            this.selectedQuestion.exam_teacher_subject = question.exam_teacher_subject
            this.selectedQuestion.suggestions = question.suggestions
            
            this.selectedQuestion.generate_correction_criterion.forEach(generate => {
                generate.question = question.pk
            })

            this.selectedQuestion.generate_correction_criterion.forEach((criterion) => {
                if(criterion.question == question.pk) {
                    response.data.text_correction_answer.forEach((competence) => {
                        if(criterion.order == competence.order) {
                            criterion.checkedLabel = competence.point
                        }
                    })
                } 
            })
            response.data.text_correction_answer.forEach(correction => {
                this.selectedCorrection(question.pk, correction.order, correction.point, correction.correction_criterion)
            });

            this.feedbackSaved = false
            this.feedbackSaving = false
            this.feedbackError = false
            this.spinnerFeedbackSaved = false
        }) 
    }
},

formatDate: function(date) {
    return moment(date).format('HH:mm:ss')
},
setGrade(grade) {
    this.selectedQuestion.teacher_grade = grade
    this.$forceUpdate()
},
setEmptyAnswer() {
    Swal.fire({
        text: 'Você tem certeza que deseja deixar a nota do aluno em branco?',
        showConfirmButton: true,
        showCancelButton: true,
        confirmButtonText: 'Sim, confirmo',
        cancelButtonText: `Cancelar`,
    }).then((result) => {
        if(result.isConfirmed) {

            let feedbackUrl = ''
            let answerId = ''
            if(this.selectedQuestion.category === 'Discursiva') {
            
                feedbackUrl = "{% url 'answers:text_update_feedback' pk='00000000-0000-0000-0000-000000000000' %}"
                answerId = this.selectedQuestion.textual_answer
            
            } else if (this.selectedQuestion.category === 'Arquivo anexado') {
                
                feedbackUrl = "{% url 'answers:file_update_feedback' pk='00000000-0000-0000-0000-000000000000' %}"
                answerId = this.selectedQuestion.file_answer

            } else {

                feedbackUrl = "{% url 'applications:api-set-empty-questions-applicationstudent' pk='00000000-0000-0000-0000-000000000000' %}"
                answerId = this.selectedApplicationStudent.pk

                axios.post(feedbackUrl.replace('00000000-0000-0000-0000-000000000000', answerId), { question_id: this.selectedQuestion.pk }).then((response) => {
                    this.applicationStudent.empty_option_questions = response.data
                    
                    let _question = this.applicationStudent.questions.find(question => question.pk === this.selectedQuestion.pk)
                    
                    this.selectedQuestion.answer = null
                    this.selectedQuestion.option_answer = null
                    this.selectedQuestion.empty = null

                    _question.answer = null
                    _question.option_answer = null
                    _question.empty = true
                    
                    this.$forceUpdate()
                })
                
                return
            }
            
            if(answerId) {
                feedbackUrl = feedbackUrl.replace('00000000-0000-0000-0000-000000000000', answerId)
            }
        
            const requestBody = { 
                question: this.selectedQuestion.pk,
                who_corrected: '{{user.id}}',
                student_application: this.applicationStudent.pk,
                empty: true,
            }

            axios.put(feedbackUrl, requestBody).then(response => {
                this.selectedQuestion.empty = response.data.empty
                this.selectedQuestion.teacher_grade = null
                
                let _question = this.applicationStudent.questions.find(question => question.pk === this.selectedQuestion.pk)
                _question.empty = this.selectedQuestion.empty
                _question.teacher_grade = null
                
                this.$forceUpdate()
            })
        }
    })
},
resetDataSelectedQuestion(applicationStudentQuestion, response, removeAnswer) {
    if (removeAnswer) {
        this.selectedQuestion.answer = null
        this.selectedQuestion.option_answer = null
        this.selectedQuestion.textual_answer = null
        this.selectedQuestion.file_answer = null
        this.selectedQuestion.teacher_grade = null
        this.selectedQuestion.who_corrected = null
        this.selectedQuestion.corrected_but_no_answer = null
        this.selectedQuestion.empty = false
        
        applicationStudentQuestion.answer = null
        applicationStudentQuestion.option_answer = null
        applicationStudentQuestion.textual_answer = null
        applicationStudentQuestion.file_answer = null
        applicationStudentQuestion.teacher_grade = null
        applicationStudentQuestion.who_corrected = null
        applicationStudentQuestion.corrected_but_no_answer = null
        applicationStudentQuestion.empty = false

    } else {

        this.selectedQuestion.teacher_grade = response.data.teacher_grade
        this.selectedQuestion.who_corrected = response.data.who_corrected
        this.selectedQuestion.corrected_but_no_answer = response.data.corrected_but_no_answer
        
        applicationStudentQuestion.teacher_grade = response.data.teacher_grade
        applicationStudentQuestion.who_corrected = response.data.who_corrected
        applicationStudentQuestion.corrected_but_no_answer = response.data.corrected_but_no_answer
    }

    this.$forceUpdate()

},
removeGradeAlert(isOption=true) {
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
            this.removeGrade()
        } else if (result.isDenied) {
            this.removeGrade(removeAnswer = true)
        }
    })
},
removeGrade(removeAnswer) {

    let url = removeAnswer ? this.urls.textualAnswerDelete : this.urls.textualAnswerUpdate
    let id = this.selectedQuestion.textual_answer

    if(this.selectedQuestion.category == "Arquivo anexado") {
        
        url = removeAnswer ? this.urls.fileAnswerDelete : this.urls.fileAnswerUpdate
        id = this.selectedQuestion.file_answer

    } else if(this.selectedQuestion.category == "Objetiva") {

        url = this.urls.optionAnswerDelete
        id = this.selectedQuestion.option_answer
    
    }

    let applicationStudentQuestion = this.applicationStudent.questions.find(q => q.pk == this.selectedQuestion.pk)
    
    if (this.selectedQuestion.category == "Objetiva" || removeAnswer) {
        axios.delete(this.getUrl(url, id)).then((response) => {
            this.resetDataSelectedQuestion(applicationStudentQuestion, null, true)
        })
    } else {
        object = { 
            teacher_grade: null,
            who_corrected: null,
            corrected_but_no_answer: false,
        }
    
        axios.patch(this.getUrl(url, id), object).then((response) => {
            this.resetDataSelectedQuestion(applicationStudentQuestion, response)
        }).catch((e) => {
            console.log(e)
        })
    }

},
setQuestionList(question, questionWeight, hasCorrection=false, isOption) {
    if(questionWeight === null || questionWeight === undefined) {
        this.removeGradeAlert(isOption)
        return 
    }
    question.teacher_grade = questionWeight
    this.sendTeacherFeedback(question, next = false, hasCorrection)
},
changeViewType(){
    this.correctionFast = !this.correctionFast
    localStorage.setItem('correctionFast', this.correctionFast)

},
getQuestionsSummary(summary, applicationStudent) {
    if(summary == 'correct_answers') {
        return applicationStudent.questions.filter(question => !question.annuled && question.teacher_grade == question.question_weight).length
    } else if(summary == 'partial_answers') {
        return applicationStudent.questions.filter(question => !question.annuled && question.teacher_grade > 0 && question.teacher_grade < question.question_weight).length
    } else if(summary == 'incorrect_answers') {
        return applicationStudent.questions.filter(question => !question.annuled && question.teacher_grade == 0).length
    } else if(summary == 'total_grade') {
        return applicationStudent.questions.filter(question => !question.annuled).reduce((total = 0, question) => {
            return total += Number(question.teacher_grade)
        }, 0)
    }
},
sendTeacherFeedback(question, next = false, hasCorrection = false) {  
    self = this
    let feedbackUrl = ''
    let answerId = ''
    
    if(question.category === 'Discursiva') {
        feedbackUrl = "{% url 'answers:text_update_feedback' pk='00000000-0000-0000-0000-000000000000' %}"
        answerId = question.textual_answer
    } else {
        feedbackUrl = "{% url 'answers:file_update_feedback' pk='00000000-0000-0000-0000-000000000000' %}"
        answerId = question.file_answer
    }
    
    if(answerId) {
        feedbackUrl = feedbackUrl.replace('00000000-0000-0000-0000-000000000000', answerId)
    }   
    const requestBody = { 
        question: question.pk,
        teacher_feedback: question.teacher_feedback, 
        teacher_grade: question.teacher_grade ? question.teacher_grade : 0, 
        who_corrected: '{{user.id}}',
        student_application: this.applicationStudent.pk,
        ai_suggestion_accepted: question.ai_suggestion_accepted ? true : false,
    }

    if(parseFloat(question.teacher_grade) >= 0 && parseFloat(question.teacher_grade) <= parseFloat(question.question_weight)){
        
        self.spinnerFeedbackSaved = true

        axios.put(feedbackUrl, requestBody).then(response => {
            
            question.formValid = 'is-valid'
            let _question = this.applicationStudent.questions.find(element => element.pk === question.pk)

            if(question.category === 'Discursiva') {
                question.textual_answer = response.data.id
            } else {
                question.file_answer = response.data.id
            }
            
            _question.teacher_feedback = response.data.teacher_feedback
            _question.teacher_grade = response.data.teacher_grade
            _question.corrected_but_no_answer = response.data.corrected_but_no_answer
            _question.empty = false
            this.selectedQuestion.empty = false
            
            if(next) {
                currentIndex = this.applicationStudent.questions.findIndex(question => !question.teacher_grade && question.category != 'Objetiva')
                this.getEnunciation(this.applicationStudent.questions[currentIndex])
            }
            if(!hasCorrection){
                this.saveUpdateCorrection(question)
            }
            self.spinnerFeedbackSaved = false
        }).catch(error => {
            self.feedbackError = true
            self.spinnerFeedbackSaved = false
        })
    } else {
        if(question.teacher_grade){
            question.formValid = 'is-invalid'
        }
    }
},
orderQuestions(category, invertOrdering=true) {
    const self = this

    if(self.ordering.category == category) {            
        self.ordering.ascending = invertOrdering ? !self.ordering.ascending : self.ordering.ascending
    } else {
        self.ordering.ascending = true
        self.ordering.category = category       
    }

    this.applicationStudent.questions.sort((firstQuestion, secondQuestion) => {
        let firstValue = parseInt(firstQuestion.order);
        let secondValue = parseInt(secondQuestion.order);
        switch (category) {
            case 'duration':
                firstValue = new Date(`2000-01-01T${firstQuestion.duration}.000000-00:00`)
                secondValue = new Date(`2000-01-01T${secondQuestion.duration}.000000-00:00`)
                break;
            case 'total_answers':
                firstValue = parseInt(firstQuestion.total_answers);
                secondValue = parseInt(secondQuestion.total_answers);
                break;
            case 'last_modified':
                firstValue = new Date(firstQuestion.last_modified);
                secondValue = new Date(secondQuestion.last_modified);
                break;
            default:
                break;
        }
        
        return self.ordering.ascending ? firstValue - secondValue : secondValue - firstValue
    })
},

generateAlternativeOrder(index, isSum=false){
    if (isSum) {
        return Math.pow(2, index)
    }
    return "abcdefghijk"[index]
},

updateChoiceAnswer(alternativeID, questionToUpdate, isSelectedQuestion = false) {
    this.selectedQuestion = questionToUpdate
    let questionPK = this.selectedQuestion.id ? this.selectedQuestion.id : this.selectedQuestion.pk
    this.loadingSaveQuestion.push(questionPK)

    data = {
        "student_application": this.applicationStudent.pk,
        "question_option": alternativeID,
    }    
    axios.post("{% url 'answers:create_option_coordination' %}", data)
    .then((response) => {
        
        this.selectedQuestion.answer = response.data.question_option
        this.selectedQuestion.option_answer = response.data.id
        this.selectedQuestion.answer_created_by_id = response.data.created_by
        this.selectedQuestion.answer_created_by_name = response.data.created_by_name
        this.selectedQuestion.answer_created_at = response.data.created_at
        this.selectedQuestion.is_correct = response.data.is_correct
        this.selectedQuestion.empty = false
        
        this.selectedApplicationStudent.empty_option_questions.splice(this.selectedApplicationStudent.empty_option_questions.indexOf(this.selectedQuestion.pk), 1)
        
        if(isSelectedQuestion) {
            let question = this.applicationStudent.questions.find((_question) => _question.id == this.selectedQuestion.id || _question.pk == this.selectedQuestion.id)
            question.answer = response.data.question_option
            question.option_answer = response.data.id
            question.answer_created_by_id = response.data.created_by
            question.answer_created_by_name = response.data.created_by_name
            question.answer_created_at = response.data.created_at
            question.is_correct = response.data.is_correct
            question.empty = false
        }
        this.$forceUpdate()
    }).finally(() => {
        this.loadingSaveQuestion.splice(questionPK, 1)
    })
},

updateSumQuestionAnswer(sumValue, questionToUpdate, isSelectedQuestion = false) {
    this.selectedQuestion = questionToUpdate
    let questionPK = this.selectedQuestion.id ? this.selectedQuestion.id : this.selectedQuestion.pk
    this.loadingSaveQuestion.push(questionPK)

    data = {
        "application_student": this.applicationStudent.pk,
        "question": questionPK,
        "sum_value": sumValue,
    }

    axios.post("{% url 'answers:sum_question_update' %}", data)
    .then((response) => {
        this.selectedQuestion.answer_created_by_id = response.data.created_by
        this.selectedQuestion.answer_created_by_name = response.data.created_by_name
        this.selectedQuestion.answer_created_at = response.data.created_at
        this.selectedQuestion.sum_question_sum_value = response.data.sum_question_sum_value
        this.selectedQuestion.sum_question_checked_answers = response.data.checked_answers
        this.selectedQuestion.teacher_grade = response.data.grade
        this.selectedQuestion.empty = false
        
        this.selectedApplicationStudent.empty_option_questions.splice(this.selectedApplicationStudent.empty_option_questions.indexOf(this.selectedQuestion.pk), 1)
        
        if(isSelectedQuestion) {
            let question = this.applicationStudent.questions.find((_question) => _question.id == this.selectedQuestion.id || _question.pk == this.selectedQuestion.id)
            question.answer_created_by_id = response.data.created_by
            question.answer_created_by_name = response.data.created_by_name
            question.answer_created_at = response.data.created_at
            question.sum_question_sum_value = response.data.sum_question_sum_value
            question.sum_question_checked_answers = response.data.checked_answers
            question.teacher_grade = response.data.grade
            question.empty = false
        }
    }).finally(() => {
        this.loadingSaveQuestion.splice(questionPK, 1)
    })
},

checkAnswerType(fileanswer) {
    if(fileanswer) {
        const types = ['.jpeg', '.jpg', '.jpe', '.jfif', '.png', '.bmp', '.gif', '.tif', '.psd', '.tiff', '.exif', '.raw', '.crw', '.cr2', '.nef', '.nrw', '.eps', '.svg', '.webp']
        if(types.find(type => fileanswer.toLowerCase().includes(type)))
            return true
    }
    return false
},
changeStudent(option) {
    currentIndex = this.applicationsStudent.indexOf(this.applicationsStudent.find(s => s.id == this.selectedApplicationStudent.pk))
    if(option == 'previous') {
        this.openStudentModal(this.applicationsStudent[currentIndex > 0 ? currentIndex - 1 : 0])
    } else {
        this.openStudentModal(this.applicationsStudent[currentIndex < (this.applicationsStudent.length -1) ? currentIndex + 1: (this.applicationsStudent.length - 1)])
    }
},
getUrl(url, id1, id2 = '') {
    return url.replace('00000000-0000-0000-0000-000000000000', id1).replace('11111111-1111-1111-1111-111111111111', id2)
},
proportion(value, denominator) {
    if (value && denominator > 0) {
        value /= denominator;
        return value * 100;
    }
    return 0;
},
selectedCorrection(questionId, order, point, criterionId){ 
                
    let competence = this.selectPoint.find((item) => item.order == order)
    if(competence){
        competence.point = point;
    }else{
        this.selectPoint.push({'questionId': questionId, 'order': order ,'point': point, 'criterion_id': criterionId});
    }
    let sumMaximumScore = this.selectedQuestion.generate_correction_criterion.reduce((total = 0 , generate_correction_criterion) => total + parseFloat(generate_correction_criterion.maximum_score), 0);
    
    let sumPoints = this.selectPoint.reduce((total = 0 , competence) => total + competence.point, 0)

    let total = (sumPoints  / sumMaximumScore) * this.selectedQuestion.question_weight;
    this.totalPoints = total.toFixed(2)
    this.selectedQuestion.teacher_grade = total.toFixed(2)
},
saveUpdateCorrection() {
    this.selectPoint.forEach(competence => {
        let correction = this.selectedQuestion.text_correction_answer.find((item) => item.order == competence.order)
        let answerCorretion = this.selectedQuestion.category === 'Discursiva' ? 'textual_answer' : 'file_answer'
        let formData = new FormData()
        formData.append('correction_criterion', competence.criterion_id)
        formData.append('point', competence.point)
        formData.append(answerCorretion, this.selectedQuestion[answerCorretion])


        if(!correction){
            let correctionAnswer = '';
            if(this.selectedQuestion.category === 'Discursiva'){
                correctionAnswer = "{% url 'corrections:correction_textual_answer_list_create' %}"
            }else{
                correctionAnswer = "{% url 'corrections:correction_file_answer_list_create' %}"
            }
            axios.post(correctionAnswer, formData)
            .then(response => {
                let corretionAnswer = this.selectedQuestion.category === 'Discursiva' ? 'textual_answer' : 'file_answer'
                this.selectedQuestion.text_correction_answer.push({
                    'correction_criterion': competence.criterionId,
                    'order': competence.order,
                    'id': response.data.id ,
                    'point': response.data.point,
                    corretionAnswer: response.data[corretionAnswer]
                })
            })
        }else{
            if(this.selectedQuestion.category === 'Discursiva'){
                correctionUpdateUrl = "{% url 'corrections:correction_textual_answer_update' pk='00000000-0000-0000-0000-000000000000' %}"
            }else{
                correctionUpdateUrl = "{% url 'corrections:correction_file_answer_update' pk='00000000-0000-0000-0000-000000000000' %}"
            }
            axios.put(correctionUpdateUrl.replace("00000000-0000-0000-0000-000000000000", correction.id), formData)
        }
    })
},
clearApplicationStudent(applicationStudent, missed = null) {
    url = this.getUrl(this.urls.clearApplicationStudent, applicationStudent.id)
    if (missed != null) {
        Swal.fire({
            title: `Você confirma?`,
            html: `Você esta prestes a marcar falta no aluno(a) <br/><strong>${applicationStudent.student_name}<strong>`,
            showCancelButton: true,
            confirmButtonText: 'Confirmar',
            confirmButtonColor: '#736DD8',
            showLoaderOnConfirm: true,
        }).then((result) => {
            if (result.isConfirmed) {
                axios.patch(url, {  missed: missed }).then((response) => {
                    this.alertTop(missed ? 'Falta adicionada ao aluno':'A falta foi removida')
                    applicationStudent.missed = response.data.missed
                })
            }
        })
    } else {
        Swal.fire({
            title: `Você quer digitar algum feedback?`,
            html: `Você selecionou o aluno(a) <br/><strong>${applicationStudent.student_name}<strong>`,
            input: 'text',
            inputAttributes: {
                autocapitalize: 'off'
            },
            showCancelButton: true,
            confirmButtonText: 'Confirmar',
            confirmButtonColor: '#736DD8',
            showLoaderOnConfirm: true,
            preConfirm: (value) => {
                return axios.patch(url + '?clean_answers=true', {  feedback_after_clean: value }).then(response => {
                    return response.data
                }).catch(error => {
                    if (error.response) {
                        Swal.showValidationMessage(error.response.data)
                    }
                })
            },
            allowOutsideClick: () => !Swal.isLoading()
        }).then((result) => {
            if (result.isConfirmed) {
                if (result.value) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Prova zerada com sucesso'
                    })
                    applicationStudent.total_answers = 0
                    applicationStudent.total_correct_answers = 0
                    applicationStudent.total_corrected_answers = 0
                    applicationStudent.total_grade = null
                    applicationStudent.total_incorrect_answers = 0
                    applicationStudent.total_partial_answers = 0
                    applicationStudent.total_text_file_answers = 0
                }
            }
        })
    }
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
setSuggestion(suggestion, setFeedback = false) {
    this.setGrade(parseFloat(this.selectedQuestion.question_weight * suggestion.grade).toFixed(4))
    this.selectedQuestion.ai_suggestion_accepted = true
    
    if (setFeedback) {
        this.selectedQuestion.teacher_feedback = suggestion.teacher_feedback
    }

    this.sendTeacherFeedback(this.selectedQuestion, true)
}