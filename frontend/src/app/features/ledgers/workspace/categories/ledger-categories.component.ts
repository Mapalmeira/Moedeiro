import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, effect, inject, signal, untracked, viewChild } from '@angular/core';
import { DialogShellComponent } from '../../../../shared/ui/dialog-shell.component';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subscription, finalize } from 'rxjs';
import { ApiErrorService } from '../../../../core/api/api-error';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { LedgerCategory, LedgerCategoryTreeNode } from '../../../../core/ledgers/ledger-categories.models';
import { flattenCategoryTree } from '../../../../core/ledgers/ledger-category-tree';
import { LedgerCategoriesService } from '../../../../core/ledgers/ledger-categories.service';
import { LedgerContextService } from '../../../../core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from '../../../../core/ledgers/ledger-workspace-state.service';
import { EntityBadgeComponent } from '../../../../shared/ledger/entity-badge.component';
import { normalizeSearchText } from '../../../../shared/search-normalization';
import { FormMessageComponent } from '../../../../shared/ui/form-message.component';
import { IconComponent } from '../../../../shared/ui/icon.component';
import { CategoryEditorComponent } from './category-editor.component';

interface CategoryRow {
  category: LedgerCategory;
  indent: string;
  hasChildren: boolean;
  hasVisibleChildren: boolean;
  isLast: boolean;
  isRootBranch: boolean;
  branchParentStart: string;
  branchWidth: string;
  ancestorGuides: readonly CategoryTreeGuide[];
}

interface CategoryTreeGuide {
  start: string;
}

const ROOT_DROP_TARGET = '__root__';

