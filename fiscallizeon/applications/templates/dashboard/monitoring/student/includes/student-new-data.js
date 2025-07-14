{% load static %}
{% load remove_line_break %}


    server: "{{object.application.prefix}}.rtc.fiscallize.com.br",
    janus: null,
    sfutest: null,
    pluginHandle: null,
    mypvtid: null,
    mystream:null,
    registred:false,
    openedChat:false,
    chatNotificationCount: 0,
    transactions: [],
    myId: "",

    participants:{},

    videoRoomId: {{ object.application.video_room_id|default_if_none:'00000' }},
    videoRoomPin: "{{ object.application.video_room_pin|default_if_none:'00000' }}",

    textRoomId: {{ object.text_room_id|default_if_none:'00000' }},
    textRoomPin: "{{object.text_room_pin|default_if_none:'00000'}}",

    studentId: {{object.student_room_id|default_if_none:'00000'|safe}},

    firstName: "{{user.get_user_first_name}}",
    functionUser: "{{user.get_user_function}}",
    notificationSound: new Audio("{% static 'administration/assets/sound/not_sound.mp3' %}"),
    sendingMessage: false,
    textMessage:"",
    time: "",
    inspectors: [],
    // waiting, started, paused, finished
    state:"{{object.application_state}}",
    new_state:"{{object.application_state}}",


    selectedQuestion: null,
    errorDescription: "",

    messages: [
    {% for message in object.messages.all %}
        {
        "name": "{{message.sender.get_user_first_name}}",
        "function": "{{message.sender.get_user_function}}",
        "date_time": "{{message.created_at|date:'d/m/Y \à\s H:i'}}",
        "message": "{{message.get_escaped_content|remove_line_break}}",
        },
        {% endfor %}
    ],
    notices: [
        {% for notice in object.application.notices.all %}
        {
            "name":"{{notice.inspector.get_user_first_name}}",
            "function":"{{notice.inspector.get_user_function}}",
            "time":"{{notice.created_at|date:'H:i'}}",
            "notice":"{{notice.notice|remove_line_break}}"
        },
        {% endfor %}
        ],
    pendingRequest: 
    {% if object.pending_event %}
    {
        "pk":"{{object.pending_event.pk}}",
        "get_event_type_display": "{{object.pending_event.get_event_type_display}}",
        "created_at": "{{object.pending_event.created_at|date:'c'}}",
        "start": "{{object.pending_event.start}}",
        "end": "{{object.pending_event.end}}",
        "inspector_first_name": "{{object.pending_event.inspector.get_user_first_name}}",
        "get_response_display": "{{object.pending_event.get_response_display}}",
        "response_datetime": "{{object.pending_event.response_datetime|date:'c'}}",
    }
    {% else %}
    null
    {% endif %}
