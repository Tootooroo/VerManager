# MIT License
#
# Copyright (c) 2020 Gcom
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import abc
import asyncio
import datetime
import manager.worker.configs as configs

from typing import Optional, cast, Dict
from manager.basic.letter import Letter
from .proc_common import Output, ChannelEntry

# Need by JobProcUnit
import platform
import os
import subprocess
import shutil
from manager.basic.util import packShellCommands, execute_shell,\
    pathSeperator
from manager.basic.letter import NewLetter, ResponseLetter,\
    BinaryLetter


class ProcUnit(abc.ABC):

    PROC_UNIT_STATE = int
    # A ProcUnit is in stop state before it's
    # install into Processor
    STATE_STOP = 0
    # Ready to handle letter
    STATE_READY = 1
    # Normal space is out of space
    STATE_OVERLOAD = 2
    # DENY state means ProcUnit is unable
    # to accept any more jobs.
    STATE_DENY = 3
    # A ProcUnit is stop cause of exception
    STATE_EXCEP = 4

    def __init__(self, ident: str) -> None:
        self._unitIdent = ident

        self._state = self.STATE_STOP

        self._install = False

        self._normal_space = asyncio.Queue(256)  # type: asyncio.Queue[Letter]
        self._reserved_space = asyncio.Queue(128)  \
            # type: asyncio.Queue[Letter]

        # Queue that hold letter generate by ProcUnit
        # should be transfered to master.
        # Will be setup while install into Processor.
        self._output_space = None  # type: Optional[Output]

        self._start_at = datetime.datetime.utcnow()
        self._channel = None  # type: Optional[ChannelEntry]
        self._t = None  # type: Optional[asyncio.Task]

    def ident(self) -> str:
        return self._unitIdent

    async def _run_noexcep(self) -> None:
        try:
            await self.run()
        except Exception:
            self._state = self.STATE_EXCEP
            return

        self._state = self.STATE_STOP

        if self._channel is not None:
            self._channel.update('state', self.STATE_STOP)

    def start(self) -> None:
        # Setup state
        self._state = self.STATE_READY

        # Run ProcLogic in current loop
        loop = asyncio.get_running_loop()
        self._t = loop.create_task(self._run_noexcep())

    def stop(self) -> None:
        if self._t is not None:
            self._t.cancel()
            self._t = None

        self._state = self.STATE_STOP

    @abc.abstractmethod
    async def run(self) -> None:
        """
        Start the ProcUnit. After started it will
        handle letter receive from Processor
        """

    async def proc(self, letter: Letter) -> None:

        try:
            self._normal_space.put_nowait(letter)

        except asyncio.QueueFull:
            await self._store_job_to_reserved_space(letter)
            raise PROC_UNIT_HIGHT_OVERLOAD(self._unitIdent)

    async def job_retrive(self, timeout=None) -> Letter:

        # Flush letters from reserved space
        # to normal space if there is any
        # letters within reserved space
        self._flush()

        return await asyncio.wait_for(
            self._normal_space.get(), timeout=timeout)

    def _flush(self) -> None:
        reserved_empty = self._reserved_space.empty()
        noSpace = self._normal_space.full()

        if reserved_empty or noSpace:
            return None

        while True:

            try:
                self._normal_space.put_nowait(
                    self._reserved_space.get_nowait())
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                return None

    async def _store_job_to_reserved_space(self, letter: Letter) -> None:
        try:
            self._reserved_space.put_nowait(letter)
        except asyncio.QueueFull:
            raise PROC_UNIT_IS_IN_DENY_MODE(self._unitIdent)

    def msg_gen(self) -> None:
        if self._channel is None:
            return

        self._channel.update('state', self._state)
        self._channel.update('ident', self._unitIdent)
        self._channel.update('failureCount', 0)

        uptime = (datetime.datetime.utcnow() - self._start_at).seconds
        self._channel.update('uptime', uptime)

    def _notify(self) -> None:
        if self._channel is None:
            return None
        self._channel.push()

    def state(self) -> int:
        return self._state

    def setChannel(self, channel: ChannelEntry) -> None:
        self._channel = channel

    def setOutput(self, space: Output) -> None:
        self._output_space = space

    @abc.abstractmethod
    async def reset(self) -> None:
        """ Reset ProcUnit's status to initial state """

    def _send(self, letter: Letter) -> None:
        if self._output_space is None:
            raise PROC_UNIT_NO_OUTPUT_SPACE(self._unitIdent)
        self._output_space.put_nowait(letter)


