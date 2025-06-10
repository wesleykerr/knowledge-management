# Standard Library
import os
import uuid
from pathlib import Path

# Third Party
import peewee
import pydantic

# Project
from bookmarks import models
from bookmarks.processors import arxiv
from bookmarks.utils import llm

PATH = "/home/wkerr/sync/Obsidian/wkerr-kg/research-notes"

SYSTEM_PROMPT = """You are an expert at separating out markdown documents.
You will receive documents and need to extract the Notes section verbatim.
Additionally each note has several properties that we need to extract.

1. Whether or not the document was read, and if read what was the read_date.
2. The arxiv-url from the document.
3. When the document was added.
"""

USER_PROMPT = "Here is the content: {content}"


class ExpectedOutput(pydantic.BaseModel):
    notes: str = pydantic.Field(description="The notes section of the markdown document.")
    read: bool = pydantic.Field(description="Whether the document has been read.")
    read_date: str = pydantic.Field(description="When the document was read.")
    arxiv_url: str = pydantic.Field(description="The URL of the arxiv document.")
    added_date: str = pydantic.Field(description="When the document was added.")


def list_documents(path: str):
    """List all markdown documents in the research-notes folder."""
    docs_path = Path(path)
    markdown_files = []

    # Walk through all directories and files
    for root, dirs, files in os.walk(docs_path):
        for file in files:
            if file.endswith(".md"):
                full_path = Path(root) / file
                markdown_files.append(str(full_path))

    return markdown_files


if __name__ == "__main__":
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    docs = list_documents(PATH)
    for doc in docs:
        print(doc)
        with open(doc, "r") as input_io:
            data = input_io.read()
        _, results = llm.call_structured_llm(
            uuid.uuid4(), data, SYSTEM_PROMPT, USER_PROMPT, ExpectedOutput
        )
        results = results.model_dump()
        url = results.pop("arxiv_url")
        arxiv.process_arxiv_url(url, None, results)

        os.remove(doc)
