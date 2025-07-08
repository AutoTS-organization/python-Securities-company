
import os
import requests
import json
import pandas as pd
from datetime import date

import kis_auth


# 토큰 가져오기
authorization = kis_auth.auth(svr='prod')  # 토큰만 반환한다면 Bearer 붙여야 함

# API URL 정확히 입력
url = 'https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/ranking/market-cap'  # 정확한 path로 교체!

req_header = {
    'content-type': 'application/json; charset=utf-8',
    'authorization': f'Bearer {authorization}',  # Bearer 붙이기
    'appkey': kis_auth.get_app_key(),
    'appsecret': kis_auth.get_app_secret(),
    'tr_id': 'HHDFS76350100',
    'custtype': 'P',
    'mac_address': '58:40:4e:eb:c2:66'
}

req_param = {
    'KEYB': '',
    'AUTH': '',
    'EXCD': 'NYS', 
    'VOL_RANG': '0'
}

# headers는 dict 그대로!
res = requests.post(url, headers=req_header, params=req_param)
print(f'상태 코드: {res.status_code}')

if res.status_code == 200:
    try:
        response_data = res.json()
        # print(json.dumps(response_data, indent=4, ensure_ascii=False))

        if 'output1' in response_data and 'output2' in response_data:
            header_info = response_data['output1'] # 헤더 정보
            detail_data = response_data['output2'] # 상세 데이터
            df = pd.DataFrame(detail_data)

            # csv 파일로 저장
            today = date.today().strftime("%Y-%m-%d")
            file_name = today + '_US_ranking.csv'

            directory_path = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(directory_path, 'data', 'overseas_ranking', file_name)
            
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print('csv로 저장 완료')
        

    except json.JSONDecodeError:
        print("오류: 응답이 유효한 JSON 형식이 아닙니다.")
        print("응답 본문:", res.text) # JSON이 아닌 경우 원본 텍스트 출력
    except Exception as e:
        print(f'오류 발생: {e}')