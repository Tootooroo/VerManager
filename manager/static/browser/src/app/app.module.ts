import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { VerGenComponent } from './ver-gen/ver-gen.component';
import { VerRegisterComponent } from './ver-register/ver-register.component';

@NgModule({
    declarations: [
        AppComponent,
        VerGenComponent,
        VerRegisterComponent
    ],
    imports: [
        BrowserModule,
        BrowserAnimationsModule,
        HttpClientModule
    ],
    providers: [],
    bootstrap: [AppComponent]
})
export class AppModule { }
