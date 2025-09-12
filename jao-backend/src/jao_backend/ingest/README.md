Data Ingest
===========

Parquet data ingest
===================

This initial ingester was for the legacy parquet file.

The legacy parquet file is a flat file that was formatted for the original jao streamlit app,
it was pre-processed by a data pipeline; so is fairly close to the schema in this
django app.

This enabled building out the database schema with a representative sample of data, as well as benchmarking
the difference that splitting embedding from the ingester made.


Data is extracted, transformed and loaded.
------------------------------------------

Since the source is a parquet file, it doesn't arrive in the Django ORM format, instead Pydantic schemas are used.
Each row of data in the parquet file is extracted and transformed

Source: django_schema.py
........................

These schemas map to django models, but don't have any transformations in them.

Any Django app with models that can be written to from the ingester has a schema: `ingest_schemas/django_schema.py`
These have a one-to-one match to the Django models (so the Vacancy model gets a VacancySchema) and are 
generated using djantic.ModelSchema.

Destination: parquet_schemas.py
...............................

The schemas here, specify how to transform and load data.
These extend the schemas from django_schema (so Vacancy is extended to IngestVacancy), and specify transformations:

Changing field names:
These are specified using pydantic alias:

Changing values:
Using Pydantic validators (e.g. a Django Model requires None and the data has -1)


Handling Foreign Key instances
..............................

Django needs actual model instances when populating a model with ForeignKeys, which can't be done using Pydantic, in
this, to workaround this ids are used, model_dump - dumps the data to a dict where ids are deleted and replaced with
model instances.

Load
....

At this point the dict is ready to pass to the Django model.   It would be possible to call .save() here,
but instead the the model instance is yielded, allowing for Bulk ingest.  



Bulk ingest
===========

The ingester attempts to balance being relatively frugal with resources, and be fast using bulk_create / bulk_update.

To do this, the parquet file is split into 5000 row chunks which are passed to process_chunk.

This has separate functions to create the vacancies, and applicant_statistics.

In this way, memory can be freeds between each, these functions broadly work by:

1. Query the database and remove any data already present from the dataframe.
2. Create dependencies
3. Generate the model instances and store in a list, using data transformed by Pydantic (see above)
4. Use Djangos bulk create / update functions to create the data.


Embedding: Not covered
======================

In previous versions of the app ingestion and embedding happened at the same time, this has been seperated
to it's own task to enable faster ingest, and greater flexibility in the embedding process (e.g. we can
add new embedders or text preperation techniques without needing to reingest data)
