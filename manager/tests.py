from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string
from selenium import webdriver

from manager.views import index, verRegPage

from manager.misc.verControl import RevSync

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

class HttpRequest_:
    def __init__(self):
        self.headers = {}
        self.body = ""

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
        self.assertTrue(response.status_code == 200)

    def test_new_rev(self):
        revSyncner = RevSync()

        revSyncner.revDBInit()
        revSyncner.start()

        request = HttpRequest_()
        request.headers = {'Content-Type':'application/json', 'X-Gitlab-Event':'Merge Request Hook'}

        request.body = '{ "object_attributes": {\
                            "state": "merged",\
                            "last_commit": {\
                              "id": "12345678",\
                              "message": "message",\
                              "timestamp": "2019-05-09T01:39:08Z",\
                              "author": {\
                                "name": "root"\
                              }\
                            }\
                           }\
                         }'

        import json

        from manager.views import newRev
        newRev(request)

        from manager.models import Revisions

        import time
        time.sleep(2)

        try:
            rev = Revisions.objects.get(pk='12345678')

            self.assertEqual("12345678", rev.sn)
            self.assertEqual("message", rev.comment)
            self.assertEqual("root", rev.author)
            self.assertEqual("2019-05-08 17:39:08+00:00", str(rev.dateTime))

            self.assertTrue(True)
        except:
            self.assertTrue(False)

    def test_letter(self):
        from manager.misc.letter import Letter

        content = {"key":"value"}
        l = Letter(Letter.NewTask, content)

        self.assertEqual(Letter.NewTask, l.type_)
        self.assertEqual(content, l.content)
        self.assertEqual('%s{"type":"new", "content":{\'key\': \'value\'}}' % 42, l.toString())
        self.assertEqual(Letter.NewTask, Letter.typeOfLetter(l))

        # Json to letter
        l1 = Letter.json2Letter('{"type":"new", "content":{"key":"value"}}')
        self.assertEqual(Letter.NewTask, l1.type_)
        self.assertEqual(content, l1.content)
        self.assertEqual('%s{"type":"new", "content":{\'key\': \'value\'}}' % 42, l.toString())
        self.assertEqual(Letter.NewTask, Letter.typeOfLetter(l))
        self.assertEqual('value', l1.getContent('key'))

if __name__ == '__main__':
    unittest.main(warnings='ignore')
