// Per-Django App entrypoint for webpack.
// This should include anything not included common/../base.js

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import {
  renderApplicantMap
} from './applicant_map.js';

export {
  renderApplicantMap,
}