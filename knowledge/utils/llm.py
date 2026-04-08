# Standard Library
import base64
import hashlib

# Third Party
import anthropic
import httpx
import pydantic

# Project
from knowledge import models


def get_url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()


def get_content_hash(content, prompt_template, max_tokens):
    hash_string = f"{content}|{prompt_template}|{max_tokens}"
    return hashlib.sha256(hash_string.encode()).hexdigest()


def call_structured_llm_with_pdf(
    url_hash: str,
    system_prompt: str,
    user_prompt: str,
    pdf_url: str,
    response_format: pydantic.BaseModel = None,
) -> pydantic.BaseModel:
    model = "claude-3-5-sonnet-20241022"
    pdf_data = base64.standard_b64encode(httpx.get(pdf_url).content).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {
                    "type": "text",
                    "text": user_prompt,
                },
            ],
        },
        {"role": "assistant", "content": "Here is the JSON requested:\n{"},
    ]

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=model,
        betas=["pdfs-2024-09-25"],
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    json_string = "{" + response.content[0].text
    try:
        summary_obj = response_format.model_validate_json(json_string)
    except Exception as e:
        print(e)
        print(json_string)
        raise e
    print(summary_obj)

    audit = models.ChatPromptAudit.create(
        response_id=response.id,
        url_hash=url_hash,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        content_tokens=0,
        total_tokens=0,
        output=json_string,
    )
    audit.save()
    return response.id, summary_obj
