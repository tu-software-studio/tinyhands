from __future__ import unicode_literals

import glob
import gzip
import os
import warnings
import re
import zipfile
from itertools import product

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import  CommandError
from django.core.management.color import no_style
from django.core.management.utils import parse_apps_and_model_labels
from django.db import (
    DEFAULT_DB_ALIAS, DatabaseError, IntegrityError, connections, router
)
from django.utils.encoding import force_str
from django.utils.functional import cached_property
import json

from dataentry.models.form import FormType, Category, Storage

try:
    import bz2
    has_bz2 = True
except ImportError:
    has_bz2 = False

_magic_check = re.compile('([*?[])')

def glob_escape(pathname):
    drive, pathname = os.path.splitdrive(pathname)
    pathname = _magic_check.sub(r'[\1]', pathname)
    return drive + pathname


class LoadFormData:
    base_form_data_name = settings.BASE_DIR + '/fixtures/initial-required-data/form_data'
    basic_form_data_file = base_form_data_name + '.json'
    help = 'Installs the named fixture(s) in the database.'

    def load(self):
        self.ignore = False
        self.using = DEFAULT_DB_ALIAS
        self.app_label = None
        self.verbosity = 0
        self.excluded_models, self.excluded_apps = parse_apps_and_model_labels([])
        
        fixture_labels = [LoadFormData.basic_form_data_file]
        print('Loading ', fixture_labels)
        self.loaddata(fixture_labels)
        
        
        fixture_labels = []
        tag_form_types = FormType.objects.filter(tag_enabled=True)
        for tag_form_type in tag_form_types:
            fixture_labels.append(LoadFormData.base_form_data_name + '_' + tag_form_type.name + '.json')
        
        if len(fixture_labels) > 0:
            print('Loading ', fixture_labels)
            self.loaddata(fixture_labels)

    def loaddata(self, fixture_labels):
        connection = connections[self.using]

        # Keep a count of the installed objects and fixtures
        self.fixture_count = 0
        self.loaded_object_count = 0
        self.fixture_object_count = 0
        self.models = set()

        self.serialization_formats = serializers.get_public_serializer_formats()
        # Forcing binary mode may be revisited after dropping Python 2 support (see #22399)
        self.compression_formats = {
            None: (open, 'rb'),
            'gz': (gzip.GzipFile, 'rb'),
            'zip': (SingleZipReader, 'r'),
        }
        if has_bz2:
            self.compression_formats['bz2'] = (bz2.BZ2File, 'r')

        # Django's test suite repeatedly tries to load initial_data fixtures
        # from apps that don't have any fixtures. Because disabling constraint
        # checks can be expensive on some database (especially MSSQL), bail
        # out early if no fixtures are found.
        for fixture_label in fixture_labels:
            if self.find_fixtures(fixture_label):
                break
        else:
            return

        with connection.constraint_checks_disabled():
            for fixture_label in fixture_labels:
                self.load_label(fixture_label)

        # Since we disabled constraint checks, we must manually check for
        # any invalid keys that might have been added
        table_names = [model._meta.db_table for model in self.models]
        try:
            connection.check_constraints(table_names=table_names)
        except Exception as e:
            e.args = ("Problem installing fixtures: %s" % e,)
            raise

        # If we found even one object in a fixture, we need to reset the
        # database sequences.
        if self.loaded_object_count > 0:
            sequence_sql = connection.ops.sequence_reset_sql(no_style(), self.models)
            if sequence_sql:
                if self.verbosity >= 2:
                    self.stdout.write("Resetting sequences\n")
                with connection.cursor() as cursor:
                    for line in sequence_sql:
                        cursor.execute(line)

        if self.verbosity >= 1:
            if self.fixture_object_count == self.loaded_object_count:
                self.stdout.write(
                    "Installed %d object(s) from %d fixture(s)"
                    % (self.loaded_object_count, self.fixture_count)
                )
            else:
                self.stdout.write(
                    "Installed %d object(s) (of %d) from %d fixture(s)"
                    % (self.loaded_object_count, self.fixture_object_count, self.fixture_count)
                )

    def load_label(self, fixture_label):
        """
        Loads fixtures files for a given label.
        """
        show_progress = self.verbosity >= 3
        for fixture_file, fixture_dir, fixture_name in self.find_fixtures(fixture_label):
            _, ser_fmt, cmp_fmt = self.parse_name(os.path.basename(fixture_file))
            open_method, mode = self.compression_formats[cmp_fmt]

            if fixture_label == LoadFormData.basic_form_data_file:
                ser_fmt = 'json'
            else:
                ser_fmt = 'form_data_tag'

            fixture = open_method(fixture_file, mode)
            try:
                self.fixture_count += 1
                objects_in_fixture = 0
                loaded_objects_in_fixture = 0
                if self.verbosity >= 2:
                    self.stdout.write(
                        "Installing %s fixture '%s' from %s."
                        % (ser_fmt, fixture_name, humanize(fixture_dir))
                    )

                objects = serializers.deserialize(
                    ser_fmt, fixture, using=self.using, ignorenonexistent=self.ignore,
                )

                for obj in objects:
                    objects_in_fixture += 1
                    if (obj.object._meta.app_config in self.excluded_apps or
                            type(obj.object) in self.excluded_models):
                        continue
                    if router.allow_migrate_model(self.using, obj.object.__class__):
                        loaded_objects_in_fixture += 1
                        self.models.add(obj.object.__class__)
                        try:
                            obj.save(using=self.using)
                            if show_progress:
                                self.stdout.write(
                                    '\rProcessed %i object(s).' % loaded_objects_in_fixture,
                                    ending=''
                                )
                        except (DatabaseError, IntegrityError) as e:
                            e.args = ("Could not load %(app_label)s.%(object_name)s(pk=%(pk)s): %(error_msg)s" % {
                                'app_label': obj.object._meta.app_label,
                                'object_name': obj.object._meta.object_name,
                                'pk': obj.object.pk,
                                'error_msg': force_str(e)
                            },)
                            raise
                if objects and show_progress:
                    self.stdout.write('')  # add a newline after progress indicator
                self.loaded_object_count += loaded_objects_in_fixture
                self.fixture_object_count += objects_in_fixture
            except Exception as e:
                if not isinstance(e, CommandError):
                    e.args = ("Problem installing fixture '%s': %s" % (fixture_file, e),)
                raise
            finally:
                fixture.close()

            # Warn if the fixture we loaded contains 0 objects.
            if objects_in_fixture == 0:
                warnings.warn(
                    "No fixture data found for '%s'. (File format may be "
                    "invalid.)" % fixture_name,
                    RuntimeWarning
                )

    #@lru_cache.lru_cache(maxsize=None)
    def find_fixtures(self, fixture_label):
        """
        Finds fixture files for a given label.
        """
        fixture_name, ser_fmt, cmp_fmt = self.parse_name(fixture_label)
        databases = [self.using, None]
        cmp_fmts = list(self.compression_formats.keys()) if cmp_fmt is None else [cmp_fmt]
        ser_fmts = serializers.get_public_serializer_formats() if ser_fmt is None else [ser_fmt]

        if self.verbosity >= 2:
            self.stdout.write("Loading '%s' fixtures..." % fixture_name)

        if os.path.isabs(fixture_name):
            fixture_dirs = [os.path.dirname(fixture_name)]
            fixture_name = os.path.basename(fixture_name)
        else:
            fixture_dirs = self.fixture_dirs
            if os.path.sep in os.path.normpath(fixture_name):
                fixture_dirs = [os.path.join(dir_, os.path.dirname(fixture_name))
                                for dir_ in fixture_dirs]
                fixture_name = os.path.basename(fixture_name)

        suffixes = (
            '.'.join(ext for ext in combo if ext)
            for combo in product(databases, ser_fmts, cmp_fmts)
        )
        targets = set('.'.join((fixture_name, suffix)) for suffix in suffixes)

        fixture_files = []
        for fixture_dir in fixture_dirs:
            if self.verbosity >= 2:
                self.stdout.write("Checking %s for fixtures..." % humanize(fixture_dir))
            fixture_files_in_dir = []
            path = os.path.join(fixture_dir, fixture_name)
            for candidate in glob.iglob(glob_escape(path) + '*'):
                if os.path.basename(candidate) in targets:
                    # Save the fixture_dir and fixture_name for future error messages.
                    fixture_files_in_dir.append((candidate, fixture_dir, fixture_name))

            if self.verbosity >= 2 and not fixture_files_in_dir:
                self.stdout.write("No fixture '%s' in %s." %
                                  (fixture_name, humanize(fixture_dir)))

            # Check kept for backwards-compatibility; it isn't clear why
            # duplicates are only allowed in different directories.
            if len(fixture_files_in_dir) > 1:
                raise CommandError(
                    "Multiple fixtures named '%s' in %s. Aborting." %
                    (fixture_name, humanize(fixture_dir)))
            fixture_files.extend(fixture_files_in_dir)

        if not fixture_files:
            raise CommandError("No fixture named '%s' found." % fixture_name)

        return fixture_files

    @cached_property
    def fixture_dirs(self):
        """
        Return a list of fixture directories.

        The list contains the 'fixtures' subdirectory of each installed
        application, if it exists, the directories in FIXTURE_DIRS, and the
        current directory.
        """
        dirs = []
        fixture_dirs = settings.FIXTURE_DIRS
        if len(fixture_dirs) != len(set(fixture_dirs)):
            raise ImproperlyConfigured("settings.FIXTURE_DIRS contains duplicates.")
        for app_config in apps.get_app_configs():
            app_label = app_config.label
            app_dir = os.path.join(app_config.path, 'fixtures')
            if app_dir in fixture_dirs:
                raise ImproperlyConfigured(
                    "'%s' is a default fixture directory for the '%s' app "
                    "and cannot be listed in settings.FIXTURE_DIRS." % (app_dir, app_label)
                )

            if self.app_label and app_label != self.app_label:
                continue
            if os.path.isdir(app_dir):
                dirs.append(app_dir)
        dirs.extend(list(fixture_dirs))
        dirs.append('')
        dirs = [os.path.abspath(os.path.realpath(d)) for d in dirs]
        return dirs

    def parse_name(self, fixture_name):
        """
        Splits fixture name in name, serialization format, compression format.
        """
        parts = fixture_name.rsplit('.', 2)

        if len(parts) > 1 and parts[-1] in self.compression_formats:
            cmp_fmt = parts[-1]
            parts = parts[:-1]
        else:
            cmp_fmt = None

        if len(parts) > 1:
            if parts[-1] in self.serialization_formats:
                ser_fmt = parts[-1]
                parts = parts[:-1]
            else:
                raise CommandError(
                    "Problem installing fixture '%s': %s is not a known "
                    "serialization format." % (''.join(parts[:-1]), parts[-1]))
        else:
            ser_fmt = None

        name = '.'.join(parts)

        return name, ser_fmt, cmp_fmt


class SingleZipReader(zipfile.ZipFile):

    def __init__(self, *args, **kwargs):
        zipfile.ZipFile.__init__(self, *args, **kwargs)
        if len(self.namelist()) != 1:
            raise ValueError("Zip-compressed fixtures must contain one file.")

    def read(self):
        return zipfile.ZipFile.read(self, self.namelist()[0])


def humanize(dirname):
    return "'%s'" % dirname if dirname else 'absolute path'
