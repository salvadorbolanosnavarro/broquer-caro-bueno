import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';
const raiz=fileURLToPath(new URL('../',import.meta.url));
export default defineConfig({root:raiz+'mobile',publicDir:raiz+'public',plugins:[react()],resolve:{alias:{'@':raiz,'next/link':raiz+'mobile/navigation.tsx','next/navigation':raiz+'mobile/navigation.tsx'}},build:{outDir:raiz+'mobile-dist',emptyOutDir:true}});
