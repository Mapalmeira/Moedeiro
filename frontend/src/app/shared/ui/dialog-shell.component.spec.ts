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
