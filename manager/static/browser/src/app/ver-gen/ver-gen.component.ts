import { Component, OnInit } from '@angular/core';
import { of } from 'rxjs';
import { catchError, delay } from 'rxjs/operators';
import { throwError } from 'rxjs/index';

import { VersionService } from '../version.service';
import { RevisionService } from '../revision.service';
import { Version, VersionBuild, BuildInfo } from '../version';
import { Revision } from '../revision';
import { HttpErrorResponse } from '@angular/common/http';

enum VerStatus {
    IN_PROCESSING_STATUS = 0,
    FAILURE_STATUS = 1
}

@Component({
    selector: 'app-ver-gen',
    templateUrl: './ver-gen.component.html',
    styleUrls: ['./ver-gen.component.css']
})
export class VerGenComponent implements OnInit {

    versions: Version[] = [];
    revisions: Revision[] = [];

    constructor(
        private verService: VersionService,
        private revService: RevisionService
    ) { }

    ngOnInit(): void {
        this.verService.getVersions()
            .subscribe(versions => this.versions = versions);
        this.revService.getRevisions()
            .subscribe(revisions => this.revisions = revisions);
    }

    generate(version: Version, ...infos: string[]): void {
        let buildInfo: BuildInfo;

        if (infos.length === 2) {
            buildInfo = { logFrom: infos[0], logTo: infos[1] };
        } else if (infos.length === 0) {
            buildInfo = {};
        }

        const build: VersionBuild = { ver: version, info: buildInfo };
        this.verService.generate(build).subscribe();
    }

    private waitFinErrHandle(error: HttpErrorResponse) {
        if (error.status === 304) {
            /* Version generation is in processing */
            return of(VerStatus.IN_PROCESSING_STATUS);
        } else if (error.status === 400) {
            return of(VerStatus.FAILURE_STATUS);
        }
    }

    waitFinished(version: Version): void {
        this.verService.waitFinished(version)
            .pipe(
                /* Delay 1000ms to control rate of query */
                delay(3000),
                catchError(this.waitFinErrHandle)
            )
            .subscribe(status => {
                switch (status) {
                    case VerStatus.IN_PROCESSING_STATUS:
                        this.waitFinished(version);
                        break;
                    case VerStatus.FAILURE_STATUS:
                        break;
                }
            });
    }
}
