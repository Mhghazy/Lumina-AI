import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [],
  base: '/Database008/',
  // Serve public/index.html as the main entry
  root: './public',
  publicDir: false, // public folder is already the root
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
});
