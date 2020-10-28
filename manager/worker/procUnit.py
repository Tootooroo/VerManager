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

import os
import platform
import tempfile
import abc
import asyncio
import manager.worker.configs as configs

from datetime import datetime
from typing import Optional, cast, Dict, BinaryIO, List, \
    Callable, IO
from manager.basic.letter import Letter
from .proc_common import Output
from .channel import ChannelEntry

# Need by JobProcUnit
import subprocess
import shutil
from manager.basic.util import packShellCommands, execute_shell,\
    pathSeperator, execute_shell_until_complete
from manager.basic.letter import NewLetter, ResponseLetter,\
    BinaryLetter
from manager.worker.connector import Link
from manager.basic.info import Info

# Need by PostProcUnit
from manager.basic.letter import PostTaskLetter


UNIT_TYPE_JOB_PROC = 0
UNIT_TYPE_POST_PROC = 1


class CommandExecutor:

    def __init__(self, cmds: List[str] = None) -> None:
        self._cmds = cmds  # type: Optional[List[str]]
        self._max_stucked_time = 3600
        self._running = False
        self._last_stucked = None  # type: Optional[datetime]
        self._last_pos = 0
        self._ret = 0
        self._ref = None  # type: Optional[subprocess.Popen]

    def _reset(self) -> None:
        self._running = False
        self._last_pos = 0
        self._last_stucked = None

    def stop(self) -> None:
        if self._ref is not None:
            self._ref.terminate()
            self._reset()

    async def run(self) -> int:

        if self._cmds is None:
            return -1

        command_str = packShellCommands(self._cmds)
        output = tempfile.TemporaryFile("w")

        self._running = True

        ref = execute_shell(command_str, stdout=output)
        if ref is None:
            self._ret = -1
            self._reset()
            return -1
        else:
            self._ref = ref

        while True:
            # Check whether the command done
            ret = ref.poll()
            if ret is not None:
                self._ret = ret
                break

            # Check whether the command is stucked
            if self.isStucked(output):
                self._ret = -1
                ref.terminate()
                break

            await asyncio.sleep(3)

        self._ref = None
        self._running = False

        if ret is None:
            return -1

        self._reset()
        return ret

    def return_code(self) -> int:
        return self._ret

    def isRunning(self) -> bool:
        return self._running

    def isStucked(self, output: IO[str]) -> bool:
        current_pos = output.tell()

        # Stucked from last position
        if current_pos == self._last_pos:
            current = datetime.utcnow()
            if self._last_stucked is None:
                self._last_stucked = datetime.utcnow()
            else:
                # Stucked timeout
                return (current - self._last_stucked).seconds > \
                    self._max_stucked_time
        else:
            if self._last_stucked is not None:
                self._last_stucked = None
            self._last_pos = current_pos

        return False

    def getStuckedLimit(self) -> int:
        return self._max_stucked_time

    def setStuckedLimit(self, limit: int) -> None:
        self._max_stucked_time = limit

    def setCommand(self, cmds: List[str]) -> None:
        self._cmds = cmds


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

    def __init__(self, ident: str, type: int) -> None:
        self._unitIdent = ident
        self._type = type

        self._state = self.STATE_STOP

        self._install = False

        self._normal_space = asyncio.Queue(4096)  # type: asyncio.Queue[Letter]
        self._hightwaterlevel = self._normal_space.maxsize * (2/3)

        # Queue that hold letter generate by ProcUnit
        # should be transfered to master.
        # Will be setup while install into Processor.
        self._output_space = None  # type: Optional[Output]

        self._start_at = datetime.utcnow()
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

            if self._normal_space.qsize() > self._hightwaterlevel:
                raise PROC_UNIT_HIGHT_OVERLOAD(self._unitIdent)

        except asyncio.QueueFull:
            raise PROC_UNIT_IS_IN_DENY_MODE(self._unitIdent)

    async def job_retrive(self, timeout=None) -> Letter:
        return await asyncio.wait_for(
            self._normal_space.get(), timeout=timeout)

    def msg_gen(self) -> None:
        if self._channel is None:
            return

        self._channel.update('state', self._state)
        self._channel.update('ident', self._unitIdent)
        self._channel.update('failureCount', 0)

        uptime = (datetime.utcnow() - self._start_at).seconds
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
        self._output_space.send_nowait(letter)


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
async def job_result_transfer(target: str, job: NewLetter, output: Output) -> None:
    extra = job.getExtra()
    tid = job.getTid()
    version = job.getContent('vsn')
    build_dir = cast(Info, configs.config).getConfig("BUILD_DIR")

    projName = cast(Info, configs.config).getConfig("PROJECT_NAME")
    result_path = build_dir + "/" + projName + '/' + extra['resultPath']
    fileName = result_path.split(pathSeperator())[-1]

    await output.sendfile(target, result_path, tid, version, fileName)
    # await do_job_result_transfer(
    #    result_path, tid, target, version, fileName,
    #    send_rtn)


