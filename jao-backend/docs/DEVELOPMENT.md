NPM/NPX based tools.
===

NPM based tools are used to build and bundle resources such as CSS via SASS - this is all bundled together via Webpack


Webpack
----

Resources are bundled using webpack, somewhat based on https://saashammer.com/blog/setup-webpack-project-django/ 
but adjusted to govuk-frontend instead of bootstrap where appropriate.

This folder holds webpack config for dev and prod (webpack.dev.js and webpack.prod respectively)

AThese files configure how to chunk resources from the application and it's dependencies.





Webpack under dev:

Dev is optimised for easier debugging and faster loading of indvidual components, and can be build with:

```
$ npm run build:dev```
```

Prod is optimised for faster overall loading and can be built with:

```
$ npm run build:prod
```

Ingest Data
===========

The data ingester, ingests a parquet file from an S3 bucket, this can can be minio running on localhost

```
$ python src/manage.py ingest s3://localhost:9001/browser/loader/all_data_8.parquet
```

Migrations
===

See the Django docs for commands -
https://docs.djangoproject.com/en/5.1/topics/migrations/

In general with changes, you may build up migrations while developing on a branch but it is best to flatten them
before pushing your PR.



Celery
======

Celery https://docs.celeryq.dev/ is used orchestrate and run background tasks.

Celery tasks are found in `tasks.py` files, the entrypoint for celery is in jao_backend.common.celery


