Development Guide
=================

Setup Instructions
------------------

Getting Started
~~~~~~~~~~~~~~~

1. **Clone the repository**

   .. code-block:: bash

      git clone <repository-url>
      cd jao-backend

2. **Set up virtual environment**

   .. code-block:: bash

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**

   .. code-block:: bash

      pip install -r requirements.txt

4. **Environment Configuration**

   Copy the example environment file and configure:

   .. code-block:: bash

      cp .env.example .env
      # Edit .env with your database and other settings

5. **Database Setup**

   .. code-block:: bash

      python manage.py migrate
      python manage.py createsuperuser

6. **Run Development Server**

   .. code-block:: bash

      python manage.py runserver

Project Structure
-----------------

The Job Application Optimiser (JAO) Backend is organized as a Django project
using the **src layout** with all code under ``src/jao_backend/``.

Core Applications
~~~~~~~~~~~~~~~~~

* **vacancies** - Core vacancy management and job posting functionality

  - ``models.py`` - Vacancy, VacancyGrade, VacancyRoleType, VacancyEmbedding
  - ``tasks.py`` - Background tasks for vacancy processing
  - ``embed.py`` - AI embedding generation for semantic search
  - ``querysets.py`` - Custom database query logic

* **roles** - Job roles, grades, and role type management

  - ``models.py`` - RoleType, Grade, OleeoGradeGroup, OleeoRoleTypeGroup
  - ``enums.py`` - Role-related enumeration values
  - ``querysets.py`` - Role and grade query logic

* **embeddings** - AI embedding functionality for semantic search

  - ``models.py`` - Embedding, EmbeddingModel, EmbeddingTag, TaggedEmbedding
  - ``querysets.py`` - Embedding query and retrieval logic

* **oleeo** - OLEEO system integration for data synchronization

  - ``models.py`` - All OLEEO database table models (Applications, Vacancies, etc.)
  - ``base_models.py`` - Base classes for OLEEO models
  - ``sync_primitives.py`` - Data synchronization utilities
  - ``querysets.py`` - OLEEO-specific query logic
  - ``errors.py`` - OLEEO integration error handling

* **application_statistics** - Application analytics and reporting

  - ``models/statistics.py`` - Statistical models and calculations
  - ``models/lists.py`` - Reference data for statistics

* **ingest** - Data ingestion processes and ETL operations

  - ``ingester/`` - Core ingestion logic
  - ``management/commands/`` - Django management commands for data processing
  - ``ingest_schemas/`` - Data validation schemas

* **departments** - Department and organizational structure management
* **common** - Shared utilities, base models, and common functionality

  - ``db/`` - Database utilities (fields, functions, models)
  - ``celery/`` - Background task configuration
  - ``text_processing/`` - Text cleaning and processing utilities
  - ``management/`` - Common management commands and helpers

Supporting Applications
~~~~~~~~~~~~~~~~~~~~~~~

* **home** - Main dashboard and landing pages
* **api** - REST API endpoints and serializers (includes v0 API)
* **healthcheck** - System health monitoring endpoints
* **inline_exceptions** - Debug and exception handling utilities

Key Directories
~~~~~~~~~~~~~~~

.. code-block::

   jao-backend/
   ├── src/jao_backend/           # Main Django project (src layout)
   │   ├── settings/              # Environment-specific settings
   │   ├── vacancies/             # Core vacancy management
   │   ├── roles/                 # Job roles and grades
   │   ├── embeddings/            # AI embeddings
   │   ├── oleeo/                 # OLEEO integration
   │   ├── ingest/                # Data ingestion
   │   ├── application_statistics/ # Analytics
   │   ├── common/                # Shared utilities
   │   └── ...                    # Other apps
   ├── docs/                      # Sphinx documentation
   ├── requirements/              # Dependency management
   └── scripts/                   # Deployment and utility scripts

Development Workflow
--------------------

Local Development
~~~~~~~~~~~~~~~~~

1. **Activate virtual environment**

   .. code-block:: bash

      source venv/bin/activate

2. **Install development dependencies**

   .. code-block:: bash

      pip install -r requirements/dev.txt

3. **Run migrations**

   .. code-block:: bash

      python manage.py migrate

4. **Start development server**

   .. code-block:: bash

      python manage.py runserver

Data Management
~~~~~~~~~~~~~~~

The JAO Backend integrates with OLEEO for vacancy and application data:

* **Data Ingestion**: ``python manage.py ingest`` - Synchronize data from OLEEO
* **Embedding Generation**: ``python manage.py embed_vacancies`` - Generate AI embeddings
* **Statistics**: ``python manage.py aggregate_statistics`` - Update analytics
* **Vacancy Updates**: ``python manage.py update_vacancies`` - Refresh vacancy data

Background Tasks
~~~~~~~~~~~~~~~

JAO uses Celery for background processing:

.. code-block:: bash

   # Start Celery worker
   celery -A jao_backend worker -l info

   # Start Celery beat (scheduler)
   celery -A jao_backend beat -l info

   # Clear task locks if needed
   python manage.py clear_task_locks

Testing
-------

Running Tests
~~~~~~~~~~~~~

Run the full test suite:

.. code-block:: bash

   python manage.py test

Run specific app tests:

