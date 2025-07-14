import logging
import os

from mixer.backend.django import mixer

from django import test

from fiscallizeon.omr.models import OMRUpload
from fiscallizeon.omr.tasks.finish_processing import finish_processing
from fiscallizeon.core.utils import CustomTransactionTestCase

class TestOMRPrinting(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.omr_upload = mixer.blend(OMRUpload)
        os.makedirs(os.path.join('tmp', str(self.omr_upload.pk)), exist_ok=True)

    def test_finish_processing(self):
        omr_upload_id = self.omr_upload.id
        finish_processing(omr_upload_id)
        omr_upload = OMRUpload.objects.get(pk=omr_upload_id)
        self.assertEqual(omr_upload.status, OMRUpload.FINISHED)

    def tearDown(self):
        logging.disable(logging.NOTSET)