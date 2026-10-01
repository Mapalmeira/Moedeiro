import { describe, expect, it } from 'vitest';
import { homeChartTooltipCenter } from './home-flow-chart.component';

describe('homeChartTooltipCenter', () => {
  it('keeps the tooltip centered on the selected point while it fits', () => {
    expect(homeChartTooltipCenter(240, 180, 20, 480)).toBe(240);
  });

  it('clamps the tooltip at the left boundary', () => {
    expect(homeChartTooltipCenter(40, 180, 20, 480)).toBe(110);
  });

  it('clamps the tooltip at the right boundary', () => {
    expect(homeChartTooltipCenter(460, 180, 20, 477)).toBe(387);
  });

  it('centers an oversized tooltip in the available boundary', () => {
    expect(homeChartTooltipCenter(40, 500, 20, 480)).toBe(250);
  });
});
