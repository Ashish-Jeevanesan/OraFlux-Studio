import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChartSuggestionsComponent } from './chart-suggestions.component';

describe('ChartSuggestionsComponent', () => {
  let component: ChartSuggestionsComponent;
  let fixture: ComponentFixture<ChartSuggestionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChartSuggestionsComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(ChartSuggestionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
