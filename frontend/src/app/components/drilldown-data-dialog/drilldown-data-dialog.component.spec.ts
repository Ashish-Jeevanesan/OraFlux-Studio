import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DrilldownDataDialogComponent } from './drilldown-data-dialog.component';

describe('DrilldownDataDialogComponent', () => {
  let component: DrilldownDataDialogComponent;
  let fixture: ComponentFixture<DrilldownDataDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DrilldownDataDialogComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(DrilldownDataDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
