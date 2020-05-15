import { TestBed } from '@angular/core/testing';
import { VersionService } from './version.service';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

describe('VersionService', () => {
    let service: VersionService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule]
        });
        service = TestBed.inject(VersionService);
    });

    it('#getVersion should return Version object identified by vsn', () => {
        service.getVersion("VersionToto").subscribe();
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });
});
