/* Utility helpers – markdown, math, sanitisation */
import {marked} from 'https://cdn.jsdelivr.net/npm/marked@4.3.0/lib/marked.esm.js';
import DOMPurify from 'https://cdn.jsdelivr.net/npm/dompurify@2.4.5/dist/purify.es.js';

/**
 * Convert markdown string to safe HTML.
 * @param {string} src
 * @returns {string} sanitized HTML
 */
export const mdToHtml = (src) => {
  const raw = marked.parse(src, {gfm:true, breaks:true});
  return DOMPurify.sanitize(raw);
};

/**
 * Render KaTeX math inside a container using the global `renderMathInElement`.
 * @param {Element} container
 */
export const renderMath = (container) => {
  if (typeof renderMathInElement === "function") {
    renderMathInElement(container, {
      delimiters: [
        {left:"$", right:"$", display:false},
        {left:"$$", right:"$$", display:true}
      ],
      throwOnError:false,
      errorColor:"#cc0000"
    });
  }
};
