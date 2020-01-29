from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string
from selenium import webdriver

from manager.views import index, verRegPage

from manager.misc.verControl import RevSync
from manager.misc.workerRoom import WorkerRoom
from manager.misc.basic.letter import *
from manager.misc.eventListener import EventListener
from manager.misc.worker import Task

from manager.misc.dispatcher import Dispatcher

import time
import unittest
import socket
from threading import Thread
from multiprocessing import Process

# Create your tests here.

class ServerT(Thread):

    def __init__(self, action):
        Thread.__init__(self)
        self.action = action

    def run(self):
        self.action()


class ClientT(Thread):

    def __init__(self, action, args):
        Thread.__init__(self)
        self.action = action
        self.args = args

    def run(self):
        self.action(self.args)

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

    def tes_new_rev(self):
        import manager.misc.components as Components
        from manager.misc.basic.info import Info
        Components.config = Info("./config.yaml")

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

    def test_info(self):
        from manager.misc.basic.info import Info

        cfgs = Info("./config.yaml")

        predicates = [
            lambda c: "Address" in c,
            lambda c: "Port" in c,
            lambda c: "LogDir" in c,
            lambda c: "ResultDir" in c,
            lambda c: "GitlabUrl" in c,
            lambda c: "PrivateToken" in c,
            lambda c: "TimeZone" in c
        ]

        self.assertTrue(cfgs.validityChecking(predicates))

    def test_letter(self):

        def letterTest(l):
            self.assertEqual(Letter.NewTask, l.type_)
            self.assertEqual(content, l.content)
            self.assertEqual(Letter.NewTask, Letter.typeOfLetter(l))

            # Content testing
            self.assertEqual('sn', l.getContent('sn'))
            self.assertEqual('vsn', l.getContent('vsn'))
            self.assertEqual('123', l.getContent('datetime'))

            # Header testing
            self.assertEqual('t', l.getHeader('tid'))
            self.assertEqual('i', l.getHeader('ident'))

        header = {"ident":"i", "tid":"t"}
        content = {"sn":"sn", "vsn":"vsn", "datetime":"123"}
        l = Letter(Letter.NewTask, header, content)

        letterTest(l)

        # Json to letter
        l1 = Letter.json2Letter('{"type":"new", "header":{"ident":"i", "tid":"t"},"content":{"sn":"sn", "vsn":"vsn", "datetime":"123"}}')
        letterTest(l1)

        # Letter parse
        letterInBytes = l.toBytesWithLength()
        l_parsed = Letter.parse(letterInBytes)
        letterTest(l)

        # Parse Binary type
        tid = b"".join([str(x).encode() for x in range(64)])[0:64]
        letterInBytes = (1).to_bytes(2, "big") \
                        + (4).to_bytes(4, "big") \
                        + tid \
                        + (123123).to_bytes(4, "big")
        l_parsed = Letter.parse(letterInBytes)

        self.assertEqual(tid.decode(), l_parsed.getHeader('tid'))
        self.assertEqual((123123).to_bytes(4, "big"), l_parsed.getContent('bytes'))

        # letterBytesRemain check
        streamComplete = (14).to_bytes(2, "big") + b'{"type":"new"}'
        streamIncomplete = (14).to_bytes(2, "big") + b'{"type":"new"'

        self.assertEqual(0, Letter.letterBytesRemain(streamComplete))
        self.assertEqual(1, Letter.letterBytesRemain(streamIncomplete))

        letterInBytes_incomplete = (1).to_bytes(2, "big") \
                                + (4).to_bytes(4, "big") \
                                + tid \
                                + (123123).to_bytes(3, "big")

        self.assertEqual(0, Letter.letterBytesRemain(letterInBytes))
        self.assertEqual(1, Letter.letterBytesRemain(letterInBytes_incomplete))

        # Parse testing

        # NewTask Letter
        newLetter = NewLetter(ident = "123", tid = "tid", sn = "sn", vsn = "vsn", datetime = "123")
        l = Letter.parse(newLetter.toBytesWithLength())

        self.assertEqual("123", l.getHeader('ident'))
        self.assertEqual("tid", l.getHeader('tid'))
        self.assertEqual("sn", l.getContent("sn"))
        self.assertEqual("vsn", l.getContent("vsn"))
        self.assertEqual("123", l.getContent("datetime"))

        # Response Letter
        responseLetter = ResponseLetter(ident = "ident", tid = "tid", state = "s")
        l = Letter.parse(responseLetter.toBytesWithLength())

        self.assertEqual("ident", l.getHeader("ident"))
        self.assertEqual("tid", l.getHeader("tid"))
        self.assertEqual("s", l.getContent("state"))

        # PropertyNotify Letter
        propLetter = PropLetter(ident = "123", max = "2", proc = "2")
        l = Letter.parse(propLetter.toBytesWithLength())

        self.assertEqual("123", l.getHeader('ident'))
        self.assertEqual("2", l.getContent('MAX'))
        self.assertEqual("2", l.getContent('PROC'))

        # Binary Letter
        binLetter = BinaryLetter(tid = "123", bStr = b"123")
        l = Letter.parse(binLetter.toBytesWithLength())

        self.assertEqual("123", l.getHeader('tid'))
        self.assertEqual(b"123", l.getContent("bytes"))

        # Log Letter
        logLetter = LogLetter(logId = "123", logMsg = "123")
        l = Letter.parse(logLetter.toBytesWithLength())

        self.assertEqual("123", l.getHeader('logId'))
        self.assertEqual("123", l.getContent('logMsg'))

        # Log Register Letter
        logRegLetter = LogRegLetter(logId = "123")
        l = Letter.parse(logRegLetter.toBytesWithLength())

        self.assertEqual("123", l.getHeader('logId'))

    def test_worker(self):
        import socket
        import json
        from threading import Thread

        from manager.misc.worker import Worker
        from manager.misc.eventListener import EventListener

        from manager.misc.logger import Logger
        import manager.misc.components as Components

        Components.logger = Logger("./logger")

        listener = EventListener(WorkerRoom('localhost', 8013))
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
                w.active()

                test.assertEqual('test', w.ident)
                test.assertEqual(2, w.max)
                test.assertEqual(0, w.numOfTaskProc())
                listener.registerEvent('test_event', Server.testEvent)
                listener.addWorker(w)
                test.assertTrue(listener.getWorker("test") != None)

                task = Task('1', {"sn":"123", "vsn":"123"})
                w.do(task)

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

                content = b'{"type":"notify", "header":{"ident":"test"}, "content":{"MAX":"2", "PROC":"0"}}'
                content = len(content).to_bytes(2, "big") + content
                sock.send(content)

                chunk = sock.recv(100)
                content = json.loads(chunk.decode()[2:])

                ident = content['header']['ident']
                tid = content['header']['tid']
                sn = content['content']['sn']
                vsn = content['content']['vsn']

                test.assertEqual(Letter.NewTask, content['type'])
                test.assertEqual('test', ident)
                test.assertEqual('1', tid)
                test.assertEqual('123', sn)
                test.assertEqual('123', vsn)

                response = b'{"type":"test_event", "header":{"ident":"test", "tid":"1"}, "content":{"state":"2"}}'
                response = len(content).to_bytes(2, "big") + response
                sock.send(response)

        s_thread = Server()
        s_thread.start()

        time.sleep(1)

        c_thread = Client()
        c_thread.start()

        time.sleep(10)

    def test_WorkerRoom_EventListener(self):
        import json

        from manager.misc.logger import Logger
        import manager.misc.components as Components

        Components.logger = Logger("./logger")

        def register(worker, args):
            el = args[0]
            el.fdRegister(worker)

        def serverAction():
            workerRoom = WorkerRoom('localhost', 8012)
            el = EventListener(workerRoom)

            workerRoom.hookRegister((register, [el]))

            workerRoom.start()

            time.sleep(5)

            self.assertTrue(workerRoom.isExists('A'))
            self.assertTrue(workerRoom.isExists('B'))
            self.assertTrue(workerRoom.isExists('C'))

            self.assertTrue(workerRoom.getNumOfWorkers() == 3)

        s = ServerT(serverAction)
        s.start()

        time.sleep(2)

        def clientAction(ident):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 8012))

            content = b'{"type":"notify", "header":{"ident":"' + ident.encode() + \
                      b'"}, "content":{"MAX":"2", "PROC":"0"}}'

            content = len(content).to_bytes(2, "big") + content
            sock.send(content)

            chunk = sock.recv(100)

            time.sleep(10)

        c1 = ClientT(clientAction, 'A')
        c2 = ClientT(clientAction, 'B')
        c3 = ClientT(clientAction, 'C')

        c1.start()
        c2.start()
        c3.start()

        time.sleep(10)

    def tes_integration(self):
        import sys
        sys.path.append("./worker")

        from worker.server import Server, RESPONSE_TO_SERVER_DAEMON, TASK_DEAL_DAEMON
        from manager.misc.eventListener import responseHandler, binaryHandler
        from worker.info import Info

        def register(worker, args):
            el = args[0]
            el.fdRegister(worker)

        def serverAction():
            workerRoom = WorkerRoom('127.0.0.1', 8024)
            el = EventListener(workerRoom)
            dispatcher = Dispatcher(workerRoom)

            el.registerEvent(Letter.Response, responseHandler)
            el.registerEvent(Letter.BinaryFile, binaryHandler)

            workerRoom.hookRegister((register, [el]))

            workerRoom.start()
            el.start()
            dispatcher.start()

            task = Task("abc", {"sn":"282a4eff09d6630457bd57571968b46c460da0b9", "vsn":"abc"})
            dispatcher.dispatch(task)

            time.sleep(10)

        def clientAction():
            info = Info("worker/config.yaml")
            print(info.getConfigs())

            s = Server(info)
            self.assertTrue(s.init() == 0)


            t1 = TASK_DEAL_DAEMON(s, info)
            t2 = RESPONSE_TO_SERVER_DAEMON(s, info)

            t1.start()
            t2.start()

            time.sleep(13)


        s = Process(target=serverAction)
        c = Process(target=clientAction)

        s.start()
        time.sleep(1)
        c.start()

        s.join()
        c.join()

    def test_logger(self):

        from .misc.logger import Logger
        from manager.misc.eventListener import responseHandler, logHandler, logRegisterhandler

        logger = Logger("./logger")
        logger.start()

        logger.log_register("123")
        logger.log_put("123", "ABC")

        time.sleep(10)

        # log letter
        import manager.misc.components as Components

        def register(worker, args):
            el = args[0]
            el.fdRegister(worker)

        def serverAction():
            w = WorkerRoom('127.0.0.1', 8025)
            e = EventListener(w)
            l = Logger("./log")

            Components.logger = l

            e.registerEvent(Letter.Response, responseHandler)
            e.registerEvent(Letter.LogRegister, logRegisterhandler)
            e.registerEvent(Letter.Log, logHandler)
            w.hookRegister((register, [e]))

            l.start()
            w.start()
            e.start()

            time.sleep(3)

        def clientAction(args):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', 8025))

            content = b'{"type":"notify", "header":{"ident":"test"}, "content":{"MAX":"2", "PROC":"0"}}'
            content = len(content).to_bytes(2, "big") + content

            sock.send(content)

            logRegLetter = b'{"type":"logRegister", "header":{"logId":"logTest"}, "content":{"1":1}}'
            logRegLetter = len(logRegLetter).to_bytes(2, "big") + logRegLetter
            sock.send(logRegLetter)

            logLetter = b'{"type":"log", "header":{"logId":"logTest"}, "content":{"logMsg":"Logger Test success"}}'
            logLetter = len(logLetter).to_bytes(2, "big") + logLetter

            sock.send(logLetter)

            time.sleep(3)

        s = ServerT(serverAction)
        c = ClientT(clientAction, None)

        s.start()
        time.sleep(1)
        c.start()

        time.sleep(10)


if __name__ == '__main__':
    unittest.main(warnings='ignore')
