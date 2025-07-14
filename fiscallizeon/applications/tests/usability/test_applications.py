from playwright.sync_api import sync_playwright
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .mixins.applications_setup import ApplicationUsablityMixin
from fiscallizeon.core.utils import CustomTransactionTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class TestUsabilityApplicationManager(StaticLiveServerTestCase, ApplicationUsablityMixin, CustomTransactionTestCase):
    databases = '__all__'
    page = None

    # def test_something(self):
    #     with sync_playwright() as p:
    #         browser = p.chromium.launch()
    #         self.page = browser.new_page()
            
    #         self.login()
            
    #         self.page.goto(self.live_server_url + reverse('exams:exams_list')+'?v=2')

    #         assert "Listagem - Lize" in self.page.title()

    #         browser.close()

    """
    def fields_and_validations_test(self):
        self.page.locator('button[type="submit"]').first.click()
        
        self.page.wait_for_timeout(500)
        
        self.page.keyboard.press('Enter')
        
        self.page.wait_for_timeout(1000)

        # Testa os principais campos comuns a todos os tipos de aplicações
        self.assertTrue(self.page.locator('span', has_text="O instrumento avaliativo é obrigatório.").is_visible())
        self.assertTrue(self.page.locator('span', has_text="Você deve selecionar pelo menos um aluno ou turma.").is_visible())

        def commom_fields():
            self.assertTrue(self.page.locator('#id_date:required').is_visible())
            self.assertTrue(self.page.locator('#id_student_stats_permission_date:required').is_visible())
            self.assertTrue(self.page.locator('#id_start.border-danger').is_visible())
            self.assertTrue(self.page.locator('#id_end.border-danger').is_visible())
            self.assertTrue(self.page.locator('#id_release_result_at_end').is_visible())
            self.assertTrue(self.page.locator('#id_show_result_only_for_started_application').is_visible())
            self.assertTrue(self.page.locator('#id_deadline_for_correction_of_responses').is_visible())
            self.assertTrue(self.page.locator('#id_deadline_for_sending_response_letters').is_visible())

        # Certifica-se de que os campos comuns estão visiveis
        commom_fields()

        # Campos para category Exam
        self.assertTrue(self.page.locator('#id_block_after_tolerance').is_visible())
        self.assertTrue(self.page.locator('#id_min_time_finish').is_visible())
        self.assertTrue(self.page.locator('#id_max_time_tolerance').is_visible())
        self.assertTrue(self.page.locator('#id_can_be_done_pc').is_visible())
        self.assertTrue(self.page.locator('#id_can_be_done_cell').is_visible())
        self.assertTrue(self.page.locator('#id_can_be_done_tablet').is_visible())
        self.assertTrue(self.page.locator('#id_orientations').is_hidden())

        # Clica em catetory homework
        self.page.locator("#onlineHomeworkCategory").click()

        self.page.wait_for_timeout(500)

        # Certifica-se de que os campos comuns estão visiveis
        commom_fields()
        
        # Verifica se tem algum campo que não deveria aparecer em atividade de casa
        self.assertFalse(self.page.locator('#id_min_time_finish').is_visible())
        self.assertFalse(self.page.locator('#id_max_time_tolerance').is_visible())
        self.assertFalse(self.page.locator('#id_can_be_done_pc').is_visible())
        self.assertFalse(self.page.locator('#id_can_be_done_cell').is_visible())
        self.assertFalse(self.page.locator('#id_can_be_done_tablet').is_visible())

        # Testa aplicações do tipo homework
        self.assertTrue(self.page.locator('#id_date_end:required').is_visible())

        # Testa campos para aplicação presencial

        # Clica em catetory homework
        self.page.locator("#presentialSelectButton").click()
        self.page.wait_for_timeout(500)
        
        # Certifica-se de que os campos comuns estão visiveis
        commom_fields()
        
        # Verifica os campos de aplicações presenciais
        self.assertFalse(self.page.locator('#id_min_time_finish').is_visible())
        self.assertFalse(self.page.locator('#id_max_time_tolerance').is_visible())
        self.assertFalse(self.page.locator('#id_can_be_done_pc').is_visible())
        self.assertFalse(self.page.locator('#id_can_be_done_cell').is_visible())
        self.assertFalse(self.page.locator('#id_can_be_done_tablet').is_visible())

        # Volta para aplicação online
        self.page.wait_for_timeout(500)
        self.page.locator("#onlineSelectButton").click()

    def select_exam(self):
        # Seleciona um caderno
        self.page.wait_for_timeout(300)

        self.page.locator('[data-select-exams]').click()

        self.page.wait_for_timeout(300)

        self.page.locator('#inputSearch').fill(self.exam.name)

        self.page.wait_for_timeout(1500)

        self.page.locator(f'[data-exam-name="{self.exam.name}"]').click()

    def select_unities_and_grade(self):
        # Clica no input de unidades
        self.page.wait_for_timeout(500)
        input_unities = self.page.locator('[data-id="id_unity"]')
        input_unities.click()

        # Procura o botão que seleciona todos e clica nele
        self.page.wait_for_timeout(500)
        self.page.locator('.actions-btn', has_text='Todos').click()

        # Clica no input de séries
        self.page.wait_for_timeout(500)
        input_grades = self.page.locator('[data-id="id_grade"]')
        input_grades.click()

        # Procura o botão da série e clica
        self.page.wait_for_timeout(500)
        self.page.locator('a', has_text=self.grade.__str__()).click()

    def select_classes(self):
        # Clica no botão para selecionar as turmas
        self.page.wait_for_timeout(500)
        self.page.locator('[data-select-classes]').click()
        self.page.wait_for_timeout(500)
        self.page.locator('#inputSearchClasses').fill(self.school_class.name)
        self.page.wait_for_timeout(1500)
        self.page.locator(f'[data-classe-name="{self.school_class.name}"]').click()
        self.page.wait_for_timeout(500)
        self.page.locator(f'[data-classe-name="{self.school_class.name}"]').click()
        self.page.keyboard.press('Escape')

        # Clica para expendir a turma para selecionar alunos
        self.page.wait_for_timeout(500)
        self.page.locator(f'[data-selected-classe="{self.school_class.name}"]').click()
        
        # Pega todos os alunos da turma
        all_students_inputs = self.page.locator('input[data-type="student"]').all()

        # Remove os alunos
        self.page.wait_for_timeout(500)
        for student_input in all_students_inputs:
            student_input.click()
        
        # Adiciona alunos
        self.page.wait_for_timeout(500)
        for student_input in all_students_inputs:
            student_input.click()

        # Remove o ultimo aluno para testar o fluxo de alunos na aplicação
        self.page.wait_for_timeout(500)
        self.page.locator('input[data-type="student"]').last.click()

    def select_students(self):
        # Adiciona aluno avulso
        self.page.wait_for_timeout(500)
        self.page.locator(f'[data-select-students]').click()
        self.page.wait_for_timeout(500)
        self.page.locator('#inputSearchStudents').fill(self.avulse_student.name)
        self.page.wait_for_timeout(1500)
        self.page.locator(f'[data-selected-student="{self.avulse_student.name}"]').click()
        self.page.wait_for_timeout(300)
        self.page.keyboard.press('Escape')

    def test_simple_application_creation(self):
        
        with sync_playwright() as p:

            self.browser = p.chromium.launch(headless=True, timeout=5000)
            
            self.page = self.browser.new_page()
            self.login()

            self.page.goto(self.BASE_URL + reverse('applications:applications_list'))

            self.page.locator('#createSimpleApplication').click()


            # Espera e clica em aplicação online
            self.page.wait_for_selector('#onlineSelectButton', timeout=1000)
            self.page.locator('#onlineSelectButton').click()
            
            self.fields_and_validations_test()

            self.page.locator('#id_date').fill((timezone.now() + timedelta(days=1)).date().strftime('%Y-%m-%d'), timeout=300)
            self.page.locator('#id_student_stats_permission_date').fill((timezone.now() + timedelta(days=2)).date().strftime('%Y-%m-%dT%H:%M'), timeout=300)
            self.page.locator('#id_start').fill('10:00', timeout=300)
            self.page.locator('#id_end').fill('13:00', timeout=300)

            self.select_exam()

            self.select_unities_and_grade()

            self.select_classes()

            self.select_students()

            # Configurações avançadas
            self.assertTrue(self.page.locator('input[name="min_time_finish"]').is_visible())
            self.assertTrue(self.page.locator('input[name="max_time_tolerance"]').is_visible())
            self.assertFalse(self.page.locator('input[name="deadline_to_request_review"]').is_visible())
            self.assertTrue(self.page.locator('input[name="deadline_for_correction_of_responses"]').is_visible())
            self.assertTrue(self.page.locator('input[name="deadline_for_sending_response_letters"]').is_visible())

            self.page.locator('[for="id_block_after_tolerance"]').click()
            
            self.page.locator('input[name="deadline_for_correction_of_responses"]').fill((timezone.now() + timedelta(days=7)).date().strftime('%Y-%m-%d'))
            self.page.wait_for_timeout(300)
            self.page.locator('input[name="deadline_for_sending_response_letters"]').fill((timezone.now() + timedelta(days=7)).date().strftime('%Y-%m-%d'))
            
            # Submit form
            self.page.locator('button[type="submit"]').first.click()
            
            self.application_list()
            self.check_students_count()
    
    def application_list(self):

        # Clica no botão de alterar aplicação na listagem de aplicações
        self.page.locator(f'[data-original-title="Alterar aplicação"]').first.click()

        self.page.wait_for_selector('#onlineSelectButton', timeout=1000)
        
        # Procura por inputs obrigatórios
        self.assertTrue(self.page.locator(f'input.disabled-input').is_visible())
        self.assertFalse(self.page.locator(f'[data-select-classes]').is_visible())
        self.assertFalse(self.page.locator(f'[data-select-students]').is_visible())

        # Seleciona novamente o caderno para ver se o update ta funcionando
        self.select_exam()

        # Altera o inicio e o fim
        self.page.locator('#id_start').fill('11:00', timeout=300)
        self.page.locator('#id_end').fill('15:00', timeout=300)

        # Submit form
        self.page.locator('button[type="submit"]').first.click()

    def check_students_count(self):

        # Clica no botão adicionar ou remover alunos
        self.page.locator(f'[data-original-title="Adiciona ou remove alunos desta aplicação"]').first.click()
        
        # Encontra o texto do card "Alunos registrados"
        card_students_count = self.page.locator(".card", has_text="Alunos registrados")
        self.assertEqual(int(card_students_count.locator('div>h3').text_content()), self.students_count)

        # Encontra o texto do card de "Turmas selecionadas"
        card_classes_count = self.page.locator(".card", has_text="Turmas Selecionadas")
        self.assertEqual(int(card_classes_count.locator('div>h3').text_content()), 1)

        self.browser.close()
    
    """