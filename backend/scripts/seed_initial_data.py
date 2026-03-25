"""
시드 스크립트 진입점.
backend/ 에서 실행:
  python3 -m scripts.seed_initial_data

또는 backend/ 에서:
  python3 seed_initial_data.py
"""
import sys
import os

# backend/ 를 sys.path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from seed_initial_data import seed
import asyncio

if __name__ == "__main__":
    asyncio.run(seed())
