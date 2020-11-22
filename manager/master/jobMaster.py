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

    async def begin(self) -> None:
        return

    async def cleanup(self) -> None:
        return

    async def do_job(self, job: Job) -> None:
        # Dispatch job
        await self._do_job(job)

        # Notify to client
        await self.client_notify("job.info", str(job))

        # Store Job into database
        await database_sync_to_async(
            Jobs.objects.create
        )(jobid=job.jobid)

    async def _do_job(self, job: Job) -> None:
        """
        Bind a Job with a command then dispatch
        to Workers.
        """

        if job.jobid in self._jobs:
            return None
        else:
            self._jobs[job.jobid] = job

        try:
            # Bind Job with a job command
            self.bind(job)

            # Assign job to another module typically
            # is Dispatcher.
            for task in job.tasks():
                await self.peer_notify((Dispatcher.ENDPOINT_DISPATCH, task))

            job.state = Job.STATE_IN_PROCESSING
        except Job_Bind_Failed:
            # notify to client that
            # this Job is failed to dispatch.
            await self.client_notify("job.fail", job.jobid)

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
            await self.client_notify("job.info", str(job))

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
        await self._notify_job_to_client(jobid, taskid, state)

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

    async def client_notify(self, type: str, text: str) -> None:
        for client in Client.clients:
            await self._channel_layer.send(client.id, {
                "type": type,
                "text": text
            })

    async def _notify_job_to_client(self, jobid: str, taskid: str,
                                    state: str) -> None:
        job = self._jobs[jobid]
        if job.is_fin():
            # Remove Job from database
            job_db = await database_sync_to_async(
                Jobs.objects.filter
            )(jobid=jobid)

            await database_sync_to_async(
                job_db.delete
            )()

            # Remove Job from JobMaster
            del self._jobs[jobid]

        self.client_notify(
            "job.state.change",
            ":".join([jobid, taskid, state])
        )

    async def _job_maintain(self, jobid: str, state: str) -> None:
        """
        Maintain Fin Jobs and Fail Jobs.
        """
        type_str, text_str = "", ""

        if state == Task.STATE_STR_MAPPING[Task.STATE_FINISHED]:
            # Setup notify content of client notification.
            type_str = "job.fin"
            text_str = "..."
        elif state == Task.STATE_STR_MAPPING[Task.STATE_FAILURE]:
            # Cancel Job, cause a task of the job is failure.
            # need to cancel all tasks of the job to make sure
            # the consistency of tasks of a job is statisfied.
            await self.cancel_job(jobid)

            type_str = "job.fail"
            text_str = "..."
        else:
            return

        # Notify to client
        self.client_notify(type_str, text_str)

        # Remove Job from JobMaster
        del self._jobs[jobid]
