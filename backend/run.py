#!/usr/bin/env python3
"""启动入口"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from app.config import DATA_DIR


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  工程检测公司综合管理系统 v1.0.0")
    print("=" * 60)
    print()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )