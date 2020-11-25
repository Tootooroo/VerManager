import { Injectable } from '@angular/core';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { Observable, Subject } from 'rxjs';

@Injectable({
    providedIn: 'root'
})
export class ChannelService {

    private channels: { [index: string]: WebSocketSubject<Object> } = {};
    constructor() { }

    create(url: string): Observable<Object> {
        let channel: WebSocketSubject<Object>;

        if (typeof this.channels[url] == 'undefined') {
            // New channel
            channel = webSocket(url);
            this.channels[url] = channel;
        } else {
            // Exist channel
            channel = this.channels[url];
        }

        return channel;
    }

    close(url: string): void {
        if (typeof this.channels[url] != 'undefined') {
            this.channels[url].complete();
        }
    }
}
