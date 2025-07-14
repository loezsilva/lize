import requests
import os
import shutil
import zipfile

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.omr.models import OMRUpload

from fiscallizeon.applications.models import Application
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.omr.tasks.group_answer_sheet_files import safe_string

class Command(BaseCommand):
    help = 'Agrupa zips de malotes discursivos (solução temporária)'

    APPLICATION_PKS = [
        'c5cbf86c-4d49-4773-8466-7042bba7e795',
        '54bd5cd5-ae56-4658-a24e-cf17e84485d7',
        'f3d8b38a-49d2-443e-962b-b3bd9c70cf11',
        'ff9eedd7-6a16-42d8-8c57-70d38c552012',
        'ad24d59b-dd17-4127-a552-58c504c78e0a',
        '97df27ce-9e7c-4d2b-8585-f9fd256cec59',
        'b081679d-23a6-40b5-b118-bd182df63037',
        '4e6cf9c0-1150-4ef1-b490-f039ecda6d6b',
        'add24b4e-f62f-4c2f-8b56-dbf55f3c1d77',
        'b1429ce5-4bf3-42a8-b2ad-d06f09e34afb',
        'd7a4c07f-ad19-4833-9a85-4406794c10d2',
        'd6558bdd-4858-4f62-8239-942c62ed6177',
        '2ba4fcc6-84f6-4dda-8c68-ea8d15f204e6',
        'f503a395-2134-4971-bcef-45ed9e1e4bb1',
        'a53b6856-ec99-436c-a831-23f4464d856c',
        '8d7aca43-adb8-487a-8542-9c07571f9ca9',
        '60a37314-7b3c-45b5-92c7-676a4268b1ac',
        'ed3b1626-d583-4253-8b17-22e4b20e882f',
        'a36795cd-79f3-49ee-b2de-24f1e94fc24d',
        '90236139-286c-4d04-98ee-b9612836448f',
        'aa4471ae-d586-44a9-ad3e-a86385ac31bd',
        '12c25618-7bc9-460e-b506-aaeb79af36e8',
        '966019cf-2f25-4a26-873e-e86456dac420',
        '7907d484-9229-4a79-8fe9-3b4e1cc8c170',
        '147fa572-7f11-4763-8745-5ff1e491da34',
        'd01af458-473b-4a9c-94a4-7cbf5269b202',
        '86ef6d6c-b21b-4bb6-b5d7-8eda392228ce',
        '869f4adf-a1c2-4ec9-80c9-1716c33c5d43',
        'cf0d1548-be41-4082-8992-4c97f6ea09cf',
        '8997e66d-e8cb-431e-aa37-482b9eef2ff0',
        'cda9772d-8e0e-4e8a-9261-88f76180706a',
        'f3ec6947-5321-4238-bec2-335f80916ddb',
        '4b5d0843-5bc2-47db-b17a-5f8dc056f461',
        'c3922446-e4ae-4c40-bc43-18bd70a047e7',
        'dd6e0e6f-a5f8-4da2-991c-fd1efe883883',
        '66bd2bbd-500e-4c22-a262-3c4bc3ab600c',
        '039a6404-ed0e-40fe-b35a-0e7152e8cba5',
        '7c9c3ec3-2ea6-4475-88b6-c94364bfbea5',
        'cae41ebb-94f2-4e60-bc9c-ee7da5ba9335',
        '16c998fc-fc9c-44ea-b7c2-7f2a6c82af26',
        'f1139281-4364-4d61-baae-5e85ddf5b334',
        '3f1531e3-8f19-4905-9c23-2c888927b67f',
        'c1f9a17b-05bc-4ef2-b5e7-f02b1c83f56f',
        '8b44531f-d33a-40d1-b792-1e1ad2a97768',
        '524ab219-7286-4ee6-a211-7905b195a90b',
        'ba0aa77a-c287-4cf1-b680-14f0c5f1ee67',
        '61d75576-0eb4-4684-93fd-b3a83c480acd',
        'cd6efece-d84b-4b97-b03e-63e1cd0092fb',
        '8c71ce70-1f4c-4745-a5bd-da9e2d287b77',
        '62bb9bfd-546f-4f78-9d44-5495dfdb1da0',
        '30bd4d29-8ce8-4ec2-bc80-0a109a4a3207',
        'afacc104-b458-41af-a15d-affd18052153',
        'acd3f702-a916-4ab1-92a9-99973893216a',
        '5fae75b6-9e20-45e1-8c02-5af29403b6c3',
        '08571044-42ee-4a89-8645-10ddedea6c30',
        '2513c365-059f-4541-b173-dd6cf2f93ba2',
        '1504d3b9-6dd6-4c1a-90cf-4b1bbf3d9d9e',
        '4010e864-84da-4170-b02f-c904cdcbb466',
        '86687f13-6452-4ff9-a94e-d74ab4fd3063',
        'bf4a682a-8710-4545-bb4a-6030b3d95e88',
        '7046a142-2bde-4dd8-aee5-4d43c2e41800',
        '084a436c-604b-4ffc-87ab-1c43f541c2f6',
        '8cbecd4c-8571-43bc-bf18-baa1cf4a0395',
        'b4c1b252-2847-43f2-a455-c0cbb7a044a1',
        'bf1f786f-be3a-4d82-9184-91362291a482',
        '51315bfe-da00-49e8-87bd-5b6f3c65bb40',
        'e5a6e28c-61ff-4968-8bb0-87eff24538d3',
        '42344f3d-5628-41d2-a641-669200b7e009',
        'e004f88b-2795-4b5e-953d-31344651ede5',
        'd042540a-2577-45a4-aca2-ecac86d67821',
        'fcbc9915-92bb-489c-8475-c41e7cdb381a',
        'd347fe2b-ea7b-46be-bb3c-b49f299bbeca',
        'd23dca6e-f101-4132-b826-dd214881b614',
        '92740383-4324-44a5-b9b2-4c672bd54277',
        'a0b5d5b1-aca3-401c-a096-4eb5516f1a4b',
        'bb1faf7d-0b42-4563-b02a-c09e1b621a75',
        '269bdf92-e086-4a01-bc5b-aa00489b3740',
        '96a0162e-d077-469e-8d38-4a590d5157ae',
        '27ffa5ce-5666-4d90-9707-58cd9356b2de',
        '8c50e270-3a82-42fb-9115-bc5c057d377b',
        '15e18f52-a102-451d-a5f4-8359f61f82f2',
        '259041ce-3d06-471a-af27-ba7adf6be16d',
        '2c35b32c-2842-40b4-b7b2-181800f654cc',
        '98af8f55-e71c-4887-b15f-32791ac7c727',
        'ad470e41-71d9-416e-8eb6-6adae3594dba',
        '06358b1f-e950-445c-8332-eadc442ca8ab',
        '3fc149ab-8deb-4c98-bda1-439a158231da',
        '09e4302a-9da5-4b38-93b0-b196e26cb1fa',
        '6adb2b62-069a-4a0b-abbc-7d409ff29d5e',
        '651eb96e-dc98-4c20-8a89-65cd2bf1adf1',
        '0eaf936e-bf39-455e-ab04-e7952f2bc945',
        '7f331972-36fc-4306-972e-d20c8ae29490',
        '302ea34a-89eb-4353-9432-91d91588ffe2',
        '44d64d17-569f-4106-800f-292ef66bf546',
        '04cd1fe2-4423-4ff4-8d78-d599398ce36e',
        '140abb2f-5f09-4c65-b643-9c10a24de4ba',
        '69f399a1-4395-4a49-a973-9072e3f9d887',
        '2be00c91-fe1b-478d-b570-8c06a99c9de5',
        'fc6a6ad4-da1d-46f9-86b3-418cc15f160d',
        'd0a608fd-3c69-4bb9-b19f-2ca3dc309895',
        '26a6dd1b-84aa-4260-b23b-ebdf54f56064',
        '9c33fa5a-cc84-4a85-b525-4c46f138d7aa',
        'bc97eea5-adb3-4f75-86c8-26b11e8fd956',
        '61f8d7e2-1a12-4972-b723-b45e901d2561',
        '90cc6fcf-a63a-4baf-966a-193d85c4b168',
        'ba331e93-a55c-40fe-8e79-cf419f363735',
        '5767ae97-d9fd-445f-b4f9-80c5eeca3e66',
        'a140a1b2-dd9f-4fc1-9b37-805f4684b9a9',
        'afca0d78-c44f-4edc-806d-1e39c0f5b33e',
        '845c390d-b573-42ee-9276-495d85fddd34',
        '0e7fcd42-173b-4d2d-b2e0-bdd18b649fba',
        'f1440769-71f0-4cc9-b550-3c8906a7131f',
        '7beb5378-0887-4eb9-9b0c-3fc98f7f3a49',
        '02f7f0b1-3c28-4afd-b6fb-d37385c1dc7a',
        '4fc5de46-2d20-49a3-a8e4-33c376be101d',
        'd5493fe1-df50-45bb-9c9f-3f11367abd61',
        '54c00b92-a0a0-4150-9747-9a91364e1ee2',
        '7f16efc5-ce60-446d-8f0b-d291ff34b10c',
        '74ebbe9e-ea9b-49d8-8c92-e6696c5e954e',
        'a7ab17da-37e9-4198-a061-71ddb89101fe',
        '35b29c06-4c17-448e-acbc-be8ddf429f45',
        '627ac33e-e0b6-42a7-9b82-702613396235',
        'd80cc37d-a9ea-45cc-97c2-aca29b8e65a0',
        '200e6438-a740-45ab-b6e2-ce006407472e',
        '4d40536b-3c5c-4c33-bfd0-34a2ac9eb9a8',
        '209d06d6-7ad8-4cc0-8aa3-0441c4934113',
        'dfd2959f-9c8a-4d75-b641-30f67cb37035',
        '94e7cae6-ceb5-4875-a8d4-561d9db02ae6',
        '896aef0f-da49-4bfc-ac71-e714df92ef70',
        'fff6326b-308d-4d01-ba5c-5f4c1cd62f1c',
        'f631a65b-44de-4b68-9d6d-7b61630adffb',
        '7172ad75-b1d4-41b9-ad85-772ca1d1ebe9',
        '80c25cd4-9d6b-4705-a89f-0a1674812ea6',
        '4a9b523f-963b-4cd8-94ee-c5a3da035fa7',
        'b09b8032-7496-4030-bb7b-62e54705b73f',
        'fa08b154-1846-4589-b209-2b0f95571fc1',
        '43b1ab29-ecd0-4bb5-82d5-aa3fb28e521c',
        '52aae13a-e918-49e0-a69d-8aca7bea4a5b',
        'db3b9ece-cb23-4c6a-aba3-4cec56f30967',
        'e510dcc2-1b4e-452e-9e4e-f7d3d375ed9c',
        'afc3cc47-5b93-4b27-9527-d11752c7a202',
        'c3153b28-d1ca-43eb-96da-f574013db3eb',
        'e6adb38b-e06f-49ce-b786-e83296a1a661',
        '38e7c33e-e28f-4f58-aa13-9434b25769e1',
        'e3217bf4-1cf4-4add-99d1-c922459d824a',
        '448fc15a-fdef-44bf-b7e8-0a3f36f0ed8e',
        'a4188aac-f880-47f4-93a8-4aec8377392b',
        'daefb1ed-91dc-4d1e-802a-91d32caaedbd',
        'a8d050a4-0c8b-4025-8a78-c8b40ccd1eed',
        '44b2a40e-d700-4edd-9ec9-de61cef7dfb2',
        '59a93fe1-1338-4a7f-b553-b332cafa4935',
        '339187b7-2704-4e8d-879c-13e939576090',
        '3d29562c-f0d5-4eba-8039-0dad74178048',
        '547798e6-b83f-4da7-bc6d-19b13660330c',
        '5692f24e-0531-4509-b06b-784b2f9f447d',
        '5fb48d09-c5f3-4be7-94dc-96c581a4fde3',
        '2853e83c-34ca-4099-837c-b7a07fa1a523',
        'c9e3624f-ae6d-40e1-aa79-77f6a44af5e3',
        'ba220dd6-53d0-4758-9d92-3bf97f78641d',
        '8aad8fdf-0555-49b5-a595-055d10b141f9',
        '9f223d32-92e2-4673-b62c-395b23d97a27',
    ]

    def add_arguments(self, parser):
        parser.add_argument('export_version', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        export_version = kwargs['export_version'][0] or 90

        fs = PrivateMediaStorage()
        file_paths = []
        os.makedirs('/code/tmp/discursivas_decisao', exist_ok=True)

        for application_pk in self.APPLICATION_PKS:
            application = Application.objects.get(pk=application_pk)
            exam_name = safe_string(application.exam.name)[:64]
            remote_path = f"applications/answer_sheets/{application_pk}/discursivas_{export_version}.zip"
            tmp_file = f'/code/tmp/discursivas_decisao/{exam_name}.zip'
            file_paths.append(tmp_file)
            with requests.get(fs.url(remote_path), stream=True, timeout=300) as r:
                with open(tmp_file, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

        final_zip_name = '/code/tmp/decisao_discursivas.zip'
        with zipfile.ZipFile(final_zip_name, 'w') as zipf:
            for file in file_paths:
                zipf.write(file, os.path.basename(file))

        remote_file = fs.save(
            'decisao_tmp/decisao_discursivas_p2.zip',
            open(final_zip_name, 'rb')
        )

        print(f"Processo finalizado: {remote_file}")