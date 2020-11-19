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
from manager.master.job import Job
from manager.master.exceptions import Job_Command_Not_Found
from manager.master.build import Build, BuildSet
from manager.master.task import SingleTask, PostTask, Task
from manager.basic.endpoint import Endpoint
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async


JobCommandPrefix = "JOB_COMMAND_"


def prepend_prefix(prefix: str, ident: str) -> str:
    return prefix + "_" + ident


class JobMaster(Endpoint):

    def __init__(self) -> None:
        Endpoint.__init__(self)

        self._jobs = {}  # type: Dict[str, Job]
        self._config = config.config

    async def doJob(self, job: Job) -> None:
        # Dispatch job
        await self._doJob(job)

        # Notify to client
        await self.notify_client(job)

        # Store Job into database
        await database_sync_to_async(
            Jobs.objects.create
        )(jobid=job.jobid)

    async def _doJob(self, job: Job) -> None:
        """
        Bind a Job with a command then dispatch
        to Workers.
        """

        if job.jobid in self._jobs:
            return None

        # Bind Job with a job command
        self.bind(job)

        # Assign job to another module typically
        # is Dispatcher.
        for task in job.tasks():
            await self.peer_notify(task)

        job.state = Job.STATE_IN_PROCESSING

    async def notify_client(self, job: Job) -> None:
        channel_layer = get_channel_layer()

        for client in Client.clients:
            await channel_layer.send(client.id, {
                "type": "job.info",
                "text": str(job)
            })

    async def handle(self, msg: Any) -> None:
        """
        Perr should notify to JobMaster that
        which job's state is change.

        STATE should be str type.
        """
        taskid, state = msg  # type: Tuple[str, str]

        jobid = taskid.split("_")[0]
        taskid = taskid[taskid.find("_")+1:]

        # To check that is the job is finished
        # if fin remove the job from database and
        # JobMaster.
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

        channel_layer = get_channel_layer()

        for client in Client.clients:
            await channel_layer.send(client.id, {
                "type": "job.state.change",
                "text": ":".join([jobid, taskid, state])
            })

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
        for build in bs.getBuilds():
            st = SingleTask(prepend_prefix(job.jobid, build.getIdent()),
                            sn=job.get_info('vsn'),
                            revision=job.get_info('sn'),
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
        job.addTask(st)

    def exists(self, jobid: str) -> bool:
        return jobid in self._jobs