class PROC_UNIT_NO_OUTPUT_SPACE(Exception):

    def __init__(self, unit_ident: str) -> None:
        self.unit_ident = unit_ident

    def __str__(self) -> str:
        return "ProcUnit " + self.unit_ident + "'s output space is not seted"


class PROC_UNIT_HIGHT_OVERLOAD(Exception):

    def __init__(self, unit_ident: str) -> None:
        self.unit_ident = unit_ident

    def __str__(self) -> str:
        return 'ProcUnit ' + self.unit_ident + ' is overload'


class PROC_UNIT_IS_IN_DENY_MODE(Exception):

    def __init__(self, unit_ident: str) -> None:
        self.unit_ident = unit_ident

    def __str__(self) -> str:
        return 'ProcUnit ' + self.unit_ident + ' is deny jobs'


# Concrete ProcUnits

class JobProcUnit(ProcUnit):
    """ ProcUnit to process job from server """

    def __init__(self, ident: str) -> None:
        ProcUnit.__init__(self, ident)
        self._config = configs.config
        self._job_refs = {}  # type: Dict[str, subprocess.Popen]

    async def reset(self) -> None:
        return

    async def _do_job(self, job: NewLetter) -> None:
        assert(self._config is not None)

        extra = job.getExtra()
        needPost = job.needPost()
        tid = job.getTid()
        cmds = extra['cmds']

        repo_url = self._config.getConfig("REPO_URL")
        projName = self._config.getConfig("PROJECT_NAME")
        revision = job.getContent('sn')

        commands = [
            # Go into project root
            "cd " + projName,
            # Fetch from server
            "git fetch",
            # Checkout the version
            "git checkout -f " + revision
        ] + cmds

        if not os.path.exists(projName):
            commands = ["git clone -b master " + repo_url] + commands

        # Pack all building commands into a single string
        # so all of them will be executed in the same shell
        # environment.
        cmds_str = packShellCommands(commands)

        # notify job state
        await self._notify_job_state(tid, Letter.RESPONSE_STATE_IN_PROC)

        # Doing the job
        job_ref = execute_shell(cmds_str)
        if job_ref is None:
            # Job failed need to notify master
            await self._notify_job_state(tid, Letter.RESPONSE_STATE_FAILURE)
            return

        # If already exists then cover
        # the old one with the new.
        self._job_refs[tid] = job_ref

        # Wait for the job
        while True:
            ret_code = job_ref.wait()

            # Error code handle
            if ret_code != 0:
                if ret_code != 128:
                    await self._notify_job_state(
                        tid, Letter.RESPONSE_STATE_FAILURE)
                break
            else:
                break

        # Transfer job result to Target destination
        # if the job need a post-processing then send
        # to Poster as a PostProvider otherwise to Master.
        if needPost == 'True':
            await self._job_result_result_transfer("Poster", job)
        else:
            await self._job_result_result_transfer("Master", job)

        # Cleanup
        shutil.rmtree(projName)

    async def _job_result_result_transfer(self, target: str,
                                          job: NewLetter) -> None:

        assert(self._output_space is not None)

        extra = job.getExtra()
        tid = job.getTid()
        result_path = extra['resultPath']
        version = job.getContent('vsn')
        mid = job.getMenu()
        fileName = result_path.split(pathSeperator())[-1]

        result_file = open(result_path, "rb")

        for line in result_file:
            line_bin = BinaryLetter(
                tid=tid, bStr=line, menu=mid,
                parent=version, fileName=fileName)
            line_bin.setHeader("linkid", target)

            await self._output_space.put(line_bin)

        end_bin = BinaryLetter(tid=tid, bStr=b"", menu=mid,
                               parent=version, fileName=fileName)
        end_bin.setHeader("linkid", target)
        await self._output_space.put(end_bin)

    async def _notify_job_state(self, tid: str, state: str) -> None:
        assert(self._config is not None)
        await self._output_space.put(  # type: ignore
            ResponseLetter(self._config.getConfig('WORKER_NAME'), tid, state))

    async def run(self) -> None:

        assert(self._config is not None)
        assert(self._output_space is not None)
        assert(self._channel is not None)

        while True:
            job = cast(NewLetter, await self.job_retrive())

            if not isinstance(job, NewLetter):
                continue

            # Notify components who intrest JobProcUnit
            # is working.
            await self._channel.update_and_notify('isProcessing', 'true')

            await self._do_job(job)


class PostProcUnit(ProcUnit):

    def __init__(self, ident: str) -> None:
        ProcUnit.__init__(self, ident)

    async def reset(self) -> None:
        return

    async def run(self) -> None:
        pass
