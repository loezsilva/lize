from rest_framework import serializers

from fiscallizeon.subjects.models import MainTopic, Theme, Topic


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = '__all__'


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = ('id', 'name',)


class MainTopicSerializer(serializers.ModelSerializer):
    theme = ThemeSerializer(read_only=True)

    class Meta:
        model = MainTopic
        fields = ('id', 'name', 'theme',)


class TopicSimpleSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.name')
    grade = serializers.SerializerMethodField(read_only=True)
    main_topic = MainTopicSerializer(read_only=True)
    theme = ThemeSerializer(read_only=True)
    stage = serializers.CharField(source='get_stage_display')

    class Meta:
        model = Topic
        fields = ('id', 'name', 'stage', 'theme', 'main_topic', 'subject', 'grade',)

    def get_grade(self, obj):
        return obj.grade.name if obj.grade else None

class TopicValidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ('id', 'name', 'stage', 'theme', 'main_topic', 'subject', 'grade',)
        extra_kwargs = {
            'stage': {'required': False, 'allow_null': True},
            'theme': {'required': False},
            'main_topic': {'required': False}
        }

    def validate(self, data):
        subject = data.get('subject')
        grade = data.get('grade')
        name = data.get('name')
        stage = data.get('stage')
        theme = data.get('theme')
        main_topic = data.get('main_topic')
        client = self.context['request'].user.get_clients().first()

        if theme:
            if Topic.objects.filter(
                    theme=theme,
                    main_topic=main_topic,
                    stage=stage,
                    name=name,
                    subject=subject,
                    client=client,
                    grade=grade
                ).exists():
                raise serializers.ValidationError("Este tópico já existe com os mesmos atributos.")
        if main_topic:
            if Topic.objects.filter(
                    main_topic=main_topic,
                    stage=stage,
                    name=name,
                    subject=subject,
                    client=client,
                    grade=grade
                ).exists():
                raise serializers.ValidationError("Este tópico já existe com os mesmos atributos.")
        else:
            if Topic.objects.filter(
                    stage=stage,
                    name=name,
                    subject=subject,
                    client=client,
                    grade=grade
                ).exists():
                raise serializers.ValidationError("Este tópico já existe com os mesmos atributos.")

        return data
