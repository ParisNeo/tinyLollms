/* Build script – bundles third‑party libs into a single ES‑module (optional for production) */
import {build} from 'esbuild';

await build({
  entryPoints: ['static/lollms_chat.js'],
  bundle: true,
  minify: true,
  format: 'esm',
  outfile: 'static/bundle.js',
  loader: {'.js':'js'},
  external: [
    // keep these as external if you prefer CDN loading
    'https://cdn.jsdelivr.net/*'
  ],
});
console.log('Bundle created: static/bundle.js');
