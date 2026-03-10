import { TestBed } from '@angular/core/testing';

import { ChartSuggestionService } from './chart-suggestion.service';

describe('ChartSuggestionService', () => {
  let service: ChartSuggestionService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ChartSuggestionService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
