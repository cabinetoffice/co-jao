# jao-backend-schemas

The pydantic schemas as used by the backend.

This is used by jao-backend and can be used by anything that communicate with the backend.

# Rationale

By keeping schemas as a separate installable python module, applications that wish to communicate
with the backend can import them without all of the dependencies of the backend itself.