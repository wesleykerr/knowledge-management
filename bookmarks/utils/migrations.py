# Standard Library
import functools
import json
import logging
import os
from datetime import datetime

# Third Party
import click
import peewee
from playhouse.migrate import SchemaMigrator
from playhouse.migrate import migrate as migrate_fn

# Project
from bookmarks import models

MIGRATIONS = []

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
)


def get_db():
    """Creates a connection to the MySQL database."""
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)
    return db


class DatabaseVersion(peewee.Model):
    """This class stores the current status of the database so that migrations can automatically be perfomed."""

    migrations_applied = peewee.TextField()

    class Meta:
        database = models.db
        db_table = "database_versions"


def audit_migration(func):
    @functools.wraps(func)
    def wrapper(db):
        func(db)

        version = DatabaseVersion()
        version.migrations_applied = func.__name__
        version.save()

    return wrapper


def register_migration(func):
    MIGRATIONS.append(func)


@audit_migration
def migration_1_0_2(db):
    db.create_tables(
        [
            models.ChatPromptAudit,
        ],
        safe=True,
    )


@audit_migration
def migration_1_0_1(db):
    try:
        migrator = SchemaMigrator(db)
        migrate_fn(
            migrator.add_column("summary", "filename", peewee.TextField(null=True)),
        )
    except peewee.OperationalError as op_error:
        if "duplicate column name: filename" in str(op_error):
            return
        raise op_error


@audit_migration
def migration_1_0_0(db):
    db.create_tables(
        [
            models.Bookmark,
            models.WebPage,
            models.ReadabilityPage,
            models.ReadabilityHTMLPage,
            models.Error,
            models.Summary,
            models.AuditAPI,
        ],
        safe=True,
    )


@click.group()
def main():
    pass


@main.command()
def migrate():
    register_migration(migration_1_0_0)
    register_migration(migration_1_0_1)
    register_migration(migration_1_0_2)

    try:
        db = get_db()
        db.create_tables([DatabaseVersion], safe=True)
        for migration in MIGRATIONS:
            try:
                DatabaseVersion.get(DatabaseVersion.migrations_applied == migration.__name__)
            except peewee.DoesNotExist:
                logging.info("Running migration: {}".format(migration.__name__))
                migration(db)
        logging.info("Database is up to date!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
