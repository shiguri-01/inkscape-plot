import random
import re


def sanitize_id(text: str) -> str:
    """テキストをID用にサニタイズする"""
    text = text.replace(" ", "_")
    # XML特殊文字と制御文字を削除
    text = re.sub(r'[<>&"\'\x00-\x1f\x7f]', "", text)

    if len(text) > 50:
        text = text[:50]
    if not text:
        text = "untitled"
    return text


def make_id(id_str: str) -> str:
    """描画する要素のidを生成する

    セットしようとしたidが重複しているとエラーになるため、ランダムな数字を付与して一意にする。
    """
    return f"{id_str}_{random.randint(0, 9999):04d}"
