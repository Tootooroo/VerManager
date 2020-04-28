import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { VerGenComponent } from './ver-gen.component';

describe('VerGenComponent', () => {
  let component: VerGenComponent;
  let fixture: ComponentFixture<VerGenComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ VerGenComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(VerGenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
