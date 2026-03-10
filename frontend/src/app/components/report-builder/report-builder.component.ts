// frontend/src/app/components/report-builder/report-builder.component.ts
import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { finalize } from 'rxjs/operators';
import { EChartsOption } from 'echarts';

// External Modules
import { NgxEchartsModule } from 'ngx-echarts';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';


import { ApiService } from '../../services/api.service';
import { ColumnInfo, ChartConfig, AggregateQueryResponse, ChartY } from '../../interfaces/api.interfaces';

@Component({
  selector: 'app-report-builder',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NgxEchartsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatIconModule,
    MatSlideToggleModule
  ],
  templateUrl: './report-builder.component.html',
  styleUrls: ['./report-builder.component.scss'],
})
export class ReportBuilderComponent implements OnChanges {
  @Input() baseSql = '';
  @Input() columns: ColumnInfo[] = [];

  builderForm: FormGroup;
  isLoading = false;
  errorMessage: string | null = null;
  chartOption: EChartsOption | null = null;
  showSecondYAxis = false;

  readonly chartTypes: ChartConfig['type'][] = ['bar', 'line', 'pie', 'histogram'];
  readonly aggregations: ChartConfig['y'][0]['agg'][] = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'COUNT(DISTINCT)'];
  readonly granularities: ChartConfig['granularity'][] = ['YYYY', 'Q', 'MM', 'DD'];

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private snackBar: MatSnackBar
  ) {
    this.builderForm = this.fb.group({
      chartType: ['bar', Validators.required],
      xColumn: [null, Validators.required],
      // Y1
      y1Column: [null, Validators.required],
      y1Aggregation: ['COUNT', Validators.required],
      // Y2 (optional)
      y2Column: [null],
      y2Aggregation: ['SUM'],
    });

    this.builderForm.get('chartType')?.valueChanges.subscribe(type => {
      this.updateValidators(type);
    });
  }
  
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['columns'] && !changes['columns'].firstChange) {
      this.builderForm.patchValue({
        xColumn: null,
        y1Column: null,
        y2Column: null,
      });
      this.chartOption = null;
    }
  }
  
  updateValidators(chartType: ChartConfig['type']) {
    const granularityControl = this.builderForm.get('granularity');
    if (chartType === 'line') {
        granularityControl?.setValidators(Validators.required);
    } else {
        granularityControl?.clearValidators();
    }
    granularityControl?.updateValueAndValidity();
  }

  generateReport() {
    if (this.builderForm.invalid) return;

    this.isLoading = true;
    this.errorMessage = null;
    this.chartOption = null;

    const formVal = this.builderForm.value;
    
    // Construct the list of Y-axis metrics
    const yMetrics: ChartY[] = [];
    yMetrics.push({ column: formVal.y1Column, agg: formVal.y1Aggregation, role: 'measure' });
    if (this.showSecondYAxis && formVal.y2Column) {
      yMetrics.push({ column: formVal.y2Column, agg: formVal.y2Aggregation, role: 'measure' });
    }

    const chartConfig: ChartConfig = {
      type: formVal.chartType,
      x: { column: formVal.xColumn, role: 'dimension' },
      y: yMetrics,
      granularity: formVal.granularity,
      bins: formVal.bins
    };

    this.apiService.runAggregateQuery({
      baseSql: this.baseSql,
      chart: chartConfig
    })
    .pipe(finalize(() => this.isLoading = false))
    .subscribe({
      next: (response) => {
        this.snackBar.open(`Chart generated in ${response.executionMs}ms`, 'Close', { duration: 3000 });
        this.renderChart(response, chartConfig);
      },
      error: (err) => {
        this.errorMessage = err.message;
      }
    });
  }

  private renderChart(data: AggregateQueryResponse, config: ChartConfig) {
    if (config.type === 'pie') {
      const seriesName = `${config.y[0].agg}(${config.y[0].column})`;
      this.renderPieChart(data, seriesName);
    } else {
      this.renderCartesianChart(data, config);
    }
  }

  private renderPieChart(data: AggregateQueryResponse, seriesName: string) {
    this.chartOption = {
      title: {
        text: seriesName,
        left: 'center'
      },
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        left: 'left',
      },
      series: [
        {
          name: seriesName,
          type: 'pie',
          radius: '50%',
          data: data.rows.map(row => ({ name: row[0] as string, value: Number(row[1]) })),
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowOffsetX: 0,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }
      ]
    };
  }

  private renderCartesianChart(data: AggregateQueryResponse, config: ChartConfig) {
    const xValues = data.rows.map(row => row[0]);
    const yAxes: any[] = [];
    const series: any[] = [];
    const legendData: string[] = [];

    config.y.forEach((yMetric, index) => {
      const seriesName = `${yMetric.agg}(${yMetric.column})`;
      legendData.push(seriesName);

      yAxes.push({
        type: 'value',
        name: seriesName,
        position: index === 0 ? 'left' : 'right',
        axisLine: {
          show: true,
        },
        axisLabel: {
          formatter: '{value}'
        }
      });

      series.push({
        name: seriesName,
        type: config.type,
        yAxisIndex: index,
        data: data.rows.map(row => row[index + 1]) // y0 is at index 1, y1 at index 2, etc.
      });
    });

    this.chartOption = {
      tooltip: { 
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      grid: {
        left: '3%',
        right: config.y.length > 1 ? '4%' : '10%', // Make more room for right axis
        bottom: '10%',
        containLabel: true
      },
      legend: {
        data: legendData
      },
      xAxis: {
        type: 'category',
        data: xValues,
        axisLabel: {
          rotate: 30,
        }
      },
      yAxis: yAxes,
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          type: 'slider',
          start: 0,
          end: 100
        }
      ],
      series: series,
    };
  }
}
