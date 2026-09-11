import { ComponentFixture, TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DialogShellComponent } from './dialog-shell.component';

describe('DialogShellComponent', () => {
  let fixture: ComponentFixture<DialogShellComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [DialogShellComponent] }).compileComponents();
  });

  it('focuses the first available control', async () => {
    fixture = TestBed.createComponent(DialogShellComponent);
    fixture.detectChanges();
    const button = document.createElement('button');
    fixture.nativeElement.querySelector('.ui-dialog-surface').appendChild(button);

    await Promise.resolve();

    expect(document.activeElement).toBe(button);
  });

  it('dismisses on Escape when the event was not already handled', async () => {
    fixture = TestBed.createComponent(DialogShellComponent);
    const dismissed = vi.fn();
    fixture.componentInstance.dismiss.subscribe(dismissed);
    fixture.detectChanges();
    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true });

    document.dispatchEvent(event);
    await Promise.resolve();

    expect(event.defaultPrevented).toBe(true);
    expect(dismissed).toHaveBeenCalledOnce();
  });

  it('only lets the topmost dialog handle Escape', async () => {
    const lower = TestBed.createComponent(DialogShellComponent);
    const upper = TestBed.createComponent(DialogShellComponent);
    const lowerDismissed = vi.fn();
    const upperDismissed = vi.fn();
    lower.componentInstance.dismiss.subscribe(lowerDismissed);
    upper.componentInstance.dismiss.subscribe(upperDismissed);
    lower.detectChanges();
    upper.detectChanges();
    await Promise.resolve();

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));

    expect(upperDismissed).toHaveBeenCalledOnce();
    expect(lowerDismissed).not.toHaveBeenCalled();

    upper.destroy();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));

    expect(lowerDismissed).toHaveBeenCalledOnce();
    lower.destroy();
  });

  it('only lets the topmost dialog trap Tab', () => {
    const lower = TestBed.createComponent(DialogShellComponent);
    const upper = TestBed.createComponent(DialogShellComponent);
    lower.detectChanges();
    upper.detectChanges();
    const lowerEvent = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    const upperEvent = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });

    lower.componentInstance.trapFocus(lowerEvent);
    upper.componentInstance.trapFocus(upperEvent);

    expect(lowerEvent.defaultPrevented).toBe(false);
    expect(upperEvent.defaultPrevented).toBe(true);

    upper.destroy();
    lower.destroy();
  });

  it('restores focus to the element active before the dialog was created', async () => {
    const previous = document.createElement('button');
    document.body.appendChild(previous);
    previous.focus();
    fixture = TestBed.createComponent(DialogShellComponent);
    fixture.detectChanges();
    await Promise.resolve();

    fixture.destroy();

    expect(document.activeElement).toBe(previous);
    previous.remove();
  });
});
