import asyncio
import typing
from manager.master.task import Task
from manager.master.worker import Worker
from manager.basic.commands import Command


class StreamReaderDummy(asyncio.StreamReader):
    def __init__(self) -> None:
        return None


class StreamWriterDummy(asyncio.StreamWriter):
    def __init__(self) -> None:
        return None


class DO_RTN_NOT_SETED(Exception):
    pass


class CONTROL_RTN_NOT_SETED(Exception):
    pass


class WorkerStub(Worker):

    def __init__(self) -> None:
        Worker.__init__(
            self,
            StreamReaderDummy(),
            StreamWriterDummy()
        )

    async def do(self, task: Task) -> None:
        """
        Respond to Task dispatch
        """

    async def control(self, cmd: Command) -> None:
        """
        Respond to control command
        """

    async def reply(self, msg: typing.Any) -> None:
        """
        Method to reply message to Master
        coperate with do and control method
        to work like a real Worker
        """
