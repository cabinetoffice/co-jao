Job Advert Optimiser Backend
==

Django app to serve the backend using [Django-Ninja](https://django-ninja.dev/).

Internal admin is available at `/admin/` and the API is available at `/api/`.

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


Environment variables:

| Variable | Description |
| JAO_BACKEND_DATABASE_URL | Database URL for the database to use (in the format dj_database_url accepts) |
| JAO_BACKEND_INGEST_DATABASE_URL | Database URL for the database to use (in the format dj_database_url accepts) |


Note:  To see a full list of environment variables, the jao_common.settings* files are the source of truth.

Prerequisites
---


NPM
Install npm then install dependencies:

```sh
$ npm install
```

Webpack

Webpack packs up Javascript and SCSS, during dev it can update these:

```sh
$ npm webpack start
``` 

To build resources for production:

```sh
$ npm webpack build
```


Poetry
Manages python dependencies and environments, install it, activate your virtualenv then use
it to install dependencies:

```sh
$ poetry install
```


Commands
---

Collect static resources, for production (if you are running locally with ENV=dev, you can keep an
empty static directory.)

```sh
$ python src/manage.py collectstatic
```

Migrate
```sh
$ python src/manage.py migrate
```

On pulling down a new version of the site from github you will need to run any new migrations.



Start the django dev server
```sh
$ python src/manage.py runserver
```


Start the django server via hypercorn async server
```sh
$ hypercorn asgi:application --reload
```

(The src directory does not need to be included here).


Celery
------

Celery requires celery-beat to orchestrate the tasks, and one or more celery workers.

Start celery-beat:

```
$ celery -A jao_backend.common.celery beat
```

Start a worker with loglevel INFO

```
$ celery -A jao_backend.common.celery worker --loglevel=INFO
```

Checking up on tasks:

You can use `celery inspect` or run `celery flower` for a GUI view:

```
$ celery -A jao_backend.common.celery flower
```

More info:

Celery is configured via the django settings, so see `jao_backend.settings*` and `jao_backend.common.celery`.

Redis (or a Redis compatible service) is used as the backend - this is compatible with the dependency celery-singleton/

Tasks:

Celery tasks can be found in `tasks.py`


Jupyter
-------

A Jupyter shell is available as `django-extensions` is installed.

Run Jupyter with:

```
$ python shell_plus --lab
```

This gives you a Jupyter shell with access to models in the Django ORM.


Databases and database urls:
----------------------------

Database connections are configured through environment variables (see the python package dj_database_url for the format)

Default database:

`JAO_BACKEND_DATABASE` is expected to be a postgres database, e.g. running locally it could be `postgres://postgres:postgres@localhost/jao-backend`


OLEOO database:

`JAO_BACKEND_OLEEO_DATABASE` is expected to be a SQLServer database, e.g. the format looks like this: `mssqlms://username:password@example.com:1433/database_name`

GRID holds a copy of the OLEEO database in a format the ORM can ingest it,
the particulars of this are in the oleeo app, while ingest code itself lives in the ingest app.

This is an mssql database, installing from poetry will enable the python libraries for this,
system libraries are also required:

Installing ODBC libraries using homebrew:

Pre-requisites:
- Homebrew
- Xcode command line tools

```sh
$ brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
$ brew update
$ HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql17 mssql-tools
```

(This info adapted from https://iamsimi.medium.com/development-on-the-m1-mac-connecting-to-microsoft-sql-server-using-python-14fd5012c8d6)

For more detail, see the README.md in oleoo and ingest apps:

[oleeo](src/jao_backend/oleeo/README.md)
[ingest](src/jao_backend/ingest/README.md)
