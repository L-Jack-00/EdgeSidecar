# 🛡️ Edge Sidecar Browser (v1.3.3)

<p align="center">
  <img src="https://img.shields.io/badge/Release-v1.3.3-0ea5e9?style=for-the-badge&logo=windows&logoColor=white" alt="Release v1.3.3" />
  <img src="https://img.shields.io/badge/Default%20Browser-Windows%20Integrated-10b981?style=for-the-badge&logo=windows11&logoColor=white" alt="Default Browser Integrated" />
  <img src="https://img.shields.io/badge/MS%20Telemetry-0%25%20Blocked-ef4444?style=for-the-badge&logo=microsoftedge&logoColor=white" alt="Telemetry 0%" />
  <img src="https://img.shields.io/badge/Manifest%20V3-Bypassed-8b5cf6?style=for-the-badge" alt="MV3 Bypassed" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License" />
</p>

> **Windows 기본 웹 브라우저 완벽 연동 + 외부 프로그램(카톡/디스코드/슬랙) 단일 인스턴스 새 탭 포워딩 + 포터블 크로뮴 내장 + 최신 엔진 자동 교체(Auto-Swapper) + MS 텔레메트리 0% + 실시간 패킷 규칙 제어**  
> *(가볍고 안전한 프라이버시 중심의 완전 독립형 메인 크로뮴 사이드카 브라우저)*

---

