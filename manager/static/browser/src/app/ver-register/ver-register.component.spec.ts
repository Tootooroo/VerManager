import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VerRegisterComponent } from './ver-register.component';

describe('VerRegisterComponent', () => {
  let component: VerRegisterComponent;
  let fixture: ComponentFixture<VerRegisterComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ VerRegisterComponent ]
    })
    .compileComponents();
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
