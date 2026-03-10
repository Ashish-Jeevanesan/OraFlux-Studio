import { Injectable } from '@angular/core';
import { ColumnInfo, ChartConfig } from '../interfaces/api.interfaces';

export interface SuggestedChart {
  title: string;
  config: ChartConfig;
}

@Injectable({
  providedIn: 'root'
})
export class ChartSuggestionService {

  constructor() { }

  generateSuggestions(columns: ColumnInfo[]): SuggestedChart[] {
    if (!columns || columns.length === 0) {
      return [];
    }

    const suggestions: SuggestedChart[] = [];
    const temporalCols = this.filterColumns(columns, ['DATE', 'TIMESTAMP']);
    const quantitativeCols = this.filterColumns(columns, ['NUMBER', 'INTEGER', 'FLOAT', 'DECIMAL']);
    const categoricalCols = this.filterColumns(columns, ['VARCHAR', 'CHAR', 'NVARCHAR2'], ['ID']);

    // Suggestion 1: Quantitative over Time (Line Chart)
    if (temporalCols.length > 0 && quantitativeCols.length > 0) {
      const temporal = temporalCols[0];
      quantitativeCols.forEach(q => {
        suggestions.push({
          title: `Total ${q.name} over Time (by ${temporal.name})`,
          config: {
            type: 'line',
            x: { column: temporal.name, role: 'dimension' },
            y: [{ column: q.name, agg: 'SUM', role: 'measure' }],
            granularity: 'MM' // Default to month
          }
        });
      });
    }

    // Suggestion 2: Count by Category (Bar/Pie Chart)
    categoricalCols.forEach(c => {
      suggestions.push({
        title: `Count of Records by ${c.name}`,
        config: {
          type: 'bar',
          x: { column: c.name, role: 'dimension' },
          y: [{ column: '*', agg: 'COUNT', role: 'measure' }]
        }
      });
    });

    // Suggestion 3: Quantitative by Category (Bar Chart)
    if (categoricalCols.length > 0 && quantitativeCols.length > 0) {
      const category = categoricalCols[0];
      quantitativeCols.forEach(q => {
        suggestions.push({
          title: `Average ${q.name} by ${category.name}`,
          config: {
            type: 'bar',
            x: { column: category.name, role: 'dimension' },
            y: [{ column: q.name, agg: 'AVG', role: 'measure' }]
          }
        });
      });
    }
    
    // Suggestion 4: Distribution of a Quantitative value (Histogram)
    quantitativeCols.forEach(q => {
        suggestions.push({
          title: `Distribution of ${q.name}`,
          config: {
            type: 'histogram',
            x: { column: q.name, role: 'dimension' }, // Placeholder for x
            y: [{ column: q.name, agg: 'COUNT', role: 'measure' }],
            bins: 20
          }
        });
    });
    
    // Remove duplicate suggestions based on title
    return [...new Map(suggestions.map(item => [item.title, item])).values()];
  }

  private filterColumns(columns: ColumnInfo[], types: string[], nameExcludes: string[] = []): ColumnInfo[] {
    const lowerCaseTypes = types.map(t => t.toLowerCase());
    const lowerCaseNameExcludes = nameExcludes.map(n => n.toLowerCase());

    return columns.filter(c => 
      lowerCaseTypes.some(t => c.type.toLowerCase().includes(t)) &&
      !lowerCaseNameExcludes.some(ne => c.name.toLowerCase().includes(ne))
    );
  }
}
