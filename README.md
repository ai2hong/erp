# VAPE DOG ERP

전자담배 매장 ERP 시스템 — 증산점·양산점·범어점

## 기술 스택
- **백엔드**: Python FastAPI + PostgreSQL + SQLAlchemy (async)
- **인증**: JWT (Access + Refresh, bcrypt 해싱)
- **프론트**: Vue.js (별도 진행)

## 빠른 시작

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# .env 설정
cp .env.example .env
python3 scripts/gen_secret.py
# 출력된 값을 .env의 SECRET_KEY, REFRESH_SECRET_KEY로 교체

# DB 시드 (매장 3개 + 사장 계정 + 샘플 고객)
python3 seed_initial_data.py

# 서버 실행
uvicorn app.main:app --reload
```

## 확인
- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

## 주요 API
| 엔드포인트 | 설명 |
|---|---|
| POST /auth/login | 로그인 |
| GET /auth/me | 내 정보 |
| GET /products/ | 상품 목록 |
| GET /customers/ | 고객 목록 |
| GET /transactions/ | 거래 목록 |
| POST /transactions/ | 거래 생성 |
| GET /staff/ | 직원 목록 |
| GET /dayclose/ | 일마감 목록 |

## 보안
- SECRET_KEY, REFRESH_SECRET_KEY는 .env에서만 관리
- bcrypt rounds=12 해싱
- JWT Access(30분) + Refresh(7일) rotate
- 1계정 1기기 세션 제한
- 역할 기반 접근 제어 (사장 > 총괄 > 매니저 > 판매사원)
