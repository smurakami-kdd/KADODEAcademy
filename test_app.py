import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app


class TemplateDirectoryTestCase(unittest.TestCase):
    """一時ディレクトリをテンプレートディレクトリとして使うテストの基底クラス。"""

    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.template_directory = self.root / "templates"
        self.template_directory.mkdir()

        patcher = mock.patch.object(app, "TEMPLATE_DIRECTORY", self.template_directory)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_template(self, template_name: str, content: str) -> None:
        (self.template_directory / f"{template_name}.txt").write_text(content, encoding="utf-8")


class LoadTemplateTest(TemplateDirectoryTestCase):
    def test_loads_existing_template(self) -> None:
        self.write_template("polite", "ようこそ、$nameさん")
        self.assertEqual(app.load_template("polite"), "ようこそ、$nameさん")

    def test_allows_hyphen_and_underscore(self) -> None:
        self.write_template("my-template_1", "hi")
        self.assertEqual(app.load_template("my-template_1"), "hi")

    def test_rejects_empty_or_whitespace_name(self) -> None:
        for template_name in ["", " ", "\t"]:
            with self.subTest(template_name=template_name):
                with self.assertRaises(ValueError):
                    app.load_template(template_name)

    def test_rejects_path_traversal(self) -> None:
        (self.root / "secret.txt").write_text("secret", encoding="utf-8")
        for template_name in ["../secret", "..", "sub/../../secret", "..\\secret"]:
            with self.subTest(template_name=template_name):
                with self.assertRaises(ValueError):
                    app.load_template(template_name)

    def test_rejects_absolute_path(self) -> None:
        secret_path = self.root / "secret"
        secret_path.with_suffix(".txt").write_text("secret", encoding="utf-8")
        with self.assertRaises(ValueError):
            app.load_template(str(secret_path))

    def test_rejects_null_character(self) -> None:
        with self.assertRaises(ValueError):
            app.load_template("default\x00")

    def test_missing_template_raises_template_error_without_path(self) -> None:
        with self.assertRaises(app.TemplateError) as context:
            app.load_template("missing")
        self.assertEqual(str(context.exception), app.TEMPLATE_LOAD_ERROR_MESSAGE)
        self.assertNotIn(str(self.template_directory), str(context.exception))

    def test_directory_template_raises_template_error(self) -> None:
        (self.template_directory / "folder.txt").mkdir()
        with self.assertRaises(app.TemplateError):
            app.load_template("folder")

    def test_non_utf8_template_raises_template_error(self) -> None:
        (self.template_directory / "broken.txt").write_bytes(b"\xff\xfe\xfa")
        with self.assertRaises(app.TemplateError):
            app.load_template("broken")


class CreateGreetingTest(TemplateDirectoryTestCase):
    def test_substitutes_name(self) -> None:
        self.write_template("default", "こんにちは、${name}さん\n")
        self.assertEqual(app.create_greeting("山田"), "こんにちは、山田さん")

    def test_uses_specified_template(self) -> None:
        self.write_template("polite", "ようこそ、$nameさん")
        self.assertEqual(app.create_greeting("山田", "polite"), "ようこそ、山田さん")

    def test_rejects_empty_or_whitespace_name(self) -> None:
        self.write_template("default", "$name")
        for name in ["", " ", "\n"]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    app.create_greeting(name)

    def test_does_not_evaluate_attribute_references(self) -> None:
        self.write_template("default", "{name.__class__} ${name.__class__} $name")
        self.assertEqual(
            app.create_greeting("山田"),
            "{name.__class__} ${name.__class__} 山田",
        )

    def test_malformed_or_unknown_placeholders_are_left_as_is(self) -> None:
        for content in ["{", "}", "{0}", "$", "${", "$unknown", "{unknown}"]:
            with self.subTest(content=content):
                self.write_template("default", content)
                self.assertEqual(app.create_greeting("山田"), content)

    def test_name_is_not_expanded_as_placeholder(self) -> None:
        self.write_template("default", "$name")
        self.assertEqual(app.create_greeting("$name ${name}"), "$name ${name}")


class MainTest(TemplateDirectoryTestCase):
    def test_returns_zero_on_success(self) -> None:
        self.write_template("default", "こんにちは、${name}さん")
        with self.assertLogs(app.logger, level="INFO") as logs:
            self.assertEqual(app.main(["山田"]), 0)
        self.assertEqual(logs.records[-1].getMessage(), "こんにちは、山田さん")

    def test_returns_one_without_arguments(self) -> None:
        with self.assertLogs(app.logger, level="ERROR"):
            self.assertEqual(app.main([]), 1)

    def test_returns_one_for_invalid_template_name(self) -> None:
        with self.assertLogs(app.logger, level="ERROR"):
            self.assertEqual(app.main(["山田", "../secret"]), 1)

    def test_missing_template_logs_fixed_message(self) -> None:
        with self.assertLogs(app.logger, level="ERROR") as logs:
            self.assertEqual(app.main(["山田", "missing"]), 1)
        self.assertEqual(logs.records[-1].getMessage(), app.TEMPLATE_LOAD_ERROR_MESSAGE)


class BundledTemplateTest(unittest.TestCase):
    def test_default_template_exists(self) -> None:
        self.assertEqual(app.create_greeting("山田"), "こんにちは、山田さん")


if __name__ == "__main__":
    unittest.main()
