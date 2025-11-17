# IDARS: Intelligent Document-Ledger Auto-Reconciliation System
## 완전한 프로젝트 명세서 (PRD + Tech Spec)

**버전**: 1.0  
**작성일**: 2025-11-16  
**담당자**: CJ (Management Audit Office, POSCO International)  
**업데이트 방식**: 각 Stage 구현 후 "구현 결과" 섹션 업데이트

---

# Quick Start 가이드

## 📌 IDARS 핵심 개념 3줄 요약
1. **프로젝트 단위 관리**: "2025년 11월 1주차" 같은 프로젝트 생성 → 중단/재개 가능
2. **5단계 자동 파이프라인**: 전표 임포트 → 문서 분류 → 필드 추출 → 정규화 → 대사
3. **e-Book UI 검증**: 왼쪽(전표 리스트) + 오른쪽(PDF+하이라이트)로 검토

## 🚀 첫 프로젝트 시작하기 (5분)

### 1. 프로젝트 생성
```python
from workflow.opal_engine import OPALEngine

# 새 프로젝트 생성
project_id = "2025-11-W1"
engine = OPALEngine(project_id)
```

### 2. 전표 임포트
```python
# SAP에서 다운로드한 Excel 업로드
engine.import_ledger("전표리스트_11월1주.xlsx", "증빙PDF폴더/")
```

### 3. 파이프라인 실행 (자동)
```python
# 한 줄로 Stage 2~5 자동 실행
engine.run_pipeline()

# 출력:
# 🚀 Stage 2: 문서 분류 시작... ✅ 완료 (247건 → 482개 문서)
# 🚀 Stage 3: 필드 추출 시작... ✅ 완료 (482개 문서)
# 🚀 Stage 4: 데이터 정규화... ✅ 완료
# 🚀 Stage 5: 대사 실행... ✅ 완료
#   - 완전일치: 198건
#   - 중간일치: 35건
#   - 불일치: 14건
```

### 4. 결과 확인
```python
# e-Book UI 열기 (또는 Excel 다운로드)
engine.open_verification_ui()
```

## 🔄 중단된 프로젝트 재개하기

```python
# 마지막 체크포인트부터 자동 재개
engine = OPALEngine("2025-11-W1")
engine.resume()  # Stage 3 350/482 지점부터 계속
```

---

