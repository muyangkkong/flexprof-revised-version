import pandas as pd
import numpy as np
import os
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

import glob  # 파일 패턴 매칭을 위해 상단에 추가해 주세요

def load_and_clean_dataset():
    all_X = []
    all_y = []
    
    file_pattern = "metrics_by_*.xlsx"
    file_list = glob.glob(file_pattern)
    if len(file_list) == 0:
        file_list = glob.glob("metrics_by_*.XLSX")
        
    print(f"   [디버그] 발견된 Excel 파일 개수: {len(file_list)}개")
    if len(file_list) == 0:
        raise ValueError("현재 폴더에 'metrics_by_...' 형식의 .xlsx 파일이 존재하지 않습니다.")
        
    for file_name in file_list:
        if "~$" in file_name or "benchmark" in file_name:
            continue
            
        try:
            print(f"   [읽는 중] {file_name}의 시트들을 추출하고 있습니다...")
            excel_sheets = pd.read_excel(file_name, sheet_name=None)
            
            for sheet_name, df in excel_sheets.items():
                if "All" in sheet_name:
                    continue
                
                # --------------------------------------------------------
                # [핵심 수정] 대소문자 불일치 및 앞뒤 공백(띄어쓰기) 전면 해결
                # 모든 컬럼 이름을 대문자로 바꾸고, 앞뒤 공백을 싹 지워버립니다.
                # --------------------------------------------------------
                df.columns = [str(col).strip().upper() for col in df.columns]
                
                # 시뮬레이션 실패 행 제거 (여기서도 대문자 기준인 'TOTAL_SIMULATION_CYCLES'로 체크)
                if 'TOTAL_SIMULATION_CYCLES' in df.columns:
                    df = df.dropna(subset=['TOTAL_SIMULATION_CYCLES'])
                else:
                    continue
                    
                if df.empty:
                    continue
                    
                # --------------------------------------------------------
                # 1. 타겟 정답 레이블(y) 분리 (대문자 기준 매칭)
                # --------------------------------------------------------
                target_col = 'RD_REQUEST_RATIO' if 'RD_REQUEST_RATIO' in df.columns else 'RD_REQUEST_RATIO'
                # 만약 컬럼이 없으면 에러를 내지 않고 안전하게 넘어가기 위한 방어코드
                if target_col not in df.columns:
                    print(f"      -> [스킵] {sheet_name}에 RD_REQUEST_RATIO 컬럼이 없습니다.")
                    continue
                y = df[target_col]
                
                # --------------------------------------------------------
                # 2. 불필요한 컬럼 및 사후 치트키 컬럼 전면 제거 (전부 대문자로 변경)
                # --------------------------------------------------------
                invalid_cols = [
                    'BENCHMARK', 'REMAINING', 'RD_REQUEST_RATIO', 'WR_REQUEST_RATIO',
                    'TOTAL_READS_SERVICED', 'TOTAL_WRITES_SERVICED', 
                    'NUM_READS_MERGED', 'NUM_WRITES_MERGED', 'MERGED_REQUEST_COUNT'
                ]
                X = df.drop(columns=[col for col in invalid_cols if col in df.columns])
                
                # --------------------------------------------------------
                # 3. 파생 변수 생성 (컬럼이 존재할 때만 안전하게 계산하도록 변경)
                # --------------------------------------------------------
                if 'TOTAL_SIMULATION_CYCLES' in df.columns and 'TOTAL_READS_SERVICED' in df.columns and 'TOTAL_WRITES_SERVICED' in df.columns:
                    X['CYCLES_PER_REQUEST'] = df['TOTAL_SIMULATION_CYCLES'] / (df['TOTAL_READS_SERVICED'] + df['TOTAL_WRITES_SERVICED'] + 1e-5)
                else:
                    X['CYCLES_PER_REQUEST'] = 0
                    
                if 'QUEUE_LATENCY' in df.columns and 'MLP' in df.columns:
                    X['READ_WRITE_LATENCY_RATIO'] = df['QUEUE_LATENCY'] / (df['MLP'] + 1e-5)
                else:
                    X['READ_WRITE_LATENCY_RATIO'] = 0
                
                # 뱅크 분산 값 로그 변환
                if 'BANK_ACCESS_VARIANCE' in X.columns:
                    X['BANK_ACCESS_VARIANCE'] = np.log1p(X['BANK_ACCESS_VARIANCE'])
                    
                all_X.append(X)
                all_y.append(y)
                
        except Exception as e:
            print(f"   [오류] {file_name} 파일 처리 중 문제 발생: {e}")
            
    if len(all_X) == 0:
        raise ValueError("유효한 데이터가 포함된 시트가 존재하지 않아 학습을 진행할 수 없습니다.")
        
    final_X = pd.concat(all_X, ignore_index=True)
    final_y = pd.concat(all_y, ignore_index=True)
    
    return final_X, final_y
