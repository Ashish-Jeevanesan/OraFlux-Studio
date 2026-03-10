import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

// Material Components
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule, MatIconRegistry } from '@angular/material/icon';
import { DomSanitizer } from '@angular/platform-browser';

import { ColumnInfo, ChartConfig } from '../../interfaces/api.interfaces';
import { ChartSuggestionService, SuggestedChart } from '../../services/chart-suggestion.service';

const AUTO_AWESOME_ICON = `
  <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="#000000">
    <path d="M0 0h24v24H0V0z" fill="none"/>
    <path d="M19 9h-4V3H9v6H5l7 7 7-7z"/>
  </svg>
`;

@Component({
  selector: 'app-chart-suggestions',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatButtonModule, MatIconModule],
  templateUrl: './chart-suggestions.component.html',
  styleUrls: ['./chart-suggestions.component.scss']
})
export class ChartSuggestionsComponent implements OnChanges {
  @Input() columns: ColumnInfo[] = [];
  @Output() suggestionClick = new EventEmitter<ChartConfig>();

  suggestions: SuggestedChart[] = [];

  constructor(
    private chartSuggestionService: ChartSuggestionService,
    private matIconRegistry: MatIconRegistry,
    private domSanitizer: DomSanitizer
  ) {
    this.matIconRegistry.addSvgIconLiteral('auto_awesome', this.domSanitizer.bypassSecurityTrustHtml(AUTO_AWESOME_ICON));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['columns'] && this.columns.length > 0) {
      this.suggestions = this.chartSuggestionService.generateSuggestions(this.columns);
    } else {
      this.suggestions = [];
    }
  }

  onSuggestionClick(config: ChartConfig) {
    this.suggestionClick.emit(config);
  }
}
