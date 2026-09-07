# 프로젝트 개발 및 Git 관리 규칙

## 1. Git 커밋 분할 원칙 (Atomic Commits)
- 하나의 커밋에는 단일 목적의 변경 사항만 포함합니다.
- 환경설정/패키지 의존성(uild, chore)과 기능 구현(eat, ix, efactor)은 반드시 분리하여 단계별로 스테이징 및 커밋합니다.
  - **1단계 (빌드/환경)**: pyproject.toml, uv.lock, .env.example, .gitignore 등
  - **2단계 (기능/로직)**: 뉴스 수집 스크립트, 파싱 모듈, 유틸리티 등
  - **3단계 (문서/정리)**: README.md, 가이드라인 등

## 2. 커밋 메시지 규약
- Conventional Commits 형식(접두사: 명확한 한글 설명)을 준수합니다.
  - uild: 빌드 시스템, 패키지 의존성 추가/수정
  - eat: 새로운 기능 추가
  - ix: 버그 수정
  - docs: 문서 추가 및 수정
  - efactor: 코드 리팩토링
  - chore: 기타 잡무 및 유지보수

## 3. 파일 추적 보안 및 데이터 격리
- 크롤링 결과 데이터(.csv, .json), 가상환경(.venv), 개인 API 키(.env)는 절대 Git에 커밋되지 않도록 사전 점검합니다.
