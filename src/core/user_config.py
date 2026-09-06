"""用户级配置持久化：界面偏好等保存在 用户主目录/zy_rpa/config.json。

与代码仓库分离，换机/升级不丢失个性化设置。
"""
import json
import os
from pathlib import Path


class UserConfig:
    """用户偏好（界面风格、深浅色等）的读取与保存。"""

    # 默认存储在 用户主目录/zy_rpa/config.json
    DIR = Path.home() / "zy_rpa"
    PATH = DIR / "config.json"

    DEFAULTS = {
        "ui_style": "macos",       # 界面风格：macos | win11
        "theme_mode": "system",    # 深浅色：system | light | dark
    }

    def __init__(self, path: Path = None):
        if path is not None:
            self.PATH = path
            self.DIR = path.parent
        self._data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        try:
            if self.PATH.is_file():
                with open(self.PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update({k: v for k, v in loaded.items()
                                       if v is not None})
        except Exception:
            pass  # 配置损坏时静默回退默认值
        return self

    def save(self, **kwargs):
        self._data.update(kwargs)
        try:
            self.DIR.mkdir(parents=True, exist_ok=True)
            tmp = self.PATH.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.PATH)   # 原子写入，避免半截文件
        except Exception as e:
            return False
        return True

    def get(self, key, default=None):
        return self._data.get(key, default)

    def all(self):
        return dict(self._data)