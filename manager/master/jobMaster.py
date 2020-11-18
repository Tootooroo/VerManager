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
from typing import Dict
from manager.master.job import Job
from manager.master.exceptions import Job_Command_Not_Found
from manager.master.build import Build, BuildSet
from manager.master.task import SingleTask, PostTask
from manager.master.master import get_module

JobCommandPrefix = "JOB_COMMAND_"


def prepend_prefix(prefix: str, ident: str) -> str:
    return prefix + "_" + ident


class JobMaster:

    def __init__(self) -> None:
        self._jobs = {}  # type: Dict[str, Job]
        self._config = config.config

    def doJob(self, job: Job) -> None:
        pass

    def bind(self, job: Job) -> None:
        """
        Bind a job with a Job command that defined in
        configuration file, after binded a set of tasks
        will be generated and store in to the job.
        """

        # Configuration file is needed
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
            job.addTask(st)

        # Build PostTask
        st_idents = [prepend_prefix(job.jobid, build.getIdent())
                     for build in bs.getBuilds()]

        merge_command = bs.getMerge()
        pt = PostTask(job.jobid, job.get_info('vsn'), st_idents, merge_command)
        pt.job = job
        job.addTask(pt)

    def _bind_build(self, job: Job, cmd: Dict) -> None:
        # Job Command is a Build
        build = Build(job.cmd_id, cmd)

        st = SingleTask(prepend_prefix(job.jobid, build.getIdent()),
                        sn=job.get_info('vsn'),
                        revision=job.get_info('sn'),
                        build=build,
                        extra={})
        job.addTask(st)
