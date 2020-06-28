import unittest

from manager.master.task import Task
from manager.worker.client import Client
from manager.master.master import ServerInst
from manager.master.dispatcher import Dispatcher
from manager.master.workerRoom import WorkerRoom
from manager.basic.info import Info

class FunctionalTest(unittest.TestCase):

    def test_dispatcher(self):

        import os
        import time
        from multiprocessing import Process

        def clientStart(name:str) -> None:
            info = Info("./manager/worker/config.yaml")

            c = Client("127.0.0.1", 8013, info,
                       name = name)
            c.start()
            c.join()

        def clientInterrupt(name:str) -> None:
            info = Info("./manager/worker/config.yaml")
            c = Client("127.0.0.1", 8013, info,
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

if __name__ == '__main__':
    unittest.main()