@Component({
  selector: 'app-ledger-categories',
  standalone: true,
  imports: [DialogShellComponent, CategoryEditorComponent, EntityBadgeComponent, FormMessageComponent, IconComponent],
  templateUrl: './ledger-categories.component.html',
  styleUrl: './ledger-categories.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerCategoriesComponent {
  private readonly categoriesService = inject(LedgerCategoriesService);
  private readonly errors = inject(ApiErrorService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly workspaceState = inject(LedgerWorkspaceStateService);
  readonly context = inject(LedgerContextService);
  readonly i18n = inject(I18nService);
  private loadRequest?: Subscription;
  private mutationRequest?: Subscription;
  private activePointerId: number | null = null;
  private pointerClientX = 0;
  private pointerClientY = 0;
  private autoScrollFrame: number | null = null;
  private readonly categoryRows = viewChild<ElementRef<HTMLElement>>('categoryRows');

  readonly tree = signal<LedgerCategoryTreeNode[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly operationError = signal<string | null>(null);
  readonly search = signal('');
  readonly collapsed = signal<ReadonlySet<string>>(new Set<string>());
  readonly rootCollapsed = signal(false);
  readonly draggingUuid = signal<string | null>(null);
  readonly dropTarget = signal<string | null>(null);
  readonly movingUuid = signal<string | null>(null);

  readonly editorOpen = signal(false);
  readonly editing = signal<LedgerCategory | null>(null);
  readonly createParentUuid = signal<string | null>(null);
  readonly deleting = signal<LedgerCategory | null>(null);
  readonly deletingBusy = signal(false);
  readonly deleteError = signal<string | null>(null);

  readonly rootDropTarget = ROOT_DROP_TARGET;
  readonly allCategories = computed(() => flattenCategoryTree(this.tree()));
  readonly categoryByUuid = computed(() => new Map(this.allCategories().map(category => [category.uuid, category] as const)));
  readonly searchVisibleUuids = computed<ReadonlySet<string> | null>(() => {
    const query = normalizeSearchText(this.search().trim());
    if (!query) return null;

    const byUuid = this.categoryByUuid();
    const visible = new Set<string>();
    for (const category of this.allCategories()) {
      if (!normalizeSearchText(category.name).includes(query)) continue;
      let current: LedgerCategory | undefined = category;
      while (current && !visible.has(current.uuid)) {
        visible.add(current.uuid);
        current = current.parent_uuid ? byUuid.get(current.parent_uuid) : undefined;
      }
    }
    return visible;
  });
  readonly visibleRows = computed(() => {
    const searchVisible = this.searchVisibleUuids();
    if (!searchVisible && this.rootCollapsed()) return [];
    const collapsed = this.collapsed();
    const rows: CategoryRow[] = [];

    const visit = (nodes: readonly LedgerCategoryTreeNode[], depth: number, ancestorContinuations: readonly boolean[]): void => {
      const visibleNodes = nodes.filter(node => !searchVisible || searchVisible.has(node.category.uuid));
      visibleNodes.forEach((node, index) => {
        const isLast = index === visibleNodes.length - 1;
        const visibleChildren = node.children.filter(child => !searchVisible || searchVisible.has(child.category.uuid));
        rows.push({
          category: node.category,
          indent: this.categoryIndent(depth),
          hasChildren: node.children.length > 0,
          hasVisibleChildren: visibleChildren.length > 0 && (searchVisible !== null || !collapsed.has(node.category.uuid)),
          isLast,
          isRootBranch: depth === 0,
          branchParentStart: depth === 0 ? 'var(--category-tree-start)' : this.categoryIndent(depth - 1),
          branchWidth: depth === 0 ? 'var(--category-root-child-indent)' : 'var(--category-tree-indent)',
          ancestorGuides: ancestorContinuations.flatMap((continues, ancestorDepth) => continues && ancestorDepth > 0
            ? [{ start: this.categoryIndent(ancestorDepth - 1) }]
            : []),
        });
        if (searchVisible || !collapsed.has(node.category.uuid)) {
          visit(visibleChildren, depth + 1, [...ancestorContinuations, !isLast]);
        }
      });
    };
    visit(this.tree(), 0, []);
    return rows;
  });
  readonly hasSearchResults = computed(() => this.visibleRows().length > 0);

  constructor() {
    effect(() => {
      const ledgerUuid = this.context.ledgerUuid();
      untracked(() => {
        this.resetViewState(ledgerUuid);
        if (ledgerUuid) this.load();
      });
    });
    this.destroyRef.onDestroy(() => this.stopAutoScroll());
  }

  filter(event: Event): void {
    this.search.set((event.target as HTMLInputElement).value);
    this.operationError.set(null);
    this.saveViewState();
  }

  load(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.loadRequest?.unsubscribe();
    this.loading.set(true);
    this.error.set(null);
    this.loadRequest = this.categoriesService.getTree(ledgerUuid).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.loading.set(false)),
    ).subscribe({
      next: tree => this.tree.set(tree),
      error: error => this.error.set(this.errors.message(error, 'errors.categoriesLoadFailed')),
    });
  }

  toggleRoot(event: Event): void {
    event.stopPropagation();
    this.rootCollapsed.update(value => !value);
    this.saveViewState();
  }

  toggleCategory(event: Event, categoryUuid: string): void {
    event.stopPropagation();
    const next = new Set(this.collapsed());
    next.has(categoryUuid) ? next.delete(categoryUuid) : next.add(categoryUuid);
    this.collapsed.set(next);
    this.saveViewState();
  }

  openCreate(parentUuid: string | null, event?: Event): void {
    event?.stopPropagation();
    this.editing.set(null);
    this.createParentUuid.set(parentUuid);
    this.editorOpen.set(true);
    this.operationError.set(null);
  }

  openEdit(category: LedgerCategory): void {
    if (this.draggingUuid()) return;
    this.editing.set(category);
    this.createParentUuid.set(category.parent_uuid);
    this.editorOpen.set(true);
    this.operationError.set(null);
  }

  closeEditor(): void {
    this.editorOpen.set(false);
  }

  saved(category: LedgerCategory): void {
    this.editorOpen.set(false);
    this.revealParent(category.parent_uuid);
    this.load();
  }

  requestDelete(category: LedgerCategory): void {
    this.editorOpen.set(false);
    this.deleteError.set(null);
    this.deleting.set(category);
  }

  closeDelete(): void {
    if (!this.deletingBusy()) this.deleting.set(null);
  }

  remove(): void {
    const category = this.deleting();
    const ledgerUuid = this.context.ledgerUuid();
    if (!category || !ledgerUuid || this.deletingBusy()) return;

    this.deletingBusy.set(true);
    this.deleteError.set(null);
    this.mutationRequest?.unsubscribe();
    this.mutationRequest = this.categoriesService.delete(ledgerUuid, category.uuid).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.deletingBusy.set(false)),
    ).subscribe({
      next: () => {
        this.deleting.set(null);
        this.load();
      },
      error: error => this.deleteError.set(this.errors.message(error, 'errors.categoryDeleteFailed')),
    });
  }

  startDrag(event: DragEvent, category: LedgerCategory): void {
    if (this.activePointerId !== null || this.movingUuid()) {
      event.preventDefault();
      return;
    }
    this.beginDrag(category.uuid);
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', category.uuid);
    }
  }

  dragOver(event: DragEvent, parentUuid: string | null): void {
    if (!this.canDropOn(parentUuid)) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    this.dropTarget.set(parentUuid ?? ROOT_DROP_TARGET);
  }

  drop(event: DragEvent, parentUuid: string | null): void {
    event.preventDefault();
    event.stopPropagation();
    const sourceUuid = this.draggingUuid();
    this.endDrag();
    if (sourceUuid) this.moveCategory(sourceUuid, parentUuid);
  }

  startPointerDrag(event: PointerEvent, category: LedgerCategory): void {
    if (event.pointerType === 'mouse' || this.activePointerId !== null || this.movingUuid()) return;
    event.preventDefault();
    event.stopPropagation();
    this.activePointerId = event.pointerId;
    this.pointerClientX = event.clientX;
    this.pointerClientY = event.clientY;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    this.beginDrag(category.uuid);
    this.updatePointerDropTarget(event.clientX, event.clientY);
    this.startAutoScroll();
  }

  pointerDrag(event: PointerEvent): void {
    if (event.pointerId !== this.activePointerId || !this.draggingUuid()) return;
    event.preventDefault();
    this.pointerClientX = event.clientX;
    this.pointerClientY = event.clientY;
    this.updatePointerDropTarget(event.clientX, event.clientY);
    this.startAutoScroll();
  }

  endPointerDrag(event: PointerEvent): void {
    if (event.pointerId !== this.activePointerId) return;
    event.preventDefault();
    event.stopPropagation();
    const sourceUuid = this.draggingUuid();
    const target = this.dropTarget();
    const targetElement = event.currentTarget as HTMLElement;
    if (targetElement.hasPointerCapture(event.pointerId)) targetElement.releasePointerCapture(event.pointerId);
    this.activePointerId = null;
    this.stopAutoScroll();
    this.endDrag();
    if (!sourceUuid || !target) return;
    this.moveCategory(sourceUuid, target === ROOT_DROP_TARGET ? null : target);
  }

  cancelPointerDrag(event: PointerEvent): void {
    if (event.pointerId !== this.activePointerId) return;
    const targetElement = event.currentTarget as HTMLElement;
    if (targetElement.hasPointerCapture(event.pointerId)) targetElement.releasePointerCapture(event.pointerId);
    this.activePointerId = null;
    this.stopAutoScroll();
    this.endDrag();
  }

  endDrag(): void {
    this.stopAutoScroll();
    this.draggingUuid.set(null);
    this.dropTarget.set(null);
  }

  canDropOn(parentUuid: string | null): boolean {
    const sourceUuid = this.draggingUuid();
    return !!sourceUuid && this.canMove(sourceUuid, parentUuid);
  }

  private beginDrag(categoryUuid: string): void {
    this.draggingUuid.set(categoryUuid);
    this.dropTarget.set(null);
    this.operationError.set(null);
  }

  private moveCategory(sourceUuid: string, parentUuid: string | null): void {
    if (!this.canMove(sourceUuid, parentUuid)) return;
    const source = this.categoryByUuid().get(sourceUuid);
    const ledgerUuid = this.context.ledgerUuid();
    if (!source || !ledgerUuid) return;

    this.movingUuid.set(sourceUuid);
    this.operationError.set(null);
    this.mutationRequest?.unsubscribe();
    this.mutationRequest = this.categoriesService.update(ledgerUuid, sourceUuid, {
      name: source.name,
      icon: source.icon,
      color_code: source.color_code,
      parent_uuid: parentUuid,
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
      finalize(() => this.movingUuid.set(null)),
    ).subscribe({
      next: category => {
        this.revealParent(category.parent_uuid);
        this.load();
      },
      error: error => this.operationError.set(this.errors.message(error, 'errors.categoryMoveFailed')),
    });
  }

  private canMove(sourceUuid: string, parentUuid: string | null): boolean {
    const source = this.categoryByUuid().get(sourceUuid);
    if (!source || source.parent_uuid === parentUuid || sourceUuid === parentUuid) return false;

    let currentUuid = parentUuid;
    const byUuid = this.categoryByUuid();
    while (currentUuid) {
      if (currentUuid === sourceUuid) return false;
      currentUuid = byUuid.get(currentUuid)?.parent_uuid ?? null;
    }
    return true;
  }

  private revealParent(parentUuid: string | null): void {
    this.rootCollapsed.set(false);
    if (!parentUuid) return;
    const next = new Set(this.collapsed());
    let currentUuid: string | null = parentUuid;
    const byUuid = this.categoryByUuid();
    while (currentUuid) {
      next.delete(currentUuid);
      currentUuid = byUuid.get(currentUuid)?.parent_uuid ?? null;
    }
    this.collapsed.set(next);
    this.saveViewState();
  }

  private updatePointerDropTarget(clientX: number, clientY: number): void {
    const dropElement = document.elementFromPoint(clientX, clientY)?.closest<HTMLElement>('[data-category-drop-target]');
    if (!dropElement) {
      this.dropTarget.set(null);
      return;
    }
    const target = dropElement.dataset['categoryDropTarget'];
    const parentUuid = target === ROOT_DROP_TARGET ? null : target ?? null;
    this.dropTarget.set(this.canDropOn(parentUuid) ? (parentUuid ?? ROOT_DROP_TARGET) : null);
  }

  private startAutoScroll(): void {
    if (this.autoScrollFrame !== null || this.activePointerId === null) return;
    this.autoScrollFrame = requestAnimationFrame(() => this.autoScroll());
  }

  private autoScroll(): void {
    this.autoScrollFrame = null;
    if (this.activePointerId === null || !this.draggingUuid()) return;

    const scroller = this.categoryRows()?.nativeElement;
    if (!scroller) return;
    const styles = getComputedStyle(scroller);
    const edgeSize = Number.parseFloat(styles.getPropertyValue('--list-row-height'));
    const maxStep = Number.parseFloat(styles.getPropertyValue('--space-3'));
    if (!Number.isFinite(edgeSize) || !Number.isFinite(maxStep) || edgeSize <= 0 || maxStep <= 0) return;

    const rect = scroller.getBoundingClientRect();
    let delta = 0;
    if (this.pointerClientY < rect.top + edgeSize) {
      const intensity = Math.min(1, Math.max(0, (rect.top + edgeSize - this.pointerClientY) / edgeSize));
      delta = -maxStep * intensity;
    } else if (this.pointerClientY > rect.bottom - edgeSize) {
      const intensity = Math.min(1, Math.max(0, (this.pointerClientY - (rect.bottom - edgeSize)) / edgeSize));
      delta = maxStep * intensity;
    }

    if (delta !== 0) {
      scroller.scrollTop += delta;
      this.updatePointerDropTarget(this.pointerClientX, this.pointerClientY);
    }
    this.startAutoScroll();
  }

  private stopAutoScroll(): void {
    if (this.autoScrollFrame === null) return;
    cancelAnimationFrame(this.autoScrollFrame);
    this.autoScrollFrame = null;
  }

  private categoryIndent(depth: number): string {
    const increments = ['var(--category-root-child-indent)', ...Array.from({ length: depth }, () => 'var(--category-tree-indent)')];
    return `calc(var(--category-tree-start) + ${increments.join(' + ')})`;
  }

  private resetViewState(ledgerUuid: string | null): void {
    this.loadRequest?.unsubscribe();
    this.mutationRequest?.unsubscribe();
    this.tree.set([]);
    const saved = ledgerUuid ? this.workspaceState.getCategoryView(ledgerUuid) : null;
    this.search.set(saved?.search ?? '');
    this.collapsed.set(new Set(saved?.collapsed ?? []));
    this.rootCollapsed.set(saved?.root_collapsed ?? false);
    this.draggingUuid.set(null);
    this.dropTarget.set(null);
    this.movingUuid.set(null);
    this.activePointerId = null;
    this.stopAutoScroll();
    this.editorOpen.set(false);
    this.editing.set(null);
    this.deleting.set(null);
    this.operationError.set(null);
    this.error.set(null);
  }

  private saveViewState(): void {
    const ledgerUuid = this.context.ledgerUuid();
    if (!ledgerUuid) return;
    this.workspaceState.setCategoryView(ledgerUuid, {
      search: this.search(),
      collapsed: [...this.collapsed()],
      root_collapsed: this.rootCollapsed(),
    });
  }

}
