from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string
from selenium import webdriver

from manager.views import index, verManagerPage

from manager.master.verControl import RevSync
from manager.master.workerRoom import WorkerRoom
from manager.basic.letter import *
from manager.master.eventListener import EventListener
from manager.master.worker import Task

from manager.master.dispatcher import Dispatcher

from manager.basic.util import spawnThread

from manager.master.master import ServerInst
from manager.worker.client import Client

import time
import unittest
import socket

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
        import manager.master.components as Components
        from manager.basic.info import Info
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
        except Exception:
            self.assertTrue(False)

    def tes_info(self):
        from manager.basic.info import Info

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

        from manager.basic.letter import NewLetter, \
            ResponseLetter, BinaryLetter

        from datetime import datetime

        # NewLetter Test
        dateStr = str(datetime.utcnow())
        newLetter = NewLetter("newLetter", "sn_1", "vsn_1",
                              datetime=dateStr, menu="Menu",
                              parent="123456", needPost="true")
        self.assertEqual("sn_1", newLetter.getSN())
        self.assertEqual("vsn_1", newLetter.getVSN())
        self.assertEqual(dateStr, newLetter.getDatetime())
        self.assertEqual('true', newLetter.needPost())
        self.assertEqual('Menu', newLetter.getMenu())
        self.assertEqual('123456', newLetter.getParent())

        newLetter = Letter.parse(newLetter.toBytesWithLength())
        self.assertEqual("sn_1", newLetter.getSN())
        self.assertEqual("vsn_1", newLetter.getVSN())
        self.assertEqual(dateStr, newLetter.getDatetime())
        self.assertEqual('true', newLetter.needPost())
        self.assertEqual('Menu', newLetter.getMenu())
        self.assertEqual('123456', newLetter.getParent())

        # ResponseLetter Test
        response = ResponseLetter("ident", "tid_1", Letter.RESPONSE_STATE_IN_PROC, parent = "123456")
        self.assertEqual("ident", response.getIdent())
        self.assertEqual("tid_1", response.getTid())
        self.assertEqual(Letter.RESPONSE_STATE_IN_PROC, response.getState())
        self.assertEqual("123456", response.getParent())

        # BinaryLetter Test
        binary = BinaryLetter("tid_1", b"123456", menu = "menu", fileName = "rar", parent = "123456")
        self.assertEqual("tid_1", binary.getTid())
        self.assertEqual(b"123456", binary.getBytes())
        self.assertEqual("menu", binary.getMenu())
        self.assertEqual("123456", binary.getParent())
        self.assertEqual("rar", binary.getFileName())

        binBytes = binary.binaryPack()
        binary_parsed = Letter.parse(binBytes)
        self.assertEqual("tid_1", binary_parsed.getTid())
        self.assertEqual(b"123456", binary_parsed.getBytes())
        self.assertEqual("menu", binary_parsed.getMenu())
        self.assertEqual("123456", binary_parsed.getParent())
        self.assertEqual("rar", binary_parsed.getFileName())

        # MenuLetter Test
        menuLetter = MenuLetter("version", "mid_1", ["cd /home/test", "touch test.py"],
                                ["file1", "file2"], "/home/test/test.py")
        self.assertEqual("version", menuLetter.getVersion())
        self.assertEqual("mid_1", menuLetter.getMenuId())
        self.assertEqual(["cd /home/test", "touch test.py"], menuLetter.getCmds())
        self.assertEqual(["file1", "file2"], menuLetter.getDepends())
        self.assertEqual("/home/test/test.py", menuLetter.getOutput())

        menuBytes = menuLetter.toBytesWithLength()
        menuLetter_parsed = Letter.parse(menuBytes)

        self.assertEqual("version", menuLetter_parsed.getVersion())
        self.assertEqual("mid_1", menuLetter_parsed.getMenuId())
        self.assertEqual(["cd /home/test", "touch test.py"], menuLetter_parsed.getCmds())
        self.assertEqual(["file1", "file2"], menuLetter_parsed.getDepends())
        self.assertEqual("/home/test/test.py", menuLetter_parsed.getOutput())

        # commandLetter Test
        commandLetter = CommandLetter("cmd_type", "T", "extra_information", content = {"1":"1"})

        self.assertEqual("cmd_type", commandLetter.getType())
        self.assertEqual("T", commandLetter.getTarget())
        self.assertEqual("extra_information", commandLetter.getExtra())
        self.assertEqual("1", commandLetter.content_("1"))

        commandLetter_bytes = commandLetter.toBytesWithLength()
        commandLetter_parsed = Letter.parse(commandLetter_bytes)

        self.assertEqual("cmd_type", commandLetter_parsed.getType())
        self.assertEqual("T", commandLetter_parsed.getTarget())
        self.assertEqual("extra_information", commandLetter_parsed.getExtra())
        self.assertEqual("1", commandLetter_parsed.content_("1"))

        # CmdResponseLetter Test
        cmdResponseLetter = CmdResponseLetter("wIdent", "post",
                                              CmdResponseLetter.STATE_SUCCESS, reason = "NN",
                                              target = "tt")

        self.assertEqual("wIdent", cmdResponseLetter.getIdent())
        self.assertEqual("post", cmdResponseLetter.getType())
        self.assertEqual(CmdResponseLetter.STATE_SUCCESS, cmdResponseLetter.getState())
        self.assertEqual("NN", cmdResponseLetter.getReason())
        self.assertEqual("tt", cmdResponseLetter.getTarget())

        cmdRBytes = cmdResponseLetter.toBytesWithLength()
        cmdRLetter_parsed = Letter.parse(cmdRBytes)

        self.assertEqual("wIdent", cmdRLetter_parsed.getIdent())
        self.assertEqual("post", cmdRLetter_parsed.getType())
        self.assertEqual(CmdResponseLetter.STATE_SUCCESS, cmdRLetter_parsed.getState())
        self.assertEqual("NN", cmdRLetter_parsed.getReason())
        self.assertEqual("tt", cmdRLetter_parsed.getTarget())

    def tes_Connected(self):

        sInst = ServerInst("127.0.0.1", 8012, "./config.yaml")
        sInst.start()
        time.sleep(1)

        client1 = Client("127.0.0.1", 8012, "./manager/worker/config.yaml", name = "W1")
        client1.start()

        client2 = Client("127.0.0.1", 8012, "./manager/worker/config.yaml", name = "W2")
        client2.start()

        client3 = Client("127.0.0.1", 8012, "./manager/worker/config.yaml", name = "W3")
        client3.start()

        time.sleep(2)

        wr = sInst.getModule('WorkerRoom')
        self.assertEqual(3, wr.getNumOfWorkers())

        time.sleep(15)
        print(wr.postRelations())

        # Reconnect tests case
        client1.disconnect()

        # After client1 disconnect there should be one
        # worker in wait queue
        time.sleep(3)

        self.assertEqual(1, wr.getNumOfWorkersInWait())

        time.sleep(10)

        # At this time worker should reconnect to master
        self.assertEqual(0, wr.getNumOfWorkersInWait())
        self.assertEqual(3, wr.getNumOfWorkers())

        # Client Stop
        client1.stop()
        client2.stop()
        client3.stop()

        time.sleep(3)

        self.assertTrue(client1.isStop())
        self.assertTrue(client2.isStop())
        self.assertTrue(client3.isStop())

        time.sleep(10)

        self.assertEqual(0, wr.getNumOfWorkersInWait())

    def tes_logger(self):

        from manager.master.logger import Logger

        logger = Logger("./logger")
        logger.start()

        logger.log_register("Test")
        Logger.putLog(logger, "Test", "123")

    def test_dispatcher(self):

        # Create a server
        sInst = ServerInst("127.0.0.1", 8013, "./config_test.yaml")
        sInst.start()

        time.sleep(1)

        # Create workers
        client1 = Client("127.0.0.1", 8013, "./manager/worker/config.yaml", name = "W1")
        client2 = Client("127.0.0.1", 8013, "./manager/worker/config.yaml", name = "W2")
        client3 = Client("127.0.0.1", 8013, "./manager/worker/config.yaml", name = "W3")
        client4 = Client("127.0.0.1", 8013, "./manager/worker/config.yaml", name = "W4")

        workers = [client1, client2, client3, client4]

        # Activate workers
        list( map(lambda c: c.start(), workers) )

        # Then wait a while so workers have enough time to connect to master
        time.sleep(15)

        # Get 'Dispatcher' Module on server so we can dispatch task to workers
        dispatcher = sInst.getModule("Dispatcher")
        if not isinstance(dispatcher, Dispatcher):
            self.assertTrue(False)

        # Dispatch task
        task1 = Task("123", "123", "123")
        dispatcher.dispatch(task1)

        time.sleep(8)

        # To check that whether the task dispatch to one of four workers
        w_set = list( filter(lambda w: w.inProcTasks() > 0, workers) )

        # There should be only one worker has task in processing
        self.assertTrue(len(w_set) == 4)

        workerRoom = sInst.getModule("WorkerRoom")
        self.assertTrue(isinstance(workerRoom, WorkerRoom))

        status = workerRoom.statusOfWorker("W1")
        self.assertTrue(status["processing"] == 1 or status["processing"] == 2)

        time.sleep(30)

        """
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



        # Now client1 should have two task in processing
        cond = len(client1.inProcTasks()) == 2 or \
               len(client2.inProcTasks()) == 2 or \
               len(client3.inProcTasks()) == 2
        self.assertTrue(cond)

        """

    def tes_storage(self):

        import os
        from manager.basic.storage import Storage, StoChooser

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

    def tes_build(self):
        from manager.basic.info import Info
        from manager.master.build import Build, BuildSet

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

    def tes_task(self):
        from manager.basic.info import Info
        from manager.master.build import Build, BuildSet
        from manager.master.task import Task, SuperTask, SingleTask
        from manager.basic.letter import MenuLetter

        info = Info("./config_test.yaml")

        buildSet = info.getConfig('BuildSet')

        bs = BuildSet(buildSet)

        # Create a taks object
        t = SuperTask("VersionToto", "ABC", "VersionToto", buildSet = bs)

        # Get a group which GL5610 reside in
        groupOfGL5610 = t.getGroupOf("GL5610")

        # GL5610-v2 should in this group
        GL5610_v2 = list(filter(lambda t: t.id() == "GL5610-v2", groupOfGL5610))
        self.assertTrue(len(GL5610_v2) == 1)
        # Check the parent of GL5610-v2
        self.assertTrue(GL5610_v2[0].isAChild() and GL5610_v2[0].getParent().id() == "VersionToto")

        # GL5610-v3 should in this group too
        GL5610_v3 = list(filter(lambda t: t.id() == "GL5610-v3", groupOfGL5610))
        self.assertTrue(len(GL5610_v3) == 1)
        # Check the parent of GL5610-v3
        self.assertTrue(GL5610_v3[0].isAChild() and GL5610_v3[0].getParent().id() == "VersionToto")

        # Get group which GL8900 reside in
        groupOfGL8900 = t.getGroupOf("GL8900")
        self.assertTrue(len(groupOfGL8900) == 1)
        # Check the parent of GL8900
        self.assertTrue(groupOfGL8900[0].id() == "GL8900", groupOfGL8900[0].getParent().id() == "VersionToto")

        # Posts
        pt = t.getPostTask()
        self.assertEqual("VersionToto", pt.id())
        postLetter = pt.toLetter()

        self.assertEqual([], postLetter.frags())
        menus = postLetter.menus()
        self.assertTrue("GL5610_OEM" in menus)
        self.assertTrue("GL8900_OEM" in menus)

        # Menu GL5610 check
        menu_GL5610 = postLetter.getMenu("GL5610_OEM")
        depends = menu_GL5610.getDepends()
        self.assertTrue("GL5610" in depends)
        self.assertTrue("GL5610-v2" in depends)
        self.assertTrue("GL5610-v3" in depends)

        cmds = menu_GL5610.getCmds()
        self.assertEqual(["touch post"], cmds)


        # Menu GL8900 check
        menu_GL8900 = postLetter.getMenu("GL8900_OEM")
        depends_89 = menu_GL8900.getDepends()
        self.assertTrue("GL8900" in depends_89)

        cmds = menu_GL8900.getCmds()
        self.assertEqual(["touch post_gl8900"], cmds)

        # Get children of the task
        children = t.getChildren()
        children_id = list(map(lambda t: t.id(), children))

        # Check memebers
        self.assertTrue("GL5610" in children_id)
        self.assertTrue("GL5610-v2" in children_id)
        self.assertTrue("GL5610-v3" in children_id)
        self.assertTrue("GL8900" in children_id)

        # Convert child to letter
        # Format
        # header  : '{"ident":"...", "tid":"...", "needPost":"true/false"}'
        # content : '{"sn":"...", "vsn":"...", "datetime":"...",
        #             "extra":{"resultPath":"...", "cmds":"..."} }"
        v2Letter = GL5610_v2[0].toLetter()

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

        self.assertEqual("./ll2", resultPath)
        self.assertEqual(['touch ll2'], cmds)

    def tes_postListener(self):

        from manager.basic.letter import MenuLetter, BinaryLetter
        from manager.master.worker import Worker
        from manager.basic.info import Info
        from manager.worker.server import Server
        from manager.basic.mmanager import MManager
        from manager.worker.postListener import PostListener, PostProvider

        manager = MManager()

        info = Info("./manager/worker/config.yaml")
        manager.addModule(info)

        server = Server("127.0.0.1", 8044, info, manager)
        manager.addModule(server)

        pl = PostListener("127.0.0.1", 8033, manager)
        pl.start()

        manager.addModule(pl)

        postTaskLetter = PostTaskLetter("version",
                                        ["echo 'POST_PROCESSING'", "echo Processing > processing"],
                                        "./processing")

        menuLetter = MenuLetter("version", "Mid",

                                ["cd /home/aydenlin",
                                 "touch ll",
                                 "echo '123' > ll"],

                                ["file1", "file2", "file3"],
                                "/home/aydenlin/ll")

        postTaskLetter.addMenu(menuLetter)
        pl.postAppend(postTaskLetter)

        time.sleep(1)

        # file1
        binaryLetter = BinaryLetter("file1", b"123456", menu = "Mid", fileName = "file1", parent = "version")
        binaryLetter_last = BinaryLetter("file1", b"", menu = "Mid", fileName = "file1", parent = "version")

        provider_1 = PostProvider("127.0.0.1", 8033, connect=True)
        provider_1.provide(binaryLetter)
        provider_1.provide(binaryLetter_last)

        # file2
        binaryLetter = BinaryLetter("file2", b"123456", menu = "Mid", fileName = "file2", parent = "version")
        binaryLetter_last = BinaryLetter("file2", b"", menu = "Mid", fileName = "file2", parent = "version")

        provider_2 = PostProvider("127.0.0.1", 8033, connect=True)
        provider_2.provide(binaryLetter)
        provider_2.provide(binaryLetter_last)

        # file3
        binaryLetter = BinaryLetter("file3", b"123456", menu = "Mid", fileName = "file3", parent = "version")
        binaryLetter_last = BinaryLetter("file3", b"", menu = "Mid", fileName = "file3", parent = "version")

        provider_3 = PostProvider("127.0.0.1", 8033, connect=True)
        provider_3.provide(binaryLetter)
        provider_3.provide(binaryLetter_last)


        time.sleep(3)

        # Binary letter from postListener
        bin_letter = server.responseRetrive()
        self.assertTrue(bin_letter is not None)
        self.assertEqual(b'Processing\n', bin_letter.getContent('bytes'))
        self.assertEqual("processing", bin_letter.getFileName())
        self.assertEqual("version", bin_letter.getTid())

        bin_letter = server.responseRetrive()
        self.assertTrue(bin_letter is not None)
        self.assertEqual(b'', bin_letter.getContent('bytes'))
        self.assertEqual("processing", bin_letter.getFileName())
        self.assertEqual("version", bin_letter.getTid())

        # Response letter from postListener
        response_letter = server.responseRetrive()
        self.assertTrue(response_letter is not None)
        self.assertEqual("WORKER_EXAMPLE", response_letter.getIdent())
        self.assertEqual("version", response_letter.getTid())


if __name__ == '__main__':
    unittest.main(warnings='ignore')
