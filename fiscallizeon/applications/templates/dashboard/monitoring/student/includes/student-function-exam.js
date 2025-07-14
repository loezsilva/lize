{% load static %}

saveAnswers(question, option_id, index, time){
    self = this
    try {
        self.saveLeaveEventPending()
        self.saveFinishPendingRequest()
    } catch (error) {
        
    }

    if (!localStorage.getItem("{{object.pk}}"+ "-" +question.id) || (localStorage.getItem("{{object.pk}}"+ "-" +question.id) && (new Date(JSON.parse(localStorage.getItem("{{object.pk}}"+ "-" +question.id)).time) <= time)))
        localStorage.setItem("{{object.pk}}"+ "-" +question.id, JSON.stringify({
            'answer': option_id, 'time': time, 'index': index
        }));

    if (!question.saving){
        question.saving = true
        
        data = {
            "student_application": "{{object.pk}}",
            "question_option": JSON.parse(localStorage.getItem("{{object.pk}}"+ "-" +question.id)).answer,
            "duration": question.timing,
            "index_alternative": index
        }

        
        axios.post("{% url 'answers:create_option'  %}", data
        ).then(function(response){
            question.saving = false
            question.error = false
            question.answerId = JSON.parse(localStorage.getItem("{{object.pk}}"+ "-" +question.id)).answer
        }).catch(function(error){
            
            if(error.response && error.response.status == 400 && error.response.data.error == 'not_allowed')
                self.callAlertNotPermitedAnswer(error.response.data.message)

            question.error = true
            question.saving = false
            question.answerId = "error"
            document.getElementById('alternative-'+option_id).checked = false
            setTimeout(function(){
                self.saveAnswers(question, option_id, index, time)
            }, 10000)
        })   
    }
},
callAlertNotPermitedAnswer(message){
    self = this
    return Swal.fire({
        icon: 'error',
        title: message,
        text: 'Caso tenha algo fora do comum, entre em contato com o suporte ou sua coordenação.',
        showConfirmButton: true,
        confirmButtonText: 'Ok!',
        allowOutsideClick: false,
        allowEscapeKey: false,
    }).then(function(){
        window.location.href = "{% url 'core:redirect_dashboard' %}"
    })
},
checkFile(question){
    self = this
    var file = self.$refs['file'+question.id][0].files[0]
    var message = ""

    if (file){
        var size =  (file.size/1024/1024).toFixed(2)

        if (size > 10)
            message += `O arquivo possui ${size}MB. Máximo permitido é de 10MB.`

        question.fileMessage = message
    }else{
        message = "Houve algum problema com seu arquivo, tente novamente!"
    }


    return message == "" ? true : false
},
saveAnswersFile(question){
    self = this

    try {
        self.saveLeaveEventPending()
        self.saveFinishPendingRequest()
    } catch (error) {
        
    }

    this.openingFileInput = false

    if (!this.checkFile(question))
        return

    question.saving = true

    let formData = new FormData();
    formData.append('question', question.id);
    formData.append('student_application', "{{object.pk}}");
    formData.append('duration', question.timing);
    formData.append('send_on_qrcode', false);
    formData.append('arquivo', self.$refs['file'+question.id][0].files[0]);


    if (question.answerId !== ""){
        url = "{% url 'answers:file_retrieve_update' pk='00000000-0000-0000-0000-000000000000'  %}"
        axios.put(url.replace("00000000-0000-0000-0000-000000000000", question.answerId), formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }}
        ).then(function(response){
            question.answerContent = response.data.arquivo
            question.send_on_qrcode = false
            question.saving = false
            question.error = false
        }).catch(function(error){

            if(error.response.status == 400 && error.response.data.error == 'not_allowed')
                self.callAlertNotPermitedAnswer(error.response.data.message)
            
            question.error = true
            question.saving = false
        })

        return
    }

    axios.post("{% url 'answers:file_create'  %}", formData, {
    headers: {
        'Content-Type': 'multipart/form-data'
    }}
    ).then(function(response){
        question.answerId = response.data.id
        question.answerContent = response.data.arquivo
        question.saving = false
        question.error = false
    }).catch(function(error){

        if(error.response.status == 400 && error.response.data.error == 'not_allowed')
                self.callAlertNotPermitedAnswer(error.response.data.message)
        
        question.error = true
        question.saving = false

    }).finally(function(){
    })

},
saveAnswersText: _.debounce(function(question){
    self = this
    
    try {
        self.saveLeaveEventPending()
        self.saveFinishPendingRequest()
    } catch (error) {
        console.log(error)
    }
    
    var content = question.answerContent

    question.saving = true

    data = {
        "question": question.id,
        "student_application": "{{object.pk}}",
        "duration": question.timing,
        "content": content
    }

    if (question.answerId !== ""){
        url = "{% url 'answers:text_retrieve_update' pk='00000000-0000-0000-0000-000000000000'  %}"
        axios.put(url.replace("00000000-0000-0000-0000-000000000000", question.answerId), data
        ).then(function(response){
            question.error = false
        }).catch(function(error){
            if(error.response.status == 400 && error.response.data.error == 'not_allowed')
                self.callAlertNotPermitedAnswer(error.response.data.message)
            question.error = true
            setTimeout(function(){
                self.saveAnswersText(question)
            }, 10000)
        }).finally(function(){
            question.saving = false
        })
    }else{
        axios.post("{% url 'answers:text_create'  %}", data).then(function(response){
            question.answerId = response.data.id
        }).then(function(){
            question.error = false
        }).catch(function(error){
            if(error.response.status == 400 && error.response.data.error == 'not_allowed')
                self.callAlertNotPermitedAnswer(error.response.data.message)
            question.error = true
            setTimeout(function(){
                self.saveAnswersText(question)
            }, 10000)
        }).finally(function(){
            question.saving = false
        })
    }

}, 1000),
changeFontSize(fontSize){
    this.fontSize = fontSize
},
alertLeavePage(){
    self = this

    if(!(["started", "paused"].indexOf(self.state) >= 0) || self.openingFileInput)
        return

    var data = {
        "event_type": "2",
        "student_application": "{{object.pk}}"
    }

    if (!self.leaveEventPending){
        axios.post("{% url 'events:event_create'  %}", data).then(function(response){
            self.leaveEventPending = response.data
        })

        if (self.pluginHandle){
            self.pluginHandle.data({
            text: JSON.stringify({
            textroom: "message",
            transaction: Janus.randomString(12),
            room: self.textRoomId,
            text: JSON.stringify({
                "type":"outScreen"
                })
            }),
            error: function(reason) {
            
            },
            success: function() {},
            });
        }
    
        
    }


    if (!(Swal.isVisible())){
        return Swal.fire({
            icon: 'error',
            title: 'Atenção! Durante a aplicação você não pode sair para outras abas!',
            text: 'Caso persista você poderá ser eliminado. Todas as vezes que você está tentando ir a outras páginas/abas estão sendo registradas.',
            showConfirmButton: true,
            confirmButtonText: 'Ok, voltar a fazer a prova'
        }).then(function(){
            self.saveLeaveEventPending()
      })
    }
    
},
saveLeaveEventPending(){
    self = this
    if (self.leaveEventPending){
        url = "{% url 'events:event_finish' pk='00000000-0000-0000-0000-000000000000'  %}"
        axios.put(url.replace("00000000-0000-0000-0000-000000000000", self.leaveEventPending.pk)).then(function(response){
            self.leaveEventPending = null
        }).then(function(){
            if (self.pluginHandle){

                self.pluginHandle.data({
                text: JSON.stringify({
                textroom: "message",
                transaction: Janus.randomString(12),
                room: self.textRoomId,
                text: JSON.stringify({
                    "type":"inScreen"
                    })
                }),
                error: function(reason) {
                    
                },
                success: function() {},
                });
            }
        })
    }
},
preOpeningFilePicker(idInput){
    self = this
    this.openingFileInput = true
    
    var interval;
    var fileElem = document.getElementById(idInput);
    
    interval = setInterval(function(){
        if (document.activeElement !== fileElem){
            self.openingFileInput = false;
            clearInterval(interval)
        }
    }, 500);

},
generateAlternativeText(alternative, index){
    alpha = "abcdefghij"
    return `${alternative.text}`
},
generateAlternativeOrder(index){
    return "abcdefghij"[index]
},
generateAlternativeSum(index){
    return String(2 ** index)
},
checkPendingAnswers(){
    self = this
    
    var storage_answer = ""

    self.getAllQuestions().find(question => {
        storage_answer = localStorage.getItem("{{object.pk}}"+ "-" +question.id) ? JSON.parse(localStorage.getItem("{{object.pk}}"+ "-" +question.id)).answer : false
        
        if (question.category == 'Objetiva' && storage_answer){
            storage_answer_time = new Date(JSON.parse(localStorage.getItem("{{object.pk}}"+ "-" +question.id)).time)

            if ((question.answerId != storage_answer) && (storage_answer_time > question.answerTime)){
                self.saveAnswers(question, storage_answer, storage_answer.index, storage_answer_time)
            }
        }

    })
},
updateSumQuestionOptions(question, optionId) {
    if (question.sumQuestionOptionsChecked.includes(optionId)) {
        this.$set(question, 'sumQuestionOptionsChecked', question.sumQuestionOptionsChecked.filter(id => id !== optionId));
    } else {
        this.$set(question, 'sumQuestionOptionsChecked', [...question.sumQuestionOptionsChecked, optionId]);
    }
},
updateselectedIndexes(question, index) {
    if (question.selectedIndexes.includes(index)) {
        const updatedIndexes = question.selectedIndexes.filter(i => i !== index);
        this.$set(question, 'selectedIndexes', updatedIndexes);
    } else {
        const updatedIndexes = [...question.selectedIndexes, index];
        this.$set(question, 'selectedIndexes', updatedIndexes);
    }
},
updateLocalStorageIfNeeded(key, question, time) {
    let savedData = JSON.parse(localStorage.getItem(key)) || {};
    if (!localStorage.getItem(key) || new Date(savedData.time) <= time) {
        savedData['sumQuestionOptionsChecked'] = question.sumQuestionOptionsChecked;
        savedData['time'] = time;
        savedData['selectedIndexes'] = question.selectedIndexes;
        localStorage.setItem(key, JSON.stringify(savedData));
    }
}, 
calculateTotalSum(question) {
    return question.selectedIndexes.reduce((sum, idx) => sum + parseInt(idx), 0);
},
saveAnswersSum(question, optionId, index, time) {
    this.updateSumQuestionOptions(question, optionId);
    this.updateselectedIndexes(question, index)
    let key = `sum-{{object.pk}}-${question.id}`;

    this.updateLocalStorageIfNeeded(key, question, time);

    let totalSum = this.calculateTotalSum(question);


    let data = {
        "student_application": "{{object.pk}}",
        "question": question.id,
        "question_option_checked": question.sumQuestionOptionsChecked,
        "value": totalSum,
        "time": time,
    };

    axios.post("{% url 'answers:create_update_sum_answer' %}", data)
    .then(response => {
        question.saving = false;
        question.error = false;
        question.sumQuestionOptionsChecked = response.data.question_option_checked

        let savedData = localStorage.getItem(key);
        
        if (savedData) {
            let parsedData = JSON.parse(savedData);
            question.selectedIndexes =  parsedData.selectedIndexes 
        }          
    })
    .catch(error => {
        question.error = true;
        question.saving = false;
        question.answerId = "error";
        setTimeout(() => {
            this.saveAnswersSum(question, optionId, index, time);
        }, 10000);
    }); 
},
calculatePowersOfTwo(number) {
    let factors = [];
    let power = 1;

    while (power <= number) {
        if (number & power) {  
            factors.push(power);
        }
        power *= 2;
    }
    return factors.map(String).sort((a, b) => parseInt(a) - parseInt(b));
},
updateSelectedIndexes() {
    this.questions.forEach((question, index) => {
        if (!Array.isArray(question.selectedIndex)) {
            question.selectedIndexes = [];
        }
        const result = this.calculatePowersOfTwo(question.values); // Example: using (index + 1)
        result.forEach(value => {
            question.selectedIndexes.push(String(value));  // Adicionando a string diretamente
        });
    });
},    
shouldHideIcon(question, alternative, index) {

    const result = question.selectedIndexes.some((selectedIndex) => {
        const generatedText = this.generateAlternativeText(alternative, index);
        const plainText = generatedText.replace(/<\/?[^>]+(>|$)/g, "");
        return plainText === String(selectedIndex); 
    });
    return result;
},