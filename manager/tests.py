from django.test import TestCase
from django.http import HttpRequest
from django.template.loader import render_to_string

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

    def test_dispatcher(self):

        import os
        from multiprocessing import Process

        def clientStart(name:str) -> None:
            c = Client("127.0.0.1", 8013, "./manager/worker/config.yaml",
                       name = name)
            c.start()
            c.join()

        def clientInterrupt(name:str) -> None:
            c = Client("127.0.0.1", 8013, "./manager/worker/config.yaml",
                       name = name)
            c.start()

            time.sleep(15)
            c.stop()

            c.join()

        # Create a server
        sInst = ServerInst("127.0.0.1", 8013, "./config_test.yaml")
        sInst.start()

        time.sleep(1)

        # Create workers
        client1 = Process(target=clientStart, args = ("W1", ))
        time.sleep(3)
        client2 = Process(target=clientStart, args = ("W2", ))
        client3 = Process(target=clientStart, args = ("W3", ))
        client4 = Process(target=clientStart, args = ("W4", ))

        workers = [client1, client2, client3, client4]

        # Activate workers
        list( map(lambda c: c.start(), workers) )

        # Then wait a while so workers have enough time to connect to master
        time.sleep(25)

        # Get 'Dispatcher' Module on server so we can dispatch task to workers
        dispatcher = sInst.getModule("Dispatcher")
        if not isinstance(dispatcher, Dispatcher):
            self.assertTrue(False)

        # Dispatch task
        task1 = Task("122", "123", "122")
        dispatcher.dispatch(task1)

        workerRoom = sInst.getModule("WorkerRoom")
        self.assertTrue(isinstance(workerRoom, WorkerRoom))

        # Now let us dispatch three more task to workers
        # if nothing wrong each of these workers should
        # in work.
        task2 = Task("124", "123", "124")
        dispatcher.dispatch(task2)

        task3 = Task("125", "123", "125")
        dispatcher.dispatch(task3)

        task4 = Task("126", "123", "126")
        dispatcher.dispatch(task4)

        time.sleep(30)

        self.assertTrue(os.path.exists("./Storage/122/122total"))
        self.assertTrue(os.path.exists("./Storage/124/124total"))
        self.assertTrue(os.path.exists("./Storage/125/125total"))
        self.assertTrue(os.path.exists("./Storage/126/126total"))

        for path in ["./Storage/" + sub for sub in ["122", "124", "125", "126"]]:
            fileName = path.split("/")[-1] + "total"
            os.remove(path+"/"+fileName)
            os.rmdir(path)

        time.sleep(10)



