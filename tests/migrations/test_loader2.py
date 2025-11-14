import pkgutil
from importlib import import_module
from unittest import mock

from django.db.migrations.graph import MigrationGraph

from django.apps import apps
from django.conf import settings

from django.db import connection
from django.db.migrations.exceptions import (
    CircularDependencyError,
)
from django.db.migrations.loader import MigrationLoader, MIGRATIONS_MODULE_NAME
from django.test import TestCase, modify_settings, override_settings, tag
from django.test.utils import env


@env(PYTHONHASHSEED="0")
class LoaderTests(TestCase):
    """
    Tests the disk and database loader, and running through migrations
    in memory.
    """

    @override_settings(
        MIGRATION_MODULES={
            "app1": "migrations.test_migrations_squashed_replaced_order.default.app1",
            "app2": "migrations.test_migrations_squashed_replaced_order.app2",
            "app3": "migrations.test_migrations_squashed_replaced_order.app3",
        }
    )
    @modify_settings(
        INSTALLED_APPS={
            "append": [
                "migrations.test_migrations_squashed_replaced_order.default.app1",
                "migrations.test_migrations_squashed_replaced_order.app2",
                "migrations.test_migrations_squashed_replaced_order.app3",
            ]
        }
    )
    def test_migration_names_set_order_succeeds(self):
        """
        This test will pass if migration_names in MigrationLoader.load_disk is
        a list.
        If migration_names is a set, there is a 50% chance that this test will
        cause a CircularDependencyError, the other 50% will not.
        To verify that migration_names is a set when it doesn't raise, we
        check the imported_modules order, but there is still a rare chance
        that the order will be the same as when migration_names is a list.
        MigationGraph remove_replaced_nodes is called from MigrationLoader
        replace_migration.
        If app1.0002 is replaced before app1.0001, then a
        CircularDependencyError occurs.
        If app1.0001 is replaced before app1.0002, then a
        CircularDependencyError does not occur.
        The failing replacement causes app1.0002 to contain a child of
        app2.0001.
        """
        import os
        original_import_module = import_module
        imported_order = []
        imported_modules = {}  # for programmatically figuring out the import order

        def wrapped(name, package=None):
            imported_order.append(name)
            module = original_import_module(name, package=package)
            if name.endswith(f".{MIGRATIONS_MODULE_NAME}"):
                imported_modules[name] = module
            return module

        with mock.patch("django.db.migrations.loader.import_module", wraps=wrapped):
            # This could cause a CircularDependencyError.
            raised = False
            try:
                MigrationLoader(connection)
            except CircularDependencyError:
                raised = True

        self.assertFalse(
            raised,
            msg="A CircularDependencyError was triggered by "
            "migration_names being iterated in the wrong order.",
        )

        # But there is a 50% chance that a set will pass.
        # In that case verify that the imported modules order is equal.
        expected_order = []
        # Generate the imported modules in the correct order.
        for app_config in apps.get_app_configs():
            module_name, _explicit = MigrationLoader.migrations_module(app_config.label)
            if module_name is None:
                continue
            expected_order.append(module_name)
            if module_name in imported_modules:
                module = imported_modules[module_name]
            elif module_name in settings.MIGRATION_MODULES.values():
                module = app_config.module
            else:
                continue
            migration_names = [  # Must be a list.
                name
                for _, name, is_pkg in pkgutil.iter_modules(module.__path__)
                if not is_pkg and name[0] not in "_~"
            ]
            if migration_names:
                for migration_name in migration_names:
                    migration_path = "%s.%s" % (module_name, migration_name)
                    expected_order.append(migration_path)

        self.assertListEqual(imported_order, expected_order, msg="")

    @override_settings(
        MIGRATION_MODULES={
            "app1": "migrations.test_migrations_squashed_replaced_order.reversed.app1",
            "app2": "migrations.test_migrations_squashed_replaced_order.app2",
            "app3": "migrations.test_migrations_squashed_replaced_order.app3",
        }
    )
    @modify_settings(
        INSTALLED_APPS={
            "append": [
                "migrations.test_migrations_squashed_replaced_order.reversed.app1",
                "migrations.test_migrations_squashed_replaced_order.app2",
                "migrations.test_migrations_squashed_replaced_order.app3",
            ]
        }
    )
    def test_loading_squashed_set_order_raises(self):
        """
        This test will pass if migration_names in MigrationLoader.load_disk is
        a list.
        If migration_names is a set, there is a 50% chance that this test will
        cause a CircularDependencyError, the other 50% will not.
        To verify that migration_names is a set, we check the imported_modules
        order, but there is still a rare chance that the order will be the
        same as when migration_names is a list.
        MigationGraph remove_replaced_nodes is called from MigrationLoader
        replace_migration.
        If app1.0002 is replaced before app1.0001, then a
        CircularDependencyError occurs.
        If app1.0001 is replaced before app1.0002, then a
        CircularDependencyError does not occur.
        The failing replacement causes app1.0002 to contain a child of
        app2.0001.
        """
        self.maxDiff = None
        original_import_module = import_module
        imported_order = []
        imported_modules = {}  # for programmatically figuring out the import order

        def wrapped(name, package=None):
            imported_order.append(name)
            module = original_import_module(name, package=package)
            if name.endswith(f".{MIGRATIONS_MODULE_NAME}"):
                imported_modules[name] = module
            return module

        with mock.patch("django.db.migrations.loader.import_module", wraps=wrapped):
            # This could cause a CircularDependencyError.
            raised = False
            try:
                MigrationLoader(connection)
            except CircularDependencyError:
                raised = True
        self.assertTrue(
            raised,
            msg="A CircularDependencyError was not triggered by "
            "migration_names being iterated in the wrong order.",
        )

        # But there is a 50% chance that a set will pass.
        # In that case verify that the imported modules order is equal.
        expected_order = []
        # Generate the imported modules in the correct order.
        for app_config in apps.get_app_configs():
            module_name, _explicit = MigrationLoader.migrations_module(app_config.label)
            if module_name is None:
                continue
            expected_order.append(module_name)
            if module_name in imported_modules:
                module = imported_modules[module_name]
            elif module_name in settings.MIGRATION_MODULES.values():
                module = app_config.module
            else:
                continue
            migration_names = [  # Must be a list.
                name
                for _, name, is_pkg in pkgutil.iter_modules(module.__path__)
                if not is_pkg and name[0] not in "_~"
            ]
            if migration_names:
                for migration_name in migration_names:
                    migration_path = "%s.%s" % (module_name, migration_name)
                    expected_order.append(migration_path)
        self.assertListEqual(imported_order, expected_order, msg="")

    @override_settings(
        MIGRATION_MODULES={
            "app1": "migrations.test_migrations_squashed_replaced_order.default.app1",
            "app2": "migrations.test_migrations_squashed_replaced_order.app2",
            "app3": "migrations.test_migrations_squashed_replaced_order.app3",
        }
    )
    @modify_settings(
        INSTALLED_APPS={
            "append": [
                "migrations.test_migrations_squashed_replaced_order.default.app1",
                "migrations.test_migrations_squashed_replaced_order.app2",
                "migrations.test_migrations_squashed_replaced_order.app3",
            ]
        }
    )
    def test_migration_loader_replacement_order_succeeds(self):
        """
        This test will pass if the replacement order is done in the order the
        migrations would run.
        If the migration_names in MigrationLoader.load_disk is a list, it will
        not cause a CircularDependencyError, and the test will pass.
        If the migration_names is a set, there is a 50% chance that this test
        will cause a CircularDependencyError, the other 50% will do the
        replacement in the correct order.
        MigationGraph remove_replaced_nodes is called from MigrationLoader
        replace_migration.
        If app1.0002 is replaced before app1.0001, then a
        CircularDependencyError occurs.
        If app1.0001 is replaced before app1.0002, then a
        CircularDependencyError does not occur.
        The failing replacement causes app1.0002 to contain a child of
        app2.0001.
        """
        replacement_order = []

        def remove_replaced_nodes_test(self, replacement, replaced):
            replacement_order.append(replacement)
            return self.remove_replaced_nodes_original(replacement, replaced)

        # Patch remove_replaced_nodes
        MigrationGraph.remove_replaced_nodes_original = (
            MigrationGraph.remove_replaced_nodes
        )
        MigrationGraph.remove_replaced_nodes = remove_replaced_nodes_test

        # This could cause a CircularDependencyError.
        raised = False
        try:
            MigrationLoader(connection)
        except CircularDependencyError:
            raised = True

        # Undo patch on remove_replaced_nodes
        MigrationGraph.remove_replaced_nodes = (
            MigrationGraph.remove_replaced_nodes_original
        )
        del MigrationGraph.remove_replaced_nodes_original

        self.assertFalse(
            raised,
            msg="A CircularDependencyError was triggered by "
            "migrations being replaced in the wrong order.",
        )

        self.assertTrue(
            replacement_order.index(("app1", "0001_squashed_initial"))
            < replacement_order.index(("app1", "0002_squashed_initial"))
        )

    @override_settings(
        MIGRATION_MODULES={
            "app1": "migrations.test_migrations_squashed_replaced_order.reversed.app1",
            "app2": "migrations.test_migrations_squashed_replaced_order.app2",
            "app3": "migrations.test_migrations_squashed_replaced_order.app3",
        }
    )
    @modify_settings(
        INSTALLED_APPS={
            "append": [
                "migrations.test_migrations_squashed_replaced_order.reversed.app1",
                "migrations.test_migrations_squashed_replaced_order.app2",
                "migrations.test_migrations_squashed_replaced_order.app3",
            ]
        }
    )
    def test_migration_loader_replacement_order_raises(self):
        """
        This test will pass if the replacement order is done in the wrong
        order that migrations would run.  It expects a CircularDependencyError
        to occur.
        If the migration_names in MigrationLoader.load_disk is a list, it will
        generate the CircularDependencyError and pass.
        If the migration_names is a set, there is a 50% chance that this test
        will cause a CircularDependencyError, the other 50% will do the
        replacement in the correct order.
        MigationGraph remove_replaced_nodes is called from MigrationLoader
        replace_migration.
        If app1.0002 is replaced before app1.0001, then a
        CircularDependencyError occurs.
        If app1.0001 is replaced before app1.0002, then a
        CircularDependencyError does not occur.
        The failing replacement causes app1.0002 to contain a child of
        app2.0001.
        """
        replacement_order = []

        def remove_replaced_nodes_test(self, replacement, replaced):
            replacement_order.append(replacement)
            return self.remove_replaced_nodes_original(replacement, replaced)

        # Patch remove_replaced_nodes
        MigrationGraph.remove_replaced_nodes_original = (
            MigrationGraph.remove_replaced_nodes
        )
        MigrationGraph.remove_replaced_nodes = remove_replaced_nodes_test

        # This could cause a CircularDependencyError.
        raised = False
        try:
            MigrationLoader(connection)
        except CircularDependencyError:
            raised = True

        # Undo patch on remove_replaced_nodes
        MigrationGraph.remove_replaced_nodes = (
            MigrationGraph.remove_replaced_nodes_original
        )
        del MigrationGraph.remove_replaced_nodes_original

        self.assertTrue(
            raised,
            msg="A CircularDependencyError was not triggered by "
            "migrations being replaced in the wrong order.",
        )
        self.assertNotIn(("app1", "0002_squashed_initial"), replacement_order)
