/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND: 'python' | 'typescript';
  readonly VITE_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

