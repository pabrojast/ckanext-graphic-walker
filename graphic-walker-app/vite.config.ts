import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../ckanext/graphic_walker/public/graphic-walker-app'),
    emptyOutDir: true,
    lib: {
      entry: path.resolve(__dirname, 'src/main.tsx'),
      name: 'GraphicWalkerCKAN',
      formats: ['iife'],
      fileName: () => 'graphic-walker-ckan.js',
    },
    rollupOptions: {
      output: {
        assetFileNames: 'graphic-walker-ckan.[ext]',
        inlineDynamicImports: true,
      },
    },
    cssCodeSplit: false,
    minify: 'esbuild',
    sourcemap: false,
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
});
