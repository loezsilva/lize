import os
import io
import uuid
import shutil
import requests

from PyPDF2 import PdfReader, PdfFileWriter
from pikepdf import Pdf

from django.conf import settings

from fiscallizeon.core.retry import retry
from fiscallizeon.core.requests_utils import get_session_retry

def resize_pdf(pdf_path, resize_factor):
    writer = PdfFileWriter()
    read_pdf = PdfReader(pdf_path)
    for page in read_pdf.pages:
        page.scaleBy(resize_factor)
        writer.addPage(page)

    with open(pdf_path, 'wb') as output:
        writer.write(output)

def merge_pdfs(pdf_paths, output_dir=None):
    output_dir = output_dir or '/tmp'
    tmp_filename = f'{output_dir}/{uuid.uuid4()}.pdf'

    pdf = Pdf.new()

    with open(tmp_filename, 'wb') as output:
        for path in pdf_paths:
            src = Pdf.open(path)
            pdf.pages.extend(src.pages)
        pdf.save(tmp_filename)
    return tmp_filename

def merge_memory_pdfs(file_1, file_2=None):
    if not file_2:
        return file_1

    pdf1 = Pdf.open(file_1)
    pdf2 = Pdf.open(file_2)
    merged_pdf = Pdf.new()

    for page in pdf1.pages:
        merged_pdf.pages.append(page)
    for page in pdf2.pages:
        merged_pdf.pages.append(page)

    file = io.BytesIO()
    merged_pdf.save(file)

    return file

def merge_urls_legacy(urls, temp_path):
    """
    DEPRECATED
    """
    tmp_files = []
    for index, url in enumerate(urls):
        tmp_file = os.path.join(temp_path, str(index))
        tmp_files.append(tmp_file)
        with requests.get(url, stream=True) as r:
            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

    return merge_pdfs(tmp_files, temp_path)

def get_file(url, temp_path):
    
    tmp_file = os.path.join(temp_path, str(uuid.uuid4()))
    
    session = get_session_retry()
    
    with session.get(url, stream=True, timeout=300) as r:
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return tmp_file

@retry(tries=6)
def merge_urls(urls, temp_path):
    url = settings.LOCAL_PRINTING_SERVICE_BASE_URL + settings.MERGING_SERVICE_PATH

    params = {
        'output_name': f'{uuid.uuid4()}.pdf',
        'urls': [x for x in urls if x],
    }

    tmp_file = os.path.join(temp_path, str(uuid.uuid4()))

    session = get_session_retry()
    timeout = 30 if settings.DEBUG else 300
    with session.post(url, json=params, stream=True, timeout=timeout) as r:
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return tmp_file