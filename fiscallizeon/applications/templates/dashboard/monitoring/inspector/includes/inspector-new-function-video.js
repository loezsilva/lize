{% load static %}
{% load remove_line_break %}

publishOwnFeed: function(useAudio=false, useVideo=false) {
    var self = this
    self.pluginHandle.createOffer({
        media: { audioRecv: false, videoRecv: true, audioSend: useAudio, videoSend: useVideo, data:false },
        simulcast: false,
        simulcast2: false,
        success: function(jsep) {
          Janus.debug("Got publisher SDP!", jsep);
          var publish = { request: "configure", audio: useAudio, video:useVideo };
          self.pluginHandle.send({ message: publish, jsep: jsep });

        },
        error: function(error) {
          Janus.error("WebRTC error:", error);
          if(useAudio && useVideo) {
            app.publishOwnFeed(useAudio=useAudio, useVideo=useVideo);
          } else {
            console.log("WebRTC error... xx" + error.message);
          }
        }
      });
},
newRemoteFeedInspector: function(id, display, audio, video) {
  if (!display.includes("Fiscal"))
      return

  var self = this
  var remoteFeed = null;
  var inspector = null

  var length = self.inspectors.length

  inspector = {
      "id":id,
      "pluginHandle":null,
      "displayName": display,
      "audio":audio,
      "video":video
  }

  self.inspectors.push(inspector)

  self.session.attach(
    {
      plugin: "janus.plugin.videoroom",
      
      success: function(pluginHandle) {
        self.inspectors[length].pluginHandle = pluginHandle

        remoteFeed = pluginHandle;
        remoteFeed.simulcastStarted = false;

        var subscribe = {
          request: "join",
          room: self.videoRoomId,
          ptype: "subscriber",
          feed: id,
          private_id: self.mypvtid,
          pin: self.videoRoomPin,
        };

        if(Janus.webRTCAdapter.browserDetails.browser === "safari" && (video === "vp9" || (video === "vp8" && !Janus.safariVp8))) {
          if(video)
            video = video.toUpperCase()
          console.log("Publisher is using " + video + ", but Safari doesn't support it: disabling video");
          subscribe["offer_video"] = false;
        }
        remoteFeed.videoCodec = video;
        remoteFeed.send({ message: subscribe });
      },
      error: function(error) {
        Janus.error("  -- Error attaching plugin...", error);
        // console.log("Error attaching plugin... " + error);
      },
      onmessage: function(msg, jsep) {
        Janus.debug(" ::: Got a message (subscriber) :::", msg);
        var event = msg["videoroom"];
        Janus.debug("Event: " + event);
        if(msg["error"]) {
          // console.log(msg["error"]);
        } else if(event) {
          if(event === "attached") {
            
            remoteFeed.rfid = msg["id"];
            remoteFeed.rfdisplay = msg["display"];

            Janus.log("Successfully attached to feed " + remoteFeed.rfid + " (" + remoteFeed.rfdisplay + ") in room " + msg["room"]);
          
          } else if(event === "event") {
            // Check if we got an event on a simulcast-related event from this publisher
            var substream = msg["substream"];
            var temporal = msg["temporal"];
            if((substream !== null && substream !== undefined) || (temporal !== null && temporal !== undefined)) {
              if(!remoteFeed.simulcastStarted) {
                remoteFeed.simulcastStarted = true;}
            }
          } else {
            // What has just happened?
          }
        }
        if(jsep !== undefined && jsep !== null) {
          Janus.debug("Handling SDP as well...", jsep);

          remoteFeed.createAnswer(
            {
              jsep: jsep,
              // Add data:true here if you want to subscribe to datachannels as well
              // (obviously only works if the publisher offered them in the first place)
              media: { audioSend: false, videoSend: false, data:false },	// We want recvonly audio/video
              success: function(jsep) {
                Janus.debug("Got SDP!", jsep);
                var body = { request: "start", room: self.videoRoomId };
                remoteFeed.send({ message: body, jsep: jsep });
              },
              error: function(error) {
                Janus.error("WebRTC error: sem camera", error);
                // alert("WebRTC error... xxxx " + error.message);
              }
            });
        }
      },
      iceState: function(state) {
        Janus.log("ICE state of this WebRTC PeerConnection (feed #" + remoteFeed.rfindex + ") changed to " + state);
      },
      webrtcState: function(on) {
        Janus.log("Janus says this WebRTC PeerConnection (feed #" + remoteFeed.rfindex + ") is " + (on ? "up" : "down") + " now");
      },
      onlocalstream: function(stream) {
        // The subscriber stream is recvonly, we don't expect anything here
      },
      onremotestream: function(stream) {

        Janus.debug("Remote feed #" + remoteFeed.rfindex + ", stream:", stream);
        
        if($("#inspeector-remote-video-"+id).length === 0) {
          $("#inspeector-remote-video-"+id).bind("playing", function () {

            if(remoteFeed.spinner)
              remoteFeed.spinner.stop();
            remoteFeed.spinner = null;
          });
        }

        Janus.attachMediaStream($('#inspeector-remote-video-'+id).get(0), stream);

      },
      oncleanup: function() {
        Janus.log(" ::: Got a cleanup notification (remote feed " + id + ") :::");
        if(remoteFeed.spinner)
          remoteFeed.spinner.stop();
        remoteFeed.spinner = null;
      },
    });
},
newRemoteFeed: function(id, display, audio, video, student) {
  var remoteFeed = null;
  var self = this

  student.shareScreen = (display == "screen")
  
  self.session.attach({
      plugin: "janus.plugin.videoroom",
      opaqueId: student.opaqueId,
      success: function(pluginHandle) {
        remoteFeed = pluginHandle;
        remoteFeed.simulcastStarted = false;
        Janus.log("Plugin attached! (" + remoteFeed.getPlugin() + ", id=" + remoteFeed.getId() + ")");
        Janus.log("  -- This is a subscriber");


        var subscribe = {
          request: "join",
          room: self.application.videoRoomId,
          displayName: "Fiscal - "+ " " +self.firstName,
          ptype: "subscriber",
          feed: student.studentId,
          pin: self.application.videoRoomPin,
        };

        if(Janus.webRTCAdapter.browserDetails.browser === "safari" &&
            (video === "vp9" || (video === "vp8" && !Janus.safariVp8))) {
          if(video)
            video = video.toUpperCase()
          alert("Publisher is using " + video + ", but Safari doesn't support it: disabling video");
          subscribe["offer_video"] = false;
        }
        remoteFeed.videoCodec = video;
        remoteFeed.send({ message: subscribe });
      },
      error: function(error) {
        Janus.error("  -- Error attaching plugin...", error);
        alert("Error attaching plugin... " + error);
      },
      onmessage: function(msg, jsep) {
        Janus.debug(" ::: Got a message (subscriber) :::", msg);
        var event = msg["videoroom"];
        Janus.debug("Event: " + event);
        if(msg["error"]) {
          alert(msg["error"]);
        } else if(event) {
          if(event === "attached") {
            
            remoteFeed.rfid = msg["id"];
            remoteFeed.rfdisplay = msg["display"];

            Janus.log("Successfully attached to feed " + remoteFeed.rfid + " (" + remoteFeed.rfdisplay + ") in room " + msg["room"]);

          
          } else if(event === "event") {
            // Check if we got an event on a simulcast-related event from this publisher
            var substream = msg["substream"];
            var temporal = msg["temporal"];
            if((substream !== null && substream !== undefined) || (temporal !== null && temporal !== undefined)) {
              if(!remoteFeed.simulcastStarted) {
                remoteFeed.simulcastStarted = true;
              }
            }
            // self.pluginHandle = remoteFeed
          } else {
            // What has just happened?
          }
        }
        if(jsep !== undefined && jsep !== null) {
          Janus.debug("Handling SDP as well...", jsep);
          // Answer and attach
          remoteFeed.createAnswer(
            {
              jsep: jsep,
              // Add data:false here if you want to subscribe to datachannels as well
              // (obviously only works if the publisher offered them in the first place)
              media: { audioSend: true, videoSend: true, data:false },	// We want recvonly audio/video
              success: function(jsep) {
                Janus.debug("Got SDP!", jsep);
                var body = { request: "start", room: self.roomId };
                remoteFeed.send({ message: body, jsep: jsep });
              },
              error: function(error) {
                Janus.error("WebRTC error:", error);
                console.log(error)
                Swal.fire({
                    icon: 'error',
                    title: 'Câmera e Microfone Desativado!',
                    text: 'Para utilizar nossa plataform é necessário que você autorize sua câmera e microfone.',
                    showConfirmButton: true,
                    confirmButtonText: 'Ok, irei autorizar!'
                })
              }
            });
        }
      },
      iceState: function(state) {
        Janus.log("ICE state of this WebRTC PeerConnection (feed #" + student.studentId + ") changed to " + state);
      },
      webrtcState: function(on) {
        Janus.log("Janus says this WebRTC PeerConnection (feed #" + student.studentId + ") is " + (on ? "up" : "down") + " now");
      },
      onlocalstream: function(stream) {
        // The subscriber stream is recvonly, we don't expect anything here
      },
      onremotestream: function(stream) {
        Janus.debug("Remote feed #" + student.studentId + ", stream:", stream);

        Janus.attachMediaStream($('#remote-video-'+student.studentId).get(0), stream);

        $('#remote-video-'+student.studentId).get(0).muted = "muted";
        student.actived = true
        // self.copyStreamVideoToSelectedStudent(student)
      },
      oncleanup: function() {

        Janus.log(" ::: Got a cleanup notification (remote feed " + id + ") :::");
        if(remoteFeed.spinner)
          remoteFeed.spinner.stop();
        remoteFeed.spinner = null;
      },
      
    });
},
registerUsername: function(application) {
  var self = this
  var register = {
    request: "join",
    ptype: "publisher",
    display: "Fiscal - "+ " " +self.firstName,
    room: application.videoRoomId,
    pin: application.videoRoomPin,
  };
  try {
    self.pluginHandle.send({ message: register });
    self.registred = true
  }
  catch (e) {
    console.log(e)
    self.registred = false
    setTimeout(function(){
      self.registerUsername(application)
    }, 5000)
  }
},
createNewSession: function(){
  self = this
  self.session = new Janus({
    server: "wss://"+self.server+"/ws",
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
        self.session.attach({
            plugin: "janus.plugin.videoroom",
            opaqueId: self.application.opaqueId,
            success: function(pluginHandle) {
              self.pluginHandle = pluginHandle;
              Janus.log("Plugin attached! (" + self.pluginHandle.getPlugin() + ", id=" + self.pluginHandle.getId() + ")");
              Janus.log("  -- This is a publisher/manager");
              app.registerUsername(self.application)
            },
            error: function(error) {
              Janus.error("  -- Error attaching plugin...", error);
              setTimeout(function(){
                self.createNewSession()
              }, 5000)
            },
            consentDialog: function(on) {
              Janus.debug("Consent dialog should be " + (on ? "on" : "off") + " now");
              if(on) {
                // console.log("permita o uso da camera")
              } else {
                // Restore screen
              }
            },
            iceState: function(state) {
              Janus.log("ICE state changed to " + state);
            },
            mediaState: function(medium, on) {
              Janus.log("Janus " + (on ? "started" : "stopped") + " receiving our " + medium);
            },
            webrtcState: function(on) {
              Janus.log("Janus says our WebRTC PeerConnection is " + (on ? "up" : "down") + " now");
              if(!on)
                return;
            },
            onmessage: function(msg, jsep) {
              Janus.debug(" ::: Got a message (publisher) :::", msg);
              var event = msg["videoroom"];
              Janus.debug("Event: " + event);
              if(event) {
                if(event === "joined") {
                  // Publisher/manager created, negotiate WebRTC and attach to existing feeds, if any
                  myid = msg["id"];
                  self.mypvtid = msg["private_id"];
                  Janus.log("SOwnFeeduccessfully joined room " + msg["room"] + " with ID " + myid);

                  app.publishOwnFeed(useAudio=self.shareAudio, useVideo=self.shareVideo);
                  
                  
                  if(msg["publishers"]) {
                    var list = msg["publishers"];
                    Janus.debug("Got a list of available publishers/feeds:", list);
                    for(var f in list) {
                      var id = list[f]["id"];
                      var display = list[f]["display"];
                      var audio = list[f]["audio_codec"];
                      var video = list[f]["video_codec"];
                      Janus.debug("  >> [" + id + "] " + display + " (audio: " + audio + ", video: " + video + ")");
                      
                      new_student = app.getStudent(id)

                      if (new_student !==  null && new_student !==  undefined){
                        app.newRemoteFeed(id, display, audio, video, new_student);
                      }
                      else{
                        app.newRemoteFeedInspector(id, display, audio, video);
                      }
                    }
                  }
                } else if(event === "destroyed") {
                  // The room has been destroyed
                  Janus.error("The room has been destroyed!");
                } else if(event === "event") {
                  // Any new feed to attach to?
                  if(msg["publishers"]) {
                    var list = msg["publishers"];
                    Janus.debug("Got a list of available publishers/feeds:", list);
                    for(var f in list) {
                      var id = list[f]["id"];
                      var display = list[f]["display"];
                      var audio = list[f]["audio_codec"];
                      var video = list[f]["video_codec"];
                      Janus.debug("  >> [" + id + "] " + display + " (audio: " + audio + ", video: " + video + ")");
                      
                      new_student = app.getStudent(id)

                      if (new_student !==  null && new_student !==  undefined)
                        app.newRemoteFeed(id, display, audio, video, new_student);
                      else
                        app.newRemoteFeedInspector(id, display, audio, video);
                      
                    }
                  } else if(msg["leaving"]) {
                    // One of the publishers has gone away?
                    var leaving = msg["leaving"];
                    Janus.log("Publisher left: " + leaving);
                    var remoteFeed = null;

                    student = app.getStudent(leaving)
                    
                    if(student !== undefined && student !== null) {
                      student.status = "leaving"
                      student.registred = false
                      student.actived = false
                      
                      if(student.remoteFeed !== undefined && student.remoteFeed !== null) 
                        student.remoteFeed.detach();
                    }
                    else{
                      inspector = self.inspectors.find(insp => insp.id == leaving)
                      if (inspector){
                        if(inspector.remoteFeed !== undefined && inspector.remoteFeed !== null) 
                          inspector.remoteFeed.detach();
                          self.inspectors.splice(self.inspectors.findIndex(item => item.id === leaving), 1)
                      }
                    }
                  } else if(msg["unpublished"]) {
                    var unpublished = msg["unpublished"];
                    Janus.log("Publisher left: " + unpublished);
                    if(unpublished === 'ok') {
                      self.pluginHandle.hangup();
                      return;
                    }
                    var remoteFeed = null;
                    
                    student = app.getStudent(unpublished)

                    if(student !== undefined && student !== null) {
                      student.status = "unpublished"
                      student.actived = false
                      Janus.debug("Feed has left the room, detaching");
                      
                      if(student.remoteFeed !== undefined && student.remoteFeed !== null) 
                        student.remoteFeed.detach();
                    }else{
                      inspector = self.inspectors.find(insp => insp.id == unpublished)
                      if (inspector){
                        if(inspector.remoteFeed !== undefined && inspector.remoteFeed !== null) 
                          inspector.remoteFeed.detach();
                          self.inspectors.splice(self.inspectors.findIndex(item => item.id === leaving), 1)
                      }
                    }

                  } else if(msg["error"]) {
                    if(msg["error_code"] === 426) {
                      // This is a "no such room" error: give a more meaningful description
                      console.error("<p>Apparently room <code> (the one this demo uses as a test room) " +
                        "does not exist...</p><p>Do you have an updated <code>janus.plugin.videoroom.jcfg</code> " +
                        "configuration file? If not, make sure you copy the details of room <code>" + self.application.videoRoomId + "</code> " +
                        "from that sample in your current configuration file, then restart Janus and try again."
                      );
                    } else {
                      console.error(msg["error"]);
                    }
                    setTimeout(function(){
                      self.createNewSession()
                    }, 5000)
                  }
                }
              }
              if(jsep) {
                Janus.debug("Handling SDP as well...", jsep);
                if (self.pluginHandle !== undefined && self.pluginHandle !== null)
                self.pluginHandle.handleRemoteJsep({ jsep: jsep });
                // Check if any of the media we wanted to publish has
                // been rejected (e.g., wrong or unsupported codec)
                var audio = msg["audio_codec"];
                if(self.mystream && self.mystream.getAudioTracks() && self.mystream.getAudioTracks().length > 0 && !audio) {
                  // Audio has been rejected
                  console.error("Our audio stream has been rejected, viewers won't hear us");
                }
                var video = msg["video_codec"];
                if(self.mystream && self.mystream.getVideoTracks() && self.mystream.getVideoTracks().length > 0 && !video) {
                  // Video has been rejected
                  // console.error("Our video stream has been rejected, viewers won't see us");
                  // Hide the webcam video
                }
              }
            },
            onlocalstream: function(stream) {
              Janus.debug(" ::: Got a local stream :::", stream);
              self.mystream = stream;

              Janus.attachMediaStream($('#local-stream').get(0), stream);

              $("#local-stream").get(0).muted = "muted";
              
              // if(self.pluginHandle.webrtcStuff.pc.iceConnectionState !== "completed" &&
              //     self.pluginHandle.webrtcStuff.pc.iceConnectionState !== "connected") {

              // }

             
            },
            onremotestream: function(stream) {
              // The publisher stream is sendonly, we don't expect anything here
            },
            oncleanup: function() {
              Janus.log(" ::: Got a cleanup notification: we are unpublished now :::");
            },
        });

    },
    error: function(error) {
      Janus.error(error);
      setTimeout(function(){
        self.createNewSession()
      }, 5000)
    }
  })
},
toggleCam: function(){
  self = this
  self.shareVideo = !self.shareVideo

  app.publishOwnFeed(useAudio=self.shareAudio, useVideo=self.shareVideo)

  
  // if (!self.shareVideo){
  //   var unpublish = { request: "unpublish" };
  //   self.pluginHandle.send({ message: unpublish });
  // }else{
  //   app.publishOwnFeed(useAudio=self.shareAudio, useVideo=self.shareVideo)
  // }

},
toggleAudio: function(){
  self = this
  
  self.shareAudio = !self.shareAudio

  app.publishOwnFeed(useAudio=self.shareAudio, useVideo=self.shareVideo)

},