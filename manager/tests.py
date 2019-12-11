from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string
from selenium import webdriver

from manager.views import index, verRegPage

from manager.misc.verControl import RevSync

import time
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

        header = {"key":"value"}
        content = {"key":"value"}
        l = Letter(Letter.NewTask, header, content)

        self.assertEqual(Letter.NewTask, l.type_)
        self.assertEqual(content, l.content)
        self.assertEqual(Letter.NewTask, Letter.typeOfLetter(l))
        self.assertEqual('value', l.getContent('key'))
        self.assertEqual('value', l.getHeader('key'))

        # Json to letter
        l1 = Letter.json2Letter('{"type":"new", "header":{"key":"value"},"content":{"key":"value"}}')
        self.assertEqual(Letter.NewTask, l1.type_)
        self.assertEqual(content, l1.content)
        self.assertEqual(Letter.NewTask, Letter.typeOfLetter(l))
        self.assertEqual('value', l1.getContent('key'))
        self.assertEqual('value', l1.getHeader('key'))

    def test_worker(self):
        import socket
        import json
        from threading import Thread

        from manager.misc.worker import Worker, EventListener

        listener = EventListener()
        listener.start()

        test = self

        class Server(Thread):
            def __init__(self):
                Thread.__init__(self)

            def testEvent(eventListener, letter):
                test.assertEqual('test_event', letter.typeOfLetter())
                exit(0)

            def run(self):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', 8011))
                sock.listen(1)

                (clientsock, address) = sock.accept()
                w = Worker(clientsock)

                test.assertEqual('test', w.ident)
                test.assertEqual(2, w.max)
                test.assertEqual(0, w.processing)

                listener.registerEvent('test_event', Server.testEvent)
                listener.addWorker(w)

                w.do({'tid':'1'}, {'sn':'123', 'vsn':'123'})

                time.sleep(3)

                w.counterSync()
                test.assertTrue(w.onlineCounter() == 3)
                test.assertTrue(w.offlineCounter() == 0)
                test.assertTrue(w.waitCounter() == 0)


        class Client(Thread):
            def __init__(self):
                Thread.__init__(self)

            def run(self):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', 8011))

                content = b'14{"type":"notify", "header":{"ident":"test"}, "content":{"MAX":"2", "PROC":"0"}}'
                sock.send(content)

                chunk = sock.recv(100)
                content = json.loads(chunk.decode()[2:])

                ident = content['header']['ident']
                tid = content['header']['tid']
                sn = content['content']['sn']
                vsn = content['content']['vsn']

                test.assertEqual('test', ident)
                test.assertEqual('1', tid)
                test.assertEqual('123', sn)
                test.assertEqual('123', vsn)

                response = b'12{"type":"test_event", "header":{"ident":"test", "tid":"1"}, "content":{"state":"2"}}'
                sock.send(response)

        s_thread = Server()
        s_thread.start()

        time.sleep(1)

        c_thread = Client()
        c_thread.start()

        s_thread.join()
        c_thread.join()
        listener.join()

if __name__ == '__main__':
    unittest.main(warnings='ignore')