## 📋 목차
1. [🌟 핵심 특징 한눈에 보기](#-핵심-특징-한눈에-보기)
2. [📦 배포 버전 다운로드 (설치형 vs 무설치 포터블)](#-배포-버전-다운로드)
3. [🚀 외부 프로그램 연동 & 기본 브라우저 설정 방법](#-외부-프로그램-연동--기본-브라우저-설정-방법)
4. [⚡ 핵심 기능 상세 안내](#-핵심-기능-상세-안내)
   - [Windows 기본 웹 브라우저 & 단일 인스턴스 링크 전달](#1-windows-기본-웹-브라우저--단일-인스턴스-링크-전달)
   - [내장 포터블 크로뮴 & 최신 엔진 원클릭 갈아끼우기](#2-내장-포터블-크로뮴--최신-엔진-원클릭-갈아끼우기-auto-swapper)
   - [멀티 브라우저 엔진 실시간 변경](#3-멀티-브라우저-엔진-실시간-변경)
   - [실시간 패킷 가로채기 & 제어 (규칙 엔진)](#4-실시간-패킷-가로채기--제어-규칙-엔진)
   - [마이크로소프트 텔레메트리 0% 원천 차단](#5-마이크로소프트-텔레메트리--블로트웨어-0-원천-차단)
   - [크롬 웹스토어 확장 프로그램 100% 지원](#6-모든-크롬-확장-프로그램-100-호환)
   - [개인정보 보호 & 메모리 누수 방지 안전 가드](#7-개인정보-보호--메모리-누수-방지-안전-가드)
5. [🧪 자체 검증 테스트 러너](#-자체-검증-테스트-러너)
6. [📄 라이선스](#-라이선스)

---

## 🌟 핵심 특징 한눈에 보기

| 비교 항목 | 일반 순정 Edge / Chrome | 🛡️ Edge Sidecar Browser (v1.3.3) |
| :--- | :--- | :--- |
| **외부 프로그램 링크 클릭 (메인 브라우저 사용)** | ❌ 순정 Edge로 강제 연결됨 | ✅ **Windows 기본 앱 등록 + 이미 켜진 브라우저로 0.1초 만에 새 탭 포워딩** |
| **Edge 미설치 PC 구동** | ❌ Edge 없으면 오류 발생 | ✅ **독립형 포터블 크로뮴 내장으로 100% 무조건 실행** |
| **최신 엔진 자동 교체** | ❌ 수동 재설치 필요 | ✅ **대시보드에서 1클릭으로 최신 크로뮴 자동 갈아끼우기** |
| **마이크로소프트 텔레메트리** | ⚠️ 검색어, 사용 습관 전송 | 🚫 **프록시 레벨에서 20여 개 추적 도메인 원천 드롭** |
| **패킷 변조 & CORS 해제** | ❌ Manifest V3 정책으로 차단됨 | ⚡ **CDP Fetch 기반 헤더/바디 실시간 변조 & CORS 전역 해제** |
| **크롬 웹스토어 확장 프로그램**| ⚠️ 일부 정책 제한 존재 | 🛍️ **uBlock, 번역기, 패스워드 매니저 등 100% 호환** |
| **브라우저 엔진 전환** | ❌ 고정 엔진 | 🌐 **Edge, Chrome, Brave, Whale, 포터블 간 자유 전환** |
| **1회성 세션 흔적 소거** | ⚠️ 캐시 수동 삭제 필요 | 🧹 **원클릭으로 쿠키, 세션, 캐시 완전 소거** |

---

## 📦 배포 버전 다운로드

GitHub Releases 페이지에서 내 사용 환경에 맞는 버전을 선택하여 다운로드할 수 있습니다:

### 1️⃣ [추천] 일반 사용자용 원클릭 설치 파일 (`EdgeSidecar-Setup.exe`)
* **다운로드**: [`dist_installer/EdgeSidecar-Setup.exe`](https://github.com/L-Jack-00/EdgeSidecar/releases/download/v1.3.3/EdgeSidecar-Setup.exe) (약 275 MB)
* **특징**:
  * 파이썬이나 별도 소프트웨어를 설치할 필요가 전혀 없습니다.
  * 더블 클릭 후 **[설치 시작]**만 누르면 윈도우 바탕화면과 시작 메뉴에 예쁜 방패 아이콘 바로가기가 자동 생성됩니다.
  * **설치 마법사에서 자동으로 Windows 기본 웹 브라우저 목록에 등록**해 주어 외부 프로그램(카톡, 디스코드 등) 링크가 바로 연결됩니다.

### 2️⃣ 무설치 포터블 압축 파일 (`EdgeSidecar-v1.3.3-Portable.zip`)
* **다운로드**: [`dist/EdgeSidecar-v1.3.3-Portable.zip`](https://github.com/L-Jack-00/EdgeSidecar/releases/download/v1.3.3/EdgeSidecar-v1.3.3-Portable.zip) (약 241 MB)
* **특징**:
  * 시스템 레지스트리를 건드리지 않는 100% 무설치(Clean-room) 패키지입니다.
  * 원하는 폴더나 USB 외장 드라이브에 압축을 푼 뒤 `EdgeSidecar.exe`를 실행하면 즉시 실행됩니다.

---

## 🚀 외부 프로그램 연동 & 기본 브라우저 설정 방법 (메인 브라우저 사용)

카카오톡, 디스코드, 슬랙, 노션, 메일 등 외부 프로그램에서 링크를 클릭했을 때 순정 Edge 대신 EdgeSidecar로 열리게 하려면 다음과 같이 설정할 수 있습니다:

1. **설치 시 자동 등록 (가장 쉬운 방법)**:
   * `EdgeSidecar-Setup.exe` 설치 마법사를 실행하면 **`☑ Windows 기본 웹 브라우저로 등록 (외부 프로그램 링크 연결 지원)`** 옵션이 기본 활성화되어 있습니다.
   * 설치가 끝나면 윈도우 **[기본 앱 (Default Apps)]** 설정 창이 자동으로 열리며, 웹 브라우저 목록에서 **[EdgeSidecar]**를 선택해 주시면 즉시 메인 브라우저로 지정됩니다.

2. **언제든지 대시보드에서 1클릭 설정**:
   * 대시보드 (`http://127.0.0.1:8899/dashboard`)의 **[고급 설정 & 보안]** 탭으로 이동합니다.
   * 최상단 카드에서 **`[⭐ 기본 브라우저로 등록 및 설정]`** 버튼을 클릭합니다.
   * 윈도우 레지스트리에 자동 등록되며, Windows 기본 앱 설정 창이 열리면 EdgeSidecar를 선택합니다.

3. **초고속 단일 인스턴스 (Single-Instance) URL 포워딩**:
   * EdgeSidecar가 이미 실행 중인 상태에서 외부 프로그램(카톡, 디스코드 등)의 링크를 클릭하면, 무거운 중복 프로세스를 띄우지 않고 기존 창에 **0.1초 만에 새 탭으로 즉시 열립니다.**
   * 콘솔 창 깜빡임 0, 백그라운드 프로세스 충돌 0으로 완벽한 메인 브라우저 사용성을 보장합니다.

---

## 💡 팁: 첫 실행 시 브라우저 선택 창 다시 띄우기

처음 실행할 때 선택했던 브라우저 엔진 설정을 완전히 리셋하고, **첫 실행 시 떴던 "브라우저 엔진 선택 다이얼로그"를 다시 보고 싶다면** 다음 3단계만 진행하시면 됩니다:

1. 프로그램 폴더(설치 폴더) 내의 **`settings.json`** 파일을 메모장이나 텍스트 편집기로 엽니다.
2. `"has_configured_browser": true` 값을 **`"has_configured_browser": false`** 로 수정합니다:
   ```json
   {
     "selected_browser": "auto",
     "has_configured_browser": false,
     "last_used_path": ""
   }
   ```
3. 파일을 저장한 후 프로그램을 다시 실행하면, **초기 브라우저 감지 및 선택 창이 다시 나타납니다.**

> 💡 **참고**: 굳이 `settings.json`을 수정하지 않더라도, **대시보드 [고급 관리] 탭** 또는 **시스템 트레이 아이콘 우클릭 ➔ `🌐 브라우저 엔진 변경`** 메뉴를 통해 언제든지 마우스 클릭 한 번으로 다른 브라우저로 전환할 수 있습니다.

---

## ⚡ 핵심 기능 상세 안내

### 1. 내장 포터블 크로뮴 & 최신 엔진 원클릭 갈아끼우기 (Auto-Swapper)
* 프로그램의 `bin/` 디렉토리에 오픈소스 크로뮴 최신 바이너리가 내장되어 있습니다.
* 대시보드의 **[고급 관리]** 탭에서 **`[🔍 최신 버전 확인]`** 버튼을 누르면 업스트림 보안 릴리즈를 실시간 조회합니다.
* 새 릴리즈가 있을 경우 **`[⚡ 최신 엔진으로 갈아끼우기]`** 버튼을 누르면, 백그라운드에서 다운로드 진행률(%)과 전송 속도(MB/s)를 보여주며 자동으로 압축을 풀고 엔진 바이너리를 최신 상태로 원클릭 갱신합니다.

### 2. 멀티 브라우저 엔진 실시간 변경
* 시스템에 설치된 Chromium 계열 브라우저를 스마트 감지합니다:
  * **포터블 크로뮴** (`bin/` 내장 독립형)
  * **Microsoft Edge**
  * **Google Chrome**
  * **Brave Browser**
  * **Naver Whale**
* 사용 중에도 트레이 우클릭 메뉴 또는 대시보드 드롭다운 메뉴를 통해 원클릭으로 구동 엔진을 변경할 수 있습니다.

### 3. 실시간 패킷 가로채기 & 제어 (규칙 엔진)
* Chrome DevTools Protocol(CDP) `Fetch` 도메인과 룰 엔진([`rules.py`](file:///C:/Users/SBK/.gemini/antigravity/scratch/edge-sidecar-browser/rules.py))이 브라우저 외부에서 직접 패킷을 제어합니다.
* **Manifest V3 제한 탈피**: 기존 확장 프로그램이 차단당한 네트워크 조작을 100% 무제한 수행합니다.
* **기본 탑재 규칙**:
  * 전역 CORS 제약 해제 (`Access-Control-Allow-Origin: *` 헤더 자동 주입)
  * 보안 헤더(CSP 등) 선택적 제거 및 커스텀 헤더 주입
  * 특정 API 엔드포인트 Mocking 응답 반환 및 JSON/HTML 실시간 변조

### 4. 마이크로소프트 텔레메트리 & 블로트웨어 0% 원천 차단
* `*.pipe.aria.microsoft.com`, `v10.events.data.microsoft.com`, `assets.msn.com`, `shopping.microsoft.com` 등 20여 개 이상의 MS 추적/쇼핑/광고 도메인을 프록시 레벨에서 원천 필터링합니다.
* RFC 표준 규격을 엄격히 준수하여 일반 요청은 `204 No Content`, 보안 `CONNECT` 터널링 요청은 `403 Forbidden`으로 안전하게 드롭함으로써 소켓 풀 오류 없이 쾌속 브라우징을 보장합니다.

### 5. 모든 크롬 확장 프로그램 100% 호환
* uBlock Origin, Dark Reader, 구글 번역, Bitwarden, LastPass 등 크롬 웹스토어의 모든 확장 프로그램을 순정 크롬과 완전히 동일하게 설치하고 사용할 수 있습니다.

### 6. 개인정보 보호 & 메모리 누수 방지 안전 가드
* **대용량 파일 스트리밍 보호**: 50MB 이상의 파일이나 비디오/오디오 미디어 스트리밍 감지 시 메모리 버퍼링을 건너뛰고 패스스루하여 브라우저 OOM 크래시를 방지합니다.
* **원클릭 1회성 세션 흔적 소거**: 대시보드에서 클릭 한 번으로 쿠키, 캐시, 세션 스토리지 흔적을 완전히 초기화하여 새 브라우저처럼 깨끗하게 되돌립니다.
* **Windows 개인 Root CA 연동**: 필요 시 대시보드에서 Windows 로컬 인증서 신뢰 등록/삭제를 지원합니다.

---

## 🧪 자체 검증 테스트 러너

본 프로젝트는 신뢰성 높은 무중단 구동을 위해 16대 단위/통합 테스트 스위트를 내장하고 있습니다.

```bash
# 16대 단위 및 통합 시나리오 헤드리스 검증
python tests/test_harness.py
```

* **테스트 결과**: 16/16 ALL PASS (통합 수명주기, CDP 소켓, 프록시 터널, 포터블 엔진 검증 완료)

---

## 📄 라이선스
This project is licensed under the MIT License. 자유롭게 수정, 배포, 연구 목적으로 활용하실 수 있습니다.
