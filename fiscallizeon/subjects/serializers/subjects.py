from rest_framework import serializers

from fiscallizeon.subjects.models import KnowledgeArea, Subject


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class SubjectVerySimpleSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = Subject
        fields = ['id', 'name']

    def get_name(self, obj):
        return f"{obj.name} - {obj.knowledge_area.name}"


class KnowledgeAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArea
        fields = ['id', 'name']
    
    def get_name(self, obj):
        return f"{obj.name}"
        
class SubjectKnowledgeAreaSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    knowledge_area = KnowledgeAreaSerializer()
    class Meta:
        model = Subject
        fields = ['id', 'name', 'knowledge_area']

    def get_name(self, obj):
        return f"{obj.name}"

class SubjectSimpleSerializer(serializers.ModelSerializer):
    knowledge_area_name = serializers.SerializerMethodField()
    parent_subjects = serializers.SerializerMethodField()
    parent_subject = serializers.SerializerMethodField()
    knowledge_area_id = serializers.SerializerMethodField()
    grades_id = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ("id", "name", "knowledge_area_id", "grades_id", "knowledge_area_name", "parent_subjects", "parent_subject",  "is_foreign_language_subject",)

    def get_knowledge_area_name(self, obj):
        return obj.knowledge_area.name
    
    def get_knowledge_area_id(self, obj):
        return obj.knowledge_area.id
    
    def get_grades_id(self, obj):
        return list(obj.knowledge_area.grades.all().values_list('id', flat=True))
    
    def get_parent_subject(self, obj):
        request = self.context.get('request')
        
        if request:
        
            grade = request.GET.get('knowledge_area__grades')

            if obj.parent_subject and grade:
                has_grade = obj.parent_subject.knowledge_area.grades.filter(
                    id=grade
                ).exists()
                
                return obj.parent_subject.id if has_grade else None
                
    def get_parent_subjects(self, obj):
        parents = []
        visited = set()  

        def get_parent(parent):
            if parent and parent.pk not in visited:
                visited.add(parent.pk) 
                parents.append(str(parent.pk))
                return get_parent(parent.parent_subject)
            return
        
        get_parent(obj.parent_subject)
        return parents


class SubjectTreeSerializer(serializers.ModelSerializer):
    text = serializers.SerializerMethodField()
    leaf = serializers.SerializerMethodField()
    checked = serializers.SerializerMethodField()
    expanded = serializers.SerializerMethodField()
    model = serializers.SerializerMethodField()
    is_related_to_user = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ('id', 'text', 'leaf', 'checked', 'expanded', 'model', 'is_related_to_user')

    def get_leaf(self, obj):
        return False

    def get_checked(self, obj):
        return False

    def get_expanded(self, obj):
        return False

    def get_model(self, obj):
        return 'Subject'
    
    def get_text(self, obj):
        name = obj.name
        if obj.client:
            name += f' - {obj.client}'
        return name 
    
    def get_is_related_to_user(self, obj):
        from fiscallizeon.questions.models import Question
        from fiscallizeon.inspectors.models import TeacherSubject
        from django.db.models import Q
        
        found_relation = Question.objects.filter(
            Q(created_by=self.context['request'].user),
            Q(
                Q(subject=obj)
                | Q(subject__parent_subject=obj)
                | Q(subject__parent_subject__parent_subject=obj)
                | Q(subject__parent_subject__parent_subject__parent_subject=obj)
                | Q(subject__parent_subject__parent_subject__parent_subject__parent_subject=obj)
            )
        ).exists()
        
        return found_relation


class CommonTreeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)
    leaf = serializers.BooleanField(read_only=True)
    checked = serializers.BooleanField(read_only=True)
    expanded = serializers.BooleanField(read_only=True)
    model = serializers.CharField(read_only=True)
    subject_name = serializers.CharField(read_only=True)

    class Meta:
        fields = (
            'id',
            'text',
            'leaf',
            'checked',
            'expanded',
            'model',
            'subject_name',
        )
