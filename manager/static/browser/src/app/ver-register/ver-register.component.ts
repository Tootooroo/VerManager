import { Component, OnInit } from '@angular/core';
import { VersionService } from '../version.service';
import { RevisionService } from '../revision.service';
import { Version } from '../version';
import { Revision } from '../revision';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { SlicePipe } from '@angular/common';

@Component({
    selector: 'app-ver-register',
    templateUrl: './ver-register.component.html',
    styleUrls: ['./ver-register.component.css']
})
export class VerRegisterComponent implements OnInit {

    versions: Version[] = [];
    revisions: Revision[] = [];

    lastScrollTop: number = 0;
    revList: HTMLElement | null = null;

    constructor(private verService: VersionService,
        private revService: RevisionService,
        private dialog: MatDialog) { }

    ngOnInit(): void {
        this.getVersions();
        this.getSomeRevs(null, 20);
    }

    register(rev: string): void {
        const ref = this.dialog.open(RegisterDialog, {
            width: '250px'
        });

        ref.afterClosed().subscribe(result => {
            if (result !== undefined) {
                const ver: Version = { vsn: result, sn: rev };
                this.verService.addVersion(ver)
                    .subscribe();
            }
        });
    }

    remove(ver: Version): void {
        this.verService.removeVersion(ver.vsn)
            .subscribe();
    }

    getVersions(): void {
        this.verService.getVersions()
            .subscribe(versions => this.versions = versions);
    }

    getRevisions(): void {
        this.revService.getRevisions()
            .subscribe(revisions => this.revisions = revisions);
    }

    getSomeRevs(sn: string | null, num: number): void {
        this.revService.getSomeRevs(sn, num)
            .subscribe(revisions => this.revisions = this.revisions.concat(revisions));
    }

    logging(msg: string): void {
        console.log(msg);
    }

    onScroll(event: any): void {
        // visible height + pixel scrolled >= total height
        if (event.target.offsetHeight + event.target.scrollTop >= event.target.scrollHeight) {
            let lastSn: Revision = this.revisions[this.revisions.length - 1];
            this.revService.getSomeRevs(lastSn.sn, 10)
                .subscribe(revisions => {
                    const height: number = event.target.scrollHeight;
                    this.revisions = this.revisions.concat(revisions);
                });
        }
    }
}

@Component({
    selector: 'register-dialog',
    templateUrl: 'register-dialog.html'
})
export class RegisterDialog {

    public version: string;

    constructor(
        public dialogRef: MatDialogRef<RegisterDialog>) { }

    onCancel(): void {
        this.dialogRef.close();
    }
}