async def do_job_result_transfer(path, tid: str, linkid: str,
                                 version: str, fileName: str,
                                 send_rtn: Callable) -> None:
    result_file = open(path, "rb")

    for line in result_file:
        line_bin = BinaryLetter(
            tid=tid, bStr=line, parent=version,
            fileName=fileName)
        line_bin.setHeader("linkid", linkid)

        await send_rtn(line_bin)

    end_bin = BinaryLetter(
        tid=tid, bStr=b"", parent=version, fileName=fileName)
    end_bin.setHeader("linkid", linkid)
    await send_rtn(end_bin)


async def job_result_transfer_check_link(output: Output, linkid: str, job: NewLetter,
                                         send_rtn: Callable, timeout=None) -> None:
    if timeout is not None:
        # Wait until link rebuild or timeout
        while output.link_state(linkid) != Link.CONNECTED:
            await asyncio.sleep(1)
            timeout = timeout - 1

            if timeout < 0:
                raise asyncio.exceptions.TimeoutError()

    await job_result_transfer(linkid, job, output)


async def job_result_transfer_check_link_forever(
        output: Output, linkid: str, job: NewLetter,
        send_rtn: Callable, timeout=None) -> None:

    try:
        await job_result_transfer_check_link(output, linkid, job,
                                             send_rtn, timeout=timeout)
    except (ConnectionError, BrokenPipeError):
        asyncio.get_running_loop().create_task(
            job_result_transfer_check_link_forever(
                output, linkid, job, send_rtn, timeout=timeout)
        )

    except asyncio.exceptions.TimeoutError:
        return


async def notify_job_state(tid: str, state: str, rtn: Callable) -> None:
    assert(configs.config is not None)

    # Get worker name
    workerName = configs.config.getConfig('WORKER_NAME')
    if workerName == '':
        workerName = platform.node()

    response = ResponseLetter(workerName, tid, state)
    response.setHeader('linkid', 'Master')
    await rtn(response)


class JobProcUnitProto(ProcUnit):

    def __init__(self, ident: str, type: int) -> None:
        ProcUnit.__init__(self, ident, type)

    @abc.abstractmethod
    async def cancel(self, tid: str) -> None:
        """ Cancel a job specified by tid """

    @abc.abstractmethod
    def exists(self, tid: str) -> bool:
        """ Is a job processed on a JobProcUnit """


class PostProcUnitProto(ProcUnit):

    def __init__(self, ident: str, type: int) -> None:
        ProcUnit.__init__(self, ident, type)

    @abc.abstractmethod
    async def cancel(self, tid: str) -> None:
        """ Cancel a post specified by tid """

    @abc.abstractmethod
    def exists(self, tid: str) -> bool:
        """ Is a post processed on a PostProcUnit """


