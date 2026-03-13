import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxEchartsModule } from 'ngx-echarts';
import { EChartsOption } from 'echarts';

@Component({
  selector: 'app-analytics-chart',
  standalone: true,
  imports: [CommonModule, NgxEchartsModule],
  template: '<div echarts [options]="chartOption" class="chart-container"></div>',
  styles: [':host { display: block; } .chart-container { height: 400px; }']
})
export class AnalyticsChartComponent implements OnInit {
  @Input({ required: true }) name!: string;
  @Input({ required: true }) type!: 'bar' | 'pie' | 'line';
  @Input({ required: true }) data!: { columns: any[], rows: any[] };

  chartOption!: EChartsOption;

  ngOnInit(): void {
    this.chartOption = this.createChartOptions();
  }

  private densifyTimeSeries(rows: any[][]): any[][] {
    if (rows.length < 2) {
      return rows;
    }

    const dateValues = rows.map(r => new Date(r[0])).sort((a, b) => a.getTime() - b.getTime());
    const minDate = dateValues[0];
    const maxDate = dateValues[dateValues.length - 1];
    
    const filledData = new Map<string, any[]>();
    rows.forEach(r => filledData.set(r[0], r));

    const result: any[][] = [];
    let currentDate = minDate;

    while (currentDate <= maxDate) {
      const key = currentDate.toISOString().slice(0, 7); // YYYY-MM
      if (filledData.has(key)) {
        result.push(filledData.get(key)!);
      } else {
        const newRow = new Array(rows[0].length).fill(0);
        newRow[0] = key;
        result.push(newRow);
      }
      currentDate.setMonth(currentDate.getMonth() + 1);
    }
    return result;
  }

  private createChartOptions(): EChartsOption {
    let { columns, rows } = this.data;
    
    // Densify data for time-series charts
    if ((this.type === 'bar' || this.type === 'line') && rows.length > 0 && typeof rows[0][0] === 'string' && rows[0][0].match(/^\d{4}-\d{2}$/)) {
      rows = this.densifyTimeSeries(rows);
    }

    const source = [columns.map(c => c.name), ...rows];

    switch (this.type) {
      case 'bar':
        return {
          title: { text: this.name, left: 'center' },
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          xAxis: { type: 'category' },
          yAxis: { type: 'value' },
          series: [{ type: 'bar' }],
          dataset: { source },
        };
      case 'pie':
        return {
          title: { text: this.name, left: 'center' },
          tooltip: { trigger: 'item' },
          legend: { orient: 'vertical', left: 'left' },
          series: [{ type: 'pie', radius: '70%' }],
          dataset: { source },
        };
      case 'line':
        return {
          title: { text: this.name, left: 'center' },
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category' },
          yAxis: { type: 'value' },
          series: [{ type: 'line', smooth: true }],
          dataset: { source },
        };
      default:
        return {};
    }
  }
}
