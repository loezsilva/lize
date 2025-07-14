open_endpoints = [
  '/api/v2/classes/',
  '/api/v2/classes/{pk}/',
  '/api/v2/series/',

  '/api/v2/coordinations/',
  '/api/v2/coordinations/members/',
  '/api/v2/coordinations/members/add/',
  '/api/v2/coordinations/members/user/{pk}/disable/',
  '/api/v2/coordinations/members/{pk}/remove/',
  '/api/v2/units/',

  '/api/v2/students/',
  '/api/v2/students/{pk}/',
  '/api/v2/students/{pk}/disable/',
  '/api/v2/students/{pk}/enable/',
  '/api/v2/students/{pk}/set_classes/',

  '/api/v2/subjects/',

  '/api/v2/teachers/',
  '/api/v2/teachers/{pk}/',
  '/api/v2/teachers/{pk}/add_subjects/',
  '/api/v2/teachers/{pk}/remove_subjects/',

  '/api/v2/abilities/',
  '/api/v2/competences/',
  '/api/v2/topics/',
  '/api/v2/base-texts/',
  '/api/v2/questions/',

  '/api/v2/exams/',
  '/api/v2/exam-questions/',

  '/api/v2/applications/',
  '/api/v2/exam-teachers-subjects/',

  '/api/v2/application-students-answers/',
  '/api/v2/application-students-results/',

  '/api/v2/sso/generate_accesss_token/',
  
  '/api/v2/permissions/all_groups/',
]

def preprocessing_filter_spec(endpoints):
    filtered = []
    for (path, path_regex, method, callback) in endpoints:
        if path in open_endpoints:
            filtered.append((path, path_regex, method, callback))
    return filtered
