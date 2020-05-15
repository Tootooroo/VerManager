import { Component } from '@angular/core';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent {
    title = 'Version Manager';
}

@Component({
    selector: 'navbar-row',
    templateUrl: './navbar-row.html',
    styleUrls: ['./navbar-row.css']
})
export class NavrowComponent { }
