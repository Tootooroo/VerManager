import { Injectable } from '@angular/core';
import { webSocket } from 'rxjs/webSocket';
import { Observable } from 'rxjs';
import { Message, message_parse } from './message';


class MessageQueue {
    private data: Message[] = [];

    len(): number {
        return this.data.length;
    }

    isFull(): boolean {
        return this.len() > 0;
    }

    isEmpty(): boolean {
        return this.len() == 0;
    }

    push(msg: Message): void {
        this.data.push(msg);
    }

    pop(): Message {
        return this.data.pop();
    }
}

@Injectable({
    providedIn: 'root'
})
export class MessageService {

    private sock_url = "ws://localhost/client/commu";
    private socket: any = null;

    /**
     * With Help of msg_queues MessageService able to
     * provide messages that from server, to another
     * components or services.
     *
     *  ---- message ---> MessageService ---> queue ---> component
     */
    private msg_queues: { [index: string]: MessageQueue } = {};

    constructor() { }

    ngOnInit(): void {
        this.socket = webSocket(this.sock_url);
        this.socket.subscribe(
            msg => {
                let message: Message = message_parse(msg);
                if (message == null) {
                    // invalid message
                    return;
                }

                let msg_type: string = message.msg_type;

                // If type of thie message is subscribe then add it to
                // correspond queue.
                if (typeof this.msg_queues[msg_type] != 'undefined')
                    this.msg_queues[message.msg_type].push(message);
            },
            err => {
                console.log(err);
            },
            () => {
                console.log("complete");
            }
        );
    }

    register(msg_type: string): Observable<Message> | null {
        // To check that is this msg_type is unique.
        if (typeof this.msg_queues[msg_type] == "undefined")
            this.msg_queues[msg_type] = new MessageQueue();
        else
            return null;

        return new Observable(msg_receiver => {
            setInterval(() => {
                let q: MessageQueue = this.msg_queues[msg_type];
                while (!q.isEmpty()) {
                    msg_receiver.next(q.pop());
                }
            }, 3000);
        });
    }

}
