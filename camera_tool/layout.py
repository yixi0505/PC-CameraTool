from __future__ import annotations

from math import ceil, sqrt


def fit_size(
    source_width: int,
    source_height: int,
    available_width: int,
    available_height: int,
) -> tuple[int, int]:
    """将源画面等比例放大或缩小到可用区域内。"""
    if min(source_width, source_height, available_width, available_height) <= 0:
        return 1, 1

    scale = min(
        available_width / source_width,
        available_height / source_height,
    )
    return (
        max(1, int(source_width * scale)),
        max(1, int(source_height * scale)),
    )


def grid_shape(item_count: int) -> tuple[int, int]:
    """返回接近正方形的 (行数, 列数) 宫格尺寸。"""
    if item_count <= 0:
        return 0, 0
    columns = ceil(sqrt(item_count))
    rows = ceil(item_count / columns)
    return rows, columns


def grid_positions(item_count: int) -> list[tuple[int, int]]:
    """按从左到右、从上到下的顺序生成宫格坐标。"""
    _, columns = grid_shape(item_count)
    if columns == 0:
        return []
    return [(index // columns, index % columns) for index in range(item_count)]