class JobProcUnit(JobProcUnitProto):
    """
    ProcUnit to process job from server

    JobProcUnit process only one job at a time.
    """

    def __init__(self, ident: str) -> None:
        JobProcUnitProto.__init__(self, ident, UNIT_TYPE_JOB_PROC)
        self._config = configs.config
        self._isInWork = False  # type: bool
        self._inProcTid = ""  # type: str
        self._cmd_executor = CommandExecutor()

    async def reset(self) -> None:
        """
        Stop in processing jobs
        """
        # Clear request space
        self._normal_space._queue.clear()
        await self.stopCurrentJob()

    async def stopCurrentJob(self) -> None:
        if self._cmd_executor.isRunning():
            self._cmd_executor.stop()
            self._isInWork = False

            if self._channel is not None:
                await self._channel.update_and_notify('isProcessing', 'false')

    async def cancel(self, tid: str) -> None:
        """ Cancel a job """
        if tid == self._inProcTid:
            # The job is in processing
            await self.stopCurrentJob()
        else:
            # The job is in queue
            self._remove_job_from_queue(tid)

    def exists(self, tid: str) -> bool:
        if self._inProcTid == tid:
            return True
        elif self._find_job_in_queue(tid) is not None:
            return True

        return False

    def _remove_job_from_queue(self, tid: str) -> None:
        job = self._find_job_in_queue(tid)
        if job is not None:
            if self._normal_space.qsize() > 0:
                try:
                    self._normal_space._queue.remove(job)
                except ValueError:
                    pass

    def _find_job_in_queue(self, tid: str) -> Optional[Letter]:
        if self._normal_space.qsize() == 0:
            return None

        for job in self._normal_space._queue:
            job_tid = cast(NewLetter, job).getTid()

            if tid == job_tid:
                return job

        return None

    async def _do_job(self, job: NewLetter) -> None:
        assert(self._config is not None)

        extra = job.getExtra()
        needPost = job.needPost()
        tid = job.getTid()
        cmds = extra['cmds']
        build_dir = self._config.getConfig('BUILD_DIR')

        repo_url = self._config.getConfig("REPO_URL")
        projName = self._config.getConfig("PROJECT_NAME")
        revision = job.getContent('sn')

        # Check is clean
        if not os.path.exists(build_dir+"/"+projName):
            if self.cleanup() is False:
                # Job unable to begin from dirty state.
                self._notify_job_state(tid, Letter.RESPONSE_STATE_FAILURE)

        commands = [
            "cd " + build_dir,
            # Clone
            "git clone -b master " + repo_url,
            # Go into project root
            "cd " + projName,
            # Fetch from server
            "git fetch",
            # Checkout the version
            "git checkout -f " + revision
        ] + cmds

        # notify job state
        await self._notify_job_state(tid, Letter.RESPONSE_STATE_IN_PROC)

        # Run commands
        self._cmd_executor.setCommand(commands)
        ret_code = await self._cmd_executor.run()

        # Error code handle
        if ret_code != 0:
            if ret_code != 128:
                # Cleanup
                self.cleanup()
                await self._notify_job_state(
                    tid, Letter.RESPONSE_STATE_FAILURE)
                return

        # Transfer job result to Target destination
        # if the job need a post-processing then send
        # to Poster as a PostProvider otherwise to Master.
        if needPost == 'true':
            linkid = "Poster"
        else:
            linkid = "Master"

        try:
            await self._job_result_transfer(linkid, job)
        except Exception:
            self.cleanup()
            await self._notify_job_state(tid, Letter.RESPONSE_STATE_FAILURE)
            return

        # Cleanup
        # Cleanup should be done before notify master job is finished.
        self.cleanup()
        await self._notify_job_state(tid, Letter.RESPONSE_STATE_FINISHED)

    def cleanup(self) -> bool:
        build_dir = cast(Info, self._config).getConfig('BUILD_DIR')
        projName = cast(Info, self._config).getConfig('PROJECT_NAME')

        path = build_dir+"/"+projName

        if platform.system() == "Windows":
            ret = os.system("powershell.exe Remove-Item -Recurse -Force " + path)
            if ret != 0:
                return False
        else:
            try:
                # Ignore FileNotFoundError
                # cause there is noting to cleanup.
                shutil.rmtree(path)
            except FileNotFoundError:
                return False

        return True

    async def _job_result_transfer(self, target: str,
                                   job: NewLetter) -> None:

        assert(self._output_space is not None)
        await job_result_transfer(target, job, self._output_space)

    async def _notify_job_state(self, tid: str, state: str) -> None:
        output = cast(Output, self._output_space)
        await notify_job_state(tid, state, output.send)

    def msg_gen(self) -> None:
        """
        Update info on channel
        """
        if self._channel is None:
            return

        # Basic info generate
        ProcUnit.msg_gen(self)

        # JobProcUnit's info
        if self._isInWork:
            inWork = 'true'
        else:
            inWork = 'false'

        self._channel.update('isProcessing', inWork)

    async def run(self) -> None:
        # Resources need by JobProcUnit
        assert(self._output_space is not None)
        assert(self._channel is not None)
        assert(self._config is not None)

        # Create build directory
        build_dir = self._config.getConfig('BUILD_DIR')
        if not os.path.exists(build_dir):
            os.mkdir(build_dir)

        # Channel information init
        self.msg_gen()

        while True:
            job = cast(NewLetter, await self.job_retrive())

            if not isinstance(job, NewLetter):
                continue

            # Update channel data
            await self._channel.update_and_notify('isProcessing', 'true')

            self._inProcTid = job.getTid()

            # Do job
            await self._do_job(job)

            # Update channel data
            await self._channel.update_and_notify('isProcessing', 'false')


class Frag:

    def __init__(self, ident: str) -> None:
        self.ident = ident
        self.filename = ""
        self.fd = None  # type: Optional[BinaryIO]
        self.ready = False


