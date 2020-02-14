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

from manager.misc.util import spawnThread

from manager.misc.server import ServerInst
import worker.server as Client

import time
import unittest
import socket
from threading import Thread
from multiprocessing import Process

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

    def test_Connected(self):

        sInst = ServerInst("127.0.0.1", 8012, "./config.yaml")
        sInst.start()
        time.sleep(1)

        client1 = Client.Client("127.0.0.1", 8012, "./worker/config.yaml", name = "W1")
        client1.start()

        client2 = Client.Client("127.0.0.1", 8012, "./worker/config.yaml", name = "W2")
        client2.start()

        time.sleep(2)

        wr = sInst.getModule('WorkerRoom')
        self.assertEqual(2, wr.getNumOfWorkers())

        # Reconnect tests case
        client1.disconnect()

        # After client1 disconnect there should be one
        # worker in wait queue
        time.sleep(1)
        self.assertEqual(1, wr.getNumOfWorkersInWait())

        time.sleep(10)
        self.assertEqual(0, wr.getNumOfWorkersInWait())
        self.assertEqual(2, wr.getNumOfWorkers())

        time.sleep(2)

        self.assertEqual(2, wr.getNumOfWorkers())
        self.assertEqual(0, wr.getNumOfWorkersInWait())

        # Client Stop
        time.sleep(5)

        client1.stop()
        client2.stop()

        time.sleep(3)

        self.assertEqual(1, client1.status())
        self.assertEqual(1, client2.status())

        time.sleep(10)

        self.assertEqual(0, wr.getNumOfWorkersInWait())

    def test_logger(self):

        from manager.misc.logger import Logger

        logger = Logger("./logger")
        logger.start()

        logger.log_register("Test")
        Logger.putLog(logger, "Test", "123")


    def test_dispatcher(self):

        # Create a server
        sInst = ServerInst("127.0.0.1", 8013, "./config.yaml")
        sInst.start()

        time.sleep(1)

        # Create workers
        client1 = Client.Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W1")
        client2 = Client.Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W2")
        client3 = Client.Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W3")
        client4 = Client.Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W4")

        workers = [client1, client2, client3, client4]

        # Activate workers
        list( map(lambda c: c.start(), workers) )

        # Then wait a while so workers have enough time to connect to master
        time.sleep(2)

        # Get 'Dispatcher' Module on server so we can dispatch task to workers
        dispatcher = sInst.getModule("Dispatcher")
        if not isinstance(dispatcher, Dispatcher):
            self.assertTrue(False)

        # Dispatch task
        task = Task("123", "123", "123")
        dispatcher.dispatch(task)

        time.sleep(3)

        # To check workers is task dispatch to one of four workers
        w_set = list( filter(lambda w: len(w.inProcTasks()) > 0, workers) )

        # There should be only one worker has task in processing
        self.assertTrue(len(w_set) == 1)

        w = w_set[0]

        # The task's ident should be match the ident of Task
        self.assertEqual("123", w.inProcTasks()[0])

        workerRoom = sInst.getModule("WorkerRoom")
        if not isinstance(workerRoom, WorkerRoom):
            self.assertTrue(False)

        status = workerRoom.statusOfWorker(w.getIdent())
        self.assertEqual(1, status["processing"])
        self.assertEqual("123", status["inProcTask"][0])

        # Now let us dispatch three more task to workers
        # if nothing wrong each of these workers should
        # in work.
        task = Task("124", "123", "123")
        dispatcher.dispatch(task)

        task = Task("125", "123", "123")
        dispatcher.dispatch(task)

        task = Task("126", "123", "123")
        dispatcher.dispatch(task)

        time.sleep(5)

        tasks = ["123", "124", "125", "126"]
        for w in workers:
            status = workerRoom.statusOfWorker(w.getIdent())

            self.assertTrue(len(w.inProcTasks()) == 1)
            self.assertEqual(w.inProcTasks()[0], status["inProcTask"][0])

        # Now let client4 stop
        client4.stop()

        # Wait 15 seconds so client4 will be removed
        # from WorkerRoom
        time.sleep(15)

        # Now client1 should have two task in processing
        cond = len(client1.inProcTasks()) == 2 or \
               len(client2.inProcTasks()) == 2 or \
               len(client3.inProcTasks()) == 2
        self.assertTrue(cond)

    def test_storage(self):

        import os
        from manager.misc.storage import Storage, StoChooser

        fileName = "file"
        storage = Storage("./Storage", None)

        # Create a file via storage
        chooser = storage.open(fileName)

        # To check that is the has been created
        self.assertTrue(os.path.exists(chooser.path()))
        self.assertTrue(storage.getPath(fileName))

        chooser.store(b"12345678")
        chooser.close()

        chooser = storage.open("file")
        chooser.rewind()

        bStr = chooser.retrive(8)

        # To check that is content of the file is same to
        # the string that be writed before
        self.assertEqual(b"12345678", bStr)

        chooser.close()

        filePath = chooser.path()

        storage.delete(fileName)
        self.assertTrue(not os.path.exists(filePath))

if __name__ == '__main__':
    unittest.main(warnings='ignore')
