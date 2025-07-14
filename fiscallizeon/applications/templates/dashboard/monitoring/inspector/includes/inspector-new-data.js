{% load static %}
{% load remove_line_break %}

{ fullScreen: false,
  hiddenAbsent: false,  
  defaultCamSize: {% if students.count <= 2 %}
    500,
  {% elif students.count <= 8 %}
    300,
  {% elif students.count <= 12 %}
    250,
  {% else %}
    200,
  {% endif %}
    inspectors: [],
    application: {
      id: "{{object.pk}}",
      myid: "",
      participants: {},
      server: "{{object.prefix|default_if_none:'00000'}}.rtc.fiscallize.com.br",
      textRoomId: {{ object.text_room_id|default_if_none:'00000' }},
      textRoomPin: "{{ object.text_room_pin|default_if_none:'00000' }}",

      videoRoomId: {{ object.video_room_id|default_if_none:'00000' }},
      videoRoomPin: "{{ object.video_room_pin|default_if_none:'00000' }}",
      videoRoomSecret: "{{ object.video_room_secret|default_if_none:'00000' }}",
      
      subject: "{{object.subject|capfirst}}",
      opaqueId: "textroom-"+Janus.randomString(12),
      notificationChatCount:0,
      registred:false,
      pluginHandle:null,
      messages: [
          {% for message in object.messages.all %}
          {
              sender: "{{message.sender.get_user_first_name}} ({{message.sender.get_user_function}})",
              content: "{{message.content|remove_line_break}}",
              created_at: "Hoje às {{message.created_at|date:'H:i'}}",
          },
          {% endfor %}
      ],
      pluginHandle: null,
      start: "{{object.start}}",
      end: "{{object.end}}",
  },
  notificationSound: new Audio("{% static 'administration/assets/sound/not_sound.mp3' %}"),
  server: "{{object.prefix|default_if_none:'00000'}}.rtc.fiscallize.com.br",
  janus: null,
  session: null,
  mypvtid: null,
  mystream: null,
  shareVideo: false,
  shareAudio: false,
  firstName: "{{user.get_user_first_name}}",
  function: "{{user.get_user_function}}",
  selectedStudent: {},
  transactions: [],
  textMessageCoordination: '',
  // ANOTAÇÃO
  textAnnotation:"",
  sendingAnnotation: false,
  sendingMessage: false,
  // MENSAGEM
  textMessage:"",
  // ANOTAÇÃO DA APLICAÇÃO
  textApplicationAnnotation:"",
  sendingApplicationAnnotation: false,
  // AVISOS DA APLICAÇÃO
  textApplicationNotice:"",
  sendingApplicationNotice: false,
  // CONTADOR DE TEMPO
  time:"",
  // PERMISSÃO
  isCoordination: {% if user.get_user_function == "Coordenação" %} true {% else %} false {% endif %},
  applicationAnnotations: [
    {% for annotation in object.annotations.all %}
      {
        "name":"{{annotation.inspector.get_user_first_name}}",
        "function":"{{annotation.inspector.get_user_function}}",
        "time":"{{annotation.created_at|date:'H:i'}}",
        "annotation":"{{annotation.annotation|remove_line_break}}"
        "annotation":"{{annotation.annotation|lower}}"
      },
    {% endfor %}
  ],
  applicationNotices: [
    {% for notice in object.notices.all %}
      {
        "name":"{{notice.inspector.get_user_first_name}}",
        "function":"{{notice.inspector.get_user_function}}",
        "time":"{{notice.created_at|date:'H:i'}}",
        "notice":"{{notice.notice|remove_line_break}}",
      },
    {% endfor %}
  ],
  students: [
    {% for student in students %}
        {
          "id":"{{student.id}}",
          "name": "{{student.student.name}}",
          "myid": "",
          "micOn": false,
          "firstName": "{{student.student.first_name}}",
          "roomId": {{student.text_room_id}},
          "roomPin":"{{student.text_room_pin}}",
          "registred":false,
          "studentId": {{student.student_room_id|safe}},
          "opaqueId": "videoroom-"+Janus.randomString(12),
          "device": "{{student.get_device_display|lower}}",
          "status": "created",
          "session":null,
          "pluginHandle": null,
          "shareScreen": false,
          "notificationChatCount":{{student.has_opened_messages}},
          "notificationPauseCount":{{student.count_opened_pauses}},
          "unreadAction": false,
          "state":"{{student.application_state}}",
          "actived": false,
          "isOut":{% if student.pending_leave_event %}true{% else %}false{% endif %},
          "participants":{},
          "annotations":[
            {% for annotation in student.annotations.all %}
              {
                "name":"{{annotation.inspector.get_user_first_name}}",
                "function":"{{annotation.inspector.get_user_function}}",
                "time":"{{annotation.created_at|date:'H:i'}}",
                "annotation":"{{annotation.annotation|remove_line_break}}",
                "suspicionTakingAdvantage": {{annotation.suspicion_taking_advantage|lower}}
              },
            {% endfor %}
          ],
          "messages":[
          {% for message in student.messages.all %}
            {
              "name": "{{message.sender.get_user_first_name}}",
              "function": "{{message.sender.get_user_function}}",
              "date_time": "{{message.created_at|date:'d/m/Y \à\s H:i'}}",
              "message": "{{message.get_escaped_content|remove_line_break}}",
            },
            {% endfor %}
          ],
          "events":[
            {% for event in student.bathroom_events %}
            {
              "pk":"{{event.pk}}",
              "get_event_type_display": "{{event.get_event_type_display}}",
              "created_at": "{{event.created_at|date:'c'}}",
              "start": "{{event.start}}",
              "end": "{{event.end}}",
              "inspector_first_name": "{{event.inspector.get_user_first_name}}",
              "get_response_display": "{{event.get_response_display}}",
              "response_datetime": "{{event.response_datetime|date:'c'}}",
              "student_pk": "{{student.id}}"
            },
            {% endfor %}
          ],
          "questionReports": [
              {% for report in student.get_question_error_reports %}
              {
                  "id": "{{ report.pk }}",
                  "created_at": "{{ report.created_at|date:"c" }}",
                  "question": {
                      "pk": "{{ report.question.pk }}",
                      "enunciation": {% autoescape on %} "{{ report.question|truncatechars:200|remove_line_break }}" {% endautoescape %},
                  },
                  "content": "{{ report.content|remove_line_break }}",
              },
              {% endfor %}
          ]
        },
    {% endfor %}
  ],
}
