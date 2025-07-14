from fiscallizeon.core.utils import CustomTransactionTestCase
from fiscallizeon.exams.models import Exam
from fiscallizeon.exams.tests.mixins import CreateExamTestMixin
from playwright.sync_api import sync_playwright, expect
from django.urls import reverse, reverse_lazy
from datetime import datetime
from mixer.backend.django import mixer
import csv

class TestDuplicateName(CreateExamTestMixin, CustomTransactionTestCase):
    databases = '__all__'
    page = None

    """
    def test_duplicate_name_create_exam(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True, timeout=3000)
            self.context = self.browser.new_context()
            self.page = self.browser.new_page()

            self.page.goto(self.BASE_URL)
        
            
            self.login()
            base_url = self.BASE_URL
            full_url = base_url + "/provas/cadastrar"
            self.page.goto(full_url)

            close_button_selector = '#tg-dialog-close-btn'
            self.page.locator(close_button_selector).click(force=True)

            

            name_selector = "input[name='name']"
            self.page.locator(name_selector).fill(self.nome_exam)

            self.page.locator("text='Anos Iniciais'").click()
            current_date = datetime.now().strftime('%Y-%m-%d')
            self.page.locator("input[name='elaboration_deadline']").fill(current_date)
            self.page.locator("input[name='release_elaboration_teacher']").fill(current_date)
            self.page.click("button[type='submit'][form='form-exam-create-update']")

            error_modal = self.page.locator('div.swal2-popup.swal2-icon-error')
            # deve aparecer erro
            expect(error_modal).to_be_visible()

            error_message = self.page.locator('div.swal2-html-container')
            expect(error_message).to_have_text(f"Já existe um caderno com o nome '{self.nome_exam}'")
    def test_duplicate_name_edit_exam(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True, timeout=3000)
            self.context = self.browser.new_context()
            self.page = self.browser.new_page()

            self.page.goto(self.BASE_URL)
        
            
            self.login()
            base_url = self.BASE_URL
            full_url = base_url + f"/provas/{self.exam_id}/editar"
            self.page.goto(full_url)

            close_button_selector = '#tg-dialog-close-btn'
            self.page.locator(close_button_selector).click(force=True)

            

            name_selector = "input[name='name']"
            self.page.locator(name_selector).fill(self.nome_exam_2)

            self.page.locator("text='Anos Iniciais'").click()
            current_date = datetime.now().strftime('%Y-%m-%d')
            self.page.locator("input[name='elaboration_deadline']").fill(current_date)
            self.page.locator("input[name='release_elaboration_teacher']").fill(current_date)
            self.page.click("button[type='submit'][form='form-exam-create-update']")
            self.page.wait_for_timeout(2000)

            error_modal = self.page.locator('div.swal2-popup.swal2-icon-error')
            # deve aparecer erro
            expect(error_modal).to_be_visible()

            error_message = self.page.locator('div.swal2-html-container')
            expect(error_message).to_have_text(f"Já existe um caderno com o nome '{self.nome_exam_2}'")

    def test_duplicate_name_import_exam(self):
        path_csv = 'tmp/tests/modelo_importacao_cadernos.csv'
        with open(path_csv, mode='r') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
        for row in rows:
            row['Título da avaliação'] = self.nome_exam
            row['Unidade e Coordenação'] = self.unity.name + "-" + self.coordination.name
        with open(path_csv, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True, timeout=3000)
            self.context = self.browser.new_context()
            self.page = self.browser.new_page()

            self.page.goto(self.BASE_URL)

            self.login()
            full_url = self.BASE_URL + "/provas/importar/cadernos"
            
            self.page.goto(full_url)

            self.page.locator("input[id='file']").set_input_files(path_csv)
            self.page.locator("button[type='submit']").click()
    """
