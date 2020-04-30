import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Revision } from './revision';

@Injectable({
    providedIn: 'root'
})
export class RevisionService {

    private revUrl = 'manager/api/revisions';

    constructor(private http: HttpClient) { }

    getRevision(sn: string): Observable<Revision> {
        const url = `${this.revUrl}/${sn}`;
        return this.http.get<Revision>(url);
    }

    getRevisions(): Observable<Revision[]> {
        return this.http.get<Revision[]>(this.revUrl);
    }

    getSomeRevs(sn: string | null, num: number): Observable<Revision[]> {
        const url: string = sn != null ? `${this.revUrl}/${sn}/getSomeRevsFrom` :
            `${this.revUrl}/getSomeRevs`;
        const options = { params: { num: `${num}` } };
        return this.http.get<Revision[]>(url, options);
    }

}
