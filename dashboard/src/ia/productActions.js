import { dialog, toast } from 'frappe-ui'

// Every action a merchant can take from a product page, grouped by intent.
// The `productActions` IA axis only changes where these are rendered — the set
// itself stays the same, so the variants stay comparable.
//
// `handlers` carries the real, wired actions ProductDetail.vue owns
// (publish/unpublish across every option via catalog.set_product_published,
// archive/restore via catalog.update_product). Everything else here has no
// backend counterpart in ls_shop yet (bulk variant add/edit, a per-product
// stock adjustment with a reason, duplicate, delete, CSV export, a saved
// collection-rule picker, a per-product sales report) and stays a toast, the
// same stub-and-flag treatment Products.vue already gave its own unbacked
// actions in the prior wiring section.
export function buildProductActions(product, router, handlers = {}) {
  const isArchived = product.status === 'archived'
  const isPublished = product.variants.some((variant) => variant.is_published)

  const publish = {
    key: 'publish',
    label: isPublished ? 'Unpublish' : 'Publish to storefront',
    icon: isPublished ? 'lucide-eye-off' : 'lucide-globe',
    onClick: handlers.onTogglePublish ?? (() => toast.success(isPublished ? 'Hidden from the storefront' : 'Published')),
  }

  const groups = [
    {
      id: 'storefront',
      label: 'Storefront',
      items: [
        publish,
        { key: 'preview', label: 'Preview on storefront', icon: 'lucide-external-link', onClick: () => toast.info('Opens the live product page') },
        { key: 'link', label: 'Copy product link', icon: 'lucide-link', onClick: () => toast.success('Link copied') },
        { key: 'seo', label: 'Edit SEO listing', icon: 'lucide-search', onClick: () => toast.info('Jumps to the storefront section') },
      ],
    },
    {
      id: 'catalogue',
      label: 'Catalogue',
      items: [
        { key: 'option', label: product.hasVariants ? 'Add an option' : 'Split into variants', icon: 'lucide-git-branch', onClick: () => toast.info('Options regenerate the variant matrix') },
        { key: 'bulk', label: 'Bulk edit variants', icon: 'lucide-table-2', onClick: () => toast.info('Select variants to bulk edit') },
        { key: 'type', label: 'Change product type', icon: 'lucide-shapes', onClick: () => router.push('/product-types') },
        { key: 'collection', label: 'Add to collection', icon: 'lucide-layers', onClick: () => toast.info('Pick a collection') },
      ],
    },
    {
      id: 'inventory',
      label: 'Inventory',
      items: [
        {
          key: 'adjust',
          label: 'Adjust stock',
          icon: 'lucide-package-plus',
          onClick: () =>
            dialog.prompt({
              title: 'Adjust stock',
              message: `Recorded as an adjustment against ${product.title}.`,
              fields: [
                { name: 'qty', label: 'Change', required: true, description: 'Use a minus sign to remove stock.' },
                { name: 'reason', label: 'Reason', type: 'select', options: ['Received', 'Damaged', 'Stock count', 'Theft'] },
              ],
              onConfirm: ({ values }) => toast.success(`Stock adjusted by ${values.qty}`),
            }),
        },
        { key: 'transfer', label: 'Transfer between locations', icon: 'lucide-arrow-left-right', onClick: () => toast.info('Pick a source and destination') },
        { key: 'barcode', label: 'Print barcode labels', icon: 'lucide-printer', onClick: () => toast.info('Sent to the label printer') },
        { key: 'restock', label: 'Set a restock alert', icon: 'lucide-bell', onClick: () => toast.success('You will be told below 5 units') },
      ],
    },
    {
      id: 'pricing',
      label: 'Pricing',
      items: [
        { key: 'price', label: 'Bulk edit prices across products', icon: 'lucide-indian-rupee', onClick: () => router.push('/pricing') },
        { key: 'discount', label: 'Apply a discount', icon: 'lucide-percent', onClick: () => toast.info('Creates a price rule for this product') },
      ],
    },
    {
      id: 'insight',
      label: 'Reporting',
      items: [
        { key: 'sales', label: 'View sales report', icon: 'lucide-chart-line', onClick: () => toast.info('30-day report for this product') },
        { key: 'orders', label: 'Orders with this product', icon: 'lucide-shopping-bag', onClick: () => router.push('/orders') },
      ],
    },
    {
      id: 'manage',
      label: 'Manage',
      items: [
        {
          key: 'archive',
          label: isArchived ? 'Restore from archive' : 'Archive',
          icon: isArchived ? 'lucide-archive-restore' : 'lucide-archive',
          onClick: () =>
            isArchived || !handlers.onToggleArchive
              ? (handlers.onToggleArchive ?? (() => toast.success('Restored')))()
              : dialog.confirm({
                  title: 'Archive this product?',
                  message: 'It leaves the storefront. Past orders keep their line items.',
                  theme: 'red',
                  confirmLabel: 'Archive',
                  onConfirm: handlers.onToggleArchive,
                }),
        },
        {
          key: 'delete',
          label: 'Delete',
          icon: 'lucide-trash-2',
          theme: 'red',
          onClick: () =>
            dialog.confirm({
              title: `Delete ${product.title}?`,
              message: 'This cannot be undone, and it removes the product from every collection.',
              theme: 'red',
              confirmLabel: 'Delete',
              onConfirm: () => {
                toast.success('Deleted')
                router.push('/products')
              },
            }),
        },
      ],
    },
  ]

  // Look an action up by key instead of a group/index pair, so removing or
  // reordering entries above can't silently point `quick` at the wrong one.
  const findAction = (key) => groups.flatMap((group) => group.items).find((item) => item.key === key)

  // The handful worth surfacing without opening a menu.
  const quick = [publish, findAction('adjust'), findAction('price'), findAction('option')]

  return { groups, quick }
}

// Dropdown wants a flat list with `group` separators, not our nested shape.
export function asDropdownOptions(groups) {
  return groups.map((group) => ({
    group: group.label,
    options: group.items.map(({ label, icon, onClick, theme }) => ({ label, icon, onClick, theme })),
  }))
}

