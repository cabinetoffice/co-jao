# Lookup of schemas to associate JAO models with Djantic2 schemas that can translate the OLEEO data
# to the JAO data model.
from typing import Type

from djantic import ModelSchema

OLEEO_MODEL_SCHEMAS = {}


def fully_qualified_name(cls):
    """
    Returns the fully qualified name of a class.
    """
    return f"{cls.__module__}.{cls.__name__}"


def register_oleeo_mapping(model_schema):
    """
    :param model_schema: The Djantic2 schema.

    One of the schemas in the class hierarchy must have a model set, pointing to
    the destination JAO django model.

    OLEEO_MODEL_SCHEMAS is populated with [fk_model_name] = model_schema.
    """
    # Get the base class (assuming it's the first one in __mro__ after the class itself)
    for base_class in model_schema.__mro__:
        if hasattr(base_class, 'model_config') and "model" in base_class.model_config:
            destination_model = base_class.model_config["model"]
            print(f"Registering {model_schema} for {destination_model}")
            OLEEO_MODEL_SCHEMAS[fully_qualified_name(destination_model)] = model_schema
            break
    else:
        raise ValueError("No model_config found in the class hierarchy.")

    return model_schema


def get_oleeo_schema_for_model(model) -> Type[ModelSchema]:
    """
    :param model: The model class to get the schema for.

    Given a django model return the Djantic2 schema that converts OLEEO data to it.
    """
    # Check if the model is already registered
    model_key = f"{model.__module__}.{model.__name__}"
    try:
        return OLEEO_MODEL_SCHEMAS[model_key]
    except KeyError:
        raise ValueError(f"No schema registered for model: {model_key}")
