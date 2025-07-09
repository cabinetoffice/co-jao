"""
Schema registry.

Associate upstream models we want to ingest with Djantic2 schemas
that define the transformations the data goes through.

pydantic schemas define:  Fields renaming operations (by defining aliases), and basic data type
transformations (e.g. converting a string to a datetime, with validators.
"""

from typing import Type

from djantic import ModelSchema

UPSTREAM_MODEL_SCHEMAS = {}


def fully_qualified_name(cls):
    """
    Returns the fully qualified name of a class.
    """
    return f"{cls.__module__}.{cls.__name__}"


def register_upstream_mapping(model_schema):
    """
    :param model_schema: The Djantic2 schema.

    Populate UPSTREAM_MODEL_SCHEMAS with the destination name of the model referenced by
    the djantic schema as:

    UPSTREAM_MODEL_SCHEMAS[fully_qualified_model_name] = model_schema.

    This is achieved by travelling up the class hierarchy of the model_schema and stopping
    when we find a class with a `model_config` attribute that contains a `model` key.
    """
    # Get the base class (assuming it's the first one in __mro__ after the class itself)
    for base_class in model_schema.__mro__:
        if hasattr(base_class, "model_config") and "model" in base_class.model_config:
            destination_model = base_class.model_config["model"]
            fk_destination_model = fully_qualified_name(destination_model)
            if fk_destination_model in UPSTREAM_MODEL_SCHEMAS:
                raise ValueError(
                    f"Schema for {fk_destination_model} is already registered."
                )

            UPSTREAM_MODEL_SCHEMAS[fk_destination_model] = model_schema
            break
    else:
        raise ValueError("No model_config found in the class hierarchy.")

    return model_schema


def get_upstream_schema_for_model(model) -> Type[ModelSchema]:
    """
    :param model: The model class to get the schema for.

    Given a django model return the Djantic2 schema that converts upstream data to it.
    """
    # Check if the model is already registered
    model_key = f"{model.__module__}.{model.__name__}"
    try:
        return UPSTREAM_MODEL_SCHEMAS[model_key]
    except KeyError:
        raise ValueError(f"No schema registered for model: {model_key}")
