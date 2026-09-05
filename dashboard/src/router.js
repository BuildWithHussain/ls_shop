import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('./pages/Dashboard.vue') },
  { path: '/orders', name: 'Orders', component: () => import('./pages/Orders.vue') },
  { path: '/orders/:id', name: 'OrderDetail', component: () => import('./pages/OrderDetail.vue'), meta: { split: true } },
  { path: '/products', name: 'Products', component: () => import('./pages/Products.vue') },
  // `split`: the page owns its own scroll — a form pane and a summary pane
  // side by side, the way Helpdesk's ticket screen does it.
  { path: '/products/:id', name: 'ProductDetail', component: () => import('./pages/ProductDetail.vue'), meta: { split: true } },
  { path: '/products/:id/variants/:variantId', name: 'VariantDetail', component: () => import('./pages/VariantDetail.vue') },
  { path: '/collections', name: 'Collections', component: () => import('./pages/Collections.vue') },
  { path: '/product-types', name: 'ProductTypes', component: () => import('./pages/ProductTypes.vue') },
  { path: '/attributes', name: 'Attributes', component: () => import('./pages/Attributes.vue') },
  { path: '/inventory', name: 'Inventory', component: () => import('./pages/Inventory.vue') },
  { path: '/inventory/adjustments', name: 'Adjustments', component: () => import('./pages/Adjustments.vue') },
  { path: '/pricing', name: 'Pricing', component: () => import('./pages/Pricing.vue') },
  { path: '/customers', name: 'Customers', component: () => import('./pages/Customers.vue') },
  { path: '/customers/:id', name: 'CustomerDetail', component: () => import('./pages/CustomerDetail.vue') },
  // Overview is the dashboard, so /analytics itself holds nothing: it opens
  // the first report.
  { path: '/analytics', redirect: '/analytics/revenue' },
  { path: '/analytics/revenue', name: 'RevenueReport', component: () => import('./pages/analytics/Revenue.vue') },
  { path: '/analytics/inventory', name: 'InventoryReport', component: () => import('./pages/analytics/Inventory.vue') },
  { path: '/analytics/storefront', name: 'StorefrontReport', component: () => import('./pages/analytics/Storefront.vue') },
  { path: '/storefront/theme', name: 'StorefrontTheme', component: () => import('./pages/storefront/Theme.vue') },
  { path: '/storefront/navigation', name: 'StorefrontNavigation', component: () => import('./pages/storefront/Navigation.vue') },
  { path: '/storefront/pages', name: 'StorefrontPages', component: () => import('./pages/storefront/Pages.vue') },
  // A Shop Web Page is named by its title, so the create path shadows a page
  // literally titled "new" — rare enough to live with, and the editor is still
  // reachable from the list row.
  { path: '/storefront/pages/new', name: 'StorefrontPageNew', component: () => import('./pages/storefront/PageDetail.vue') },
  { path: '/storefront/pages/:name', name: 'StorefrontPageDetail', component: () => import('./pages/storefront/PageDetail.vue') },
]

export const router = createRouter({
  history: createWebHistory('/commera'),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})
