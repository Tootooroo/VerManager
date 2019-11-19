from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string
from selenium import webdriver

from manager.views import index, verRegPage

import unittest

# Create your tests here.

class FunctionalTest(TestCase):

    def setUp(self):
        self.browser = webdriver.Firefox()

    def tearDown(self):
        self.browser.quit()

#    def test_title_check(self):
#        self.browser.get('http://localhost:8000/manager')
#        self.assertEqual('GPON Team Site', self.browser.title)
#        self.fail('Test finish')

class UnitTest(TestCase):
    def test_index_page(self):
        response = self.client.get('/manager/')
        self.assertTemplateUsed(response, 'index.html')

    def test_verRegister_page(self):
        response = self.client.get('/manager/verRegister')
        self.assertTemplateUsed(response, 'verRegister.html')

    def test_register_feature(self):
        response = self.client.post('/manager/verRegister/register',
                                    data = { 'Version' : 'V1', 'verChoice' : 'XXXX' })
        self.assertTemplateUsed(response, 'register.html')
        self.assertIn("Failed to register Version V1 with revision XXXX",
                      response.content.decode())

if __name__ == '__main__':
    unittest.main(warnings='ignore')
