from rest_framework import serializers
from fiscallizeon.accounts.models import User, CustomGroup
from fiscallizeon.clients.models import CoordinationMember
from fiscallizeon.clients.serializers2.school_coordination import SchoolCoordinationSerializer

class CoordinationMemberUserSerializer(serializers.ModelSerializer):
    class CoordinationMemberSerializer(serializers.ModelSerializer):        
        class Meta:
            model = CoordinationMember
            fields = ['id', 'coordination', 'is_coordinator', 'is_reviewer', 'is_pedagogic_reviewer']
    
    coordination_member = CoordinationMemberSerializer(many=True)
    permission_groups = serializers.PrimaryKeyRelatedField(many=True, queryset=CustomGroup.objects.all(), source='custom_groups', required=False)

    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'coordination_member', 'permission_groups']
    

class CoordinationMemberSerializer(serializers.ModelSerializer):
    coordination = SchoolCoordinationSerializer()
    user = CoordinationMemberUserSerializer()
    id = serializers.UUIDField(source='user.id')
    
    class Meta:
        model = CoordinationMember
        fields = ['id', 'coordination', 'user', 'is_coordinator', 'is_reviewer', 'is_pedagogic_reviewer']
    
class CoordinationMemberUserCreateSerializer(serializers.ModelSerializer):
    
    class CoordinationMemberCreateSerializer(serializers.ModelSerializer):        
        class Meta:
            model = CoordinationMember
            fields = ['coordination', 'is_coordinator', 'is_reviewer', 'is_pedagogic_reviewer']
    
    coordination_member = CoordinationMemberCreateSerializer(many=True)
    permission_groups = serializers.PrimaryKeyRelatedField(many=True, queryset=CustomGroup.objects.all(), source='custom_groups', required=False)
    
    class Meta:
        model = User
        fields = ['name', 'email', 'coordination_member', 'permission_groups']