# ERP

초기 판매/매장 관리 프로그램 베이스.

## 보안 기준으로 지금 해둔 것
- Flask 최소 서버
- `/.health` 상태 확인
- 환경변수 분리 (`.env.example`)
- `.env`, 가상환경, 로컬 DB, 캐시를 Git에서 제외
- 기본 보안 헤더 적용
- 쿠키 기본 보안 옵션 적용
- 업로드 최대 크기 제한 (`MAX_CONTENT_LENGTH`)

## 시작
```bash
cd ~/Projects/erp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 scripts_gen_secret.py
# 출력된 값을 .env 의 SECRET_KEY 로 교체
python3 app.py
```

## 확인
- http://127.0.0.1:5000/
- http://127.0.0.1:5000/health

## 다음 보안 순서
1. Git 첫 커밋
2. private GitHub repo 유지
3. SQLite 추가 (instance 폴더 사용)
4. 관리자 로그인/권한 모델 추가
5. 배포 전 DEBUG 끄기
6. NAS/외부 공개 전 HTTPS/리버스프록시 적용
