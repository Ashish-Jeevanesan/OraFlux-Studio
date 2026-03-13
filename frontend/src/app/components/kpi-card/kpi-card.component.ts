import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  imports: [CommonModule, MatCardModule],
  templateUrl: './kpi-card.component.html',
  styleUrls: ['./kpi-card.component.scss']
})
export class KpiCardComponent {
  @Input({ required: true }) name!: string;
  @Input({ required: true }) value!: string | number;

  get formattedValue(): string {
    const isCurrency = this.name.includes('Value') || this.name.includes('Amount');
    
    if (typeof this.value === 'number') {
      const formatted = this.value.toLocaleString();
      return isCurrency ? `$${formatted}` : formatted;
    }
    
    const num = parseFloat(this.value as string);
    if (!isNaN(num) && isFinite(num)) {
      const formatted = num.toLocaleString();
      return isCurrency ? `$${formatted}` : formatted;
    }
    
    return this.value as string;
  }
}
