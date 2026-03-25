"""
비밀키 생성 유틸리티.

실행:
  python3 scripts/gen_secret.py

.env 파일의 SECRET_KEY, REFRESH_SECRET_KEY 에 복사하여 사용.
"""
import secrets

print("SECRET_KEY 용:")
print(secrets.token_hex(32))
print()
print("REFRESH_SECRET_KEY 용:")
print(secrets.token_hex(32))
