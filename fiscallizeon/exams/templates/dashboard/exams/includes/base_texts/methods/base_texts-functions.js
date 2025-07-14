            getBaseTextsExam(exam) {
                let url = "{{base_url}}{% url 'questions:base_text_exam' pk='00000000-0000-0000-0000-000000000000' %}"
                return fetch(url.replace('00000000-0000-0000-0000-000000000000', exam))
                    .then(res => res.json())
                    .then(data => {
                        this.baseTexts = data.base_texts
                        this.getBaseTextsSubjects(this.baseTexts)
                    })
            },
            getBaseTextsSubjects(baseTexts) {
                baseTexts.forEach((baseText) => {
                    this.questions.map((question) => { 
                        if(question.base_texts.find((_baseText) => _baseText.id == baseText.id)) {
                            baseText['subject'] = question.subjectID
                        }
                    })
                })
            },
            gerateBaseTextNumbers: async function() {
                let questionsWithBaseTexts = this.questions.filter((question) => question.base_texts.length > 0)
                await questionsWithBaseTexts.forEach((question) => {
                    question.base_texts.forEach((baseText) => {
                        if(this.baseTexts.find((_baseText) => _baseText.id == baseText.id)) {
                            setTimeout(() => {
                                question['baseTextRelations'].push({ baseText: baseText, ref: document.querySelector(`[data-baseText=baseText_${baseText.id}]`).innerText})
                            }, 500)
                        }
                    })
                })
            },
            checkExists(question) {
                return this.questions.find((_question) => _question.id == question.id)
            },
            filtredBaseTexts(questions) {
                if (questions == undefined)
                    return []
                return questions.filter((question) => this.questions.find((_question) => _question.id == question.id))
            },
            getQuestionsWithTheseBaseTexts(baseTexts) {
                let questions = []
                this.questions.forEach((question) => {
                    baseTexts.forEach((baseText) => {
                        if(question.base_texts.find(_baseText => _baseText.id == baseText.id) && !questions.find(_question => _question.id == question.id)){
                            questions.push(question)
                        }
                    })
                })
                return questions
            },
            selectBaseText(baseText) {
                this.selectedBaseText = baseText
            },
            getBaseText(id, ref="") {
                this.selectedBaseText = this.baseTexts.find((baseText) => baseText.id == id)
                this.selectedBaseText['ref'] = ref
            },
            getTheLowestNumber(questions, baseText) {
                filtredQuestions = questions.filter(question => question.base_texts.find(_baseText => _baseText.id == baseText.id))
                if(filtredQuestions.length) {
                    return filtredQuestions[0].number
                }
            }