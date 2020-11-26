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
import manager.master.configs as config
import client.client as Client

from manager.models import Jobs
from typing import Dict, Any, Tuple
from manager.master.dispatcher import Dispatcher
from manager.master.job import Job
from manager.master.exceptions import Job_Command_Not_Found, Job_Bind_Failed
from manager.master.build import Build, BuildSet
from manager.master.task import SingleTask, PostTask, Task
from manager.basic.endpoint import Endpoint
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from manager.basic.mmanager import Module
from client.messages import JobInfoMessage, JobStateChangeMessage, \
    JobFinMessage, JobFailMessage


JobCommandPrefix = "JOB_COMMAND_"


def prepend_prefix(prefix: str, ident: str) -> str:
    return prefix + "_" + ident


class JobMaster(Endpoint, Module):

    def __init__(self) -> None:
        Endpoint.__init__(self)
        Module.__init__(self, "JobMaster")

        self._jobs = {}  # type: Dict[str, Job]
        self._config = config.config

        self._channel_layer = get_channel_layer()
        self._loop = asyncio.get_running_loop()

    async def begin(self) -> None:
        return

    async def cleanup(self) -> None:
        return

    def new_job(self, job: Job) -> None:
        self._loop.create_task(self.do_job(job))

    async def do_job(self, job: Job) -> None:

        if job.jobid in self._jobs:
            return None
        else:
            self._jobs[job.jobid] = job

        try:
            # Dispatch job
            await self._do_job(job)

            # Notify to client
            await self.client_notify(
                str(JobInfoMessage(
                    job.jobid,
                    [t.id() for t in job.tasks()],
                    Task.STATE_STR_MAPPING[Task.STATE_PREPARE]
                ))
            )

            # Store Job into database
            await database_sync_to_async(
                Jobs.objects.create
            )(jobid=job.jobid)
        except Exception as e:
            print(e)

    async def _do_job(self, job: Job) -> None:
        """
        Bind a Job with a command then dispatch
        to Workers.
        """

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
            await self.client_notify(str(job))

    async def handle(self, msg: Any) -> None:
        """
        Peer should notify to JobMaster that
        which job's state is change.

        STATE should be str type.
        """
        print("JobMaster:" + str(msg))
        taskid, state = msg  # type: Tuple[str, str]

        jobid = taskid.split("_")[0]
        taskid = taskid[taskid.find("_")+1:]

        # Notify Job's state to client.
        await self.client_notify(
            str(JobStateChangeMessage(jobid, taskid, state))
        )

        # Maintain the Job's state
        await self._job_maintain(jobid, state)

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
            st = SingleTask(prepend_prefix(job.jobid, build.getIdent()),
                            sn=sn,
                            revision=vsn,
                            build=build,
                            needPost='true',
                            extra={})
            st.job = job
            job.addTask(build.getIdent(), st)

        # Build PostTask
        st_idents = [prepend_prefix(job.jobid, build.getIdent())
                     for build in bs.getBuilds()]

        merge_command = bs.getMerge()
        pt = PostTask(job.jobid, job.get_info('vsn'), st_idents, merge_command)
        pt.job = job
        job.addTask(job.jobid, pt)

    def _bind_build(self, job: Job, cmd: Dict) -> None:
        # Job Command is a Build
        build = Build(job.cmd_id, cmd)

        st = SingleTask(prepend_prefix(job.jobid, build.getIdent()),
                        sn=job.get_info('vsn'),
                        revision=job.get_info('sn'),
                        build=build,
                        extra={})
        job.addTask(build.getIdent(), st)

    def exists(self, jobid: str) -> bool:
        return jobid in self._jobs

    async def client_notify(self, text: str) -> None:
        print(Client.clients)
        for client in Client.clients.values():
            await self._channel_layer.send(client.id, {
                "type": "job.msg",
                "text": text
            })

    async def _job_maintain(self, jobid: str, state: str) -> None:
        """
        Maintain Fin Jobs and Fail Jobs.
        """
        text_str = ""

        if state == Task.STATE_STR_MAPPING[Task.STATE_FINISHED]:
            # Setup notify content of client notification.
            text_str = str(JobFinMessage(jobid))
        elif state == Task.STATE_STR_MAPPING[Task.STATE_FAILURE]:
            # Cancel Job, cause a task of the job is failure.
            # need to cancel all tasks of the job to make sure
            # the consistency of tasks of a job is statisfied.
            await self.cancel_job(jobid)

            text_str = str(JobFailMessage(jobid))
        else:
            return

        # Notify to client
        await self.client_notify(text_str)

        # Remove Job from JobMaster
        if self._jobs[jobid].is_fin():
            del self._jobs[jobid]

            # Remove Job from database
            job_db = await database_sync_to_async(
                Jobs.objects.filter
            )(jobid=jobid)

            await database_sync_to_async(
                job_db.delete
            )()
