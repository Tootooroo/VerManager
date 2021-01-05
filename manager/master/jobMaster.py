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

import asyncio
import traceback
import manager.master.configs as config

from manager.models import Jobs, JobInfos, Informations, \
    JobHistory, TaskHistory
from typing import Dict, Any, Tuple, Optional, cast, List
from manager.master.dispatcher import Dispatcher
from manager.master.job import Job
from manager.master.exceptions import Job_Command_Not_Found, Job_Bind_Failed
from manager.master.build import Build, BuildSet
from manager.master.task import SingleTask, PostTask, Task
from manager.basic.endpoint import Endpoint
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from manager.master.job import VerResult
from manager.basic.mmanager import Module

from client.messages import JobInfoMessage, JobStateChangeMessage, \
    JobFinMessage, JobFailMessage, JobBatchMessage, JobHistoryMessage, \
    JobAllResultsMessage, JobNewResultMessage

from manager.master.msgCell import MsgSource
from client.messages import Message

JobCommandPrefix = "JOB_COMMAND_"


def prepend_prefix(prefix: str, ident: str) -> str:
    return prefix + "_" + ident


def task_prefix_trim(ident: str) -> Optional[str]:
    begin_pos = ident.find("_") + 1
    if begin_pos + 1 > len(ident):
        return None

    return ident[begin_pos:]


def trim_prefix_of_tasks(tasks: List[Task]) -> None:
    for t in tasks:
        trim_id = task_prefix_trim(t.taskId)
        if trim_id is not None:
            t.taskId = trim_id


def task_gen_helper(id: str, state: str) -> Task:
    t = Task(id, "", "")
    t.state = int(state)

    return t


def job_to_jobInfoMsg(job: Job) -> JobInfoMessage:
    task = [
        [
            # TaskID
            cast(str, task_prefix_trim(t.id())),
            # TaskState
            Task.STATE_STR_MAPPING[t.taskState()]
        ]
        for t in job.tasks()
    ]
    return JobInfoMessage(str(job.unique_id), job.jobid, task)


class JobMasterMsgSrc(MsgSource):

    jobs = None  # type: Optional[Dict[str, Job]]

    async def gen_msg(self, args: List[str] = None) -> Optional[Message]:

        assert(args is not None)

        if self.jobs is None:
            return None

        try:
            f = getattr(self, "query_" + args[0])
            return await f(args)
        except AttributeError:
            return None

    async def query_processing(self, args: List[str]) -> Optional[Message]:
        msgs = []  # type: List[Message]

        for job in self.jobs.values():  # type: ignore
            job_info_msg = job_to_jobInfoMsg(job)
            msgs.append(job_info_msg)

        return JobBatchMessage(msgs)

    async def query_history(self, *args) -> Optional[Message]:
        jobs = []  # type: List[Job]

        jobs_history = await database_sync_to_async(
            JobHistory.objects.all
        )()

        jobs_history_list = await database_sync_to_async(
            list
        )(jobs_history)

        for job in jobs_history_list:
            task_history = await database_sync_to_async(
                TaskHistory.objects.filter
            )(jobhistory=job)

            task_history_list = await database_sync_to_async(
                list
            )(task_history)

            tasks = {
                t.task_name: task_gen_helper(t.task_name, t.state)
                for t in task_history_list
            }

            job_ = Job(job.job, "", {})
            job_.unique_id = job.unique_id
            job_._tasks = tasks

            jobs.append(job_)

        return JobHistoryMessage(jobs)

    async def query_files(self, *args) -> Optional[Message]:

        # Retrieve from database
        ver_results = await JobHistory.jobHistory_transformation(
            lambda job: VerResult(job.unique_id, job.job, job.filePath)
        )
        if len(ver_results) == 0:
            return None

        # Generate message
        return JobAllResultsMessage(ver_results)


