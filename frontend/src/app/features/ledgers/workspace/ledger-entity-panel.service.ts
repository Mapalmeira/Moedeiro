import { Injectable, signal } from '@angular/core';
import { LedgerAccount, LedgerCurrency } from '../../../core/ledgers/ledger-entities.models';

type Entity = LedgerAccount | LedgerCurrency;

export interface LedgerEntityPanelState {
  owner: object;
  kind: 'account' | 'currency';
  ledgerUuid: string;
  entity: Entity;
  currencies: LedgerCurrency[];
  onClose: () => void;
  onSaved: (entity: Entity) => void;
  onDeleteRequested: (entity: Entity) => void;
}

@Injectable()
export class LedgerEntityPanelService {
  private readonly currentState = signal<LedgerEntityPanelState | null>(null);
  readonly state = this.currentState.asReadonly();

  show(state: LedgerEntityPanelState): void {
    this.currentState.set(state);
  }

  update(owner: object, update: Pick<LedgerEntityPanelState, 'entity' | 'currencies'>): void {
    const current = this.currentState();
    if (!current || current.owner !== owner) return;
    this.currentState.set({ ...current, ...update });
  }

  requestClose(): void {
    const current = this.currentState();
    if (!current) return;
    current.onClose();
    this.currentState.set(null);
  }

  requestSaved(entity: Entity): void {
    this.currentState()?.onSaved(entity);
  }

  requestDelete(entity: Entity): void {
    this.currentState()?.onDeleteRequested(entity);
  }

  close(owner: object): void {
    const current = this.currentState();
    if (current?.owner === owner) this.currentState.set(null);
  }
}
