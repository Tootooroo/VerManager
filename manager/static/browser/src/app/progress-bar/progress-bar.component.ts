import { Component, OnInit } from '@angular/core';
import { MessageService } from '../message.service';
import { Message } from '../message';

interface Task {
    taskid: string;
    state: string;
}

interface Job {
    jobid: string;
    tasks: { [index: string]: Task };
}


@Component({
    selector: 'app-progress-bar',
    templateUrl: './progress-bar.component.html',
    styleUrls: ['./progress-bar.component.css']
})
export class ProgressBarComponent implements OnInit {

    private jobs: { [index: string]: Job } = {};

    constructor(msg_service: MessageService) {
        msg_service.register("job.state").subscribe(msg => {
            this.job_state_message_handle(msg);
        });
    }

    ngOnInit(): void { }

    job_state_message_handle(msg: Message): void {
        let content = msg.content;
        let subtype: string;

        // Corrupted by invalid format of message is
        // not allowed.
        try {
            subtype = content['subtype'];

            switch (subtype) {
                case "change":
                    this.job_state_message_change_handle(msg);
                    break;
                case "fin":
                    this.job_state_message_fin_handle(msg);
                    break;
                case "fail":
                    this.job_state_message_fail_handle(msg)
                    break;
                case "info":
                    this.job_state_message_info_handle(msg);
                    break;
            }
        } catch (error) {
            console.log(error);
        }

    }

    job_state_message_info_handle(msg: Message): void {
        let content = msg['content']['message'];

        // Create jobs from info in message.
        for (let jobid in content) {
            let job = { "jobid": jobid, tasks: content[jobid] };
            this.jobs[jobid] = job;
        }
    }

    job_state_message_change_handle(msg: Message): void {
        let content = msg['content']['message'];
        let jobid: string = content['jobid'];
        let taskid: string = content['taskid'];
        let state: string = content['state'];

        this.jobs[jobid].tasks[taskid].state = state;
    }

    job_state_message_fin_handle(msg: Message): void {
        let content = msg['content']['message'];
        let jobid: string = content['jobid'];

        delete this.jobs[jobid]
    }

    job_state_message_fail_handle(msg: Message): void {
        let content = msg['content']['message'];
        let jobid: string = content['jobid'];

        delete this.jobs[jobid]

    }
}
