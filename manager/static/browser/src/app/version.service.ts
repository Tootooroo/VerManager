import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Version } from './version';

@Injectable({
    providedIn: 'root'
})
export class VersionService {

    private verUrl = 'manager/api/versions';

    httpOptions = {
        headers: new HttpHeaders({ 'Content-Type': 'application/json' }),
    };

    constructor(
        private http: HttpClient
    ) { }

    getVersion(vsn: string): Observable<Version> {
        const url = `${this.verUrl}/${vsn}`;
        return this.http.get<Version>(url);
    }

    getVersions(): Observable<Version[]> {
        return this.http.get<Version[]>(this.verUrl);
    }

    updateVersion(ver: Version): Observable<any> {
        return this.http.put(this.verUrl, ver, this.httpOptions);
    }

    removeVersion(vsn: string): Observable<Version> {
        const url = `${this.verUrl}/${vsn}`;
        return this.http.delete<Version>(url, this.httpOptions);
    }

    addVersion(ver: Version): Observable<Version> {
        return this.http.post<Version>(this.verUrl, ver, this.httpOptions);
    }

}
