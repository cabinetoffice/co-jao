# """
# Database router for handling routing between default and Oleeo databases.
# This is placed in the common app as it's part of the project's core architecture.
# """


# class OleeoRouter:
#     """
#     A router to control database operations for the 'oleeo' app.

#     This router handles a multi-database setup where:
#     1. 'oleeo' database contains unmanaged views (different DB engine than default)
#     2. Data is ingested from Oleeo views into the default postgres database
#     3. Cross-database relations are not possible due to different DB engines

#     The router will:
#     1. Send all queries for models in the 'oleeo' app to the 'oleeo' database
#     2. Send all other queries to the default database
#     3. Prevent migrations from running on the unmanaged Oleeo database
#     4. Only allow relations between models in the same database
#     """

#     def db_for_read(self, model, **hints):
#         """
#         Route read operations to the appropriate database.
#         """
#         if model._meta.app_label == "oleeo":
#             return "oleeo"
#         return "default"

#     def db_for_write(self, model, **hints):
#         """
#         Route write operations to the appropriate database.
#         """
#         if model._meta.app_label == "oleeo":
#             return "oleeo"
#         return "default"

#     def allow_relation(self, obj1, obj2, **hints):
#         """
#         Allow relations only within the same database, as cross-database
#         relations are not possible between different database engines.
#         """
#         # Allow relations only between two models in the same database
#         if obj1._meta.app_label == obj2._meta.app_label:
#             return True

#         # For models in different apps, check if they're in the same database
#         if obj1._meta.app_label == "oleeo" and obj2._meta.app_label == "oleeo":
#             return True

#         if obj1._meta.app_label != "oleeo" and obj2._meta.app_label != "oleeo":
#             return True

#         # Disallow relations between models in different databases
#         return False

#     def allow_migrate(self, db, app_label, model_name=None, **hints):
#         """
#         Ensure migrations only run on the default database and
#         never on the unmanaged 'oleeo' database.
#         """
#         # Prevent any migrations on the oleeo database
#         if db == "oleeo":
#             return False

#         # Only run migrations for non-oleeo apps on the default database
#         if app_label == "oleeo":
#             return False

#         return db == "default"


# src/jao_backend/common/routers/router.py

# src/jao_backend/common/routers/router.py

class OleeoRouter:
    """
    Directs all database operations on oleeo models to the oleeo_upstream database.
    """
    route_app_labels = {'oleeo'}

    def db_for_read(self, model, **hints):
        """
        Reads from oleeo models go to the oleeo_upstream database.
        """
        if model._meta.app_label in self.route_app_labels:
            # Use the correct database alias
            return 'oleeo_upstream'
        # Return None to let other routers or the default behavior decide.
        return None

    def db_for_write(self, model, **hints):
        """
        Prevents any writes to the oleeo_upstream database.
        """
        if model._meta.app_label in self.route_app_labels:
            # This prevents accidental writes to your read-only database.
            return None
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the oleeo app is involved.
        """
        # This is a simple rule that works for cross-database relations in migrations.
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the oleeo app only "migrates" on the 'oleeo_upstream'
        database, and all other apps go to 'default'.
        """
        if app_label in self.route_app_labels:
            # This tells migrations that 'oleeo' models "live" on the upstream DB.
            return db == 'oleeo_upstream'
        # This allows your application_statistics app to migrate to the default DB.
        return db == 'default'