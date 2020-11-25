import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { VerRegisterComponent } from './ver-register.component';
import { MatDialog } from '@angular/material/dialog';


class MatDialogFake {
    close(): void {
        return;
    }
}

describe('VerRegisterComponent', () => {
    let component: VerRegisterComponent;
    let fixture: ComponentFixture<VerRegisterComponent>;

    beforeEach(async(() => {
        TestBed.configureTestingModule({
            imports: [HttpClientTestingModule],
            declarations: [VerRegisterComponent],
            providers: [{ provide: MatDialog, useClass: MatDialogFake }]
        }).compileComponents();
    }));

    beforeEach(() => {
        fixture = TestBed.createComponent(VerRegisterComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });
});
