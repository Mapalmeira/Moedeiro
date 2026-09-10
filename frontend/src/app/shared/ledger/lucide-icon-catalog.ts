import { icons, isLucideIconComponent, LucideIcon } from '@lucide/angular';
import { normalizeSearchText } from '../search-normalization';

export interface LucideCatalogIcon {
  id: string;
  label: string;
  searchText: string;
  component: LucideIcon;
}

function humanizeIconName(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1 $2')
    .trim();
}

const catalogById = new Map<string, LucideCatalogIcon>();

for (const [name, component] of Object.entries(icons)) {
  if (!isLucideIconComponent(component)) continue;

  const id = name.startsWith('Lucide') ? name.slice('Lucide'.length) : name;
  if (!catalogById.has(id)) {
    const label = humanizeIconName(id);
    catalogById.set(id, {
      id,
      label,
      searchText: normalizeSearchText(`${label} ${id}`),
      component,
    });
  }
}

export const LUCIDE_ICON_CATALOG: readonly LucideCatalogIcon[] = Array.from(catalogById.values())
  .sort((a, b) => a.label.localeCompare(b.label));

const ICON_BY_ID = new Map(LUCIDE_ICON_CATALOG.map(icon => [icon.id, icon.component] as const));
const LABEL_BY_ID = new Map(LUCIDE_ICON_CATALOG.map(icon => [icon.id, icon.label] as const));

export function resolveLucideIcon(iconId: string): LucideIcon | null {
  return ICON_BY_ID.get(iconId) ?? null;
}

export function resolveLucideIconLabel(iconId: string): string {
  return LABEL_BY_ID.get(iconId) ?? '';
}
