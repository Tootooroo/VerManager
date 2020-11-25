import { TestBed } from '@angular/core/testing';
import { MessageService } from './message.service';
import { Observable } from 'rxjs';
import { ChannelService } from './channel.service';
import { Message } from './message';

class ChannelServiceFake {
    producer: Observable<string> = new Observable(obs => {
        setInterval(() => {
            obs.next('{"type": "TYPE", "content": {"123": "123"}}');
        }, 3000);
    });

    create(url: string): Observable<string> {
        return this.producer;
    }
}

describe('MessageService', () => {
    let service: MessageService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [{ provide: ChannelService, useClass: ChannelServiceFake }]
        });
        service = TestBed.inject(MessageService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('register', done => {
        let msg: Message;
        service.register("TYPE").subscribe(data => {
            console.log(data);
            expect(data).toEqual({ "type": "TYPE", "content": { "123": "123" } });
            done();
        });
    });
});
