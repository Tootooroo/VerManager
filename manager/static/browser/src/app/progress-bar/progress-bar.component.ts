import { Component, OnInit } from '@angular/core';
import { MessageService } from '../message.service';
import { Message } from '../message';


interface Job {
    jobid: string;
    tasks: string[];
}


@Component({
    selector: 'app-progress-bar',
    templateUrl: './progress-bar.component.html',
    styleUrls: ['./progress-bar.component.css']
})
export class ProgressBarComponent implements OnInit {

    private jobs: Job[] = [];

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
                    break;
                case "fin":
                    break;
                case "fail":
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
        let content = msg['content'];

        // Create jobs from info in message.
        for (let jobid in content) {
            let job = { "jobid": jobid, tasks: content[jobid] };
            this.jobs.push(job);
        }
    }

    job_state_message_change_handle(msg: Message): void {

    }

    job_state_message_fin_handle(msg: Message): void {

    }

    job_state_message_fail_handle(msg: Message): void {

    }
}
