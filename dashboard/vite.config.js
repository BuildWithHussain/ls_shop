import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'

export default defineConfig({
  plugins: [
    frappeui({
      frappeProxy: {
        // `port` is the VITE dev-server port, not Frappe's. The plugin proxies to
        // whatever webserver_port common_site_config says and routes by the request's
        // Host, so browse the app at <site>:8080 to hit the right site.
        port: 8080,
        source: '^/(app|login|api|assets|files|private)(/|\\?|$)',
      },
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../ls_shop/www/commera.html',
        emptyOutDir: true,
        sourcemap: true,
        outDir: '../ls_shop/public/commera',
        target: 'es2015',
      },
    }),
    vue(),
  ],
  optimizeDeps: {
    exclude: ['frappe-ui'],
    include: [
      'feather-icons',
      'tippy.js',
      'engine.io-client',
      'socket.io-client',
      'debug',
    ],
  },
  server: {
    allowedHosts: true,
  },
})
