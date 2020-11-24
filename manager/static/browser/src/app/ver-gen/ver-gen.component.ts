import { Component, OnInit } from '@angular/core';
import { of } from 'rxjs';
import { catchError, delay } from 'rxjs/operators';
import { throwError } from 'rxjs/index';

import { VersionService } from '../version.service';
import { RevisionService } from '../revision.service';
import { Version, VersionBuild, BuildInfo } from '../version';
import { Revision } from '../revision';
import { HttpErrorResponse } from '@angular/common/http';

enum VerErrors {
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

    generate(version: Version | undefined, ...infos: string[]): void {
        let buildInfo: BuildInfo = {};

        if (typeof version !== 'undefined') {

            if (infos.length === 2) {
                buildInfo = { logFrom: infos[0], logTo: infos[1] };
            }

            const build: VersionBuild = { ver: version, info: buildInfo };
            this.verService.generate(build).subscribe();
        }
    }
}
