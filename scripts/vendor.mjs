import { copyFile, mkdir } from 'node:fs/promises';
const destination = new URL('../blogboard/web/js/vendor/', import.meta.url);
await mkdir(destination, { recursive: true });
for (const [source, name] of [
  ['marked/lib/marked.umd.js', 'marked.umd.js'],
  ['dompurify/dist/purify.min.js', 'purify.min.js'],
  ['marked/LICENSE', 'marked.LICENSE'],
  ['dompurify/LICENSE', 'dompurify.LICENSE'],
  ['dompurify/LICENSE-MPL', 'dompurify.LICENSE-MPL'],
]) {
  await copyFile(new URL(`../node_modules/${source}`, import.meta.url), new URL(name, destination));
}