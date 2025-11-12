"""Pytest配置文件。"""

import sys
from pathlib import Path

# 将src目录添加到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
