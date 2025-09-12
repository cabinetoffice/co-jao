Job Advert Optimiser Web
==

Django based frontend for the job advert optimiser.


File layout
---

This project uses src layout.


Configuration
---

Settings are in src, with per environment settings extending `common.py`.
Per-environment settings:
- `dev.py`
- `production.py`
- `test.py`

Where applicable dotenv is used to override settings.


Prerequisites
---
`jao_backend` is a fastapi app that provides backing services to jao_web and must be running.


NPM
Install npm then install dependencies:

```sh
$ npm install
```

Webpack

Webpack packs up Javascript and SCSS, during dev it can update these:

```sh
$ npm run serve
```

To build resources for production:

```sh
$ npm run build
```


Poetry
Manages python dependencies and environments, install it, activate your virtualenv then use
it to install dependencies:

```sh
$ poetry install
```


Commands
---

Start the django dev server
```sh
$ python src/manage.py runserver
```


Start the django server via hypercorn async server
```sh
$ hypercorn asgi:application --reload
```

(The src directory does not need to be included here).


Collect static resources, for production
```sh
$ python src/manage.py collectstatic
```


Testing
---

Test pure Javascript components:

```sh
npm test
```

These are not E2E tests using the browser, but unit tests using JSDom.


Unit tests
---

```
$ pytest
```

Integration tests
---

```sh
$ pytest --with-integration
```

These tests require the backend to be running, and exercise the end points for this.