.. code-block:: bash

   python manage.py test jao_backend.vacancies
   python manage.py test jao_backend.embeddings
   python manage.py test jao_backend.oleeo

Test Coverage
~~~~~~~~~~~~~

Generate coverage reports:

.. code-block:: bash

   coverage run --source='src' manage.py test
   coverage report
   coverage html

Database Testing
~~~~~~~~~~~~~~~~

The project uses separate test models in ``jao_backend.oleeo.tests.models``
for testing OLEEO integration without requiring the actual OLEEO database connection.
This allows for isolated testing of synchronization logic.

Code Quality
------------

Formatting and Linting
~~~~~~~~~~~~~~~~~~~~~~

The project follows standard Python formatting:

.. code-block:: bash

   # Format code
   black src/

   # Sort imports
   isort src/

   # Lint code
   flake8 src/

Pre-commit Hooks
~~~~~~~~~~~~~~~

Install pre-commit hooks to ensure code quality:

.. code-block:: bash

   pre-commit install

Documentation
-------------

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

Generate Sphinx documentation:

.. code-block:: bash

   cd docs/
   make html

The documentation will be available in ``docs/_build/html/``.

Each Django app has its own ``README.md`` with specific information:

* ``src/jao_backend/vacancies/README.md``
* ``src/jao_backend/oleeo/README.md``
* ``src/jao_backend/ingest/README.md``
* ``src/jao_backend/roles/README.md``
* And others...

API Documentation
~~~~~~~~~~~~~~~~

API documentation is auto-generated from docstrings. Ensure all public
methods and classes have proper docstrings following the Google/NumPy style.

Deployment
----------

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

Configure environment variables for different deployment stages:

* ``DEBUG`` - Set to False in production
* ``DATABASE_URL`` - Database connection string
* ``LITELLM_API_BASE`` - AI service endpoint for embeddings
* ``LITELLM_CUSTOM_PROVIDER`` - AI service provider configuration
* ``CELERY_BROKER_URL`` - Message broker for background tasks
* ``EMBEDDING_TAGS`` - Configuration for embedding tag management

Production Checklist
~~~~~~~~~~~~~~~~~~~~

1. Set ``DEBUG = False`` in production settings
2. Configure proper ``ALLOWED_HOSTS``
3. Set up database with proper credentials and connection pooling
4. Configure static file serving (WhiteNoise or CDN)
5. Set up Celery workers for background tasks
6. Configure logging and monitoring (Sentry, etc.)
7. Set up backup procedures for database and media files
8. Configure OLEEO database connection for data synchronization

Background Tasks
~~~~~~~~~~~~~~~

JAO uses Celery extensively for data processing:

.. code-block:: bash

   # Production Celery setup
   celery -A jao_backend worker -l info --concurrency=4
   celery -A jao_backend beat -l info

   # Monitor tasks
   celery -A jao_backend inspect active
   celery -A jao_backend inspect scheduled

Contributing
------------

Development Standards
~~~~~~~~~~~~~~~~~~~~

* Follow PEP 8 coding standards
* Write comprehensive docstrings for all public APIs
* Include unit tests for new functionality
* Update documentation for significant changes
* Each Django app should have its own README.md

Pull Request Process
~~~~~~~~~~~~~~~~~~~

1. Create feature branch from main
2. Implement changes with tests
3. Update relevant README.md files
4. Update main documentation if needed
5. Submit pull request with clear description
6. Address code review feedback
7. Ensure CI checks pass

Code Review Guidelines
~~~~~~~~~~~~~~~~~~~~~

* Focus on code clarity and maintainability
* Verify test coverage for new features
* Check for security implications (especially data handling)
* Ensure proper error handling
* Validate database migration safety
* Review OLEEO integration impacts

Troubleshooting
--------------

Common Issues
~~~~~~~~~~~~~

**Database Connection Errors**
   Check your ``.env`` file database configuration and ensure the database server is running.

**Import Errors with src Layout**
   Verify your Python path includes the ``src/`` directory and all dependencies are installed.
   The project uses ``src/jao_backend/`` as the package root.

**Embedding Service Errors**
   Check ``LITELLM_API_BASE`` and ``LITELLM_CUSTOM_PROVIDER`` configuration.
   Ensure the AI service is accessible and API keys are valid.

**Celery Task Failures**
   Verify Redis/RabbitMQ broker is running and ``CELERY_BROKER_URL`` is correct.
   Check worker logs for specific error details.

**OLEEO Synchronization Issues**
   Verify OLEEO database connection settings and permissions.
   Check the OLEEO integration logs for synchronization errors.

**Migration Conflicts**
   When working with multiple developers, migration conflicts may occur.
   Use ``python manage.py makemigrations --merge`` to resolve conflicts.

Getting Help
~~~~~~~~~~~~

* Check the app-specific README.md files in each Django app
* Review existing issues in the project repository
* Consult the Django documentation for framework-specific issues
* Check Celery documentation for background task issues
* Review OLEEO integration documentation for data sync problems

Development Tips
~~~~~~~~~~~~~~~

* Use ``python manage.py shell_plus`` for enhanced Django shell with auto-imports
* Enable Django Debug Toolbar in development for SQL query analysis
* Use ``python manage.py show_urls`` to list all available URL patterns
* Monitor Celery task queues during development: ``celery -A jao_backend inspect active``