# 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [프로젝트 관리 시스템](#2-프로젝트-관리-시스템)
3. [워크플로우 자동화](#3-워크플로우-자동화)
4. [시스템 아키텍처](#4-시스템-아키텍처)
5. [데이터 모델](#5-데이터-모델)
6. [Stage 1: Document Parsing](#stage-1-document-parsing)
7. [Stage 2: Document Classification (Splitter)](#stage-2-document-classification-splitter)
8. [Stage 3: Information Extraction (Extractor)](#stage-3-information-extraction-extractor)
9. [Stage 4: Data Normalization](#stage-4-data-normalization)
10. [Stage 5: Reconciliation & Verification](#stage-5-reconciliation--verification)
11. [Frontend: e-Book UI](#frontend-e-book-ui)
12. [배포 및 운영](#배포-및-운영)

---

# 1. 프로젝트 개요

## 1.1 목적
내부감사에서 수작업으로 진행하던 **증빙문서-회계장부 대사 업무**를 AI 기반으로 자동화하여:
- 검증 시간 80% 단축
- 정확도 95% 이상 확보
- 수백 건의 증빙을 End-to-End로 처리

## 1.2 핵심 가치
- **효율성**: SAP 전표 다운로드 → 증빙 수집 → 대사 → 검증까지 원클릭
- **투명성**: AI 추출 근거를 원본 PDF에 하이라이트로 표시
- **확장성**: POSCO 해외법인 (인도네시아, 싱가포르, 미얀마, 일본 등) 모두 적용 가능

## 1.3 대상 문서
- **BL (Bill of Lading)**: 선하증권
- **Commercial Invoice**: 상업송장
- **Packing List**: 포장명세서
- **세금계산서**
- **계약서**

## 1.4 적용 범위
- POSCO International 해외법인 매출/매입 증빙
- 내부감사팀의 분기별/연간 감사 업무
- 재무팀의 전표 검증 업무

---

# 2. 프로젝트 관리 시스템

## 2.1 프로젝트 기반 작업 흐름

IDARS는 **프로젝트 단위**로 증빙대사 작업을 관리합니다. 각 프로젝트는 독립적인 작업 세션으로, 중단/재개가 가능하며 모든 진행 상황이 저장됩니다.

### 프로젝트 생성 예시
```
프로젝트 ID: 2025-10-W4
프로젝트명: 2025년 10월 4주차 매출전표 검증
생성일: 2025-10-28
담당자: CJ
전표 건수: 247건
상태: 진행중 (Stage 3 완료, Stage 4 대기중)
```

## 2.2 프로젝트 상태 관리

### 프로젝트 상태 종류
| 상태 | 설명 | 다음 가능 액션 |
|------|------|----------------|
| **01.created** | 프로젝트 생성됨, 전표 임포트 전 | 전표 임포트 |
| **02.importing** | Stage 1 진행 중 (전표/증빙 다운로드) | 대기 또는 취소 |
| **03.imported** | Stage 1 완료, 증빙 수집 완료 | Stage 2 시작 |
| **04.splitting** | Stage 2 진행 중 (문서 분류) | 대기 또는 일시정지 |
| **05.split_complete** | Stage 2 완료 | Stage 3 시작 |
| **06.extracting** | Stage 3 진행 중 (필드 추출) | 대기 또는 일시정지 |
| **07.extracted** | Stage 3 완료 | Stage 4 시작 |
| **08.normalizing** | Stage 4 진행 중 (데이터 정규화) | 대기 |
| **09.normalized** | Stage 4 완료 | Stage 5 시작 (대사 실행) |
| **10.reconciling** | Stage 5 진행 중 (대사 실행) | 대기 |
| **11.reconciled** | Stage 5 완료, 검증 대기 | 검증 시작 |
| **12.verifying** | 사용자 검증 중 | 중간 저장 가능 |
| **13.completed** | 모든 작업 완료 | 결과 다운로드 |
| **paused** | 일시정지 (어느 Stage든 가능) | 재개 |
| **error** | 에러 발생 | 재시도 또는 수동 개입 |

### 진행 상황 추적 데이터
```json
{
  "project_id": "2025-10-W4",
  "status": "extracting",
  "progress": {
    "stage1": {"status": "completed", "items": 247, "completed": 247},
    "stage2": {"status": "completed", "items": 247, "completed": 247},
    "stage3": {"status": "in_progress", "items": 482, "completed": 350},
    "stage4": {"status": "pending", "items": 0, "completed": 0},
    "stage5": {"status": "pending", "items": 0, "completed": 0}
  },
  "last_checkpoint": "2025-10-28T15:30:00Z",
  "next_action": "Continue Stage 3 extraction"
}
```

## 2.3 중간 저장 및 재개 메커니즘

### BigQuery 체크포인트 테이블
```sql
CREATE TABLE idars.Project_Checkpoints (
  project_id STRING,
  checkpoint_time TIMESTAMP,
  current_stage STRING,  -- "stage1", "stage2", ...
  stage_status STRING,   -- "in_progress", "completed", "error"
  processed_items INT64, -- 현재 Stage에서 처리한 아이템 수
  total_items INT64,     -- 현재 Stage의 총 아이템 수
  last_processed_id STRING, -- 마지막으로 처리한 문서/전표 ID
  error_log JSON,        -- 에러 발생 시 상세 로그
  metadata JSON          -- 기타 메타데이터
);
```

### 재개 로직 예시
```python
# workflow/checkpoint_manager.py

class CheckpointManager:
    def save_checkpoint(self, project_id: str, stage: str, processed_id: str):
        """
        현재 진행 상황을 체크포인트로 저장
        """
        checkpoint = {
            'project_id': project_id,
            'checkpoint_time': datetime.now(),
            'current_stage': stage,
            'stage_status': 'in_progress',
            'last_processed_id': processed_id
        }
        # BigQuery에 INSERT
        self.bq_client.insert_rows('idars.Project_Checkpoints', [checkpoint])
    
    def resume_from_checkpoint(self, project_id: str):
        """
        마지막 체크포인트부터 재개
        """
        query = f"""
        SELECT * FROM idars.Project_Checkpoints
        WHERE project_id = '{project_id}'
        ORDER BY checkpoint_time DESC
        LIMIT 1
        """
        checkpoint = self.bq_client.query(query).to_dataframe().iloc[0]
        
        # 마지막 처리 지점 이후부터 재개
        stage = checkpoint['current_stage']
        last_id = checkpoint['last_processed_id']
        
        return stage, last_id
```

## 2.4 실전 워크플로우 예시

### 시나리오: 2025년 11월 1주차 매출전표 검증

#### 1단계: 프로젝트 생성
```python
# UI 또는 API로 프로젝트 생성
POST /api/projects/create
{
  "project_id": "2025-11-W1",
  "project_name": "2025년 11월 1주차 매출전표 검증",
  "created_by": "CJ",
  "description": "인도네시아 법인 11월 1-7일 매출 증빙 대사"
}
```

#### 2단계: 전표 리스트 임포트
- SAP에서 전표 리스트 다운로드 (247건)
- Excel 파일을 UI에 업로드
- 시스템이 자동으로 BigQuery에 적재 → **상태: imported**

#### 3단계: 증빙 PDF 다운로드
- SAP에서 각 전표별 증빙 PDF 다운로드
- GCS에 자동 업로드 → **상태: imported**

#### 4단계: 자동 파이프라인 실행 (Stage 2~5)
```python
# 파이프라인 트리거 (자동으로 Stage 2→3→4→5 실행)
POST /api/pipeline/start
{
  "project_id": "2025-11-W1"
}

# 시스템이 백그라운드에서 순차 실행:
# Stage 2: Splitter (247개 PDF → 482개 개별 문서)
# Stage 3: Extractor (482개 문서 → 필드 추출)
# Stage 4: Normalizer (데이터 정규화)
# Stage 5: Reconciler (전표-증빙 대사)

# 중간에 에러 발생 시:
# - 체크포인트 저장
# - 담당자에게 알림
# - 나중에 재개 가능
```

#### 5단계: 사용자 검증
- **대사 결과 확인**:
  - 완전일치: 198건 → 자동 승인
  - 중간일치: 35건 → AI 재분석 또는 수동 검토
  - 불일치: 14건 → 수동 검토 필수

- **e-Book UI에서 검토**:
  - 중간일치/불일치 건을 하나씩 확인
  - 원본 PDF + 하이라이트 확인
  - 최종 결론 입력 (일치/불일치)
  - 메모 작성

#### 6단계: 중간 저장
- 검증 도중 퇴근 → "중간 저장" 클릭
- 다음날 출근 → "계속하기" 클릭하여 재개
- 진행 상황이 모두 보존됨

#### 7단계: 완료 및 결과 다운로드
- 모든 전표 검증 완료 → **상태: completed**
- 결과 Excel 다운로드
- 감사 보고서 생성

### 소요 시간 예상
| 단계 | 수작업 | IDARS 자동화 | 절감 시간 |
|------|--------|--------------|-----------|
| 전표 임포트 | 30분 | 5분 | -25분 |
| 증빙 다운로드 | 2시간 | 30분 (RPA) | -1.5시간 |
| 문서 분류 | 4시간 | 10분 (AI) | -3.9시간 |
| 필드 추출 | 8시간 | 15분 (AI) | -7.75시간 |
| 대사 실행 | 3시간 | 5분 (자동) | -2.95시간 |
| 검증 | 5시간 | 2시간 (불일치만) | -3시간 |
| **합계** | **22.5시간** | **3.5시간** | **-19시간 (84%)** |

---

## 2.5 프로젝트 UI

### 프로젝트 목록 화면
```
┌──────────────────────────────────────────────────────────────┐
│  📁 IDARS 프로젝트 목록                    [+ 새 프로젝트]    │
├──────────────────────────────────────────────────────────────┤
│  검색: [프로젝트명 검색...]                                   │
│  필터: [전체] [진행중] [완료] [일시정지]                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 📊 2025년 10월 4주차 매출전표                           │  │
│  │ ID: 2025-10-W4 | 생성: 2025-10-28 | 담당: CJ          │  │
│  │                                                         │  │
│  │ 전표: 247건                                             │  │
│  │ 진행: [████████░░] 80% (Stage 3 진행중)                │  │
│  │ ├─ Stage 1: ✅ 완료 (247/247)                          │  │
│  │ ├─ Stage 2: ✅ 완료 (247/247)                          │  │
│  │ ├─ Stage 3: 🔄 진행중 (350/482 문서)                   │  │
│  │ ├─ Stage 4: ⏸️ 대기                                    │  │
│  │ └─ Stage 5: ⏸️ 대기                                    │  │
│  │                                                         │  │
│  │ 마지막 체크포인트: 2025-10-28 15:30                     │  │
│  │                                                         │  │
│  │ [계속하기] [일시정지] [삭제] [복사]                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 📊 2025년 10월 3주차 매출전표                           │  │
│  │ ID: 2025-10-W3 | 생성: 2025-10-21 | 담당: CJ          │  │
│  │                                                         │  │
│  │ 전표: 189건                                             │  │
│  │ 진행: [██████████] 100% (완료)                         │  │
│  │ ├─ 완전일치: 152건 (80.4%)                             │  │
│  │ ├─ 중간일치: 28건 (14.8%)                              │  │
│  │ └─ 불일치: 9건 (4.8%)                                  │  │
│  │                                                         │  │
│  │ [결과 보기] [엑셀 다운로드] [보고서 생성]               │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

# 3. 워크플로우 자동화

## 3.1 파이프라인 오케스트레이션 도구 비교

IDARS의 5단계 파이프라인을 자동으로 연결하기 위해 다음 도구들을 고려할 수 있습니다:

### 옵션 1: **Cloud Composer (Apache Airflow)** ⭐ 추천
**장점:**
- GCP 네이티브 서비스 (BigQuery, GCS와 완벽 통합)
- 복잡한 의존성 관리 (DAG - Directed Acyclic Graph)
- 에러 발생 시 자동 재시도, 알림
- 웹 UI로 파이프라인 모니터링
- Python 코드로 워크플로우 정의

**단점:**
- 비교적 무겁고 비용 발생 (작은 프로젝트엔 과할 수 있음)
- 설정 복잡도가 높음

**사용 예시:**
```python
# airflow_dag.py (IDARS 파이프라인 DAG)

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def stage1_import(**kwargs):
    # Stage 1 로직 실행
    from data_pipeline.stage1_parser import Stage1Parser
    parser = Stage1Parser(project_id=kwargs['project_id'])
    parser.run()

def stage2_split(**kwargs):
    # Stage 2 로직 실행
    from data_pipeline.stage2_splitter import Stage2Splitter
    splitter = Stage2Splitter(project_id=kwargs['project_id'])
    splitter.run()

# ... stage3, stage4, stage5 함수들

with DAG(
    'idars_pipeline',
    start_date=datetime(2025, 10, 28),
    schedule_interval=None,  # 수동 트리거
    catchup=False
) as dag:
    
    task_stage1 = PythonOperator(
        task_id='stage1_import',
        python_callable=stage1_import,
        op_kwargs={'project_id': '{{ dag_run.conf["project_id"] }}'}
    )
    
    task_stage2 = PythonOperator(
        task_id='stage2_split',
        python_callable=stage2_split,
        op_kwargs={'project_id': '{{ dag_run.conf["project_id"] }}'}
    )
    
    task_stage3 = PythonOperator(
        task_id='stage3_extract',
        python_callable=stage3_extract,
        op_kwargs={'project_id': '{{ dag_run.conf["project_id"] }}'}
    )
    
    task_stage4 = PythonOperator(
        task_id='stage4_normalize',
        python_callable=stage4_normalize,
        op_kwargs={'project_id': '{{ dag_run.conf["project_id"] }}'}
    )
    
    task_stage5 = PythonOperator(
        task_id='stage5_reconcile',
        python_callable=stage5_reconcile,
        op_kwargs={'project_id': '{{ dag_run.conf["project_id"] }}'}
    )
    
    # 의존성 정의 (순서대로 실행)
    task_stage1 >> task_stage2 >> task_stage3 >> task_stage4 >> task_stage5
```

**트리거 방법:**
```bash
# REST API로 프로젝트 시작
curl -X POST http://airflow-webserver/api/v1/dags/idars_pipeline/dagRuns \
  -H "Content-Type: application/json" \
  -d '{"conf": {"project_id": "2025-10-W4"}}'
```

---

### 옵션 2: **n8n** 
**장점:**
- 노코드/로우코드 워크플로우 도구
- 시각적인 노드 기반 UI (드래그 앤 드롭)
- Webhook, HTTP Request 노드로 Python 스크립트 트리거 가능
- 빠른 프로토타입 제작

**단점:**
- GCP 서비스와 통합이 Airflow보다 약함
- 복잡한 에러 핸들링이 어려움
- 대규모 데이터 처리엔 부적합

**사용 시나리오:**
- Stage 1~5를 각각 HTTP 엔드포인트로 노출
- n8n에서 순차적으로 HTTP Request 노드로 호출

---

### 옵션 3: **OPAL (자체 개발 워크플로우 엔진)**
**장점:**
- 완전히 커스터마이징 가능
- 가벼움 (필요한 기능만 구현)
- IDARS에 특화된 로직 (예: Stage 3에서 신뢰도 낮은 문서만 수동 검토)

**단점:**
- 직접 개발/유지보수 필요
- 모니터링, 로깅, 재시도 로직 등을 모두 구현해야 함

**구조:**
```python
# workflow/opal_engine.py

class OPALEngine:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.checkpoint_mgr = CheckpointManager()
    
    def run_pipeline(self):
        """
        5단계 파이프라인 순차 실행
        """
        stages = [
            ('stage1', self.run_stage1),
            ('stage2', self.run_stage2),
            ('stage3', self.run_stage3),
            ('stage4', self.run_stage4),
            ('stage5', self.run_stage5)
        ]
        
        # 마지막 체크포인트 확인
        last_stage, last_id = self.checkpoint_mgr.resume_from_checkpoint(self.project_id)
        
        # 마지막 Stage부터 재개
        start_idx = next(i for i, (name, _) in enumerate(stages) if name == last_stage)
        
        for stage_name, stage_func in stages[start_idx:]:
            try:
                print(f"🚀 {stage_name} 시작...")
                stage_func()
                
                # 체크포인트 저장
                self.checkpoint_mgr.save_checkpoint(
                    self.project_id, 
                    stage_name, 
                    status='completed'
                )
                
                print(f"✅ {stage_name} 완료")
            
            except Exception as e:
                print(f"❌ {stage_name} 에러: {e}")
                
                # 에러 로그 저장
                self.checkpoint_mgr.save_checkpoint(
                    self.project_id,
                    stage_name,
                    status='error',
                    error_log=str(e)
                )
                
                # 알림 발송 (이메일, Slack 등)
                self.send_error_notification(stage_name, e)
                
                # 파이프라인 중단
                break
    
    def run_stage1(self):
        from data_pipeline.stage1_parser import Stage1Parser
        parser = Stage1Parser(self.project_id)
        parser.run()
    
    # ... 나머지 stage 함수들
```

---

## 3.2 권장 아키텍처: Cloud Composer + 자체 오케스트레이터 하이브리드

### 🎯 CJ님 프로젝트에 대한 추천

**초기 개발 (현재)**: **자체 Python 오케스트레이터**
- 이유:
  - 빠른 프로토타입 제작
  - Cloud Composer 설정 복잡도 회피
  - 비용 절감
  - IDARS 특화 로직 구현 용이
  
**실전 배포 (3개월 후)**: **Cloud Composer (Airflow)**
- 이유:
  - 안정적인 운영
  - 웹 UI 모니터링
  - 자동 재시도, 알림
  - 스케줄링 (주간/월간 자동 실행)

### Phase 1: MVP (자체 오케스트레이터)
초기에는 **OPAL 스타일의 간단한 Python 스크립트**로 시작:
```python
# run_pipeline.py

from workflow.opal_engine import OPALEngine

if __name__ == '__main__':
    project_id = input("프로젝트 ID 입력: ")
    
    engine = OPALEngine(project_id)
    engine.run_pipeline()
```

**실행:**
```bash
python run_pipeline.py
# 입력: 2025-10-W4
# 출력: 
# 🚀 stage1 시작...
# ✅ stage1 완료
# 🚀 stage2 시작...
# ... (계속)
```

### Phase 2: Production (Cloud Composer)
실전 배포 시 **Cloud Composer (Airflow)**로 마이그레이션:
- 웹 UI로 진행 상황 모니터링
- 자동 재시도 (Splitter API 타임아웃 등)
- Slack 알림 연동
- 스케줄링 (예: 매주 월요일 자동 실행)

---

## 3.3 이벤트 기반 트리거 (고급)

각 Stage가 완료되면 **Pub/Sub 이벤트**를 발행하여 다음 Stage를 자동 트리거:

```python
# workflow/event_publisher.py

from google.cloud import pubsub_v1

class EventPublisher:
    def __init__(self):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = 'projects/your-project/topics/idars-pipeline'
    
    def publish_stage_complete(self, project_id: str, stage: str):
        """
        Stage 완료 이벤트 발행
        """
        message = {
            'project_id': project_id,
            'completed_stage': stage,
            'next_stage': self._get_next_stage(stage),
            'timestamp': datetime.now().isoformat()
        }
        
        self.publisher.publish(
            self.topic_path,
            json.dumps(message).encode('utf-8')
        )
```

**Cloud Functions로 구독:**
```python
# cloud_functions/stage_trigger.py

def on_stage_complete(event, context):
    """
    Pub/Sub 메시지를 받아 다음 Stage 실행
    """
    message = json.loads(base64.b64decode(event['data']))
    
    project_id = message['project_id']
    next_stage = message['next_stage']
    
    # 다음 Stage 실행 (Cloud Run Job 트리거 또는 직접 실행)
    if next_stage == 'stage2':
        trigger_stage2(project_id)
    elif next_stage == 'stage3':
        trigger_stage3(project_id)
    # ...
```

---

## 3.4 파이프라인 모니터링 대시보드

### 실시간 진행 상황 표시
```
┌──────────────────────────────────────────────────────────────┐
│  🚀 파이프라인 실행 중: 2025-10-W4                            │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Stage 1: Import        ✅ 완료 (247/247)  [00:02:15]        │
│  Stage 2: Split         ✅ 완료 (247/247)  [00:05:30]        │
│  Stage 3: Extract       🔄 진행중 (350/482) [00:12:45]       │
│  Stage 4: Normalize     ⏸️ 대기                              │
│  Stage 5: Reconcile     ⏸️ 대기                              │
│                                                               │
│  현재 처리 중: doc_94456950 (BL 필드 추출)                    │
│  예상 완료 시간: 2025-10-28 16:00 (약 15분 남음)             │
│                                                               │
│  [일시정지] [취소] [로그 보기]                                │
└──────────────────────────────────────────────────────────────┘
```

---

# 4. 시스템 아키텍처

## 4.1 전체 구조도
```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (React)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐      │
│  │ 프로젝트    │  │ 임포트 시트  │  │ 대사결과시트  │      │
│  │ 관리        │  │              │  │ (e-Book)      │      │
│  └─────────────┘  └──────────────┘  └───────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────┴────────────────────────────────────┐
│                Backend (Flask on Cloud Run)                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │
│  │ Projects │  │ Pipeline │  │ Reconcile │  │ Documents│  │
│  │ API      │  │ Control  │  │ API       │  │ API      │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│            Workflow Orchestrator (Cloud Composer)            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  DAG: IDARS Pipeline                                   │ │
│  │  Stage1 → Stage2 → Stage3 → Stage4 → Stage5           │ │
│  │  (자동 재시도, 에러 알림, 체크포인트)                   │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│              Data Pipeline (Python Scripts)                  │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌───────────┐   │
│  │ Stage 1  │→ │Stage 2  │→ │ Stage 3  │→ │ Stage 4   │   │
│  │ Parsing  │  │Splitter │  │Extractor │  │Normalize  │   │
│  └──────────┘  └─────────┘  └──────────┘  └───────────┘   │
│                                      ↓                       │
│                              ┌───────────────┐              │
│                              │  Stage 5      │              │
│                              │  Reconcile    │              │
│                              └───────────────┘              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────┐
│                  Storage Layer                               │
│  ┌──────────────┐                  ┌──────────────┐         │
│  │  BigQuery    │                  │     GCS      │         │
│  │  (테이블 6개)│                  │  (PDF 원본)  │         │
│  │  + Checkpoints│                 │              │         │
│  └──────────────┘                  └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## 4.2 기술 스택

### Frontend
- **Framework**: React 18
- **UI 라이브러리**: Material-UI, AG-Grid (데이터 그리드)
- **PDF 뷰어**: PDF.js, React-PDF
- **상태관리**: React Query, Context API
- **배포**: Cloud Run (또는 Vercel)

### Backend
- **API Framework**: Flask 3.0
- **워크플로우 오케스트레이터**: Cloud Composer (Apache Airflow) 또는 OPAL (자체 개발)
- **배포**: Google Cloud Run
- **인증**: Cloud IAM / OAuth 2.0

### Data Pipeline
- **언어**: Python 3.11
- **AI 모델**:
  - Splitter: Vertex AI Document AI (Custom Model - F1 0.868)
  - Extractor: Vertex AI Document AI (Custom Model - 개발 중)
- **데이터 처리**: Pandas, PyPDF2, pytesseract

### Storage
- **문서 저장**: Google Cloud Storage (GCS)
- **구조화 데이터**: BigQuery
- **캐시**: Cloud Memorystore (Redis)

### Workflow Automation
- **Phase 1 (MVP)**: Python 스크립트 기반 순차 실행
- **Phase 2 (Production)**: Cloud Composer (Apache Airflow)
- **이벤트 버스**: Cloud Pub/Sub (고급 기능)

---

# 5. 데이터 모델

## 5.1 BigQuery 테이블 스키마

### Table 1: `Projects`
프로젝트 메타데이터 및 진행 상황

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| project_id | STRING | 프로젝트 고유 ID | "2025-10-W4" |
| project_name | STRING | 사용자 정의 이름 | "2025년 10월 4주차 매출" |
| created_at | TIMESTAMP | 생성 시각 | 2025-10-28T10:00:00Z |
| created_by | STRING | 생성자 | "CJ" |
| status | STRING | 진행 상태 | "extracting" / "completed" / "paused" |
| current_stage | STRING | 현재 진행 중인 Stage | "stage3" |
| total_slips | INTEGER | 전표 총 건수 | 247 |
| processed_slips | INTEGER | 처리 완료 건수 | 198 |
| stage1_status | STRING | Stage 1 상태 | "completed" |
| stage1_progress | JSON | Stage 1 진행률 | {"total": 247, "completed": 247} |
| stage2_status | STRING | Stage 2 상태 | "completed" |
| stage2_progress | JSON | Stage 2 진행률 | {"total": 247, "completed": 247} |
| stage3_status | STRING | Stage 3 상태 | "in_progress" |
| stage3_progress | JSON | Stage 3 진행률 | {"total": 482, "completed": 350} |
| stage4_status | STRING | Stage 4 상태 | "pending" |
| stage5_status | STRING | Stage 5 상태 | "pending" |
| last_checkpoint | TIMESTAMP | 마지막 체크포인트 시각 | 2025-10-28T15:30:00Z |
| error_log | JSON | 에러 로그 (nullable) | null |

### Table 2: `Project_Checkpoints`
중간 저장 및 재개를 위한 체크포인트

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| checkpoint_id | STRING | 체크포인트 ID (PK) | "ckpt_2025-10-W4_001" |
| project_id | STRING | 프로젝트 ID (FK) | "2025-10-W4" |
| checkpoint_time | TIMESTAMP | 체크포인트 생성 시각 | 2025-10-28T15:30:00Z |
| current_stage | STRING | 현재 Stage | "stage3" |
| stage_status | STRING | Stage 상태 | "in_progress" |
| processed_items | INTEGER | 현재 Stage 처리 완료 건수 | 350 |
| total_items | INTEGER | 현재 Stage 총 건수 | 482 |
| last_processed_id | STRING | 마지막 처리 ID | "doc_94456950" |
| error_log | JSON | 에러 발생 시 로그 | null |
| metadata | JSON | 기타 메타데이터 | {"retry_count": 0} |

### Table 3: `Sales_Ledger`
### Table 3: `Sales_Ledger`
매출 전표 원장 (SAP에서 임포트)

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| project_id | STRING | 소속 프로젝트 | "2025-10-W4" |
| slip_id | STRING | 전표번호 (PK) | "94456924" |
| slip_date | DATE | 전표 일자 | 2025-10-25 |
| slip_amount | FLOAT64 | 전표 금액 | 125000.00 |
| slip_currency | STRING | 통화 | "USD" |
| bl_number | STRING | BL 번호 | "HDMUSGD250001234" |
| customer_name | STRING | 거래처명 | "ABC Trading Co." |
| remarks | STRING | 비고 | "October shipment" |
| evidence_downloaded | BOOLEAN | 증빙 다운로드 완료 여부 | true |
| evidence_gcs_path | STRING | 증빙 PDF GCS 경로 | "gs://idars-evidence/2025-10-W4/94456924.pdf" |

### Table 4: `Documents`
분류된 개별 문서 (Splitter 결과)

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| document_id | STRING | 문서 고유 ID (PK) | "doc_94456924_001" |
| slip_id | STRING | 연결된 전표번호 (FK) | "94456924" |
| document_type | STRING | 문서 유형 | "bl" / "invoice" / "pl" |
| confidence_score | FLOAT64 | 분류 신뢰도 | 0.95 |
| page_range | STRING | 원본 PDF 페이지 범위 | "1-3" |
| gcs_path | STRING | 분할된 PDF 경로 | "gs://idars-split/2025-11-W1/doc_94456924_001.pdf" |
| created_at | TIMESTAMP | 분류 시각 | 2025-11-16T10:15:00Z |

### Table 5: `Extracted_Data`
추출된 필드 데이터 (Extractor 결과)

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| extraction_id | STRING | 추출 결과 ID (PK) | "ext_94456924_001" |
| document_id | STRING | 원본 문서 ID (FK) | "doc_94456924_001" |
| slip_id | STRING | 연결된 전표번호 (FK) | "94456924" |
| document_type | STRING | 문서 유형 | "bl" |
| bl_number | STRING | BL 번호 | "HDMUSGD250001234" |
| bl_number_confidence | FLOAT64 | 신뢰도 | 0.98 |
| bl_number_bbox | STRING | Bounding Box (JSON) | "[{\"x\":100,\"y\":200,\"w\":150,\"h\":20}]" |
| invoice_number | STRING | Invoice 번호 | "INV-2025-001234" |
| invoice_confidence | FLOAT64 | 신뢰도 | 0.96 |
| total_amount | FLOAT64 | 총 금액 | 125000.00 |
| amount_confidence | FLOAT64 | 신뢰도 | 0.99 |
| currency | STRING | 통화 | "USD" |
| invoice_date | DATE | Invoice 일자 | 2025-10-23 |
| shipper | STRING | 발송인 | "POSCO International Corp." |
| consignee | STRING | 수하인 | "ABC Trading Co." |
| raw_json | JSON | 전체 추출 결과 (JSON) | {...} |
| created_at | TIMESTAMP | 추출 시각 | 2025-10-28T14:20:00Z |

### Table 6: `Reconciliation_Results`
대사 결과

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| reconciliation_id | STRING | 대사 결과 ID (PK) | "recon_94456924" |
| slip_id | STRING | 전표번호 (FK) | "94456924" |
| project_id | STRING | 프로젝트 ID | "2025-11-W1" |
| match_status | STRING | 3단계 판정 | "perfect_match" / "partial_match" / "mismatch" |
| bl_match | BOOLEAN | BL 번호 일치 여부 | true |
| amount_match | BOOLEAN | 금액 일치 여부 | true |
| amount_diff | FLOAT64 | 금액 차이 | 0.00 |
| amount_diff_pct | FLOAT64 | 금액 차이 비율 (%) | 0.0 |
| date_match | BOOLEAN | 날짜 일치 여부 | true |
| date_diff_days | INTEGER | 날짜 차이 (일) | 0 |
| ai_reanalysis_result | STRING | AI 재분석 결과 (nullable) | "금액 일치, BL 번호 오타 의심" |
| ai_reanalysis_at | TIMESTAMP | AI 재분석 시각 | 2025-10-28T16:00:00Z |
| final_conclusion | STRING | 최종 결론 (사용자 입력) | "match" / "mismatch" / "pending" |
| final_memo | STRING | 검증자 메모 | "환율 차이로 인한 오차, 문제없음" |
| verified_by | STRING | 검증자 | "CJ" |
| verified_at | TIMESTAMP | 검증 시각 | 2025-10-28T17:30:00Z |
| created_at | TIMESTAMP | 대사 실행 시각 | 2025-10-28T15:25:00Z |

## 5.2 GCS 폴더 구조
```
gs://idars-bucket/
├── evidence/                     # 원본 증빙 PDF (SAP 다운로드)
│   └── {project_id}/
│       └── {slip_id}.pdf
├── split/                        # Splitter로 분할된 개별 문서
│   └── {project_id}/
│       └── {document_id}.pdf
├── highlights/                   # 추출 필드 하이라이트 JSON
│   └── {project_id}/
│       └── {document_id}_highlight.json
└── exports/                      # 최종 결과 엑셀
    └── {project_id}_result.xlsx
```

---

# Stage 1: Document Parsing

## 현재 상태
- [x] 완료
- [ ] 진행중
- [ ] 미착수

## 목적
SAP에서 다운로드한 전표 리스트(Excel)와 증빙 PDF 묶음을 시스템에 임포트

## 입력
- **전표 리스트**: Excel 파일 (.xlsx)
  - 필수 컬럼: 전표번호, 전표일자, 금액, 통화, BL번호, 거래처명
- **증빙 PDF**: 각 전표별로 1개의 PDF (여러 페이지 포함 가능)

## 출력
- BigQuery `Sales_Ledger` 테이블에 전표 데이터 적재
- GCS `evidence/{project_id}/` 경로에 PDF 업로드
- 각 전표에 증빙 파일 경로 매핑

## Tech Spec

### 구현 방향 (초안)
```python
# data_pipeline/stage1_parser.py

import pandas as pd
from google.cloud import storage, bigquery

class Stage1Parser:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.gcs_client = storage.Client()
        self.bq_client = bigquery.Client()
        
    def import_excel(self, excel_path: str):
        """
        전표 리스트 Excel 읽기
        """
        df = pd.read_excel(excel_path)
        
        # 컬럼 검증
        required_cols = ['전표번호', '전표일자', '금액', '통화', 'BL번호', '거래처명']
        missing = set(required_cols) - set(df.columns)
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}")
        
        # 데이터 정제
        df = df.rename(columns={
            '전표번호': 'slip_id',
            '전표일자': 'slip_date',
            '금액': 'slip_amount',
            '통화': 'slip_currency',
            'BL번호': 'bl_number',
            '거래처명': 'customer_name'
        })
        
        return df
    
    def upload_pdfs(self, pdf_folder: str):
        """
        증빙 PDF들을 GCS에 업로드
        """
        bucket = self.gcs_client.bucket('idars-bucket')
        uploaded_paths = {}
        
        for pdf_file in os.listdir(pdf_folder):
            if not pdf_file.endswith('.pdf'):
                continue
            
            slip_id = pdf_file.replace('.pdf', '')
            blob_name = f"evidence/{self.project_id}/{slip_id}.pdf"
            blob = bucket.blob(blob_name)
            
            blob.upload_from_filename(os.path.join(pdf_folder, pdf_file))
            uploaded_paths[slip_id] = f"gs://idars-bucket/{blob_name}"
        
        return uploaded_paths
    
    def load_to_bigquery(self, df: pd.DataFrame, gcs_paths: dict):
        """
        BigQuery에 전표 데이터 적재
        """
        df['project_id'] = self.project_id
        df['evidence_downloaded'] = True
        df['evidence_gcs_path'] = df['slip_id'].map(gcs_paths)
        
        table_id = "your-project.idars.Sales_Ledger"
        job = self.bq_client.load_table_from_dataframe(df, table_id)
        job.result()  # 완료 대기
```

### 사용 예시
```python
parser = Stage1Parser(project_id="2025-11-W1")

# 1. Excel 읽기
ledger_df = parser.import_excel("전표리스트_11월1주.xlsx")

# 2. PDF 업로드
gcs_paths = parser.upload_pdfs("증빙PDF폴더/")

# 3. BigQuery 적재
parser.load_to_bigquery(ledger_df, gcs_paths)
```

### 구현 후 기록
(Claude Code로 작업 후 여기에 기록)
- **사용 라이브러리**:
- **성능**:
- **발견된 이슈**:
- **다음 단계 TODO**:

---

# Stage 2: Document Classification (Splitter)

## 현재 상태
- [x] 완료
- [ ] 진행중
- [ ] 미착수

## 목적
여러 문서가 합쳐진 PDF 번들을 개별 문서(BL, Invoice, Packing List 등)로 자동 분류

## 입력
- GCS에 저장된 증빙 PDF (여러 페이지)

## 출력
- 분류된 개별 문서 PDF (GCS `split/{project_id}/` 경로)
- BigQuery `Documents` 테이블에 분류 결과 저장
  - 문서 유형, 신뢰도, 페이지 범위

## Tech Spec

### AI 모델 정보
- **모델 유형**: Vertex AI Document AI Custom Classifier
- **학습 데이터**: 
  - BL: 500개
  - Invoice: 600개
  - Packing List: 400개
  - 기타: 200개
- **성능**: F1 Score 0.868
- **배포 상태**: Production 배포 완료

### API 엔드포인트
```
POST https://us-documentai.googleapis.com/v1/projects/{PROJECT_ID}/locations/us/processors/{PROCESSOR_ID}:process
```

### 구현 방향 (초안)
```python
# data_pipeline/stage2_splitter.py

from google.cloud import documentai_v1 as documentai
from google.cloud import storage
import json

class Stage2Splitter:
    def __init__(self, project_id: str, processor_id: str):
        self.project_id = project_id
        self.processor_id = processor_id
        self.docai_client = documentai.DocumentProcessorServiceClient()
        self.gcs_client = storage.Client()
    
    def split_pdf(self, slip_id: str, pdf_gcs_path: str):
        """
        PDF를 Splitter API로 분류
        """
        # GCS에서 PDF 다운로드
        bucket_name, blob_name = self._parse_gcs_path(pdf_gcs_path)
        bucket = self.gcs_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        pdf_content = blob.download_as_bytes()
        
        # Splitter API 호출
        name = f"projects/{self.project_id}/locations/us/processors/{self.processor_id}"
        request = documentai.ProcessRequest(
            name=name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
        )
        
        result = self.docai_client.process_document(request=request)
        
        # 분류 결과 파싱
        documents = []
        for entity in result.document.entities:
            doc_type = entity.type_  # "bl", "invoice", "pl" 등
            confidence = entity.confidence
            page_range = self._get_page_range(entity)
            
            documents.append({
                'type': doc_type,
                'confidence': confidence,
                'page_range': page_range
            })
        
        return documents
    
    def save_split_documents(self, slip_id: str, documents: list):
        """
        분류된 문서를 개별 PDF로 저장
        """
        # PyPDF2로 페이지 분할 후 GCS 업로드
        # (구현 상세 생략)
        pass
```

### 구현 후 기록
- **사용 라이브러리**: google-cloud-documentai, PyPDF2
- **성능**: 평균 1개 PDF (10페이지) 처리 시간 3초
- **발견된 이슈**: 
  - 신뢰도 < 0.7인 경우 분류 실패 → 수동 분류 필요
  - 스캔 품질 낮은 PDF는 OCR 정확도 하락
- **다음 단계 TODO**: 
  - 신뢰도 낮은 문서에 대한 fallback 로직 추가
  - 사용자 피드백으로 재학습 데이터 수집

---

# Stage 3: Information Extraction (Extractor)

## 현재 상태
- [ ] 완료
- [x] 진행중 (라벨링 단계)
- [ ] 미착수

## 목적
분류된 문서(BL, Invoice)에서 핵심 필드 자동 추출

## 추출 대상 필드

### BL (Bill of Lading)
- BL Number
- Shipper (발송인)
- Consignee (수하인)
- Vessel Name (선박명)
- Port of Loading (선적항)
- Port of Discharge (양륙항)
- Container Number (컨테이너 번호)
- Total Packages (총 패키지 수)
- Gross Weight (총 중량)
- Issue Date (발행일자)

### Commercial Invoice
- Invoice Number
- Invoice Date
- Supplier (공급자)
- Buyer (구매자)
- Total Amount (총 금액)
- Currency (통화)
- Payment Terms (결제 조건)
- Item List (품목 리스트)
  - Description (품명)
  - Quantity (수량)
  - Unit Price (단가)
  - Amount (금액)

## 출력
- BigQuery `Extracted_Data` 테이블에 추출 결과 저장
- GCS `highlights/{project_id}/` 경로에 Bounding Box JSON 저장

## Tech Spec

### AI 모델 정보
- **모델 유형**: Vertex AI Document AI Custom Extractor
- **학습 데이터**: 
  - BL: 라벨링 중 (목표 300개)
  - Invoice: 라벨링 중 (목표 400개)
- **성능**: (학습 완료 후 기록)
- **배포 상태**: 라벨링 단계

### 구현 방향 (초안)
```python
# data_pipeline/stage3_extractor.py

from google.cloud import documentai_v1 as documentai
import json

class Stage3Extractor:
    def __init__(self, project_id: str, bl_processor_id: str, invoice_processor_id: str):
        self.project_id = project_id
        self.bl_processor_id = bl_processor_id
        self.invoice_processor_id = invoice_processor_id
        self.docai_client = documentai.DocumentProcessorServiceClient()
    
    def extract_fields(self, document_id: str, doc_type: str, pdf_content: bytes):
        """
        문서 유형에 따라 필드 추출
        """
        processor_id = self.bl_processor_id if doc_type == 'bl' else self.invoice_processor_id
        
        name = f"projects/{self.project_id}/locations/us/processors/{processor_id}"
        request = documentai.ProcessRequest(
            name=name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
        )
        
        result = self.docai_client.process_document(request=request)
        
        # 필드 추출 결과 파싱
        extracted = {}
        bboxes = {}
        
        for entity in result.document.entities:
            field_name = entity.type_
            field_value = entity.mention_text
            confidence = entity.confidence
            bbox = self._get_bbox(entity)
            
            extracted[field_name] = field_value
            extracted[f"{field_name}_confidence"] = confidence
            bboxes[field_name] = bbox
        
        return {
            'extracted_data': extracted,
            'bounding_boxes': bboxes,
            'raw_json': result.document.to_dict()
        }
    
    def _get_bbox(self, entity):
        """
        Entity의 Bounding Box 좌표 추출
        """
        # (구현 상세 생략)
        pass
```

### 구현 후 기록
- **사용 라이브러리**:
- **성능**:
- **발견된 이슈**:
- **다음 단계 TODO**:

---

# Stage 4: Data Normalization

## 현재 상태
- [ ] 완료
- [ ] 진행중
- [x] 미착수

## 목적
추출된 데이터를 정규화하여 대사에 사용 가능한 형태로 변환

## 처리 항목
1. **통화 변환**: 모든 금액을 USD 기준으로 환산
2. **날짜 표준화**: 다양한 날짜 형식 → ISO 8601 (YYYY-MM-DD)
3. **계정과목 매핑**: 거래처명 → 표준 거래처 코드
4. **BL 번호 정제**: 공백, 특수문자 제거
5. **금액 반올림**: 소수점 2자리

## 입력
- BigQuery `Extracted_Data` 테이블의 원시 데이터

## 출력
- 동일 테이블에 정규화된 필드 추가
  - `normalized_amount_usd`
  - `normalized_date`
  - `normalized_bl_number`

## Tech Spec

### 구현 방향 (초안)
```python
# data_pipeline/stage4_normalizer.py

import pandas as pd
from datetime import datetime
import re

class Stage4Normalizer:
    def __init__(self):
        # 환율 테이블 (실시간 API 또는 고정값)
        self.exchange_rates = {
            'USD': 1.0,
            'IDR': 0.000063,  # 예시
            'SGD': 0.74,
            'JPY': 0.0067
        }
    
    def normalize_amount(self, amount: float, currency: str) -> float:
        """
        금액을 USD로 환산
        """
        rate = self.exchange_rates.get(currency, 1.0)
        return round(amount * rate, 2)
    
    def normalize_date(self, date_str: str) -> str:
        """
        날짜를 ISO 8601 형식으로 변환
        """
        # 다양한 포맷 시도
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y.%m.%d',
            '%d-%b-%Y'  # 15-Nov-2025
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except:
                continue
        
        raise ValueError(f"날짜 파싱 실패: {date_str}")
    
    def normalize_bl_number(self, bl_num: str) -> str:
        """
        BL 번호 정제 (공백, 특수문자 제거, 대문자 변환)
        """
        bl_num = re.sub(r'[^A-Z0-9]', '', bl_num.upper())
        return bl_num
```

### 구현 후 기록
- **사용 라이브러리**:
- **성능**:
- **발견된 이슈**:
- **다음 단계 TODO**:

---

# Stage 5: Reconciliation & Verification

## 현재 상태
- [ ] 완료
- [ ] 진행중
- [x] 미착수

## 목적
전표 데이터와 추출된 증빙 데이터를 규칙 기반으로 비교하여 일치 여부 판정

## 3단계 일치 판정

| 판정 | 조건 | 후속 조치 |
|------|------|----------|
| **완전일치** | 모든 핵심 필드 100% 일치 | 자동 승인 |
| **중간일치** | 일부 필드만 일치 (80~99% 유사도) | AI 재분석 또는 수동 검토 |
| **불일치** | 핵심 필드 명확히 다름 | 수동 검토 필수 |

## 비교 규칙

### BL Number
- **완전 일치**: 문자열 100% 동일
- **중간 일치**: Levenshtein Distance < 2 (오타 1~2자)
- **불일치**: 그 외

### 금액
- **완전 일치**: 절대값 차이 = 0
- **중간 일치**: 차이 < 1% 또는 < $10
- **불일치**: 그 외

### 날짜
- **완전 일치**: 날짜 동일
- **중간 일치**: ±3일 이내
- **불일치**: 그 외

## Tech Spec

### 구현 방향 (초안)
```python
# data_pipeline/stage5_reconciler.py

from google.cloud import bigquery
from Levenshtein import distance as lev_distance

class Stage5Reconciler:
    def __init__(self):
        self.bq_client = bigquery.Client()
    
    def reconcile_project(self, project_id: str):
        """
        프로젝트의 모든 전표에 대해 대사 실행
        """
        # BigQuery에서 전표 & 추출 데이터 JOIN
        query = f"""
        SELECT 
            s.slip_id,
            s.slip_amount,
            s.slip_currency,
            s.slip_date,
            s.bl_number AS slip_bl,
            e.bl_number AS extracted_bl,
            e.total_amount AS extracted_amount,
            e.currency AS extracted_currency,
            e.invoice_date AS extracted_date
        FROM `idars.Sales_Ledger` s
        LEFT JOIN `idars.Extracted_Data` e 
            ON s.slip_id = e.slip_id
        WHERE s.project_id = '{project_id}'
        """
        
        results = self.bq_client.query(query).to_dataframe()
        
        # 각 행에 대해 대사 로직 적용
        recon_results = []
        for _, row in results.iterrows():
            result = self._compare_slip(row)
            recon_results.append(result)
        
        # BigQuery에 결과 저장
        self._save_results(recon_results)
        
        return {
            'total': len(recon_results),
            'perfect_match': sum(1 for r in recon_results if r['match_status'] == 'perfect_match'),
            'partial_match': sum(1 for r in recon_results if r['match_status'] == 'partial_match'),
            'mismatch': sum(1 for r in recon_results if r['match_status'] == 'mismatch')
        }
    
    def _compare_slip(self, row):
        """
        개별 전표 대사
        """
        # BL Number 비교
        bl_match = (row['slip_bl'] == row['extracted_bl'])
        bl_similarity = 1.0 if bl_match else (1 - lev_distance(row['slip_bl'], row['extracted_bl']) / max(len(row['slip_bl']), len(row['extracted_bl'])))
        
        # 금액 비교 (USD 환산 후)
        slip_amount_usd = self._to_usd(row['slip_amount'], row['slip_currency'])
        extracted_amount_usd = self._to_usd(row['extracted_amount'], row['extracted_currency'])
        amount_diff = abs(slip_amount_usd - extracted_amount_usd)
        amount_diff_pct = (amount_diff / slip_amount_usd) * 100
        
        amount_match = (amount_diff == 0)
        
        # 날짜 비교
        date_diff_days = abs((row['slip_date'] - row['extracted_date']).days)
        date_match = (date_diff_days == 0)
        
        # 종합 판정
        if bl_match and amount_match and date_match:
            match_status = 'perfect_match'
        elif bl_similarity > 0.9 and amount_diff_pct < 1.0 and date_diff_days <= 3:
            match_status = 'partial_match'
        else:
            match_status = 'mismatch'
        
        return {
            'slip_id': row['slip_id'],
            'match_status': match_status,
            'bl_match': bl_match,
            'amount_match': amount_match,
            'amount_diff': amount_diff,
            'amount_diff_pct': amount_diff_pct,
            'date_match': date_match,
            'date_diff_days': date_diff_days
        }
```

### 구현 후 기록
- **사용 라이브러리**:
- **성능**:
- **발견된 이슈**:
- **다음 단계 TODO**:

---

# Frontend: e-Book UI

## 현재 상태
- [ ] 완료
- [ ] 진행중
- [x] 미착수

## 목적
감사자가 대사 결과를 직관적으로 검증할 수 있는 UI 제공

## 화면 구성

### 1. 임포트 시트
- 전표 리스트 테이블 (AG-Grid)
- 5단계 처리 파이프라인 진행 상황 표시
- Excel 업로드, 대사 실행 버튼

### 2. 대사결과 시트 (e-Book 스타일)
**좌측 패널**: 전표 리스트
- 전표 번호, 금액, 일치 상태 표시
- 필터: 완전일치 / 중간일치 / 불일치

**우측 패널**: 원본 PDF + 하이라이트
- PDF 뷰어 (PDF.js)
- 추출 필드 Bounding Box 하이라이트 (노란색)
- 필드별 신뢰도 표시

**중앙 패널**: 비교 테이블
```
┌─────────────────────────────────┐
│ 항목       │ 전표    │ 증빙    │
├─────────────────────────────────┤
│ BL Number  │ HDM001  │ HDM001  │ ✅
│ 금액       │ $125K   │ $125K   │ ✅
│ 날짜       │ 11/05   │ 11/03   │ ⚠️
└─────────────────────────────────┘

AI 재분석: [실행]
최종 결론: [일치 ✅] [불일치 ❌] [보류 ⏸️]
메모: [환율 차이로 인한 오차, 문제없음]
```

### 3. 대시보드
- 프로젝트별 진행 현황
- 통계 차트 (일치율, 처리 시간 등)

## Tech Spec

### 구현 방향 (초안)
```jsx
// frontend/src/components/ReconciliationSheet.jsx

import React, { useState, useEffect } from 'react';
import { Document, Page } from 'react-pdf';
import { AgGridReact } from 'ag-grid-react';

const ReconciliationSheet = ({ projectId }) => {
  const [slips, setSlips] = useState([]);
  const [selectedSlip, setSelectedSlip] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [highlights, setHighlights] = useState([]);

  useEffect(() => {
    // API: 대사 결과 불러오기
    fetch(`/api/reconciliation/results?project_id=${projectId}`)
      .then(res => res.json())
      .then(data => setSlips(data));
  }, [projectId]);

  const handleRowClick = (slip) => {
    setSelectedSlip(slip);
    
    // API: PDF URL 및 하이라이트 JSON 불러오기
    fetch(`/api/documents/${slip.slip_id}/pdf`)
      .then(res => res.json())
      .then(data => {
        setPdfUrl(data.pdf_url);
        setHighlights(data.highlights);
      });
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      {/* 좌측 패널: 전표 리스트 */}
      <div style={{ width: '30%', borderRight: '1px solid #ddd' }}>
        <AgGridReact
          rowData={slips}
          onRowClicked={(e) => handleRowClick(e.data)}
          columnDefs={[
            { field: 'slip_id', headerName: '전표번호' },
            { field: 'slip_amount', headerName: '금액' },
            { field: 'match_status', headerName: '상태', cellRenderer: (params) => {
              const statusIcons = {
                'perfect_match': '✅',
                'partial_match': '⚠️',
                'mismatch': '❌'
              };
              return statusIcons[params.value];
            }}
          ]}
        />
      </div>

      {/* 우측 패널: PDF 뷰어 + 하이라이트 */}
      <div style={{ width: '70%', position: 'relative' }}>
        {pdfUrl && (
          <>
            <Document file={pdfUrl}>
              <Page pageNumber={1} />
            </Document>
            
            {/* Bounding Box 하이라이트 */}
            {highlights.map((bbox, idx) => (
              <div
                key={idx}
                style={{
                  position: 'absolute',
                  left: bbox.x,
                  top: bbox.y,
                  width: bbox.w,
                  height: bbox.h,
                  border: '2px solid yellow',
                  backgroundColor: 'rgba(255, 255, 0, 0.2)'
                }}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
};

export default ReconciliationSheet;
```

### 구현 후 기록
- **사용 라이브러리**:
- **성능**:
- **발견된 이슈**:
- **다음 단계 TODO**:

---

# 배포 및 운영

## 배포 전략
1. **Phase 1: MVP (반자동)**
   - Python 스크립트 + Excel 출력
   - 로컬 실행
   
2. **Phase 2: UI 추가**
   - Streamlit 또는 간단한 Flask UI
   
3. **Phase 3: Full Stack**
   - React + Flask + BigQuery
   - Cloud Run 배포

## 모니터링
- Cloud Logging으로 API 로그 수집
- BigQuery로 성능 지표 분석 (처리 시간, 정확도)

## 보안
- IAM 역할 기반 접근 제어
- GCS 버킷 암호화
- API 키 관리 (Secret Manager)

---

# 부록

## A. 실전 개발 팁

### 🎯 Claude Code 활용 전략

**각 Stage 개발 시 이렇게 요청하세요:**
```
"IDARS_Complete_Spec.md의 Stage 2 섹션을 읽고,
Splitter API를 호출하는 Python 코드를 구현해줘.
- 입력: GCS PDF 경로
- 출력: 분류된 문서 리스트 (JSON)
- 에러 처리: API 타임아웃, 신뢰도 낮은 문서
- 샘플 파일: /samples/증빙_94456924.pdf

구현 완료 후 Stage 2의 '구현 후 기록' 섹션도 업데이트해줘."
```

### 📝 문서 업데이트 주기
- **매 Stage 완료 후**: "구현 후 기록" 섹션 업데이트
- **버그 발견 시**: 해당 Stage의 "발견된 이슈" 추가
- **성능 개선 시**: "다음 단계 TODO"에 아이디어 기록

### 🔧 디버깅 체크리스트
```python
# 파이프라인이 멈췄을 때 확인할 것들:
1. BigQuery `Project_Checkpoints` 테이블 → 마지막 체크포인트 확인
2. Cloud Logging → 에러 로그 검색
3. GCS 버킷 → 파일 업로드 확인
4. Document AI → API 호출 성공 여부
```

---

## B. FAQ (자주 묻는 질문)

### Q1: 파이프라인 중간에 에러가 나면?
**A**: 걱정 마세요! 
- 체크포인트가 자동 저장되어 있습니다
- `engine.resume()` 호출하면 마지막 지점부터 재개됩니다
- 예: Stage 3에서 350/482번째 문서 처리 중 에러 → 351번째부터 재개

### Q2: 100개 전표를 처리하다 퇴근해야 하면?
**A**: 언제든 중단 가능합니다
```python
# UI에서 "일시정지" 버튼 클릭 또는
engine.pause()  # 현재 문서 처리 완료 후 중단

# 다음날
engine.resume()  # 이어서 계속
```

### Q3: Splitter/Extractor 정확도가 낮으면?
**A**: 단계별 개선 방법
1. **라벨링 데이터 추가** (현재 300개 → 500개)
2. **재학습** (Vertex AI Console에서 클릭)
3. **신뢰도 임계값 조정** (0.8 → 0.9로 상향)
4. **수동 검토 건 피드백** → 재학습 데이터로 활용

### Q4: 여러 프로젝트를 동시에 실행 가능한가?
**A**: 가능하지만 권장하지 않습니다
- Document AI API에 Rate Limit 있음 (분당 100 requests)
- 동시 실행 시 속도 저하
- 순차 실행 권장: 프로젝트 A 완료 → 프로젝트 B 시작

### Q5: 기존 프로젝트를 복사하려면?
**A**: 프로젝트 복사 기능 사용
```python
engine.copy_project(
    source="2025-10-W4",
    target="2025-11-W1"
)
# 설정은 복사, 데이터는 새로 시작
```

### Q6: 결과를 Excel이 아닌 Power BI로 보고 싶으면?
**A**: BigQuery 직접 연결
```sql
-- Power BI에서 이 쿼리 실행
SELECT * FROM `idars.Reconciliation_Results`
WHERE project_id = '2025-11-W1'
```

---

## C. 용어 정리
- **BL (Bill of Lading)**: 선하증권
- **Commercial Invoice**: 상업송장
- **Packing List**: 포장명세서
- **Reconciliation**: 대사 (장부와 증빙 비교)

## B. 참고 자료
- Vertex AI Document AI 문서: https://cloud.google.com/document-ai/docs
- BigQuery SQL 레퍼런스: https://cloud.google.com/bigquery/docs/reference/standard-sql

## E. 변경 이력
| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2025-11-16 | 1.0 | 초안 작성 | CJ |
| 2025-11-16 | 1.1 | 프로젝트 관리, 워크플로우 자동화, 실전 팁 추가 | CJ + Claude |

---

## 📌 다음 할 일

### 즉시 착수 (이번 주)
- [ ] Stage 1 Parser 구현 완료
- [ ] 체크포인트 매니저 구현
- [ ] 간단한 오케스트레이터 (run_pipeline.py) 작성

### 단기 (1-2주)
- [ ] Stage 3 Extractor 라벨링 완료 → 학습
- [ ] Stage 4 Normalizer 구현
- [ ] Stage 5 Reconciler 구현

### 중기 (1개월)
- [ ] 간단한 UI (Streamlit) 추가
- [ ] 실제 전표로 파일럿 테스트

### 장기 (3개월)
- [ ] React e-Book UI 개발
- [ ] Cloud Composer 마이그레이션
- [ ] Production 배포

