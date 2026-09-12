import { FinancialEvent, FinancialMovement } from './financial-events.models';

export function financialEventFeeMovement(event: FinancialEvent): FinancialMovement | null {
  return event.movements.find(movement => movement.special_type === 'FEE') ?? null;
}

export function financialEventMainMovements(event: FinancialEvent): FinancialMovement[] {
  return event.movements.filter(movement => movement.special_type === null);
}
