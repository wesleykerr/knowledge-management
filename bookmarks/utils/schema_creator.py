# Standard Library
import json

# Third Party
import pydantic


class ExpectedOutput(pydantic.BaseModel):
    notes: str = pydantic.Field(description="The notes section of the markdown document.")
    read: bool = pydantic.Field(description="Whether the document has been read.")
    read_date: str = pydantic.Field(description="When the document was read.")
    arxiv_url: str = pydantic.Field(description="The URL of the arxiv document.")


# Function to inline references and add `additionalProperties: false`
def inline_and_enforce_additional_properties(schema, definitions):
    """Recursively replace $ref and enforce additionalProperties: false."""
    if isinstance(schema, dict):
        # Inline $ref
        if "$ref" in schema:
            ref_name = schema["$ref"].split("/")[-1]
            if ref_name in definitions:
                return inline_and_enforce_additional_properties(definitions[ref_name], definitions)
        # Process object types
        if schema.get("type") == "object":
            schema["additionalProperties"] = False
        # Recursively process properties and items
        if "properties" in schema:
            for key, value in schema["properties"].items():
                schema["properties"][key] = inline_and_enforce_additional_properties(
                    value, definitions
                )
        if "items" in schema:
            schema["items"] = inline_and_enforce_additional_properties(schema["items"], definitions)
    return schema


def generate_openai_schema(model: pydantic.BaseModel, name: str):
    """Generate schema from Pydantic model, inline references, and enforce strict validation."""
    # Generate JSON schema from Pydantic
    model_schema = model.model_json_schema()
    definitions = model_schema.get("$defs", {})
    # Inline references and enforce strict validation
    processed_schema = inline_and_enforce_additional_properties(model_schema, definitions)
    processed_schema.pop("$defs", None)  # Remove unused $defs
    # Wrap in OpenAI's format
    openai_schema = {"name": name, "schema": processed_schema, "strict": True}
    return openai_schema


# Generate the schema for ExpectedOutput
openai_schema = generate_openai_schema(ExpectedOutput, "expected_output")

# Print the schema as JSON
print(json.dumps(openai_schema, indent=2))
