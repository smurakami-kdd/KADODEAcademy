import logging
import re
import sys
from pathlib import Path
from string import Template


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

MIN_ARGUMENT_COUNT = 1
DEFAULT_TEMPLATE_NAME = "default"
TEMPLATE_DIRECTORY = Path(__file__).resolve().parent / "templates"
TEMPLATE_SUFFIX = ".txt"
TEMPLATE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
TEMPLATE_LOAD_ERROR_MESSAGE = "テンプレートを読み込めませんでした"


class TemplateError(Exception):
    """テンプレートの読み込みに失敗したことを表す例外。

    利用者に見せるメッセージは固定とし、内部のファイルパスなどは含めない。
    """


def load_template(template_name: str) -> str:
    """指定されたテンプレート名のファイル内容を読み込む。

    Args:
        template_name: 読み込むテンプレート名。英数字・ハイフン・アンダースコアのみ使用できる。

    Returns:
        テンプレートファイルの内容。

    Raises:
        ValueError: テンプレート名が空、または使用できない文字を含む場合。
        TemplateError: テンプレートファイルが存在しない、または読み込めない場合。
    """
    if not template_name.strip():
        raise ValueError("テンプレート名を入力してください")

    if not TEMPLATE_NAME_PATTERN.fullmatch(template_name):
        raise ValueError("テンプレート名には英数字・ハイフン・アンダースコアのみ使用できます")

    template_directory = TEMPLATE_DIRECTORY.resolve()
    template_path = (template_directory / f"{template_name}{TEMPLATE_SUFFIX}").resolve()
    if not template_path.is_relative_to(template_directory):
        raise ValueError("テンプレート名が不正です")

    try:
        return template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        logger.debug("テンプレートの読み込みに失敗しました: %s", error)
        raise TemplateError(TEMPLATE_LOAD_ERROR_MESSAGE) from error


def create_greeting(name: str, template_name: str = DEFAULT_TEMPLATE_NAME) -> str:
    """名前とテンプレートからあいさつ文を生成する。

    テンプレート内の ``$name`` または ``${name}`` を名前に置き換える。
    それ以外のプレースホルダや ``$`` はそのまま残し、属性参照などは行わない。

    Args:
        name: あいさつ対象の名前。
        template_name: 使用するテンプレート名。

    Returns:
        生成されたあいさつ文。

    Raises:
        ValueError: 名前またはテンプレート名が不正な場合。
        TemplateError: テンプレートファイルが存在しない、または読み込めない場合。
    """
    if not name.strip():
        raise ValueError("名前を入力してください")

    template = Template(load_template(template_name).rstrip("\n"))
    return template.safe_substitute(name=name)


def main(args: list[str]) -> int:
    """コマンドライン引数を受け取り、あいさつ文を出力する。

    Args:
        args: コマンドライン引数のリスト。

    Returns:
        終了コード。正常終了の場合は0、不正な入力の場合は1。

    Raises:
        なし。
    """
    if len(args) < MIN_ARGUMENT_COUNT:
        logger.error("使い方: python app.py <名前> [テンプレート名]")
        return 1

    template_name = DEFAULT_TEMPLATE_NAME
    if len(args) > MIN_ARGUMENT_COUNT:
        template_name = args[1]

    try:
        message = create_greeting(args[0], template_name)
    except (ValueError, TemplateError) as error:
        logger.error(str(error))
        return 1

    logger.info(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