class UnitTest(TestCase):

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

    def test_info(self):
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
                              parent="123456", needPost="true",
                              extra = {})
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
        commandLetter = CommandLetter("cmd_type", {"1":"1"}, "T", "extra_information")

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
                                              target = "tt", extra = {})

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

    def test_worker(self):
        from manager.master.build import Build, Merge
        from manager.master.task import SingleTask, PostTask
        from manager.basic.letter import sending as l_send, receving as l_recv, \
            NewLetter, PostTaskLetter
        from socket import socket, AF_INET, SOCK_STREAM
        from manager.master.worker import Worker

        Max = "2"
        InProc = "0"

        def worker_connect(sock:socket) -> None:
            # Wait m_sock
            time.sleep(3)
            sock.connect(("127.0.0.1", 9999))

            # Send PropLetter
            prop_l = PropLetter("TestWorker", Max, InProc)
            l_send(sock, prop_l)

            l = l_recv(sock)
            if l is None:
                self.assertTrue(False)
            else:
                if isinstance(l, NewLetter):
                    pass
                else:
                    self.assertTrue(False)

            l = l_recv(sock)
            if l is None:
                self.assertTrue(False)
            else:
                if isinstance(l, PostTaskLetter):
                    pass
                else:
                    self.assertTrue(False)


        s_sock = socket(AF_INET, SOCK_STREAM)
        spawnThread(worker_connect, s_sock)

        # Get worker socket
        m_sock = socket(AF_INET, SOCK_STREAM)
        m_sock.bind(("127.0.0.1", 9999))
        m_sock.listen()

        w_sock, addr = m_sock.accept()

        worker = Worker(w_sock, addr)
        worker.active()

        # Prop Assert
        self.assertEqual(int(Max), worker.maxNumOfTask())
        self.assertEqual(int(InProc), len(worker.inProcTasks()))

        # Send a task to worker
        build = Build("B_TEST", {'cmd':["cmd1", "cmd2"], 'output':["./output"]})
        worker.do(SingleTask("Test", "SN", "REV", build, {}))

        # Now inProc task should be 1
        inProcTasks = worker.inProcTasks()
        self.assertTrue(1, len(inProcTasks))

        task = inProcTasks[0]
        self.assertEqual("Test", task.id())
        self.assertEqual("SN", task.getSN())
        self.assertEqual("REV", task.getVSN())

        # Now Send a PostTask
        build_post = Build("B_TEST", {'cmd':["cmd1", "cmd2"], 'output':["./output"]})
        worker.do(PostTask("PostTest", "VSN", [], [], Merge(build_post)))

        inProcTasks = worker.inProcTasks()
        self.assertTrue(2, len(inProcTasks))

        self.assertTrue("Test" in [t.id() for t in inProcTasks])
        self.assertTrue("PostTest" in [t.id() for t in inProcTasks])

        # Remove tasks
        worker.removeTask("Test")
        inProcTasks = worker.inProcTasks()
        self.assertEqual(1, len(inProcTasks))
        self.assertTrue("Test" not in [t.id() for t in inProcTasks])
        self.assertTrue("PostTest" in [t.id() for t in inProcTasks])

        worker.removeTask("PostTest")
        inProcTasks = worker.inProcTasks()
        self.assertEqual(0, len(inProcTasks))
        self.assertTrue("Test" not in [t.id() for t in inProcTasks])
        self.assertTrue("PostTest" not in [t.id() for t in inProcTasks])

        time.sleep(3)

    def test_logger(self):

        from manager.master.logger import Logger

        logger = Logger("./logger")
        logger.start()

        logger.log_register("Test")
        Logger.putLog(logger, "Test", "123")


    def test_storage(self):

        import os
        from manager.basic.storage import Storage, StoChooser

        storage = Storage("./Storage", None)

        # Create a file via storage
        boxName = "box"
        fileName = "file"
        chooser_create = storage.create(boxName, fileName)

        self.assertTrue(os.path.exists("./Storage/box/file"))

        # Open
        chooser_open = storage.open(boxName, fileName)
        self.assertEqual(chooser_create.path(), chooser_open.path())

        self.assertEqual(1, storage.numOfFiles())

        # Remove
        storage.delete(boxName, fileName)
        self.assertTrue(not os.path.exists("./Storage/box"))

        self.assertEqual(0, storage.numOfFiles())

        # Create files
        files = ["file1", "file2", "file3", "file4", "file5"]

        for file in files:
            storage.create(boxName, file)
        self.assertEqual(len(files), storage.numOfFiles())

        self.assertTrue(os.path.exists("./Storage/box/file1"))
        self.assertTrue(os.path.exists("./Storage/box/file2"))
        self.assertTrue(os.path.exists("./Storage/box/file3"))
        self.assertTrue(os.path.exists("./Storage/box/file4"))
        self.assertTrue(os.path.exists("./Storage/box/file5"))

        for file in files:
            storage.delete(boxName, file)

        self.assertTrue(not os.path.exists("./Storage/box/file1"))
        self.assertTrue(not os.path.exists("./Storage/box/file2"))
        self.assertTrue(not os.path.exists("./Storage/box/file3"))
        self.assertTrue(not os.path.exists("./Storage/box/file4"))
        self.assertTrue(not os.path.exists("./Storage/box/file5"))

        storage.destruct()
        self.assertTrue(not os.path.exists("./Storage/"))


    def test_build(self):
        from manager.basic.info import Info
        from manager.master.build import Build, BuildSet

        from functools import reduce

        info = Info("./config_test.yaml")

        buildSet = info.getConfig("BuildSet")

        self.assertTrue(BuildSet.isValid(buildSet))

        bs = BuildSet(buildSet)

        # VarAssign testing
        builds = bs.getBuilds()
        for build in builds:
            build.varAssign([("<version>", "Ver"), ("<datetime>", "Date")])

        ret = []
        for build in builds:
            vars = ["Ver", "Date"]
            ret = [reduce(lambda acc, cur: acc and (cur in cmd), vars, True) for cmd in build.getCmd()]

        self.assertTrue(False not in ret)


        # Get a Build and test it.
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
        self.assertEqual("P2", bs_GL8900[0])
        self.assertTrue(len(bs_GL8900[1]) == 1)
        self.assertTrue(bs_GL8900[1][0].getIdent() == 'GL8900')

    def test_task(self):
        from manager.basic.info import Info
        from manager.master.build import Build, BuildSet
        from manager.master.task import Task, SuperTask, SingleTask, PostTask
        from manager.basic.letter import MenuLetter

        info = Info("./config_test.yaml")

        buildSet = info.getConfig('BuildSet')

        bs = BuildSet(buildSet)

        # Create a taks object
        t = SuperTask("VersionToto", "ABC", "VersionToto", bs, {})

        # Get a group which GL5610 reside in
        groupOfGL5610 = t.getGroupOf("GL5610")

        # GL5610-v2 should in this group
        GL5610_v2 = list(filter(lambda t: t.id() == "VersionToto__GL5610-v2", groupOfGL5610))
        self.assertTrue(len(GL5610_v2) == 1)
        # Check the parent of GL5610-v2
        self.assertTrue(GL5610_v2[0].isAChild() and GL5610_v2[0].getParent().id() == "VersionToto")

        # GL5610-v3 should in this group too
        GL5610_v3 = list(filter(lambda t: t.id() == "VersionToto__GL5610-v3", groupOfGL5610))
        self.assertTrue(len(GL5610_v3) == 1)
        # Check the parent of GL5610-v3
        self.assertTrue(GL5610_v3[0].isAChild() and GL5610_v3[0].getParent().id() == "VersionToto")

        # Get group which GL8900 reside in
        groupOfGL8900 = t.getGroupOf("GL8900")
        self.assertTrue(len(groupOfGL8900) == 1)
        # Check the parent of GL8900
        self.assertTrue(groupOfGL8900[0].id() == "VersionToto__GL8900",
                        groupOfGL8900[0].getParent().id() == "VersionToto")

        # Posts
        pt = t.getPostTask()
        pt_ident = PostTask.genIdent("VersionToto")
        self.assertEqual(pt_ident, pt.id())
        postLetter = pt.toLetter()

        deps = [t.id() for t in pt.dependence()]
        deps_ = ["VersionToto__GL5610-v2", "VersionToto__GL5610-v3",
                 "VersionToto__GL5610", "VersionToto__GL8900"]
        self.assertEqual(4, len(deps))
        self.assertEqual(deps_.sort(), deps.sort())

        self.assertEqual([], postLetter.frags())
        menus = postLetter.menus()
        self.assertTrue("P1" in menus)
        self.assertTrue("P2" in menus)

        # Menu GL5610 check
        menu_GL5610 = postLetter.getMenu("P1")
        depends = menu_GL5610.getDepends()
        self.assertTrue("VersionToto__GL5610" in depends)
        self.assertTrue("VersionToto__GL5610-v2" in depends)
        self.assertTrue("VersionToto__GL5610-v3" in depends)

        cmds = menu_GL5610.getCmds()
        self.assertEqual(["cat ll ll2 ll3 VersionToto  > post"], cmds)

        # Menu GL8900 check
        menu_GL8900 = postLetter.getMenu("P2")
        depends_89 = menu_GL8900.getDepends()
        self.assertTrue("VersionToto__GL8900" in depends_89)

        cmds = menu_GL8900.getCmds()
        self.assertEqual(["cat ll4 VersionToto  > post_gl8900", "echo 8900 VersionToto  >> post_gl8900"], cmds)

        # Get children of the task
        children = [child.id() for child in t.getChildren()]

        # Check memebers
        self.assertTrue("VersionToto__GL5610" in children)
        self.assertTrue("VersionToto__GL5610-v2" in children)
        self.assertTrue("VersionToto__GL5610-v3" in children)
        self.assertTrue("VersionToto__GL8900" in children)

        # Convert child to letter
        # Format
        # header  : '{"ident":"...", "tid":"...", "needPost":"true/false"}'
        # content : '{"sn":"...", "vsn":"...", "datetime":"...",
        #             "extra":{"resultPath":"...", "cmds":"..."} }"
        v2Letter = GL5610_v2[0].toLetter()

        v2Tid = v2Letter.getHeader("tid")
        self.assertEqual("VersionToto__GL5610-v2", v2Tid)

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
        self.assertEqual(['echo ll2 VersionToto  > ll2'], cmds)

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


    def test_observer(self):
        from manager.basic.observer import Subject, Observer

        event = ""
        log   = ""

        event_msg = "Doing Something..."
        log_msg   = "Logging message..."

        class S(Subject):
            EVENT = "EVENT"
            LOG   = "Log"

            def __init__(self) -> None:
                Subject.__init__(self, "S")

                self.addType(S.EVENT)
                self.addType(S.LOG)

            def do(self) -> None:
                self.notify(S.EVENT, event_msg)

            def log(self) -> None:
                self.notify(S.LOG, log_msg)

        class O(Observer):

            def __init__(self) -> None:
                Observer.__init__(self)

            def eventListen(self, data:Any) -> None:
                nonlocal event
                event = data

            def logListen(self, data:Any) -> None:
                nonlocal log
                log = data

        s = S()

        o_event = O()
        o_event.handler_install("S", o_event.eventListen)

        o_log   = O()
        o_log.handler_install("S", o_log.logListen)

        s.subscribe(S.EVENT, o_event)
        s.subscribe(S.LOG, o_log)

        s.do()
        s.log()

        self.assertEqual(event_msg, event)
        self.assertEqual(log_msg, log)

if __name__ == '__main__':
    unittest.main(warnings='ignore')
