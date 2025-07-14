from django.db.models import Q

from rest_framework import serializers

from ...models import Tutorial, TutorialCategory, TutorialFeedback


class TutorialSerializer(serializers.ModelSerializer):
    
    emmbbeded_video = serializers.CharField(source="get_emmbbeded_video")
    content_str = serializers.CharField(source="get_content_str")
    urls = serializers.JSONField(source="get_urls")
    
    class Meta:
        model = Tutorial
        fields = "__all__"
        
class TutorialCategorySerializer(serializers.ModelSerializer):
    urls = serializers.JSONField(source="get_urls")
    tutoriais_count = serializers.SerializerMethodField()
    description_str = serializers.CharField(source="get_description_str")
    
    class Meta:
        model = TutorialCategory
        fields = "__all__"
    
    def get_tutoriais_count(self, obj):
        if self.context['request']:
            request = self.context['request']
            user = request.user
            return obj.get_tutoriais().filter(
                Q(
                    Q(segments__isnull=True) | Q(segments__len__lte=0) | Q(segments__contains=[user.user_type])
                )
            ).count()
        
        return obj.get_tutoriais().count()


class TutorialFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorialFeedback
        fields = ('value',)
