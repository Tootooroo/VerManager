import { Component, OnInit } from '@angular/core';
import { VersionService } from '../version.service';
import { Version } from '../version';

@Component({
    selector: 'app-ver-register',
    templateUrl: './ver-register.component.html',
    styleUrls: ['./ver-register.component.css']
})
export class VerRegisterComponent implements OnInit {

    constructor(private verService: VersionService) { }

    ngOnInit(): void {

    }

    register(vsn: string, rev: string): void {
        const ver: Version = { vsn, rev };
        this.verService.addVersion(ver)
            .subscribe();
    }

    remove(ver: Version): void {
        this.verService.removeVersion(ver.vsn)
            .subscribe();
    }

}
