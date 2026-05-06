#!/usr/bin/env python3
"""将 JSON 配置中的 ``YOUR_*`` 占位符解析为环境变量中的真实值。

约定：字符串在去空白后，若以 ``YOUR_`` 开头（不区分大小写后续比较的首段），则视为占位符，
按给定顺序读取 ``env_keys`` 中第一个非空环境变量作为结果；否则返回配置中的原文字符串。

供 gopay、PayPal、其它模块复用，避免各处重复 ``os.getenv`` 与占位符判断。
"""

from __future__ import annotations

import os
from typing import Callable, Sequence

__all__ = [
    "PlaceholderResolutionError",
    "is_placeholder",
    "resolve_placeholder",
]


class PlaceholderResolutionError(ValueError):
    """占位符无法从环境变量解析，或解析后未通过校验。"""


def is_placeholder(value: str | None) -> bool:
    """若 ``value`` 在去除首尾空白后以 ``YOUR_`` 开头（忽略大小写），返回 True。"""
    s = (value or "").strip()
    return bool(s) and s.upper().startswith("YOUR_")


def resolve_placeholder(
    raw: str | None,
    env_keys: Sequence[str],
    *,
    label: str = "config value",
    validate: Callable[[str], None] | None = None,
) -> str:
    """解析配置项：占位符则从环境变量读取，否则返回原文字符串。

    Args:
        raw: 配置中的字符串（可能为 ``YOUR_PHONE_NUMBER`` 等）。
        env_keys: 环境变量名顺序列表，先试第一个非空值。
        label: 用于错误信息，标明字段含义（如 ``gopay.phone_number``）。
        validate: 仅在**成功从环境变量解析出值**后调用，用于格式校验。

    Returns:
        非占位符时为 ``raw`` 的原文字符串；占位符时为首个命中的环境变量值（已 strip）。

    Raises:
        PlaceholderResolutionError: 原文为空、占位符但无一环境变量有值、或 ``validate`` 抛出。
    """
    s = (raw or "").strip()
    if not s:
        raise PlaceholderResolutionError(f"{label} is empty")
    if not s.upper().startswith("YOUR_"):
        return str(raw)

    resolved = ""
    for key in env_keys:
        val = os.getenv(key, "").strip()
        if val:
            resolved = val
            break
    if not resolved:
        keys_display = ", ".join(env_keys)
        raise PlaceholderResolutionError(
            f"{label} is a placeholder; set it in config or export one of: {keys_display}"
        )
    if validate is not None:
        validate(resolved)
    return resolved
