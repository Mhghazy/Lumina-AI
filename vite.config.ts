import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  // Serve public/index.html as the main entry
  root: './public',
  publicDir: '../public-assets',
  build: {
    outDir: '../dist',
  },
});
