import random


def make_id(id_str: str) -> str:
    """描画する要素のidを生成する

    セットしようとしたidが重複しているとエラーになるため、ランダムな数字を付与して一意にする。
    """
    return f"{id_str}_{random.randint(0, 9999):04d}"