class Post:

    def __init__(self, ident: str, frags: List[str], cmd: List[str],
                 result_path: str, version: str) -> None:

        assert(configs.config is not None)

        self._cmd_executor = CommandExecutor()
        self._ident = ident
        self._frags = {frag: Frag(frag) for frag in frags}  \
            # type: Dict[str, Frag]

        self._result_path = result_path
        # Additional process if it's a relative path
        if self._result_path[0] is not pathSeperator():
            post_dir = configs.config.getConfig('POST_DIR')
            # POST_DIR must be seted
            if post_dir == "":
                raise Exception
            self._result_path = os.path.join(post_dir, version, result_path)

        self._cmd = cmd
        self._version = version

    def ident(self) -> str:
        return self._ident

    def version(self) -> str:
        return self._version

    async def do(self) -> str:
        assert(configs.config is not None)

        self._cmd.insert(0, "cd Post/" + self._version)
        self._cmd_executor.setCommand(self._cmd)
        await self._cmd_executor.run()

        if os.path.exists(self._result_path):
            return self._result_path
        else:
            return ""

    def isInWork(self) -> bool:
        return self._cmd_executor.isRunning()

    def stop(self) -> None:
        """
        Stop execution
        """
        if self._cmd_executor.isRunning():
            self._cmd_executor.stop()

    def set_frag_fileName(self, frag_id: str, fileName: str) -> None:
        self._frags[frag_id].filename = fileName

    def get_frag_fileName(self, frag_id: str) -> str:
        return self._frags[frag_id].filename

    def set_frag_fd(self, frag_id: str, fd: BinaryIO) -> None:
        self._frags[frag_id].fd = fd

    def get_frag_fd(self, frag_id: str) -> Optional[BinaryIO]:
        return self._frags[frag_id].fd

    def set_frag_ready(self, frag_id: str) -> None:
        self._frags[frag_id].ready = True

    def cleanup(self) -> None:
        assert(configs.config is not None)

        post_dir = configs.config.getConfig('POST_DIR')

        try:
            shutil.rmtree(os.path.join(post_dir, self._version))
        except FileNotFoundError:
            pass

    def ready(self) -> bool:
        isReady = True

        for frag in self._frags.values():
            isReady &= frag.ready

        return isReady


class PostProcUnit(PostProcUnitProto):

    def __init__(self, ident: str) -> None:
        PostProcUnitProto.__init__(self, ident, UNIT_TYPE_POST_PROC)
        self._posts = {}  # type: Dict[str, Post]

        assert(configs.config is not None)
        self._post_dir = configs.config.getConfig('POST_DIR')

    async def reset(self) -> None:
        """
        Cancel all Posts
        """
        for pid in self._posts:
            self.cancel(pid)

    async def cancel(self, tid: str) -> None:
        """
        Findout from _posts, stop if in work, and remove.
        """
        if tid in self._posts:
            post = self._posts[tid]
            if post.isInWork():
                post.stop()
            post.cleanup()
            del self._posts[tid]

    def exists(self, tid: str) -> bool:
        """
        Is a post in deal by the PostProcUnit.
        """
        return tid in self._posts

    async def _frag_collect(self, letter: BinaryLetter) -> None:
        assert(configs.config is not None)

        version = letter.getParent()
        if version not in self._posts:
            return

        tid = letter.getTid()
        post = self._posts[version]

        fd = post.get_frag_fd(tid)
        if fd is None:
            path = os.path.join(self._post_dir, version, letter.getFileName())
            fd = open(path, "wb")
            post.set_frag_fd(tid, fd)
            post.set_frag_fileName(tid, letter.getFileName())

        content = letter.getContent('bytes')
        if content == b'':
            # Transfer done.
            post.set_frag_ready(tid)
            fd.close()

            if post.ready():
                await self._do_post(post)
        else:
            fd.write(content)

    async def _do_post(self, post: Post) -> None:

        assert(self._output_space is not None)
        path = await post.do()

        if path != '':
            # Success
            fileName = path.split(pathSeperator())[-1]

            # await do_job_result_transfer(
            #     path, post.ident(), "Master", post.version(),
            #     fileName, self._output_space.send
            # )

            await self._output_space.sendfile(
                "Master", path, post.ident(), post.version(), fileName)

            # Cleanup
            post.cleanup()
            # Success
            await self._notify_job_state(
                post.ident(), Letter.RESPONSE_STATE_FINISHED)
        else:
            # Cleanup
            post.cleanup()
            # Failed
            await self._notify_job_state(
                post.ident(), Letter.RESPONSE_STATE_FAILURE)

    async def _notify_job_state(self, tid: str, state: str) -> None:
        output = cast(Output, self._output_space)
        await notify_job_state(tid, state, output.send)

    async def _new_post(self, letter: PostTaskLetter) -> None:
        ident = letter.getIdent()
        if ident in self._posts:
            return

        version = letter.getVersion()
        post = Post(ident, letter.frags(), letter.getCmds(),
                    letter.getOutput(), version)

        self._posts[version] = post

        path = self._post_dir+"/"+version
        if not os.path.exists(path):
            os.mkdir(path)

    async def run(self) -> None:

        assert(self._output_space is not None)
        assert(self._channel is not None)
        # Directory Frags is used to contain all
        # Binaries that need by Posts
        if not os.path.exists("./Post"):
            os.mkdir("./Post")

        while True:
            try:
                job = await self.job_retrive()

                if isinstance(job, BinaryLetter):
                    await self._frag_collect(job)
                elif isinstance(job, PostTaskLetter):
                    await self._new_post(job)
            except Exception as e:
                print(e)
