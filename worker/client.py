# server.py
# Usage: python server.py <configPath>

import sys
import os
import platform
import typing

import traceback

if __name__ == '__main__':
    from basic.letter import *
    from basic.info import Info
    from basic.type import *
    from basic.util import partition
else:
    from .basic.letter import *
    from .basic.info import Info
    from .basic.type import *
    from .basic.util import partition

from basic.mmanager import MManager, ModuleDaemon, Module

from processor import Processor
from sender import Sender
from receiver import Receiver
from server import Server
from post import Post

def extensionFromPath(path:str) -> str:
    fileName = path.split("/")[-1]
    nameParts = fileName.split(".")

    if '' in nameParts:
        return ""

    if len(nameParts) == 1:
        return ""
    else:
        return nameParts[-1]

def do_proc(server:'Server', post:'Post', reqLetter:Letter, info:Info) -> None:

    WORKER_NAME = info.getConfig('WORKER_NAME')

    extra = reqLetter.getContent("extra")
    building_cmds = extra['cmds']
    result_path = extra['resultPath']

    tid = reqLetter.getHeader("tid")

    if platform.system() == "Windows":
        result_path = result_path.replace("/", "\\")
        building_cmds = result_path.replace(";", "&&")

    # Notify master this task is change into in_processing state
    response = ResponseLetter(ident = WORKER_NAME,
                                tid = tid, state = Letter.RESPONSE_STATE_IN_PROC)
    server.transfer(response)

    # Processing
    try:
        repo_url = info.getConfig("REPO_URL")
        projName = info.getConfig("PROJECT_NAME")

        ret = os.system("git clone -b master " + repo_url)

        os.chdir(projName)

        revision = reqLetter.getContent('sn')
        ret = os.system("git checkout -f " + revision)

        version = reqLetter.getContent('vsn')
        version_date = reqLetter.getContent('datetime')

        building_cmds = building_cmds.replace("<vsn>", version)
        building_cmds = building_cmds.replace("datetime>", version_date)
        ret = os.system(building_cmds)

        with open(result_path, "rb") as result_file:
            vsn = reqLetter.getContent("vsn")
            needPost = reqLetter.getHeader("needPost")
            target = server # type: Union[Server, Post]

            isNeedPost = needPost == 'true'

            if isNeedPost:
                target = post

            for line in result_file:
                extension = extensionFromPath(result_path)
                binaryLetter = BinaryLetter(tid = tid, bStr = line,
                                            extension = extension)
                target.transfer(binaryLetter)

            response.setContent("state", Letter.RESPONSE_STATE_FINISHED)
            target.transfer(response)
    except:
        response.setContent("state", Letter.RESPONSE_STATE_FAILURE)
        server.transfer(response)


class Client:

    def __init__(self, mAddress:str, mPort:int, cfgPath:str, name:str = "") -> None:

        self.__cfgPath = cfgPath

        self.__name = name

        self.__mAddress = mAddress
        self.__mPort = mPort

        self.__status = 0

        self.__manager = MManager()

    def getIdent(self) -> str:
        return self.__name

    def stop(self) -> None:
        self.__manager.stopAll()

    def inProcTasks(self) -> List[str]:
        pass

    def status(self) -> int:
        return self.__status

    def connect(self) -> None:
        server = self.getModule('Server')
        taskDealer = self.getModule('Receiver')

        if server is None or not isinstance(server, Server):
            return None
        if taskDealer is None or not isinstance(taskDealer, Receiver):
            return None

        server.connect(self.__name, taskDealer.maxNumber(), taskDealer.numOfTasks())

    def disconnect(self) -> None:
        server = self.getModule('Server')
        if server is None or not isinstance(server, Server):
            return None

        server.disconnect()

    def getModule(self, ident:str) -> Optional[Module]:
        return self.__manager.getModule("ident")

    def init(self) -> None:
        info = Info(self.__cfgPath)

        address = self.__mAddress
        port = self.__mPort

        if self.__name == "":
            self.__name = workerName = info.getConfig('WORKER_NAME')
        else:
            workerName = self.__name

        max = info.getConfig('MAX_TASK_CAN_PROC')
        proc = info.getConfig('PROCESS_POOL_SIZE')

        s = Server(address, port, info, self)
        s.connect(workerName, max, proc)
        self.__manager.addModule("server", s)

        m1 = Receiver(s, info, self)
        self.__manager.addModule("Receiver", m1)

        m2 = Sender(s, info, self)
        self.__manager.addModule("Sender", m2)

        m3 = Post("127.0.0.1", 8013, info, self)
        self.__manager.addModule("Post", m3)

        m4 = Processor(info, self, procedure = do_proc)
        self.__manager.addModule("Processor", m4)

        self.__manager.startAll()

if __name__ == '__main__':
    configPath = sys.argv[1]

    info = Info(configPath)

    address = info.getConfig('MASTER_ADDRESS', 'host')
    port = info.getConfig('MASTER_ADDRESS', 'port')

    client = Client(address, port, configPath)
    client.init()
