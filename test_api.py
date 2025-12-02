"""
Step 3 통합 API 테스트 스크립트
"""
import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_extract_and_compare():
    """추출 및 비교 통합 API 테스트"""
    print("\n" + "="*80)
    print("테스트 1: 추출 및 비교 통합 API")
    print("="*80)
    
    # 프로젝트 목록 확인
    response = requests.get(f"{BASE_URL}/api/projects")
    projects = response.json()
    
    if not projects:
        print("❌ 프로젝트가 없습니다.")
        return
    
    project = projects[0]
    project_id = project['id']
    print(f"✓ 테스트 프로젝트: {project_id} - {project['name']}")
    
    # Step 1 데이터 확인
    project_path = f"Data/projects/{project_id}"
    step1_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
    
    if not os.path.exists(step1_path):
        print(f"❌ Step 1 확정 데이터가 없습니다: {step1_path}")
        return
    
    # CSV에서 전표번호 읽기
    import pandas as pd
    df = pd.read_csv(step1_path)
    
    billing_col = 'Billing Document'
    if billing_col not in df.columns:
        for col in df.columns:
            if 'billing' in col.lower() or '전표' in col:
                billing_col = col
                break
    
    selected_ids = df[billing_col].head(3).astype(str).tolist()
    print(f"✓ 선택된 전표번호: {selected_ids}")
    
    # API 호출
    payload = {
        "selectedIds": selected_ids,
        "projectsDir": "Data/projects"
    }
    
    print(f"\n📡 API 호출: POST /api/projects/{project_id}/step3/extract-and-compare")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/step3/extract-and-compare",
            json=payload,
            timeout=300  # 5분 타임아웃
        )
        
        print(f"\n✓ 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n📊 응답 결과:")
            print(f"   - 추출 성공: {result['extraction_results']['extracted']}/{result['extraction_results']['total_documents']} 건")
            print(f"   - 비교 결과: {len(result['comparison_results'])} 건")
            
            # API 사용량
            api_usage = result['api_usage']
            print(f"\n💰 API 사용량:")
            print(f"   - Input 토큰: {api_usage['total_input_tokens']:,}")
            print(f"   - Output 토큰: {api_usage['total_output_tokens']:,}")
            
            # 상태 요약
            summary = result['summary']
            print(f"\n📈 비교 상태 요약:")
            print(f"   - ✅ 완전일치: {summary['complete_match']} 건")
            print(f"   - ⚠️ 일부오류: {summary['partial_error']} 건")
            print(f"   - ❌ 재검토필요: {summary['review_required']} 건")
            
            # 첫 번째 결과 상세 출력
            if result['comparison_results']:
                first = result['comparison_results'][0]
                print(f"\n🔍 첫 번째 결과 상세 ({first['billing_document']}):")
                print(f"   - 전체 상태: {first['auto_comparison']['status']}")
                print(f"   - 불일치 수: {first['auto_comparison']['mismatch_count']}")
                
                print("\n   필드별 비교:")
                for field_name, field_result in first['auto_comparison']['field_results'].items():
                    match_icon = "✅" if field_result['match'] else "❌"
                    confidence = field_result.get('confidence')
                    conf_str = f" (신뢰도: {confidence:.2f})" if confidence else ""
                    print(f"      {match_icon} {field_name}: {field_result['step1_value']} vs {field_result['step3_value']}{conf_str}")
            
            print("\n✅ 테스트 성공!")
            return True
        else:
            print(f"\n❌ API 오류: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ 타임아웃: API 응답이 5분 내에 완료되지 않았습니다.")
        return False
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_update_field():
    """수기 수정 API 테스트"""
    print("\n" + "="*80)
    print("테스트 2: 수기 수정 API")
    print("="*80)
    
    # 프로젝트 확인
    response = requests.get(f"{BASE_URL}/api/projects")
    projects = response.json()
    
    if not projects:
        print("❌ 프로젝트가 없습니다.")
        return
    
    project_id = projects[0]['id']
    
    # auto_comparison_results.json 확인
    results_path = f"Data/projects/{project_id}/step3_data_extraction/auto_comparison_results.json"
    if not os.path.exists(results_path):
        print(f"❌ 비교 결과 파일이 없습니다. 먼저 테스트 1을 실행하세요.")
        return
    
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    if not results:
        print("❌ 비교 결과가 비어있습니다.")
        return
    
    # 첫 번째 결과 사용
    first = results[0]
    billing_doc = first['billing_document']
    
    print(f"✓ 테스트 전표: {billing_doc}")
    
    # 수정 데이터
    payload = {
        "billing_document": billing_doc,
        "field": "amount",
        "value": 99999.99,
        "note": "테스트 수정",
        "projectsDir": "Data/projects"
    }
    
    print(f"\n📡 API 호출: POST /api/projects/{project_id}/step3/update-field")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/step3/update-field",
            json=payload
        )
        
        print(f"\n✓ 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ {result['message']}")
            
            # final_comparison_results.json 확인
            final_path = f"Data/projects/{project_id}/step3_data_extraction/final_comparison_results.json"
            if os.path.exists(final_path):
                with open(final_path, 'r', encoding='utf-8') as f:
                    final_results = json.load(f)
                    
                if billing_doc in final_results:
                    correction = final_results[billing_doc].get('user_corrections', {}).get('amount', {})
                    print(f"\n📝 저장된 수정 내용:")
                    print(f"   - 원본 OCR: {correction.get('original_ocr')}")
                    print(f"   - 사용자 값: {correction.get('user_value')}")
                    print(f"   - 수정 이유: {correction.get('note')}")
                    
            print("\n✅ 테스트 성공!")
            return True
        else:
            print(f"\n❌ API 오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_send_to_dashboard():
    """대시보드 전송 API 테스트"""
    print("\n" + "="*80)
    print("테스트 3: 대시보드 전송 API")
    print("="*80)
    
    response = requests.get(f"{BASE_URL}/api/projects")
    projects = response.json()
    
    if not projects:
        print("❌ 프로젝트가 없습니다.")
        return
    
    project_id = projects[0]['id']
    
    payload = {
        "projectsDir": "Data/projects"
    }
    
    print(f"\n📡 API 호출: POST /api/projects/{project_id}/step3/send-to-dashboard")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/step3/send-to-dashboard",
            json=payload
        )
        
        print(f"\n✓ 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ {result['message']}")
            
            # dashboard_data.json 확인
            dashboard_path = f"Data/projects/{project_id}/dashboard_data.json"
            if os.path.exists(dashboard_path):
                with open(dashboard_path, 'r', encoding='utf-8') as f:
                    dashboard_data = json.load(f)
                print(f"\n📊 대시보드 데이터 저장 확인:")
                print(f"   - 확정 시간: {dashboard_data.get('confirmed_at')}")
                print(f"   - 결과 수: {len(dashboard_data.get('results', []))} 건")
                
            print("\n✅ 테스트 성공!")
            return True
        else:
            print(f"\n❌ API 오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🚀 Step 3 통합 API 테스트 시작\n")
    
    # 서버 연결 확인
    try:
        response = requests.get(f"{BASE_URL}/api/projects", timeout=5)
        print(f"✓ 백엔드 서버 연결 성공 (http://localhost:5000)")
    except:
        print("❌ 백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
        exit(1)
    
    # 테스트 실행
    test1 = test_extract_and_compare()
    
    if test1:
        test2 = test_update_field()
        test3 = test_send_to_dashboard()
        
        print("\n" + "="*80)
        print("📊 테스트 요약")
        print("="*80)
        print(f"테스트 1 (추출 및 비교): {'✅ 성공' if test1 else '❌ 실패'}")
        print(f"테스트 2 (수기 수정): {'✅ 성공' if test2 else '❌ 실패'}")
        print(f"테스트 3 (대시보드 전송): {'✅ 성공' if test3 else '❌ 실패'}")
        print("="*80)
    else:
        print("\n⚠️ 테스트 1이 실패하여 나머지 테스트를 건너뜁니다.")
