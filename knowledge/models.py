# Standard Library
import datetime
import json
import sqlite3

# Third Party
import peewee

db = peewee.Proxy()


class ListField(peewee.TextField):
    def db_value(self, value):
        if value:
            value = ",".join(value)
        return value

    def python_value(self, value):
        return value.split(",") if value else []


class DictField(peewee.TextField):
    def db_value(self, value):
        if value:
            value = json.dumps(value, sort_keys=True)
        return value

    def python_value(self, value):
        return json.loads(value) if value else {}


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Bookmark(BaseModel):
    url_hash = peewee.CharField(max_length=256, primary_key=True)
    url = peewee.TextField()
    title = peewee.TextField()
    add_date = peewee.DateTimeField(default=datetime.datetime.now)
    status = peewee.SmallIntegerField(index=True)


class WebPage(BaseModel):
    url_hash = peewee.CharField(max_length=256, primary_key=True)
    url = peewee.TextField()
    content = peewee.TextField()
    last_checked = peewee.DateTimeField(default=datetime.datetime.now)


class ReadabilityPage(BaseModel):
    url_hash = peewee.CharField(max_length=256, primary_key=True)
    url = peewee.TextField()
    content = DictField()
    last_checked = peewee.DateTimeField(default=datetime.datetime.now)


class ReadabilityHTMLPage(BaseModel):
    url_hash = peewee.CharField(max_length=256, primary_key=True)
    url = peewee.TextField()
    content = peewee.TextField()
    last_checked = peewee.DateTimeField(default=datetime.datetime.now)


class Error(BaseModel):
    url_hash = peewee.CharField(max_length=256, primary_key=True)
    url = peewee.TextField()
    title = peewee.TextField()
    exception = peewee.TextField()
    stack_trace = peewee.TextField()
    error_datetime = peewee.DateTimeField(default=datetime.datetime.now)


class Summary(BaseModel):
    url_hash = peewee.CharField(max_length=256, primary_key=True)
    url = peewee.TextField(null=True)
    summary = peewee.TextField(null=True)
    tags = ListField(null=True)
    markdown = peewee.TextField(null=True)
    filename = peewee.TextField(null=True)


class AuditAPI(BaseModel):
    content_hash = peewee.CharField(max_length=256)
    call_type = peewee.CharField(max_length=10)
    provider = peewee.CharField(max_length=20)
    content = peewee.TextField()
    prompt_template = peewee.TextField()
    prediction_id = peewee.CharField(max_length=64)
    output = peewee.TextField()
    called_at = peewee.DateTimeField(default=datetime.datetime.now)

    class Meta:
        primary_key = peewee.CompositeKey("content_hash", "call_type", "provider")


class ChatPromptAudit(BaseModel):
    response_id = peewee.CharField(max_length=64, primary_key=True)
    url_hash = peewee.CharField(max_length=256, index=True)
    model = peewee.CharField()
    system_prompt = peewee.TextField()
    user_prompt = peewee.TextField()
    content_tokens = peewee.IntegerField()
    total_tokens = peewee.IntegerField()
    output = peewee.TextField()
    called_at = peewee.DateTimeField(default=datetime.datetime.now)
