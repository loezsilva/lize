from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRStudents
from fiscallizeon.omr.tasks.reproccess_sheets import reproccess_sheets

#Prova 1e7fdb2a-8421-4005-b559-42a180504fd4
application_student_ids = [
    "d1923078-d0d0-4d4a-8b51-de4ada44374f",
    "ab65fb61-ca60-4a6c-95d8-53ace79f2289",
    "d8ad6f6a-d866-4630-b170-ea1d61e9ec88",
    "6d7d3ab1-e673-472a-b68b-151f45130d99",
    "b1189764-4cd7-468f-bd4d-2c033638cbdf",
    "0bddcd46-ce21-4676-8e87-2059f428b0a8",
    "a1ee2583-b759-4d56-9f2f-47ba1fc00c9f",
    "46e40995-e088-4a3b-9473-5e525d5aed49",
    "359a8719-94ad-42a8-8032-426f39dfef7b",
    "02530b81-0bce-47b0-ac51-e52ebb591b88",
    "5a6e0901-647e-4e36-8aa5-04ef3d2069f3",
    "9ae653ff-2c2c-43a6-a6e8-3a1577b0b770",
    "024142ee-9a65-4670-8d49-d4ecc3a29c00",
    "df13c378-4352-4c14-8971-089c7ecdef6a",
    "c78345aa-c17b-456e-8956-065dcb27eada",
    "08556f8f-2ff2-451c-adbb-7b66b965d3ac",
    "20573e69-b51f-4e20-af90-77d9ccc8f80e",
    "644964f1-3549-4453-b6ed-cd623ed320cb",
    "318965a9-a9db-4821-ac27-6da3cce68106",
    "162c5007-f540-4d23-9593-1ce41d7250ef",
    "42479b4f-7e61-416e-a277-88cbb0b8766d",
    "e7a9f182-a0c9-4395-a438-8352b9262930",
    "43ef930f-be7d-48c4-8bec-30ec065d2f8b",
    "8c1f92bd-23e0-4e11-99b8-3fbef421df9a",
    "756f013f-b8a4-4070-b0f2-b75e6c539246",
    "7b3c4cb3-8469-42cf-8137-e0ad8a64582e",
    "fce07e84-e1bf-40d3-a9d5-0c3165045e15",
    "4a7e5a08-87a6-427a-a817-0cabea375eaa",
    "9b14bf21-52cc-4ceb-8a43-1564631b99c3",
    "c008e3d3-4548-40f3-92d2-02f0cb89e923",
    "1445a0ce-5933-463b-9c5f-fb7eaf58888b",
    "66e2b0a1-5074-459a-ba4a-27aa82c109b5",
    "ba7a1ce6-1f2e-4716-91b4-c996581c4345",
    "c37f5f4b-ea04-4826-8015-a81dccad7e0a",
    "c6d99256-6612-44e1-a687-d5902d16fe5a",
    "c7b244a0-4122-447b-9b7e-710603fe99d4",
    "5da5dacc-7ea1-4691-8e78-2c1c5f545ef3",
    "ce302a75-e20e-4261-a66b-8151e1771c48",
    "e55f3570-4916-4076-9d4d-7f38a59b09a4",
    "5d5bb94d-fc61-427e-9cae-eff63f6c7fed",
    "d35a9f99-10c1-410e-b262-fc85f4371819",
    "34a21663-0faf-466f-8f6d-e3fd56b29051",
    "cf346c31-92bb-4a03-9479-0ca00f2769de",
    "f1e18830-c26c-44b8-8f7d-57af79befd89",
    "b90c717c-5710-44c7-9387-5d33417a0e3f",
    "d1b55064-751c-40b1-a748-6bcb7e9eef00",
    "7ab67649-0e7a-4f1d-a771-46f4577c495a",
    "93d1c842-e36f-4d4b-8083-ae80a6031f19",
    "f2dad8ef-db02-4664-9c83-b96c1073357b",
    "db3927e3-2669-4d03-908b-7d4e95a458d5",
    "ba93d82d-e111-4369-8ed1-5be39be971d8",
    "b5336891-220d-479f-a25f-75c246f50ee4",
    "046060bf-1583-48ff-847a-ad5b26df5bc3",
    "0a9397e8-6b16-424e-a2ff-8427faa43fd3",
    "239e797d-838f-499b-ac55-206f196fa54b",
    "007fec6e-863d-40a6-a11e-83ebca27bc52",
    "2d86849d-f32c-45c2-ba11-93fb47ffc9f7",
    "e6d8e8df-dc6c-483d-bf0a-8309177f5a89",
    "445d8ef4-4b51-479b-9c71-69a892aefce6",
    "17011117-ba24-4505-bc9f-3ebf0719a27c",
    "600b83f3-8197-427a-9a0d-97ee8e776d29",
    "6196356d-5bb2-489d-94f8-53a3ec9a8481",
]

application_students = ApplicationStudent.objects.filter(
    pk__in=application_student_ids,
)

omr_upload = OMRUpload.objects.create(
    user=User.objects.get(pk='8ee42940-609f-4465-a298-0a4d87dd96a9'),
    status=OMRUpload.FINISHED,
    error_pages_count=application_students.count(),
)

omr_error_list = []
for application_student in application_students:
    omr_error = OMRError.objects.create(
        upload=omr_upload,
        error_image=OMRStudents.objects.filter(application_student=application_student, scan_image__isnull=False).last().scan_image,
        category=OMRError.MISSING_RANDOMIZATION_VERSION
    )
    read_params = {
        "omr_error": str(omr_error.pk),
        "application": application_student.application.pk,
        "student": application_student.student.pk,
        "omr_category": OMRUpload.APPLICATION_STUDENT,
        "randomization_version": 2,
    }
    omr_error_list.append(read_params)

reproccess_sheets.apply_async(args=(omr_upload.pk, omr_error_list))
