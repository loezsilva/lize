from django.db.models import Count, Q, F

class ExamTeacherSubjectMixin(object):
    
    def get_exams(self, to_review=False):
        user = self.request.user
        teacher = user.inspector
        
        if to_review:
            return teacher.get_exams_to_review(return_exam_teacher_subjects=True).annotate(
                count=Count('examquestion', distinct=True),
                count_reviewed_questions=Count('examquestion', filter=Q(examquestion__statusquestion__user=self.request.user), distinct=True)
            ).filter(count__gt=0).exclude(count_reviewed_questions=F('count'))
            
        return teacher.get_opened_exams(with_details=True)