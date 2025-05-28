OLEEO application
=================

This Django Application models the OLEEO data held in the r2d2 database on GRID.

Ingest itself doesn't happen in this app (see `ingest` for that).

Why
---

Keeping OLEEO data here enables us to have a router (in `jao_backend/common/routers.py`) to direct data access here to
the sqlserver r2d2 database, as opposed to the default Postgres database.

This keeps the ingest simple; as the Django ORM is used for reading from OLEEO and writing to the default Postgres
database.

These databases are both configured in the DATABASES key in common/settings.py by environment variables.

Prerequisites
-------------

A connection to the r2d2 database; this is configured using the 

Initial models creation
-----------------------

The models here reflect views in grid.

By convention, those views should following the naming conventions used in the tables they reference,
the names are converted to underscore_case where needed, but otherwise the names are preserved, and
should reflect the names of the columns in the tables they reference, adhering to the principle
of least surprise.

The models here were obtained by the following process:

1. Using inspectdb to generate initial models.py
................................................

`$ python src/manage.py inspectdb --database oleeo`

2. Editing the models.py
........................

The generated models.py has a comment that mentions edits are required, see `Manual model and field changes` for
info on the required changes.


Updating models to reflect changes in the database
--------------------------------------------------

The recommended workflow is to use inspectdb to output models, then find the model(s) with changes.
Carefully bring over the required changes into the models.py in this app.

The app can then be deployed with the new changes.


A change was made in the database, but the app cannot be deployed
-----------------------------------------------------------------

In this case updating the Views in the database to map the fields will work.

It is strongly recommended to revisit afterwards and make the View match the underlying table,
fixup the models in the app and redeploy.

Maintaining consistency in these mappings will make the app easier to maintain and debug in the future.

See `Manual model and field changes` and make edits described there.


Manual model and field changes:
-------------------------------

The models and fields should be edited as described here.

Models
......

Naming:
Remove underscores and use the CamelCase.

```python
class Applications(models.Model):
    ....
```

ListModels (such as ListAgeGroups):

These should be edited to extend ListModelBase instead of Model.

add a destination_model attribute to the class, with the {application_name}.{model_name} it 
should be synched to.


```python

Fields
......

General field naming:  
The column name, with underscore_case, e.g.: ```application_id```


Primary key fields:
set `primary_key=True`


ForeignKey fields:
Use the `ForeignKey` type.


Rename the field by removing the `_id` suffix and set `db_column` to the original name (important!),
Set `related_name` to the name of the model in underscore_case.

```python
# before
class Applications(models.Model):
    vacancy_id = models.IntegerField()
    ...
```
```python
# after
class Applications(models.Model):
    vacancy = models.ForeignKey('Vacancies', models.DO_NOTHING, db_column='vacancy_id', related_name='applications')
    ...
```

Currency fields:
These should use DecimalField.
