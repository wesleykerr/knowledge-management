# Standard Library
import base64
import hashlib
import json

# Third Party
import anthropic
import httpx
import openai
import pydantic
import tiktoken

# Project
from bookmarks import models

MODEL = "gpt-4o"
tokenizer = tiktoken.encoding_for_model("gpt-4o")


def get_url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()


def get_content_hash(content, prompt_template, max_tokens):
    hash_string = f"{content}|{prompt_template}|{max_tokens}"

    return hashlib.sha256(hash_string.encode()).hexdigest()


def truncate_to_token_limit(content: str, max_tokens: int = 10_000) -> str:
    """Truncate content to stay within token limit.

    Args:
        content: Text content to truncate

    Returns:
        Content truncated to max_tokens if necessary
    """
    tokens = tokenizer.encode(content)
    if len(tokens) <= max_tokens:
        return content

    # Decode only the first max_tokens
    truncated_tokens = tokens[:max_tokens]
    return tokenizer.decode(truncated_tokens)


def call_llm(url_hash: str, content: str, system_prompt: str, user_prompt: str) -> str:
    truncated_content = truncate_to_token_limit(content)

    messages = (
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.format(content=truncated_content)},
        ],
    )

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )

    audit = models.ChatPromptAudit.create(
        response_id=response.id,
        url_hash=url_hash,
        model=MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        content_tokens=len(tokenizer.encode(truncated_content)),
        total_tokens=sum(len(tokenizer.encode(m["content"])) for m in messages),
        output=response.choices[0].message.content,
    )
    audit.save()
    return response.id, response.choices[0].message.content


def call_structured_llm(
    url_hash: str,
    content: str,
    system_prompt: str,
    user_prompt: str,
    response_format: pydantic.BaseModel = None,
) -> pydantic.BaseModel:
    truncated_content = truncate_to_token_limit(content)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt.format(content=truncated_content)},
    ]

    client = openai.OpenAI()
    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=messages,
        response_format=response_format,
    )

    audit = models.ChatPromptAudit.create(
        response_id=response.id,
        url_hash=url_hash,
        model=MODEL,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        content_tokens=len(tokenizer.encode(truncated_content)),
        total_tokens=sum(len(tokenizer.encode(m["content"])) for m in messages),
        output=response.choices[0].message.parsed.model_dump_json(),
    )
    audit.save()
    return response.id, response.choices[0].message.parsed


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

    # Finally send the API request
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

    token_count = 0
    for message in messages:
        for content in message["content"]:
            if "type" not in content:
                token_count += len(tokenizer.encode(content))
            elif content["type"] == "document":
                token_count += len(tokenizer.encode(content["source"]["data"]))
            else:
                token_count += len(tokenizer.encode(content["text"]))

    message_tokens = token_count
    system_tokens = len(tokenizer.encode(system_prompt))

    audit = models.ChatPromptAudit.create(
        response_id=response.id,
        url_hash=url_hash,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        content_tokens=message_tokens,
        total_tokens=message_tokens + system_tokens,
        output=json_string,
    )
    audit.save()
    return response.id, summary_obj
