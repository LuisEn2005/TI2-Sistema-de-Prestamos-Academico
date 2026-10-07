import { defineConfig } from 'astro/config';

export default defineConfig({
  vite: {
    server: {
      proxy: {
        '/api': process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:5000',
      },
    },
  },
});
