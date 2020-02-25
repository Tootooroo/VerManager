from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string
from selenium import webdriver

from manager.views import index, verManagerPage

from manager.misc.verControl import RevSync
from manager.misc.workerRoom import WorkerRoom
from manager.misc.basic.letter import *
from manager.misc.eventListener import EventListener
from manager.misc.worker import Task

from manager.misc.dispatcher import Dispatcher

from manager.misc.basic.util import spawnThread

from manager.misc.server import ServerInst
from worker.client import Client

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

    def tes_index_page(self):
        response = self.client.get('/manager/')
        self.assertTemplateUsed(response, 'index.html')

    def tes_verRegister_page(self):
        response = self.client.get('/manager/verManager')
        self.assertTemplateUsed(response, 'verManager.html')

    def tes_register_feature(self):
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

        from manager.misc.basic.letter import NewLetter, ResponseLetter, BinaryLetter

        # NewLetter Test
        dateStr = str(datetime.utcnow())
        newLetter = NewLetter("newLetter", "sn_1", "vsn_1", datetime = dateStr, menu = "Menu",
                              parent = "123456", needPost = "true")
        self.assertEqual("sn_1", newLetter.getContent('sn'))
        self.assertEqual("vsn_1", newLetter.getContent('vsn'))
        self.assertEqual(dateStr, newLetter.getContent('datetime'))
        self.assertEqual('true', newLetter.getHeader('needPost'))
        self.assertEqual('Menu', newLetter.getHeader('menu'))
        self.assertEqual('123456', newLetter.getHeader('parent'))

        # ResponseLetter Test
        response = ResponseLetter("tid_1", Letter.RESPONSE_STATE_IN_PROC, parent = "123456")
        self.assertEqual("tid_1", response.getHeader("tid"))
        self.assertEqual(Letter.RESPONSE_STATE_IN_PROC, response.getContent('state'))
        self.assertEqual("123456", response.getHeader('parent'))

        # BinaryLetter Test
        binary = BinaryLetter("tid_1", b"123456", menu = "menu", extension = "rar", parent = "123456")
        self.assertEqual("tid_1", binary.getHeader('tid'))
        self.assertEqual(b"123456", binary.getContent('bytes'))
        self.assertEqual("menu", binary.getHeader('menu'))
        self.assertEqual("123456", binary.getHeader("parent"))
        self.assertEqual("rar", binary.getHeader('extension'))

        binBytes = binary.binaryPack()
        binary_parsed = Letter.parse(binBytes)
        self.assertEqual("tid_1", binary_parsed.getHeader('tid'))
        self.assertEqual(b"123456", binary_parsed.getContent('bytes'))
        self.assertEqual("menu", binary_parsed.getHeader('menu'))
        self.assertEqual("123456", binary_parsed.getHeader("parent"))
        self.assertEqual("rar", binary_parsed.getHeader('extension'))

        # MenuLetter Test
        menuLetter = MenuLetter("version", "mid_1", ["cd /home/test", "touch test.py"],
                                ["file1", "file2"], "/home/test/test.py")
        self.assertEqual("version", menuLetter.getHeader('version'))
        self.assertEqual("mid_1", menuLetter.getHeader('mid'))
        self.assertEqual(["cd /home/test", "touch test.py"], menuLetter.getContent("cmds"))
        self.assertEqual(["file1", "file2"], menuLetter.getContent('depends'))
        self.assertEqual("/home/test/test.py", menuLetter.getContent('output'))

        menuBytes = menuLetter.toBytesWithLength()
        menuLetter_parsed = Letter.parse(menuBytes)

        self.assertEqual("mid_1", menuLetter_parsed.getHeader('mid'))
        self.assertEqual(["cd /home/test", "touch test.py"], menuLetter_parsed.getContent("cmds"))
        self.assertEqual(["file1", "file2"], menuLetter_parsed.getContent('depends'))
        self.assertEqual("/home/test/test.py", menuLetter_parsed.getContent('output'))

        # commandLetter Test
        commandLetter = CommandLetter("cmd_type", "T", "extra_information", content = {"1":"1"})

        self.assertEqual("cmd_type", commandLetter.getHeader("type"))
        self.assertEqual("T", commandLetter.getHeader("target"))
        self.assertEqual("extra_information", commandLetter.getHeader("extra"))
        self.assertEqual({"1":"1"}, commandLetter.getContent("content"))

        commandLetter_bytes = commandLetter.toBytesWithLength()
        commandLetter_parsed = Letter.parse(commandLetter_bytes)

        self.assertEqual("cmd_type", commandLetter_parsed.getHeader("type"))
        self.assertEqual("T", commandLetter_parsed.getHeader("target"))
        self.assertEqual("extra_information", commandLetter_parsed.getHeader("extra"))
        self.assertEqual({"1":"1"}, commandLetter_parsed.getContent("content"))


    def tes_Connected(self):

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

        # At this time worker should reconnect to master
        self.assertEqual(0, wr.getNumOfWorkersInWait())
        self.assertEqual(2, wr.getNumOfWorkers())

        # Client Stop
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


    def tes_dispatcher(self):

        # Create a server
        sInst = ServerInst("127.0.0.1", 8013, "./config.yaml")
        sInst.start()

        time.sleep(1)

        # Create workers
        client1 = Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W1")
        client2 = Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W2")
        client3 = Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W3")
        client4 = Client("127.0.0.1", 8013, "./worker/config.yaml", name = "W4")

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
        task1 = Task("123", "123", "123")
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
        task2 = Task("124", "123", "123")
        dispatcher.dispatch(task)

        task3 = Task("125", "123", "123")
        dispatcher.dispatch(task)

        task4 = Task("126", "123", "123")
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
        from manager.misc.basic.storage import Storage, StoChooser

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

    def test_build(self):
        from manager.misc.basic.info import Info
        from manager.misc.build import Build, BuildSet

        info = Info("./config_test.yaml")

        buildSet = info.getConfig("BuildSet")

        self.assertTrue(BuildSet.isValid(buildSet))

        bs = BuildSet(buildSet)

        b = bs.getBuild("GL5610")

        self.assertTrue("GL5610", b.getIdent())

        builds = bs.getBuilds()
        builds_id = list(map(lambda b: b.getIdent(), builds))
        self.assertTrue('GL5610' in builds_id)
        self.assertTrue('GL5610-v2' in builds_id)
        self.assertTrue('GL5610-v3' in builds_id)
        self.assertTrue('GL8900' in builds_id)

        self.assertTrue(bs.belongTo('GL5610') == bs.belongTo('GL5610-v2'))
        self.assertTrue(bs.belongTo('GL5610') == bs.belongTo('GL5610-v3'))

        bs_GL8900 = bs.belongTo('GL8900')
        self.assertEqual("GL8900_OEM", bs_GL8900[0])
        self.assertTrue(len(bs_GL8900[1]) == 1)
        self.assertTrue(bs_GL8900[1][0].getIdent() == 'GL8900')

    def test_task(self):
        from manager.misc.basic.info import Info
        from manager.misc.build import Build, BuildSet
        from manager.misc.task import Task

        info = Info("./config_test.yaml")

        buildSet = info.getConfig('BuildSet')

        bs = BuildSet(buildSet)

        # Create a taks object
        t = Task("VersionToto", "ABC", "VersionToto", buildSet = bs)

        # Get a group which GL5610 reside in
        groupOfGL5610 = t.getGroupOf("GL5610")

        # GL5610-v2 should in this group
        GL5610_v2 = list(filter(lambda t: t.id() == "GL5610-v2", groupOfGL5610))
        self.assertTrue(len(GL5610_v2) == 1)
        # Check the parent of GL5610-v2
        self.assertTrue(GL5610_v2[0].hasParent() and GL5610_v2[0].getParent().id() == "VersionToto")

        # GL5610-v3 should in this group too
        GL5610_v3 = list(filter(lambda t: t.id() == "GL5610-v3", groupOfGL5610))
        self.assertTrue(len(GL5610_v3) == 1)
        # Check the parent of GL5610-v3
        self.assertTrue(GL5610_v3[0].hasParent() and GL5610_v3[0].getParent().id() == "VersionToto")

        # Get group which GL8900 reside in
        groupOfGL8900 = t.getGroupOf("GL8900")
        self.assertTrue(len(groupOfGL8900) == 1)
        # Check the parent of GL8900
        self.assertTrue(groupOfGL8900[0].id() == "GL8900", groupOfGL8900[0].getParent().id() == "VersionToto")

        # Get children of the task
        children = t.getChildren()
        children_id = list(map(lambda t: t.id(), children))

        # Check memebers
        self.assertTrue("GL5610" in children_id)
        self.assertTrue("GL5610-v2" in children_id)
        self.assertTrue("GL5610-v3" in children_id)
        self.assertTrue("GL8900" in children_id)

        # Big task should unable to convert to big task
        self.assertTrue(t.toNewTaskLetter() == None)

        # Convert child to letter
        # Format
        # header  : '{"ident":"...", "tid":"...", "needPost":"true/false"}'
        # content : '{"sn":"...", "vsn":"...", "datetime":"...",
        #             "extra":{"resultPath":"...", "cmds":"..."} }"
        v2Letter = GL5610_v2[0].toNewTaskLetter()

        v2Tid = v2Letter.getHeader("tid")
        self.assertEqual("GL5610-v2", v2Tid)

        v2NeedPost = v2Letter.getHeader("needPost")
        self.assertEqual("true", v2NeedPost)

        v2SN = v2Letter.getContent("sn")
        self.assertEqual("ABC", v2SN)

        v2VSN = v2Letter.getContent("vsn")
        self.assertEqual("VersionToto", v2VSN)

        extra = v2Letter.getContent("extra")

        resultPath = extra['resultPath']
        cmds = extra['cmds']

        self.assertEqual("...", resultPath)
        self.assertEqual(['...', '...'], cmds)

    def test_postListener(self):

        from manager.misc.worker import Worker
        from worker.basic.info import Info
        from worker.server import Server
        from worker.basic.mmanager import MManager
        from worker.postListener import Stuff, Stuffs, PostMenu, PostListener, PostProcessor

        manager = MManager()

        info = Info("./worker/config.yaml")

        server = Server("127.0.0.1", 8044, info, manager)
        manager.addModule("Server", server)

        pl = PostListener("127.0.0.1", 8033, manager)
        pl.start()

        manager.addModule("PostListener", pl)

        menuLetter = MenuLetter("version", "Mid", ["cd /home/aydenlin", "touch ll", "echo '123' > ll"],
                                ["file1", "file2", "file3"],
                                "/home/aydenlin/ll")
        pl.menuAppend(menuLetter)

        # file1
        binaryLetter = BinaryLetter("file1", b"123456", menu = "Mid", extension = "rar", parent = "version")
        binaryLetter_last = BinaryLetter("file1", b"", menu = "Mid", extension = "rar", parent = "version")

        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.connect(("127.0.0.1", 8033))

        Worker.sending(sock1, binaryLetter)
        Worker.sending(sock1, binaryLetter_last)

        # file2
        binaryLetter = BinaryLetter("file2", b"123456", menu = "Mid", extension = "rar", parent = "version")
        binaryLetter_last = BinaryLetter("file2", b"", menu = "Mid", extension = "rar", parent = "version")

        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2.connect(("127.0.0.1", 8033))

        Worker.sending(sock2, binaryLetter)
        Worker.sending(sock2, binaryLetter_last)

        # file3
        binaryLetter = BinaryLetter("file3", b"123456", menu = "Mid", extension = "rar", parent = "version")
        binaryLetter_last = BinaryLetter("file3", b"", menu = "Mid", extension = "rar", parent = "version")

        #sock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sock3.connect(("127.0.0.1", 8033))

        #Worker.sending(sock3, binaryLetter)
        #Worker.sending(sock3, binaryLetter_last)

        time.sleep(20)

        # Binary letter from postListener
        bin_letter = server.responseRetrive()
        self.assertTrue(not bin_letter is None)
        self.assertEqual(b'123\n', bin_letter.getContent('bytes'))
        self.assertEqual("rar", bin_letter.getHeader('extension'))
        self.assertEqual("Mid", bin_letter.getHeader("menu"))
        self.assertEqual("version", bin_letter.getHeader("parent"))

        # Response letter from postListener
        response_letter = server.responseRetrive()
        self.assertTrue(not response_letter is None)
        self.assertEqual("Mid", response_letter.getHeader('tid'))
        self.assertEqual("version", response_letter.getHeader('parent'))

        time.sleep(10)


if __name__ == '__main__':
    unittest.main(warnings='ignore')
