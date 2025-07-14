{% load static %}
{% load remove_line_break %}


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
                opaqueId: self.opaqueId,
                success: function(pluginHandle) {

                    self.pluginHandle = pluginHandle;
            
                    Janus.log("Plugin attached! (" + self.pluginHandle.getPlugin() + ", id=" + self.pluginHandle.getId() + ")");
                    // Setup the DataChannel
                    var body = { request: "setup" };
                    Janus.debug("Sending message:", body);
                    self.pluginHandle.send({ message: body });
        
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
                        self.pluginHandle.createAnswer(
                            {
                                jsep: jsep,
                                media: { audio: false, video: false, data: true },
                                success: function(jsep) {
                                    Janus.debug("Got SDP!", jsep);
                                    var body = { request: "ack" };
                                    self.pluginHandle.send({ message: body, jsep: jsep });
                                },
                                error: function(error) {
                                  
                                    Janus.error("WebRTC error:", error);
                                    alert("WebRTC error... " + error.message);
                                }
                            });
                    }
                },
                ondataopen: function(data) {
                    app.registerUsernameText()

                    var content = {
                      "message": {
                        "state": self.state,
                        "device": "{{object.get_device_display}}".toLowerCase()
                      },
                      "type":"changeState"
                    }

                    var message = {
                      textroom: "message",
                      transaction: Janus.randomString(12),
                      room: self.textRoomId,
                      text: JSON.stringify(content)
                    };
                    if(self.pluginHandle){
                      self.pluginHandle.data({
                        text: JSON.stringify(message),
                        error: function(reason) {
                          
                        },
                        success: function() {},
                      });
                    }
                    
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
                            if (self.participants[from] !== `${self.firstName} (${self.functionUser})`){
                              self.notificationSound.play();
                              self.chatNotificationCount += 1;
                            }

                            self.messages.push(message)
                            $(".modal-content").animate({ scrollTop: $(document).height() }, 1000);
                            break;
                          case "answerRequest":
                            self.notificationSound.play();
                            self.showAnswerRequest(message.message.get_response_display)
                            break;
                          case "notice":
                            self.notificationSound.play();
                            self.showNotice(message);
                            break;
                          case "requestShareScreen":
                              self.notificationSound.play();
                              self.showRequestShareScreen();
                              break;
                          case "requestShareVideo":
                            window.location.reload()
                            break;
                          case "broadcastQuestionUpdate":
                            self.updateQuestion(message)
                            break
                          default:
                            break;
                        }

                    }  else if(what === "join") {
                        var username = json["username"];
                        var display = json["display"];
                        self.participants[username] = display ? display : username;
                        
                    } else if(what === "leave") {
                        var username = json["username"];                    
                        delete self.participants[username];
                
                    } else if(what === "destroyed") {
                        if(json["room"] !== self.textRoomId)
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
  registerUsernameText: function(){
    self = this 

    var username = `${self.firstName} (${self.functionUser})`
    var transaction = Janus.randomString(12);
    self.myId = Janus.randomString(12);

    var register = {
      textroom: "join",
      transaction: transaction,
      room: self.textRoomId,
      username: self.myId,
      display: username,
      pin: self.textRoomPin
    };

    self.transactions[transaction] = function(response) {
      if(response["textroom"] === "error") {
        // Something went wrong
        if(response["error_code"] === 417) {
          console.error("Criação de ambiente sendo executada.");
          // window.location.reload()
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
      var check = response.participants.find(function(element){
        return element.display == username
      })

      if (check){
        // Swal.fire({
        //   icon: 'error',
        //   title: 'Atenção! Usuário já está logado em outro dispositivo!',
        //   text: 'Já existe um outro dispositivo realizando a prova com esse usuário.',
        //   showConfirmButton: true,
        //   allowEscapeKey : false,
        //   allowOutsideClick: false,
        //   allowEnterKey: false,
        //   confirmButtonText: 'Ok, sair da prova!'
        // }).then(function(){
        //   window.location.href = "{% url 'core:redirect_dashboard' %}"
        // })
      }
      else{
        self.isLoading = false;
      }
          
      if(response.participants && response.participants.length > 0) {
        for(var i in response.participants) {
          var p = response.participants[i];
          self.participants[p.username] = p.display ? p.display : p.username;
          if(p.username !== self.myid && $('#rp' + p.username).length === 0) {
            // Add to the self.participants list frontend
          }
        }
      }

      

    };
    if(self.pluginHandle){
      self.pluginHandle.data({
        text: JSON.stringify(register),
        error: function(reason) {
          
          console.error("--- Enviar mensagem para fiscal " + reason);
        }
      });
    }
  },
  sendMessage(){
    self = this

    var newMessage = {
      "application_student": "{{object.pk}}",
      "content": self.textMessage
    }

    var content = {
      "name": self.firstName,
      "function": self.functionUser,
      "date_time": moment().calendar(),
      "message": self.textMessage,
      "type":"message"
    }

    var message = {
      textroom: "message",
      transaction: Janus.randomString(12),
      room: self.textRoomId,
      text: JSON.stringify(content)
    };
    if(self.pluginHandle){
      self.pluginHandle.data({
        text: JSON.stringify(message),
        error: function(reason) { 
          
          // alert(reason) 
        },
        success: function() { 
            axios.post("{% url 'events:text_message_create'  %}", newMessage).then(function(response){
            $(".modal-content").animate({ scrollTop: $(document).height() }, 1000);
            self.textMessage = ""
          })
        },
      });
    }
  }