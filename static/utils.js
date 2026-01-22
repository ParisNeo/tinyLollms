import {marked} from 'https://cdn.jsdelivr.net/npm/marked@4.3.0/lib/marked.esm.js';
import DOMPurify from 'https://cdn.jsdelivr.net/npm/dompurify@2.4.5/dist/purify.es.js';

export const mdToHtml = (src) => {
  const raw = marked.parse(src, {gfm:true, breaks:true});
  return DOMPurify.sanitize(raw);
};
