sendMessage: function(){
    self = this

    pluginHandle = self.selectedStudent.pluginHandle


    self.textMessage = self.textMessage.replace("\n", "").trim()
    
    self.sendingMessage = true

    if (self.textMessage == ""){
      self.sendingMessage = false
      return
    }

    var newMessage = {
      "application_student": self.selectedStudent.id,
      "content": self.textMessage
    }
    
    var content = {
      "name": self.firstName,
      "function": self.function,
      "date_time": moment().calendar(),
      "message": self.textMessage,
      "type":"message"
    }

    var message = {
      textroom: "message",
      transaction: Janus.randomString(12),
      room: self.selectedStudent.roomId,
      text: JSON.stringify(content)
    };


    pluginHandle.data({
      text: JSON.stringify(message),
      error: function(reason) { alert(reason) },
      success: function() { 
          axios.post("{% url 'events:text_message_create'  %}", newMessage).then(function(response){
          self.textMessage = ""
          self.sendingMessage = false
        })
       },
    });


},
registerUsernameText: function(application){
  self = this 
  application.myid = Janus.randomString(12);
  var username = `${self.firstName} (${self.function})`
  var transaction = Janus.randomString(12);
  var register = {
    textroom: "join",
    transaction: transaction,
    room: application.textRoomId,
    username: application.myid,
    display: username,
    pin: application.textRoomPin
  };
  myusername = username;
  self.transactions[transaction] = function(response) {
    if(response["textroom"] === "error") {
      // Something went wrong
      if(response["error_code"] === 417) {
        console.error("Criação de ambiente sendo executada.");
        setTimeout(function(){
          self.registerUsernameText()
        }, 5000)
      } else {
        console.error(response["error"]);
        setTimeout(function(){
          self.registerUsernameText()
        }, 5000)
      }
      return;
    }
    
    if(response.participants && response.participants.length > 0) {
      for(var i in response.participants) {
        var p = response.participants[i];
        application.participants[p.username] = p.display ? p.display : p.username;
        if(p.username !== application.myid && $('#rp' + p.username).length === 0) {
          // Add to the application.participants list frontend
        }
      }
    }
  };
  application.pluginHandle.data({
    text: JSON.stringify(register),
    error: function(reason) {
      console.error("--- Enviar mensagem para coordenação "+reason);
    }
  });
},
registerUsernameStudentText: function(student){
  self = this 
  student.myid = Janus.randomString(12);
  var username = `${self.firstName} (${self.function})`
  var transaction = Janus.randomString(12);
  var register = {
    textroom: "join",
    transaction: transaction,
    room: student.roomId,
    username: student.myid,
    display: username,
    pin: student.roomPin
  };
  myusername = username;
  self.transactions[transaction] = function(response) {
    if(response["textroom"] === "error") {
      // Something went wrong
      if(response["error_code"] === 417) {
        console.error("Criação de ambiente sendo executada.");
        setTimeout(function(){
          self.registerUsernameStudentText(student)
        }, 5000)
      } else {
        console.error(response["error"]);
        setTimeout(function(){
          self.registerUsernameStudentText(student)
        }, 5000)
      }
      return;
    }
    
    if(response.participants && response.participants.length > 0) {
      for(var i in response.participants) {
        var p = response.participants[i];
        student.participants[p.username] = p.display ? p.display : p.username;
        if(p.username !== student.myid && $('#rp' + p.username).length === 0) {
          // Add to the student.participants list frontend
        }
      }
    }
  };
  student.pluginHandle.data({
    text: JSON.stringify(register),
    error: function(reason) {
      console.error("--- Enviar mensagem para coordenação "+reason);
    }
  });
},
createNewTextSession: function() {
  var self = this
  var janus = new Janus({
      server: `wss://${self.server}/ws`,
      iceServers :[
          {
              url: 'turn:'+self.server,
              username: 'gA42zcNAp8',
              credential: 'uzQNsqqF8c',
          },
          {
              url: 'stun:stun.fiscallize.com.br'
          },
      ],
      success: function() {
          janus.attach({
              plugin: "janus.plugin.textroom",
              opaqueId: self.application.opaqueId,
              success: function(pluginHandle) {

                  self.application.pluginHandle = pluginHandle;
          
                  Janus.log("Plugin attached! (" + self.application.pluginHandle.getPlugin() + ", id=" + self.application.pluginHandle.getId() + ")");
                  // Setup the DataChannel
                  var body = { request: "setup" };
                  Janus.debug("Sending message:", body);
                  self.application.pluginHandle.send({ message: body });
      
              },
              error: function(error) {
                  console.error("  -- Error attaching plugin..." + error);
                  setTimeout(function(){
                    self.createNewTextSession()                    
                  }, 5000)
              },
              iceState: function(state) {
                  Janus.log("ICE state changed to " + state);
              },
              mediaState: function(medium, on) {
                  Janus.log("Janus " + (on ? "started" : "stopped") + " receiving our " + medium);
              },
              webrtcState: function(on) {
                  Janus.log("Janus says our WebRTC PeerConnection is " + (on ? "up" : "down") + " now");
              },
              onmessage: function(msg, jsep) {
                  Janus.debug(" ::: Got a message :::", msg);
                  if(msg["error"]) {
                      alert(msg["error"]);
                  }
                  if(jsep) {
                      // Answer
                      self.application.pluginHandle.createAnswer(
                          {
                              jsep: jsep,
                              media: { audio: false, video: false, data: true },
                              success: function(jsep) {
                                  Janus.debug("Got SDP!", jsep);
                                  var body = { request: "ack" };
                                  self.application.pluginHandle.send({ message: body, jsep: jsep });
                              },
                              error: function(error) {
                                  Janus.error("WebRTC error:", error);
                                  alert("WebRTC error... " + error.message);
                              }
                          });
                  }
              },
              ondataopen: function(data) {
                  app.registerUsernameText(self.application)
              },
              ondata: function(data) {
                  var json = JSON.parse(data);
                  var transaction = json["transaction"];
                  if(self.transactions[transaction]) {
                      // Someone was waiting for this
                      self.transactions[transaction](json);
                      delete self.transactions[transaction];
                      return;
                  }
          
                  var what = json["textroom"];

          
                  if(what === "message") {
                      var msg = json["text"];
                      msg = msg.replace(new RegExp('<', 'g'), '&lt');
                      msg = msg.replace(new RegExp('>', 'g'), '&gt');
                      var from = json["from"];

                      if (self.application.participants[from] !== `${self.firstName} (${self.function})`){
                        self.notificationSound.play();
                        self.application.notificationChatCount += 1;
                      }

                      self.application.messages.push({
                          "sender": self.application.participants[from],
                          "content": msg,
                          "created_at": moment().calendar()
                      });

                      app.downScroll("#coordination-chat")

                  }  else if(what === "join") {
                      var username = json["username"];
                      var display = json["display"];
                      self.application.participants[username] = display ? display : username;
                      
                  } else if(what === "leave") {
                      var username = json["username"];
                      delete self.application.participants[username];
              
                  } else if(what === "destroyed") {
                      if(json["room"] !== self.application.textRoomId)
                          return;
                      // Room was destroyed, goodbye!
                      alert("A sala foi removida")
                  }
              },
              oncleanup: function() {
                  Janus.log(" ::: Got a cleanup notification :::");
              }
          });

      },
      error: function(error) {
        setTimeout(function(){
          self.createNewTextSession()                    
        }, 5000)
      },
      destroyed: function() {
          alert("Servidor foi removido!")
      }
  });
},
createNewTextStudentSession: function() {
  var self = this
  var janus = new Janus({
      server: `wss://${self.server}/ws`,
      iceServers :[
          {
              url: 'turn:'+self.server,
              username: 'gA42zcNAp8',
              credential: 'uzQNsqqF8c',
          },
          {
              url: 'stun:stun.fiscallize.com.br'
          },
      ],
      success: function() {
          
        self.students.forEach(function(student){

          janus.attach({
              plugin: "janus.plugin.textroom",
              opaqueId: student.opaqueId,
              success: function(pluginHandle) {

                  student.pluginHandle = pluginHandle;
          
                  Janus.log("Plugin attached! (" + student.pluginHandle.getPlugin() + ", id=" + student.pluginHandle.getId() + ")");
                  // Setup the DataChannel
                  var body = { request: "setup" };
                  Janus.debug("Sending message:", body);
                  student.pluginHandle.send({ message: body });
      
              },
              error: function(error) {
                  console.error("  -- Error attaching plugin..." + error);
                  setTimeout(function(){
                    self.createNewTextStudentSession()                    
                  }, 5000)
              },
              iceState: function(state) {
                  Janus.log("ICE state changed to " + state);
              },
              mediaState: function(medium, on) {
                  Janus.log("Janus " + (on ? "started" : "stopped") + " receiving our " + medium);
              },
              webrtcState: function(on) {
                  Janus.log("Janus says our WebRTC PeerConnection is " + (on ? "up" : "down") + " now");
              },
              onmessage: function(msg, jsep) {
                  Janus.debug(" ::: Got a message :::", msg);
                  if(msg["error"]) {
                      alert(msg["error"]);
                  }
                  if(jsep) {
                      // Answer
                      student.pluginHandle.createAnswer(
                          {
                              jsep: jsep,
                              media: { audio: false, video: false, data: true },
                              success: function(jsep) {
                                  Janus.debug("Got SDP!", jsep);
                                  var body = { request: "ack" };
                                  student.pluginHandle.send({ message: body, jsep: jsep });
                              },
                              error: function(error) {
                                  Janus.error("WebRTC error:", error);
                                  alert("WebRTC error... " + error.message);
                              }
                          });
                  }
              },
              ondataopen: function(data) {
                  app.registerUsernameStudentText(student)
              },
              ondata: function(data) {
                  Janus.debug("We got data from the DataChannel!", data);
                  var json = JSON.parse(data);
                  var transaction = json["transaction"];
                  if(self.transactions[transaction]) {
                      // Someone was waiting for this
                      self.transactions[transaction](json);
                      delete self.transactions[transaction];
                      return;
                  }
          
                  var what = json["textroom"];
          
                  if(what === "message") {

                      var msg = json["text"];
                      msg = msg.replace(new RegExp('<', 'g'), '&lt');
                      msg = msg.replace(new RegExp('>', 'g'), '&gt');
                      var from = json["from"];

                      var message = JSON.parse(json.text)

                      switch(message.type){
                        case "message":
                          if (student.participants[from] !== `${self.firstName} (${self.function})`){
                            self.notificationSound.play();
                            student.notificationChatCount += 1;
                          }
                          student.messages.push(message)
                          break;
                        case "changeState":
                          if (message.message.state){
                            student.state = message.message.state
                            student.device = message.message.device
                          }else{
                            student.state = message.message
                          }
                          break;
                        case "requestPause":
                          self.notificationSound.play();
                          student.notificationPauseCount++;
                          student.events.unshift(message.message)
                          break;
                        case "answerRequest":
                          self.updatePendingRequest(message, self.findEvent(message.message.pk, message.message.student_pk))
                          break;
                        case "questionErrorReport":
                            self.notificationSound.play()
                            student.unreadAction = true
                            student.questionReports.unshift(message.message)
                            break;
                          case "outScreen":
                            student.isOut = true;
                            break;
                          case "inScreen":
                            student.isOut = false;
                            break;
                        default:
                          break;
                      }

                  }  else if(what === "join") {
                      var username = json["username"];
                      var display = json["display"];
                      student.participants[username] = display ? display : username;
                      
                  } else if(what === "leave") {
                      var username = json["username"];                    
                      delete student.participants[username];
              
                  } else if(what === "destroyed") {
                      if(json["room"] !== student.textRoomId)
                          return;
                      // Room was destroyed, goodbye!
                      alert("A sala foi removida")
                  }
              },
              oncleanup: function() {
                  Janus.log(" ::: Got a cleanup notification :::");
              }
          });

        })
      },
      error: function(error) {
        setTimeout(function(){
          self.createNewTextStudentSession()                    
        }, 5000)
      },
      destroyed: function() {
          alert("Servidor foi removido!")
      }
  });
}, 
sendMessageChat: function(){
  self = this
  self.sendingMessage = true
  self.textMessageCoordination = self.textMessageCoordination.replace("\n", "").trim()

  if (self.textMessageCoordination == ""){
    self.sendingMessage = false
    return
  }

  var message = {
    textroom: "message",
    transaction: Janus.randomString(12),
    room: self.application.textRoomId,
    text: self.textMessageCoordination,
  };

  self.application.pluginHandle.data({
    text: JSON.stringify(message),
    error: function(reason) { alert("error"); },
    success: function() { 
      self.application.notificationChatCount = 0;
      
      var newMessage = {
        "application": self.application.id,
        "content": self.textMessageCoordination
      }

      axios.post("{% url 'events:aplication_message_create'  %}", newMessage).then(function(response){
        app.downScroll("#coordination-chat")

        self.textMessageCoordination = ""
        self.sendingMessage = false
      })
    }
  });
},
updatePendingRequest: function(content, event){
  self = this

  var new_event = content.message

  var student = self.students.find(student => student.id == new_event.student_pk)

  student.notificationPauseCount = 0

  if (new_event.get_response_display == "Aprovado")
    student.state = 'paused'

  event.start = new_event.start
  event.inspector_first_name = new_event.inspector_first_name
  event.get_response_display = new_event.get_response_display
  event.response_datetime = new_event.response_datetime

},
findEvent: function(event_pk, student_pk){
  return this.students.find(
      student => student.id == student_pk
    ).events.find(
      event => event.pk == event_pk
    )
},

