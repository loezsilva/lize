from django.core.management.base import BaseCommand
from fiscallizeon.accounts.models import User, CustomGroup
from django.contrib.auth.models import Permission
from django.db.models import Q

import logging
logger = logging.getLogger()

class Command(BaseCommand):
    help = 'Cria os grupos de permissões'

    def add_arguments(self, parser):
        pass
    
    def handle(self, *args, **kwargs):
        
        coordination_group, created = CustomGroup.objects.update_or_create(name='COORDENADORES', segment='coordination', client__isnull=True, defaults={ "default": True })
        coordination_group.permissions.clear()

        teacher_group, created = CustomGroup.objects.update_or_create(name='PROFESSORES', segment='teacher', client__isnull=True, defaults={ "default": True })
        teacher_group.permissions.clear()
        
        coordination_permissions = [
            "accounts.view_administration_dashboard",
            "accounts.view_followup_dashboard",
            "accounts.view_grade_map_dashboard",
            "accounts.view_tri_dashboard",            
            "applications.add_application",
            "applications.can_access_print_list",
            "applications.can_add_and_remove_students",
            "applications.can_disclose_application",
            "applications.can_duplicate_application",
            "applications.can_print_bag_application",
            "applications.can_remove_generated_bag",
            "applications.change_application",
            "applications.delete_application",
            "applications.view_application",
            "bncc.add_abiliity",
            "bncc.change_abiliity",
            "bncc.delete_abiliity",
            "bncc.view_abiliity",
            "bncc.add_competence",
            "bncc.change_competence",
            "bncc.delete_competence",
            "bncc.view_competence",
            "classes.add_course",
            "classes.change_course",
            "classes.delete_course",
            "classes.view_course",
            "classes.add_coursetype",
            "classes.change_coursetype",
            "classes.delete_coursetype",
            "classes.view_coursetype",
            "classes.add_schoolclass",
            "classes.change_schoolclass",
            "classes.delete_schoolclass",
            "classes.view_schoolclass",
            "classes.add_stage",
            "classes.change_stage",
            "classes.delete_stage",
            "classes.view_stage",            
            "clients.can_export_coodinator",
            "clients.change_clientquestionsconfiguration",
            "clients.change_clientteacherobligationconfiguration",
            "clients.change_confignotification",
            "clients.add_coordinationmember",
            "clients.change_coordinationmember",
            "clients.delete_coordinationmember",
            "clients.view_coordinationmember",
            "clients.add_educationsystem",
            "clients.change_educationsystem",
            "clients.delete_educationsystem",
            "clients.view_educationsystem",
            "clients.add_examprintconfig",
            "clients.change_examprintconfig",
            "clients.delete_examprintconfig",
            "clients.view_examprintconfig",
            "clients.add_partner",
            "clients.change_partner",
            "clients.delete_partner",
            "clients.view_partner",
            "clients.add_questiontag",
            "clients.change_questiontag",
            "clients.delete_questiontag",
            "clients.view_questiontag",
            "clients.add_teachingstage",
            "clients.change_teachingstage",
            "clients.delete_teachingstage",
            "clients.view_teachingstage",
            "distribution.add_room",
            "distribution.change_room",
            "distribution.delete_room",
            "distribution.view_room",
            "exams.add_exam",
            "exams.add_template_exam",
            "exams.can_change_status_exam",
            "exams.can_correct_answers_exam",
            "exams.can_diagram_exam",
            "exams.can_duplicate_exam",
            "exams.can_print_exam",
            "exams.can_review_questions_exam",
            "exams.can_view_result_exam",
            "exams.change_exam",
            "exams.change_template_exam",
            "exams.delete_exam",
            "exams.delete_template_exam",
            "exams.export_template_exam_results",
            "exams.can_duplicate_template_exam",
            "exams.print_template_exam",
            "exams.view_exam",
            "exams.view_template_exam",
            "exams.add_examheader",
            "exams.change_examheader",
            "exams.delete_examheader",
            "exams.view_examheader",
            "exams.add_examorientation",
            "exams.change_examorientation",
            "exams.delete_examorientation",
            "exams.view_examorientation",
            "exams.view_wrong",
            "exams.can_import_exams",
            "exams.can_import_examteachersubjects",
            "inspectors.add_inspector",
            "inspectors.add_teacher",
            "inspectors.can_add_exercice_list",
            "inspectors.change_inspector",
            "inspectors.change_teacher",
            "inspectors.delete_inspector",
            "inspectors.delete_teacher",
            "inspectors.view_inspector",
            "inspectors.view_teacher",
            "inspectors.can_reset_password",
            "inspectors.can_export_teacher",
            "integrations.view_integration",
            "materials.add_studymaterial",
            "materials.change_studymaterial",
            "materials.delete_studymaterial",
            "materials.view_studymaterial",
            "omr.add_omrupload",
            "omr.view_omrupload",
            "omr.export_offset_answer_sheet",
            "omr.export_offset_answer_sheet_schoolclass",
            "omrnps.add_npsapplication",
            "omrnps.view_npsapplication",
            "omrnps.add_omrnpsupload",
            "omrnps.view_omrnpsupload",
            "omrnps.export_answer_sheet",
            "questions.add_question",
            "questions.can_duplicate_question",
            "questions.change_question",
            "questions.delete_question",
            "questions.view_question",
            "students.add_student",
            "students.change_student",
            "students.view_student",
            "students.delete_student",
            "students.can_import_student",
            "students.can_reset_password",
            "students.can_active_student",
            'students.can_export_student',
            "subjects.add_subject",
            "subjects.change_subject",
            "subjects.delete_subject",
            "subjects.view_subject",
            "subjects.add_subjectrelation",
            "subjects.change_subjectrelation",
            "subjects.delete_subjectrelation",
            "subjects.view_subjectrelation",
            "subjects.add_topic",
            "subjects.change_topic",
            "subjects.delete_topic",
            "subjects.view_topic",
        ]

        teacher_permissions = [
            'applications.add_application',
            'applications.can_access_print_list',
            'applications.can_add_and_remove_students',
            'applications.can_disclose_application',
            'applications.can_duplicate_application',
            'applications.can_print_bag_application',
            'applications.can_remove_generated_bag',
            'applications.change_application',
            'applications.delete_application',
            'applications.view_application',
            'exams.add_exam',
            'exams.can_change_status_exam',
            'exams.can_correct_answers_exam',
            'exams.can_diagram_exam',
            'exams.can_duplicate_exam',
            'exams.can_print_exam',
            'exams.can_review_questions_exam',
            'exams.can_view_result_exam',
            'exams.change_exam',
            'exams.delete_exam',
            'exams.view_exam',
            'inspectors.can_add_exercice_list',
            'questions.add_question',
            'questions.can_duplicate_question',
            'questions.change_question',
            'questions.delete_question',
            'questions.view_question',
        ]

        for perm in coordination_permissions:
            try:
                permission = Permission.objects.get(content_type__app_label=perm.split('.')[0], codename=perm.split('.')[1])
                coordination_group.permissions.add(permission)
            except:
                pass
        for perm in teacher_permissions:
            try:
                permission = Permission.objects.get(content_type__app_label=perm.split('.')[0], codename=perm.split('.')[1])
                teacher_group.permissions.add(permission)
            except:
                pass
        
        # Coordenadores
        users_coordination = User.objects.filter(
            Q(
                coordination_member__isnull=False,
                student__isnull=True,
            ),
            Q(
                Q(custom_groups__isnull=True),
                Q(user_permissions__isnull=True)
            )
        ).distinct()

        # Inspectores
        users_teachers = User.objects.filter(
            inspector__isnull=False, coordination_member__isnull=True
        ).exclude(pk__in=users_coordination).distinct()
        
        for user in users_coordination:
            if user.user_type == 'coordination':
                user.custom_groups.set([coordination_group])
                
        for user in users_teachers:
            if user.user_type == 'teacher':
                user.custom_groups.set([teacher_group])