class JobMaster(Endpoint, Module):

    M_NAME = "JobMaster"

    def __init__(self) -> None:
        Endpoint.__init__(self)
        Module.__init__(self, self.M_NAME)

        self._jobs = {}  # type: Dict[str, Job]
        self._config = config.config

        self._channel_layer = get_channel_layer()
        self._loop = asyncio.get_running_loop()

        # Setup source
        self.source = JobMasterMsgSrc(self.M_NAME)
        self.source.jobs = self._jobs

        # Lock to prevent race conditon of
        # unique id access.
        self._lock = asyncio.Lock()

    async def begin(self) -> None:
        return

    async def cleanup(self) -> None:
        return

    async def _job_record(self, job: Job) -> None:
        # Job record
        job_db = await database_sync_to_async(
            Jobs.objects.create
        )(unique_id=job.unique_id, jobid=job.jobid, cmdid=job.cmd_id)

        # Job info record
        infos = job.infos()
        for key in job.infos():
            await database_sync_to_async(
                JobInfos.objects.create
            )(jobs=job_db, info_key=key,
              info_value=infos[key])

    async def _job_record_rm(self, unique_id: str) -> None:
        # Remove Job from database
        job_db = await database_sync_to_async(
            Jobs.objects.filter
        )(unique_id=unique_id)

        await database_sync_to_async(
            job_db.delete
        )()

    def new_job(self, job: Job) -> None:
        self._loop.create_task(self.do_job(job))

    async def do_job(self, job: Job) -> None:

        if not job.is_valid():
            return None

        try:
            # Dispatch job
            await self._do_job(job)

            # Notify to client
            #
            # Task's ident is already check by upper
            # so assume that task_prefix_trim must not
            # return None.
            tasks = []  # type: List[List[str]]
            for t in job.tasks():
                id = cast(str, task_prefix_trim(t.id()))
                state = Task.STATE_STR_MAPPING[t.taskState()]
                tasks.append([id, state])

            msg = JobInfoMessage(str(job.unique_id), job.jobid, tasks)
            self.source.real_time_msg(msg, {"is_broadcast": "ON"})

            # Store Job into database
            await self._job_record(job)
        except Exception as e:
            print(e)

    async def _do_job(self, job: Job) -> None:
        """
        Bind a Job with a command then dispatch
        to Workers.
        """

        # Store job with assigned unique id
        # to make sure no conflict.
        await self.assign_unique_id(job)
        self._jobs[str(job.unique_id)] = job

        # Bind Job with a job command
        self.bind(job)

        # Assign job to another module typically
        # is Dispatcher.
        for task in job.tasks():
            await self.peer_notify((Dispatcher.ENDPOINT_DISPATCH, task))

        job.state = Job.STATE_IN_PROCESSING

    async def cancel_job(self, jobid: str) -> None:
        tasks = self._jobs[jobid].tasks()

        for task in tasks:
            await self.peer_notify((Dispatcher.ENDPOINT_CANCEL, task.id()))

    async def assign_unique_id(self, job: Job) -> None:
        """
        Read the available unique id from DB then
        assign it to Job and update DB.
        """
        async with self._lock:

            try:
                info = await database_sync_to_async(
                    Informations.objects.get
                )(idx=0)

                job.set_unique_id(info.avail_job_id)

                # Update unique id
                # avail_job_id can grow up to 9223372036854775807,
                # so it will no likely to overflow in normal scence.
                info.avail_job_id += 1
                await database_sync_to_async(
                    info.save
                )()
            except Exception:
                traceback.print_exc()

    async def _recovery(self) -> None:
        """
        Recovery Jobs that does not done in
        previous boot time.
        """

        jobs = await database_sync_to_async(
            Jobs.objects.all
        )()

        # Is there some jobs that need to recover.
        if len(jobs) == 0:
            return

        jobs = await database_sync_to_async(
            jobs.order_by
        )('-dateTime')

        for job in jobs:
            await self._do_job(job)

    async def handle(self, msg: Any) -> None:
        """
        Peer should notify to JobMaster that
        which job's state is change.

        STATE should be str type.
        """
        taskid, state = msg  # type: Tuple[str, str]

        unique_id = taskid.split("_")[0]
        taskid = taskid[taskid.find("_")+1:]

        if unique_id not in self._jobs:
            return
        else:
            jobid = self._jobs[unique_id].jobid

        # Notify Job's state to client.
        self.source.real_time_msg(
            JobStateChangeMessage(unique_id, jobid, taskid, state), {
                "is_broadcast": "ON"
            }
        )

        # Maintain the Job's state
        await self._job_maintain(unique_id, state)

    def bind(self, job: Job) -> None:
        """
        Bind a job with a Job command that defined in
        configuration file, after binded a set of tasks
        will be generated and store in to the job.
        """
        # Configuration is needed
        assert(self._config is not None)

        job_command = self._config.getConfig(JobCommandPrefix + job.cmd_id)

        # Job Command does not exists.
        if job_command is None:
            raise Job_Command_Not_Found(job.cmd_id)

        # To check that is job command a build or buildset.
        if 'Builds' in job_command:
            # Job Command is a BuildSet
            self._bind_buildset(job, job_command)
        else:
            # Job Command is a Build
            self._bind_build(job, job_command)

    def _bind_buildset(self, job: Job, cmd: Dict) -> None:
        bs = BuildSet(cmd)

        # Build SingleTask
        sn, vsn = job.get_info('sn'), job.get_info('vsn')
        if sn is None or vsn is None:
            raise Job_Bind_Failed()

        for build in bs.getBuilds():
            # Replace variable in config.
            build.varAssign([("<version>", vsn)])

            st = SingleTask(
                prepend_prefix(str(job.unique_id), build.getIdent()),
                sn=sn,
                revision=vsn,
                build=build,
                needPost='true',
                extra={}
            )
            st.job = job
            job.addTask(build.getIdent(), st)

        # Build PostTask
        st_idents = [prepend_prefix(str(job.unique_id), build.getIdent())
                     for build in bs.getBuilds()]

        merge_command = bs.getMerge()
        merge_command.varAssign([("<version>", vsn)])
        print(merge_command.getCmds())
        print(merge_command.getOutput())
        pt = PostTask(
            prepend_prefix(str(job.unique_id), job.jobid),
            vsn,
            st_idents,
            merge_command
        )
        pt.job = job
        job.addTask(job.jobid, pt)

    def _bind_build(self, job: Job, cmd: Dict) -> None:
        # Job Command is a Build
        build = Build(job.cmd_id, cmd)

        sn, vsn = job.get_info('sn'), job.get_info('vsn')
        if sn is None or vsn is None:
            raise Job_Bind_Failed()

        st = SingleTask(prepend_prefix(job.jobid, build.getIdent()),
                        sn=vsn,
                        revision=sn,
                        build=build,
                        extra={})
        job.addTask(build.getIdent(), st)

    def exists(self, jobid: str) -> bool:
        return jobid in self._jobs

    async def _record_history(self, job: Job) -> None:

        # No file is generated from an
        # unfinished job.
        if job.is_fin() and job.job_result is not None:
            filePath = job.job_result
        else:
            filePath = "None"

        jobHistory = JobHistory(
            unique_id=job.unique_id,
            job=job.jobid,
            filePath=filePath
        )

        await database_sync_to_async(
            jobHistory.save
        )()

        for task in job.tasks():
            taskHistory = TaskHistory(
                jobhistory=jobHistory,
                task_name=task_prefix_trim(task.id()),
                state=task.taskState()
            )
            await database_sync_to_async(
                taskHistory.save
            )()

    async def _job_maintain(self, jobid: str, state: str) -> None:
        """
        Maintain Fin Jobs and Fail Jobs.
        """
        job = self._jobs[jobid]

        if state == Task.STATE_STR_MAPPING[Task.STATE_FINISHED]:
            # If Job is finished
            if job.is_fin():
                await self._job_maintain_terminate(jobid, JobFinMessage(jobid))

            # A Fin job's job_result field must not none
            if job.job_result is None:
                return

            vr = VerResult(str(job.unique_id), job.jobid, job.job_result)
            self.source.real_time_broadcast(JobNewResultMessage(vr), {})

        elif state == Task.STATE_STR_MAPPING[Task.STATE_FAILURE]:
            # Cancel Job, cause a task of the job is failure.
            # need to cancel all tasks of the job to make sure
            # the consistency of tasks of a job is statisfied.
            await self.cancel_job(jobid)
            await self._job_maintain_terminate(jobid, JobFailMessage(jobid))

    async def _job_maintain_terminate(self, jobid: str, msg: Message) -> None:
        job = self._jobs[jobid]
        await self._record_history(job)

        del self._jobs[jobid]
        await self._job_record_rm(jobid)

        # Notify to client
        self.source.real_time_msg(msg, {
            "is_broadcast": "ON"
        })

        trim_prefix_of_tasks(job.tasks())
        self.source.real_time_msg(JobHistoryMessage([job]), {
            "is_broadcast": "ON"
        })
