import { EditorState } from "@codemirror/state";
import { EditorView, keymap, highlightSpecialChars, drawSelection, highlightActiveLine, dropCursor, rectangularSelection, crosshairCursor, lineNumbers, highlightActiveLineGutter } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search";
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete";
import { foldGutter, indentOnInput, syntaxHighlighting, defaultHighlightStyle, bracketMatching, foldKeymap } from "@codemirror/language";
import { lintKeymap } from "@codemirror/lint";
import { oneDark } from "@codemirror/theme-one-dark";
import { javascript } from "@codemirror/lang-javascript";

// Build our own basic setup with v6 packages
const basicSetup = [
  lineNumbers(),
  highlightActiveLineGutter(),
  highlightSpecialChars(),
  history(),
  foldGutter(),
  drawSelection(),
  dropCursor(),
  EditorState.allowMultipleSelections.of(true),
  indentOnInput(),
  syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
  bracketMatching(),
  closeBrackets(),
  autocompletion(),
  rectangularSelection(),
  crosshairCursor(),
  highlightActiveLine(),
  highlightSelectionMatches(),
  keymap.of([
    ...closeBracketsKeymap,
    ...defaultKeymap,
    ...searchKeymap,
    ...historyKeymap,
    ...foldKeymap,
    ...completionKeymap,
    ...lintKeymap
  ])
];

let initialized = false;

export function initializeEditors() {
  if (initialized) return;

  for (const scriptEl of document.querySelectorAll(".script-data")) {
    const sourceCode = JSON.parse(scriptEl.textContent);
    const container = scriptEl.parentElement.querySelector(".script-editor-container");
    if (!container) continue;

    container.textContent = "";

    // Calculate number of lines
    const lineCount = sourceCode.split('\n').length;
    const displayLines = Math.min(lineCount, 20);

    // Calculate height: line height ~20px + padding/border + 1 extra line
    const editorHeight = (displayLines + 1) * 20 + 10;

    const state = EditorState.create({
      doc: sourceCode,
      extensions: [
        basicSetup,
        oneDark,
        javascript(),
        EditorView.editable.of(false),
        EditorState.readOnly.of(true),
      ],
    });

    const view = new EditorView({ state, parent: container });

    // Set dynamic height on the editor and scroller
    view.dom.style.height = `${editorHeight}px`;
    view.dom.style.width = '100%';

    const scroller = view.dom.querySelector('.cm-scroller');
    if (scroller) {
      scroller.style.height = `${editorHeight}px`;
      scroller.style.maxHeight = `${editorHeight}px`;
      scroller.style.width = '100%';
      scroller.style.maxWidth = '100%';
    }
  }

  initialized = true;
}

export function wireScriptsTab() {
  const scriptsTab = document.getElementById("tab-scripts");
  if (!scriptsTab) return;

  scriptsTab.addEventListener("change", () => {
    if (scriptsTab.checked) setTimeout(initializeEditors, 0);
  });

  if (scriptsTab.checked) setTimeout(initializeEditors, 0);
}
