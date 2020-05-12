import { Component, OnInit } from '@angular/core';

import { VersionService } from '../version.service';
import { RevisionService } from '../revision.service';
import { Version, VersionBuild, BuildInfo } from '../version';
import { Revision } from '../revision';

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
        console.log(build);
        this.verService.generate(build).subscribe();
    }
}