# ========================================================
# 1. 데이터 로드 및 정제 수행
# ========================================================
print(">> 데이터를 불러오고 정제하는 중...")
X, y = load_and_clean_dataset()
print(f">> 총 학습 샘플 수: {X.shape[0]}개, 추출된 피처 개수: {X.shape[1]}개")
# --------------------------------------------------------
# [여기에 추가] 내 눈으로 볼 수 있게 통합 정제 파일 저장하기!
# --------------------------------------------------------
# 정답지(y)인 RD_request_ratio를 피처들과 합쳐서 하나의 완성된 표로 만듭니다.
clean_dataset = X.copy()
clean_dataset['TARGET_RD_request_ratio'] = y

# 현재 폴더에 'cleaned_total_dataset.csv' 라는 이름으로 파일을 저장합니다.
clean_dataset.to_csv("cleaned_total_dataset.csv", index=False, encoding='utf-8-sig')
print(">> 🎉 축하합니다! 정제 및 통합이 완료된 'cleaned_total_dataset.csv' 파일이 폴더에 생성되었습니다!")
# --------------------------------------------------------
# ========================================================
# 2. 데이터 정규화 (스케일링)
# ========================================================
# 미세한 수치 차이를 모델이 잘 인지할 수 있도록 표준 정규화(평균 0, 분산 1) 적용
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ========================================================
# 3. XGBoost 모델 생성 및 교차 검증 (K-Fold CV)
# ========================================================
print(">> 교차 검증 및 XGBoost 모델 훈련 시작...")
kf = KFold(n_splits=5, shuffle=True, random_state=42)
mse_scores = []

for fold, (train_idx, val_idx) in enumerate(kf.split(X_scaled)):
    X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    # 데이터 차이가 미세하고 샘플이 적으므로 과적합을 막기 위해 얕은 트리 깊이(max_depth=3) 설정
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # 검증 데이터 예측 및 평가
    preds = model.predict(X_val)
    mse = np.mean((y_val - preds) ** 2)
    mse_scores.append(mse)
    print(f"   - Fold {fold+1} 완료 | Validation MSE: {mse:.6f}")

print(f"\n>> 훈련 완료! 평균 MSE 오차: {np.mean(mse_scores):.6f}")
print(">> 이제 이 model과 scaler를 사용해 새로운 벤치마크의 수치(X)를 넣으면 R/W 비율(y)을 예측할 수 있습니다.")
# ========================================================
# 4. 여기에 코드를 그대로 붙여넣으시면 됩니다!
# ========================================================
import matplotlib.pyplot as plt

# 마지막으로 학습이 완료된 5번째 Fold의 모델을 기준으로 중요도를 뽑습니다.
importances = model.feature_importances_
print("\n🔥 [피처 중요도 분석 결과] 🔥")
print("-" * 50)
for col, imp in zip(X.columns, importances):
    print(f"피처: {col:<25} | 중요도: {imp:.4f}")
print("-" * 50)