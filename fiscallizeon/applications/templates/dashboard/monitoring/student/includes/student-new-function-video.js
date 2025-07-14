{% load static %}
{% load remove_line_break %}

publishOwnFeed: function(useAudio, useVideo, shareScreen=false) {
  var self = this 
  var media = {}

  if (shareScreen){
    media = { video: "screen", audioRecv: false, videoRecv: false, audioSend: useAudio, videoSend: useVideo, data: false }
    var sharing = "screen"
  }else{
    media = { audioRecv: true, videoRecv: false, audioSend: useAudio, videoSend: useVideo, data: false }
    var sharing = "video"
  }
 
  self.sfutest.createOffer({
    media: media,
    simulcast: false,
    simulcast2: false,
    success: function(jsep) {
      Janus.debug("Got publisher SDP!", jsep);
      var publish = { request: "configure", audio: useAudio, video: useVideo, display: sharing };
      self.sfutest.send({ message: publish, jsep: jsep });
    },
    error: function(error) {
      
      Janus.error("WebRTC error:", error);
      if(useAudio) {
        self.publishOwnFeed(!useAudio, useVideo, shareScreen);
      } else {
      }
    }
  });
},
newRemoteFeed: function(id, display, audio, video) {
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

  self.janus.attach(
    {
      plugin: "janus.plugin.videoroom",
      
      success: function(pluginHandle) {
        self.inspectors[length].pluginHandle = pluginHandle

        remoteFeed = pluginHandle;
        remoteFeed.simulcastStarted = false;
        Janus.log("Plugin attached! (" + remoteFeed.getPlugin() + ", id=" + remoteFeed.getId() + ")");
        Janus.log("  -- This is a subscriber");
        // We wait for the plugin to send us an offer
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
          // alert("Publisher is using " + video + ", but Safari doesn't support it: disabling video");
          subscribe["offer_video"] = false;
        }
        remoteFeed.videoCodec = video;
        remoteFeed.send({ message: subscribe });
      },
      error: function(error) {
        
        Janus.error("  -- Error attaching plugin...", error);
        // alert("Error attaching plugin... " + error);
      },
      onmessage: function(msg, jsep) {
        Janus.debug(" ::: Got a message (subscriber) :::", msg);
        var event = msg["videoroom"];
        Janus.debug("Event: " + event);
        if(msg["error"]) {
          // alert(msg["error"]);
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
        
        if($("#remote-video-"+id).length === 0) {
          $("#remote-video-"+id).bind("playing", function () {

            if(remoteFeed.spinner)
              remoteFeed.spinner.stop();
            remoteFeed.spinner = null;
          });
        }

        Janus.attachMediaStream($('#remote-video-'+id).get(0), stream);

      },
      oncleanup: function() {
        Janus.log(" ::: Got a cleanup notification (remote feed " + id + ") :::");
        if(remoteFeed.spinner)
          remoteFeed.spinner.stop();
        remoteFeed.spinner = null;
      },
    });
},
registerUsername: function() {
  var self = this
  var username = "Aluno -" + " " + self.studentId
  var register = {
    request: "join",
    room: self.videoRoomId,
    id: self.studentId,
    ptype: "publisher",
    display: username,
    pin: self.videoRoomPin,
  };
  
  try {
    self.sfutest.send({ message: register });
    self.registred = true
  }
  catch (e) {
    
    console.log(e)
    self.registred = false
    setTimeout(function(){
      self.registerUsername()
    }, 5000)
  }
  
},
createNewVideoSession: function(shareScreen=false){
  self = this
  self.janus = new Janus({
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
      self.janus.attach({
          plugin: "janus.plugin.videoroom",
          success: function(pluginHandle) {
            self.sfutest = pluginHandle;
            Janus.log("Plugin attached! (" + self.sfutest.getPlugin() + ", id=" + self.sfutest.getId() + ")");
            Janus.log("  -- This is a publisher/manager");
          },
          error: function(error) {
            
            Janus.error("  -- Error attaching plugin...", error);
            setTimeout(function(){
              self.createNewVideoSession()
            }, 5000)
            // alert("Error attaching plugin... " + error);
          },
          consentDialog: function(on) {
            Janus.debug("Consent dialog should be " + (on ? "on" : "off") + " now");
            if(on) {
              // alert("permita o uso da camera")
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
                Janus.log("Successfully joined room " + msg["room"] + " with ID " + myid);
                
                self.publishOwnFeed({{user.student.client.can_audio_receive|lower}}, true, shareScreen);

                if(msg["publishers"]) {
                  
                  var list = msg["publishers"];
                  Janus.debug("Got a list of available publishers/feeds:", list);
                  for(var f in list) {
                    var id = list[f]["id"];
                    var display = list[f]["display"];
                    var audio = list[f]["audio_codec"];
                    var video = list[f]["video_codec"];
                    Janus.debug("  >> [" + id + "] " + display + " (audio: " + audio + ", video: " + video + ")");
                    // alert("entrou alguem")
                    self.newRemoteFeed(id, display, audio, video);
                  }
                }
              } else if(event === "destroyed") {
                // The room has been destroyed
                Janus.warn("The room has been destroyed!");
                alert("The room has been destroyed", function() {
                  // window.location.reload();
                });
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
                    
                    self.newRemoteFeed(id, display, audio, video);
                  }
                } else if(msg["leaving"]) {
                  var leaving = msg["leaving"];
                  Janus.log("Publisher left: " + leaving);
                  
                  var remoteFeed = null;

                  inspector = self.getInspector(leaving)
                  
                  if (inspector != undefined){
                    remoteFeed = inspector.pluginHandle
                    self.inspectors.splice(self.inspectors.findIndex(item => item.id === leaving), 1)
                  }


                  if(remoteFeed != null) {
                    Janus.debug("Feed " + remoteFeed.rfid + " (" + remoteFeed.rfdisplay + ") has left the room, detaching");
                    
                    remoteFeed.detach();
                  }
                } else if(msg["unpublished"]) {

                  var unpublished = msg["unpublished"];
                  Janus.log("Publisher left: " + unpublished);
                  if(unpublished === 'ok') {
                    self.sfutest.hangup();
                    return;
                  }
                  var remoteFeed = null;
                  inspector = self.getInspector(unpublished)

                  if (inspector != undefined){
                    remoteFeed = inspector.pluginHandle
                    self.inspectors.splice(self.inspectors.findIndex(item => item.id === leaving), 1)
                  }

                  if(remoteFeed != null) {
                    Janus.debug("Feed " + remoteFeed.rfid + " (" + remoteFeed.rfdisplay + ") has left the room, detaching");                              
                    
                    remoteFeed.detach();
                  }
                } else if(msg["error"]) {
                  if(msg["error_code"] === 426) {
                    // This is a "no such room" error: give a more meaningful description
                    // alert(
                    //   "<p>Apparently room <code>" + self.videoRoomId + "</code> (the one this demo uses as a test room) " +
                    //   "does not exist...</p><p>Do you have an updated <code>janus.plugin.videoroom.jcfg</code> " +
                    //   "configuration file? If not, make sure you copy the details of room <code>" + self.videoRoomId + "</code> " +
                    //   "from that sample in your current configuration file, then restart Janus and try again."
                    // );
                  } else {
                    // alert(msg["error"]);
                  }
                }
              }
            }
            if(jsep) {
              Janus.debug("Handling SDP as well...", jsep);
              self.sfutest.handleRemoteJsep({ jsep: jsep });
              // Check if any of the media we wanted to publish has
              // been rejected (e.g., wrong or unsupported codec)
              var audio = msg["audio_codec"];
              if(self.mystream && self.mystream.getAudioTracks() && self.mystream.getAudioTracks().length > 0 && !audio) {
                // Audio has been rejected
                // alert("Our audio stream has been rejected, viewers won't hear us");
              }
              var video = msg["video_codec"];
              if(self.mystream && self.mystream.getVideoTracks() && self.mystream.getVideoTracks().length > 0 && !video) {
                // Video has been rejected
                // alert("Our video stream has been rejected, viewers won't see us");
                
              }
            }
          },
          onlocalstream: function(stream) {
            Janus.debug(" ::: Got a local stream :::", stream);
            self.mystream = stream;

            Janus.attachMediaStream($('#local-stream').get(0), stream);

            $("#local-stream").get(0).muted = "muted";
            
            if(self.sfutest.webrtcStuff.pc.iceConnectionState !== "completed" &&
                self.sfutest.webrtcStuff.pc.iceConnectionState !== "connected") {}
          },
          onremotestream: function(stream) {
            // The publisher stream is sendonly, we don't expect anything here

          },
          oncleanup: function() {
            Janus.log(" ::: Got a cleanup notification: we are unpublished now :::");
            self.mystream = null;
          },
        });
    },
    error: function(error) {
      
      
      setTimeout(function(){
        self.createNewVideoSession()
      }, 5000)
      
    },
    destroyed: function() {
      window.location.href = "/painel/aluno"
    }
  });
}