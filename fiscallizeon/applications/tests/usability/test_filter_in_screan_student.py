from mixer.backend.django import mixer

from django import test 
from playwright.sync_api import sync_playwright, expect
from django.urls import reverse, reverse_lazy
from fiscallizeon.applications.tests.usability.mixins.applications_students_setup import ApplicationAndApplicationStudentsMixin
import requests
from playwright.sync_api import expect
from fiscallizeon.core.utils import CustomTransactionTestCase
from datetime import datetime
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

class TestStudentListPage(StaticLiveServerTestCase, ApplicationAndApplicationStudentsMixin, CustomTransactionTestCase):
    databases = '__all__'
    page = None
    
    def test_filter_in_application_student_lit(self):
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True, timeout=3000)
            self.page = self.browser.new_page()

            self.login()

            base_url = self.live_server_url
            path = reverse('applications:application_student_list')
            full_url = f"{base_url}{path}?only_scheduled=true&category=online"
            self.page.goto(full_url)

            button_selector = self.page.locator('button[data-toggle-off-canvas="#right-off-canvas"]')
            button_selector.click()
            self.page.wait_for_timeout(500)

            select_selector = self.page.locator('#subject_id')
            select_selector.wait_for()
            select_selector.select_option(value=str(self.teacher_subject_one.subject.id))

            submit_button_selector = self.page.locator('button[type="submit"]')
            submit_button_selector.wait_for()
            submit_button_selector.click()

            self.page.wait_for_timeout(500)
            
            remove_filters_button = self.page.locator('a', has_text='Apagar filtro(s)').first
            remove_filters_button.wait_for()
            remove_filters_button.click()

            self.page.wait_for_timeout(500)

            button_selector = self.page.locator('button[data-toggle-off-canvas="#right-off-canvas"]')
            button_selector.click()
            
            self.page.wait_for_timeout(500)

            select_selector = self.page.locator('#classe_id')
            select_selector.wait_for()
            select_selector.select_option(value=str(self.school_class.id))

            submit_button_selector = self.page.locator('button[type="submit"]')
            submit_button_selector.wait_for()
            submit_button_selector.click()
            
            self.page.wait_for_timeout(500)
            
            remove_filters_button.click()

            self.page.wait_for_timeout(500)

            button_selector = 'button[data-toggle-off-canvas="#right-off-canvas"]'
            self.page.click(button_selector)
            
            self.page.wait_for_timeout(500)

            date_field_selector = self.page.locator('#end_time_start')
            date_field_selector.wait_for()
            now = datetime.now().strftime('%Y-%m-%d')
            date_field_selector.fill(now)

            submit_button_selector = self.page.locator('button[type="submit"]')
            submit_button_selector.wait_for()
            self.page.wait_for_timeout(500)
            submit_button_selector.click()
            
            self.browser.close()