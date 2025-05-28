// Setup webpack for govuk
import 'govuk-frontend/dist/govuk/all.mjs';
import "../scss/govuk.scss";

// Import icons to ensure they are processed by Webpack
import 'govuk-frontend/dist/govuk/assets/images/favicon.ico';
import 'govuk-frontend/dist/govuk/assets/images/favicon.svg';
import 'govuk-frontend/dist/govuk/assets/images/govuk-icon-180.png';
import 'govuk-frontend/dist/govuk/assets/images/govuk-icon-192.png';
import 'govuk-frontend/dist/govuk/assets/images/govuk-icon-512.png';
import 'govuk-frontend/dist/govuk/assets/images/govuk-icon-mask.svg';
import 'govuk-frontend/dist/govuk/assets/images/govuk-opengraph-image.png';
import {initAll} from "govuk-frontend";

export {initAll};
