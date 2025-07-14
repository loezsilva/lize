initTinyMCE() {
    var self = this
    tinyMCE.init({
        selector: 'textarea',
        menubar: false,
        plugins: [
            'advlist autolink lists link image charmap print preview anchor',
            'searchreplace visualblocks code fullscreen',
            'insertdatetime media table paste code help wordcount'
        ],
        toolbar: 'undo redo | formatselect | ' +
        'bold italic backcolor | alignleft aligncenter ' +
        'alignright alignjustify | bullist numlist outdent indent | ' +
        'removeformat',
        content_style: 'body { font-family:Helvetica,Arial,sans-serif; font-size:14px }',
        setup:function(instance) {
            instance.on('change', (e) => {
                if(e.type == 'change') {
                    if(instance.id == 'teacher_feedback') {
                        self.selectedExamQuestion.question.feedback = instance.getContent()
                    }
                    if(instance.id == 'commented_answer') {
                        self.selectedExamQuestion.question.commented_awnser = instance.getContent()
                    }
                }
            });
        }
    })
},
changeStartNumber() {
    this.examquestions.forEach((question, index) => question.order = (this.startNumber - 1) + (index + 1))
},
recalculateQuestionsOrder() {
    this.changeStartNumber()
},
generateQuestions(quantity) {
    for (let i = 0; i < quantity; i++) {
        this.examquestions.push({
            coordinations: this.coordinations,
            order: (this.startNumber - 1) + (this.examquestions.length + 1),
            weight: 0,
            is_foreign_language: false,
            question: {
                coordinations: this.coordinations,
                enunciation: '',
                category: 1,
                subject: '',
                grade: '',
                selectedSubject: {
                    id: '',
                    name: '',
                },
                knowledgeArea: {
                    id: '',
                    name: '',
                },
                feedback: '',
                commented_awnser: '',
                alternatives: [
                    {
                        text: 'A',
                        is_correct: false,
                        index: 1,
                    },
                    {
                        text: 'B',
                        is_correct: false,
                        index: 2,
                    },
                    {
                        text: 'C',
                        is_correct: false,
                        index: 3,
                    },
                    {
                        text: 'D',
                        is_correct: false,
                        index: 4,
                    },
                    {
                        text: 'E',
                        is_correct: false,
                        index: 5,
                    },
                ],
                competences: [],
                abilities: [],
                topics: [],
                is_abstract: true,
            }
        })
        this.questionsNumber++
    }
},
removeQuestions(quantity) {
    let index = (this.examquestions.length) - quantity
    this.examquestions.splice(index, quantity)
    this.questionsNumber -= quantity
},
changeQuestionsNumber() {
    
    let newValue = this.isEnglishSpanish ? Number(this.questionsNumber) + 5 : this.questionsNumber
    let oldValue = this.examquestions.length

    if(newValue > oldValue) {
        const diference = newValue - oldValue
        this.questionsNumber -= diference
        this.generateQuestions(diference)
        
    } else {
        this.examquestions.splice(newValue, oldValue - newValue)
    }
    this.getSubjectSummary()
},
selectExamQuestion(examquestion) {
    
    this.clearData()
    
    this.selectedExamQuestion = examquestion

    if(examquestion.question.selectedOptions) {
        this.fetchGrades(examquestion.question.selectedOptions.selectedLevel).then((response) => this.grades = response.data).finally(() => {
            this.selectedLevel = examquestion.question.selectedOptions.selectedLevel
            if(examquestion.question.selectedOptions.selectedGrade) {
                this.fetchKnowledgeArea(examquestion.question.selectedOptions.selectedGrade).then((response) => this.knowledgeAreas = response.data).finally(() => {
                    this.selectedGrade = examquestion.question.selectedOptions.selectedGrade
                    if(examquestion.question.selectedOptions.selectedArea) {
                        this.selectedArea = examquestion.question.selectedOptions.selectedArea
                        this.fetchSubject(this.selectedArea).then((response) => {
                            self.subjects = response.data
                        }).finally(() => {
                            this.selectedSubject = examquestion.question.selectedSubject.id
                            this.getBNCCData(examquestion)
                        })
                    }
                })
            }
        })

    } else {
        this.fetchGrades(this.selectedLevel).then((response) => {
            this.grades = response.data
        })
    }

    tinyMCE.get('teacher_feedback').setContent(examquestion.question.feedback)
    tinyMCE.get('commented_answer').setContent(examquestion.question.commented_awnser)

},
fetchGrades: async (level) => {
    let gradeListUrl = `{% url 'classes:grade_list_api' %}?level=${level}`
    return axios.get(gradeListUrl)
},
fetchKnowledgeArea: async (grade) => {
    let knowledgeAreaListUrl = `{% url 'subjects:knowledge_area_list_api' %}?grades=${grade}`
    return axios.get(knowledgeAreaListUrl)
},
fetchKnowledgeAreasWithLanguageSubject: async (grade) => {
    let fetchKnowledgeAreasWithLanguageSubject = `{% url 'subjects:knowledge_area_with_language_subject_list_api' %}?grades=${grade}`
    return axios.get(fetchKnowledgeAreasWithLanguageSubject)
},
fetchSubject: async (knowledgeArea) => {
    let subjectListUrl = `{% url 'subjects:subject_list_api' %}?knowledge_area=${knowledgeArea}`
    return axios.get(subjectListUrl)
},
checkExist(value, list) {
    let elementExists = list.find(element => element.id == value)
    return elementExists ? elementExists.id  : ""
},
checkOption(from, to, event) {
    if (event.target.checked) {
        to.push(from)
    } else {
    let i = to.map(item => item.id).indexOf(from.id)
        to.splice(i, 1)
    }
},
fetchTopics: async(subject, grade) => {
    let objectSubject = this.subjects.find((subject_obj) => subject_obj.id == subject)
    let topictListUrl = `{% url 'subjects:topic_list_api' %}?subject_pk=${subject}&grade=${grade}`    
    
    return axios.get(topictListUrl)
},
fetchCompetences: async(subject, examquestion) => {
    
    let objectSubject = this.subjects.find((subject_obj) => subject_obj.id == subject)

    let competenceListUrl = `{% url 'bncc:competence_list_api' %}?subject_in_or_none=${subject}`

    if (objectSubject && objectSubject.parent_subjects){
        objectSubject.parent_subjects.forEach(function(parent){
            competenceListUrl += `&subject_in_or_none=${parent}`
        })
    }

    if(examquestion.question.knowledge_area){
        competenceListUrl += `&knowledge_area=${examquestion.question.knowledge_area}`
    }
    
    return axios.get(competenceListUrl)
},
fetchAbilities: async(subject, examquestion) => {

    let objectSubject = this.subjects.find((subject_obj) => subject_obj.id == subject)
    
    let abilityUrl = `{% url 'bncc:ability_list_api' %}?subject_in_or_none=${subject}&grades=${examquestion.question.grade}`

    if (objectSubject && objectSubject.parent_subjects){
        objectSubject.parent_subjects.forEach(function(parent){
            abilityUrl += `&subject_in_or_none=${parent}`
        })
    }

    if(examquestion.question.knowledge_area){
        abilityUrl += `&knowledge_area=${examquestion.question.knowledge_area}`
    }

    return axios.get(abilityUrl)
},
saveOptionsAfterCloseModalSubject() {
    if(!this.selectedExamQuestion.question.selectedOptions)
        this.selectedExamQuestion.question.selectedOptions = {}

    this.selectedExamQuestion.question.selectedOptions.selectedLevel = this.selectedLevel
    this.selectedExamQuestion.question.selectedOptions.selectedGrade = this.selectedGrade
    this.selectedExamQuestion.question.selectedOptions.selectedArea = this.selectedArea

    this.selectedExamQuestion.question.grade = this.selectedGrade
},
saveOptionsAfterCloseModalBNCCInfo() {
    if(this.currentAbilities.length > 0) {
        this.selectedExamQuestion.question.selectedOptions.selectedAbilities = this.currentAbilities
        this.selectedExamQuestion.question.abilities = this.currentAbilities.map(ability => ability.id)
    }
    if(this.currentCompetences.length > 0) {
        this.selectedExamQuestion.question.selectedOptions.selectedCompetences = this.currentCompetences
        this.selectedExamQuestion.question.competences = this.currentCompetences.map(competence => competence.id)
    }
    if(this.currentTopics.length > 0) {
        this.selectedExamQuestion.question.selectedOptions.selectedTopics = this.currentTopics
        this.selectedExamQuestion.question.topics = this.currentTopics.map(topic => topic.id)
    }
    this.resetLoads()
},
upHas(data, index) {
    if(data == 'subject') {
        if(this.examquestions[index-1] && this.examquestions[index-1].question.subject)
            return true
    } else if (data == 'weight') {
        if(this.examquestions[index-1] && this.examquestions[index-1].weight)
            return true
    }
    return false
},
copyData(data, index, examquestion) {
    if(data == 'subject') {
        examquestion.question.subject = this.examquestions[index-1].question.subject
        examquestion.question.grade = this.examquestions[index-1].question.grade
        examquestion.question['selectedOptions'] = Object.assign({}, this.examquestions[index-1].question.selectedOptions)
        examquestion.question['knowledgeArea'] = Object.assign({}, this.examquestions[index-1].question.knowledgeArea)
        examquestion.question['selectedSubject'] = Object.assign({}, this.examquestions[index-1].question.selectedSubject)
        examquestion.question['topics'] = this.examquestions[index-1].question.topics
        examquestion.question['abilities'] = this.examquestions[index-1].question.abilities
        examquestion.question['competences'] = this.examquestions[index-1].question.competences
    } else if(data == 'weight') {
        examquestion.weight = this.examquestions[index-1].weight
    }
    this.getSubjectSummary()
    this.$forceUpdate()
},
getBNCCData(examquestion) {
    this.fetchTopics(examquestion.question.subject, examquestion.question.grade).then((response) => this.topics = response.data).finally(() => {
        if(examquestion.question.selectedOptions && examquestion.question.selectedOptions.selectedTopics) {
            examquestion.question.selectedOptions.selectedTopics.map((topic) => 
            setTimeout(() => { $(`#topic_${topic.id}`).click() }, 500))
        }
        this.loads.topics = false
    })
    this.fetchCompetences(examquestion.question.subject, examquestion)
    .then((response) => this.competences = response.data)
    .finally(() => {
        if(examquestion.question.selectedOptions && examquestion.question.selectedOptions.selectedCompetences) {
            examquestion.question.selectedOptions.selectedCompetences.map((competence) => 
            setTimeout(() => { $(`#competence_${competence.id}`).click() }, 500))
        }
        this.loads.competences = false
    })
    this.fetchAbilities(examquestion.question.subject, examquestion)
    .then((response) => this.abilities = response.data)
    .finally(() => {
        if(examquestion.question.selectedOptions && examquestion.question.selectedOptions.selectedAbilities) {
            examquestion.question.selectedOptions.selectedAbilities.map((ability) => 
            setTimeout(() => { $(`#ability_${ability.id}`).click() }, 500))
        }
        this.loads.abilities = false
    })
    this.$forceUpdate()
},
clearData() {
    this.selectedExamQuestion = ''
    this.selectedLevel = 0
    this.selectedGrade = ''
    this.selectedArea = ''
    this.selectedSubject = ''
    this.grades = []
    this.knowledgeAreas = []
    this.subjects = []
    this.currentTopics = []
    this.currentCompetences = []
    this.currentAbilities = []
    this.competences = []
    this.abilities = []
    this.topics = []
},
clearBNCC() {
    this.selectedExamQuestion.question.competences = []
    this.selectedExamQuestion.question.abilities = []
    this.selectedExamQuestion.question.topics = []
},
resetLoads() {
    for(prop in this.loads) 
        this.loads[prop] = true
},
resetBNCC() {
    this.selectedExamQuestion.question.topics = []
    this.selectedExamQuestion.question.abilities = []
    this.selectedExamQuestion.question.competences = []
    if(this.selectedExamQuestion.question.selectedOptions && this.selectedExamQuestion.question.selectedOptions.selectedTopics) {
        this.selectedExamQuestion.question.selectedOptions.selectedTopics = []
    }
    if(this.selectedExamQuestion.question.selectedOptions && this.selectedExamQuestion.question.selectedOptions.selectedAbilities) {
        this.selectedExamQuestion.question.selectedOptions.selectedAbilities = []
    }
    if(this.selectedExamQuestion.question.selectedOptions && this.selectedExamQuestion.question.selectedOptions.selectedCompetences) {
        this.selectedExamQuestion.question.selectedOptions.selectedCompetences = []
    }
},
getSumWeight() {
    return this.examquestions.reduce((total, examquestion) => total += Number(examquestion.weight), 0)
},
distributeWeights() {
    let questionsCount = this.examquestions.length
    if(this.isEnglishSpanish) {
        questionsCount -= 5
    }
    value = Number(this.weightDistribution / questionsCount)
    // 6 max digitis in value
    value = value.toFixed(6)
    this.examquestions.map(examquestion => ({...examquestion.weight = value}))

    this.weightDistribution = 0
},
async getSubjectSummary() {
    this.subjectsSummaryLoading = true
    this.subjectsSummary = []
    let subjects = this.examquestions.filter(examquestion => examquestion.question.subject && examquestion.question.selectedSubject).map((examquestion) => ({ 
        id: examquestion.question.selectedSubject.id,
        name: examquestion.question.selectedSubject.name,
        questions: 1,
    }))
    
    for await (subject of subjects) {
        let subjectObject = this.subjectsSummary.find((_subject) => _subject.id == subject.id)
        if (subjectObject) {
            subjectObject.questions += 1
        } else {
            this.subjectsSummary.push(subject)
        }    
    }
    this.subjectsSummaryLoading = false
},
getSubjectWeights(subjectId) {
    return this.examquestions.filter(examquestion => subjectId ? examquestion.question.subject == subjectId : !examquestion.question.subject).reduce((sum, examquestion) => sum + Number(examquestion.weight), 0)
},
removeExamQuestion(examquestion) {
    Swal.fire({
        title: 'Confirmação',
        text: 'Você confirma que quer remover esta questão?', 
        showCancelButton: true,
        confirmButtonText: 'Confirmar',
        cancelButtonText: 'Cancelar',
    }).then((result) => {
        if (result.isConfirmed) {
            index = this.examquestions.indexOf(examquestion)
            this.examquestions.splice(index, 1)
            this.questionsNumber--
            this.changeStartNumber()
            this.getSubjectSummary()
        }
    })
},
checkValue() {
    if(this.questionsNumber > 1000) {
        this.questionsNumber = 1000
    }
    if(this.isEnglishSpanish && this.questionsNumber <= 10){
        this.questionsNumber = 10
    } 
}