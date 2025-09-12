// Entrypoint for webpack.

import {
  initAll
} from "./govuk";

import {
    onAriaSelected,
    onDOMContentLoaded
} from "./helpers";

document.addEventListener('DOMContentLoaded', () => {
  initAll();
});

export {
    onAriaSelected,
    onDOMContentLoaded
}