import { TestBed } from '@angular/core/testing';
import { RevisionService } from './revision.service';

describe('RevisionService', () => {
    let service: RevisionService;
    let httpClientSpy: { get: jasmine.Spy };

    beforeEach(() => {
        httpClientSpy = jasmine.createSpyObj('HttpClient', ['get']);
        service = new RevisionService(httpClientSpy as any);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });
});
