{% load static %}
{% load remove_line_break %}

maxmizeScreen(){
  self = this
  var element = document.querySelector("body");

  element.requestFullscreen()
  .then(function() {
    self.fullScreen =  true
  })
  .catch(function(error) {
    self.fullScreen =  false
  });
},
minimizeScreen(){
  self = this
  document.exitFullscreen().then(function() {
    self.fullScreen =  false
  }).catch(function(error) {
    self.fullScreen =  true
  });
},
resizeCams(command){
  
  if(command == "+"){
    this.defaultCamSize = this.defaultCamSize + 25
    console.log(`grid-template-columns", "repeat(auto-fill, minmax(${this.defaultCamSize}px, 1fr))`)
    $('.grid-container--fit').css("grid-template-columns", `repeat(auto-fill, minmax(${this.defaultCamSize}px, 1fr))`);
  }else{
    this.defaultCamSize = this.defaultCamSize - 25
    console.log(`grid-template-columns", "repeat(auto-fill, minmax(${this.defaultCamSize}px, 1fr))`)
    $('.grid-container--fit').css("grid-template-columns", `repeat(auto-fill, minmax(${this.defaultCamSize}px, 1fr))`);
  }
},
setSelectStudent: function(student){
        
    if (!jQuery.isEmptyObject(this.selectedStudent) && this.selectedStudent !== student && this.selectedStudent.shareScreen){
      // app.toggleCam(false)
    }

    this.selectedStudent = student
    this.copyStreamVideoToSelectedStudent(student)

    student.notificationChatCount = 0
    student.notificationPauseCount = 0
    this.textMessage = ""

    $("#left-off-canvas").addClass('show');
},
copyStreamVideoToSelectedStudent: function(student){

  if (student.studentId == this.selectedStudent.studentId){
    var sourceVideo = document.getElementById('remote-video-'+student.studentId)
    var copy = document.getElementById('selected-student')
    var copyPlus = document.getElementById('plus-selected-student')
    

    var isFirefox = typeof InstallTrigger !== 'undefined';
    if (isFirefox) {
      var studentVideoStream = sourceVideo.mozCaptureStream()
    }else{
      var studentVideoStream = sourceVideo.captureStream()
    }

    copy.srcObject = studentVideoStream
    copyPlus.srcObject = studentVideoStream
  }
    
},
downScroll: function(element_id){
  $(element_id).animate({ scrollTop: 99999999999 }, 300);
},
countDown: function(){
    var countDownDate = new Date("{{object.date_time_end_tz|date:'Y-m-d H:i:s'}}").getTime();
    var x = setInterval(function() {
      
      var now = new Date().getTime();

      var distance = countDownDate - now;

      var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      var seconds = Math.floor((distance % (1000 * 60)) / 1000);

      self.time = ('0' + hours).slice(-2) + ":" + ('0' + minutes).slice(-2) + ":" + ('0' + seconds).slice(-2);

      if (distance < 0) {
        clearInterval(x);
        self.time = "Encerrado";
      }
    }, 1000);
},
getStudent: function(studentId){
  return this.students.find(element => element.studentId == studentId)
},
answerRequest: function(event, resp){
  self = this

  data = {"response": resp}

  url = "{% url 'events:event_update' pk='00000000-0000-0000-0000-000000000000'  %}"
  axios.put(url.replace("00000000-0000-0000-0000-000000000000", event.pk), data
  ).then(function(response){

    new_event = response.data

    var content = {
      "message": new_event,
      "type":"answerRequest"
    }

    var message = {
      textroom: "message",
      transaction: Janus.randomString(12),
      room: self.selectedStudent.roomId,
      text: JSON.stringify(content)
    };

    self.selectedStudent.pluginHandle.data({
      text: JSON.stringify(message),
      error: function(reason) { },
      success: function() {},
    });

  }).catch(function(error){
    Swal.fire(
      'Aconteceu algum problema',
      'Atualize sua página e tente novamente em breve.',
      'error'
    )
  })
},
sendNewAnnotation: function(){
  self = this
  self.sendingAnnotation = true
  var newAnnotation = {
    "application_student": self.selectedStudent.id,
    "annotation": self.textAnnotation,
    "suspicion_taking_advantage": self.selectedStudent.suspicionTakingAdvantage
  }

  axios.post("{% url 'applications:annotation_create_api'  %}", newAnnotation)
  .then(function(response){
    self.selectedStudent.annotations.unshift({
      "name": response.data.first_name,
      "function": response.data.function,
      "time": response.data.date_time,
      "annotation": response.data.annotation,
      "suspicionTakingAdvantage": response.data.suspicion_taking_advantage
    })

    self.selectedStudent.suspicionTakingAdvantage = false
    self.textAnnotation = ''
    self.sendingAnnotation = false
    
  }); 

},
sendNewApplicationAnnotation: function(){
  self = this
  self.sendingApplicationAnnotation = true

  self.textApplicationAnnotation = self.textApplicationAnnotation.replace("\n", "").trim()

  if (self.textApplicationAnnotation == ""){
    self.sendingApplicationAnnotation = false
    return
  }

  var newApplicationAnnotation = {
    "application": "{{ object.pk }}",
    "annotation": self.textApplicationAnnotation
  }

  axios.post("{% url 'applications:application_annotation_create_api'  %}", newApplicationAnnotation)
  .then(function(response){
    self.applicationAnnotations.unshift({
      "name":response.data.first_name,
      "function":response.data.function,
      "time":response.data.date_time,
      "annotation":response.data.annotation
    })

    self.textApplicationAnnotation = ''
    self.sendingApplicationAnnotation = false
    
  }); 
},
sendNewApplicationNotice: function(){
  self = this
  self.textApplicationNotice = self.textApplicationNotice.replace("\n", "").trim()

  Swal.fire({
    title: 'Certeza que deseja enviar este aviso?',
    text: "Ao confirmar o aviso será enviado para todos os alunos dessa aplicação",
    icon: "question",
    showCancelButton: true,
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#3085d6',
    confirmButtonText: 'Sim, enviar aviso',
    showConfirmButton: true,
  }).then((result) => {
    if (result.value) {
      self.sendingApplicationNotice = true
      
      if (self.textApplicationNotice.trim() == ""){
        self.sendingApplicationNotice = false
        return
      }

      var newApplicationNotice = {
        "application": "{{ object.pk }}",
        "notice": self.textApplicationNotice
      }

      axios.post("{% url 'applications:application_notice_create_api'  %}", newApplicationNotice)
      .then(function(response){
        self.applicationNotices.unshift({
          "name":response.data.first_name,
          "function":response.data.function,
          "time":response.data.date_time,
          "notice":response.data.notice
        })

        var content = {
          "name": response.data.first_name,
          "function": response.data.function,
          "time": moment().calendar(),
          "notice": response.data.notice,
          "type":"notice"
        }

        self.students.forEach(function(student){

            var message = {
              textroom: "message",
              transaction: Janus.randomString(12),
              room: student.roomId,
              text: JSON.stringify(content)
            };

            student.pluginHandle.data({
              text: JSON.stringify(message),
              error: function(reason) { alert(reason) },
              success: function() {}
            })
        })
        

        self.textApplicationNotice = ''
        self.sendingApplicationNotice = false

      }); 
    }
  });
},
sendMessageData: function(message){
  self = this

  var content = {
    "type":message
  }

  var message = {
    textroom: "message",
    transaction: Janus.randomString(12),
    room: self.selectedStudent.roomId,
    text: JSON.stringify(content)
  };

  self.selectedStudent.pluginHandle.data({
    text: JSON.stringify(message),
    error: function(reason) { },
    success: function() {},
  });

},
momentConvert(date, format){
  return moment(date).format(format)
},