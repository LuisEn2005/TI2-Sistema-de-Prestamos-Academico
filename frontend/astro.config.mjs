import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

const raizRepositorio = fileURLToPath(new URL('../', import.meta.url));
const entorno = loadEnv(process.env.NODE_ENV ?? 'development', raizRepositorio, '');

export default defineConfig({
  vite: {
    server: {
      proxy: {
        '/api': process.env.API_PROXY_TARGET
          || entorno.API_PROXY_TARGET
          || 'http://127.0.0.1:5000',
      },
    },
  },
});
