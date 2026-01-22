import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [],
  base: '/Database008/',
  // Root is default (current directory)
  // root: './public', // REMOVED

  // publicDir defaults to "public", which is correct now.

  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: 'index.html',
        all_suppliers: 'all_suppliers.html',
        clients: 'clients.html',
        color_preview: 'color-preview.html',
        hot_vendors: 'hot_vendors.html',
        settings: 'settings.html',
      },
    },
  },
});
