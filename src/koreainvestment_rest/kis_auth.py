'''
한국투자증권 API 사용을 위한 인증 (OAuth) 모듈
인증 토큰이 없으면 새로 생성
인증 토큰이 있을 때 
    유효기간이 만료되었으면 재발급
    유효한 토큰이면 토큰 반환

auth() 함수만 사용하면 다 알아서 해줌
'''

import os
import sys
import copy
import yaml
import requests
import json
from collections import namedtuple
from datetime import datetime

_isPaper = False ### 이 부분에서 모의인지 실전인지 정하기
_TRENV = tuple()

# 토큰 저장 위치에 도달
config_root = os.path.dirname(os.path.abspath(__file__))
token_tmp = os.path.join(config_root, 'KIS', 'KItoken.yaml')

if _isPaper == True:
    token_tmp = os.path.join(config_root, 'KIS', 'KItoken_paper.yaml')

# token 경로가 존재하지 않는다면 새로 생성해서 쓰기
if os.path.exists(token_tmp) == False:
    f = open(token_tmp, "w+")

# kis_devlp.yaml 정보 가져오기 
with open(config_root + '/kis_devlp.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)

# 기본 헤더값 정의
_base_headers = {
    "Content-Type": "application/json",
    "Accept": "text/plain",
    "charset": "UTF-8",
    'User-Agent': _cfg['my_agent']
}

def _setTRENV(cfg, isPaper):
    '''
    _cfg = kis_devlp.yaml 인 상황에서 
    kis_devlp.yaml의 내용을 / _TRENV에 네임드 튜플로 저장

    args:
        cfg: loaded data of kis_devlp.yaml, 즉 항상 _cfg를 입력
        wtf: 모의투자인지 실전투자인지 여부, 즉 항상 _wtf를 입력
    returns:
        nothing but updates _TRENV though
    '''
    nt1 = namedtuple('KISEnv', ['my_app', 'my_sec', 'my_acct', 'my_prod', 'my_url'])

    if not isPaper: # 실전투자인 경우
        d = {
            'my_app': cfg['my_app'],  # 앱키
            'my_sec': cfg['my_sec'],  # 앱시크리트
            'my_acct': cfg['my_acct_stock'],  # 종합계좌번호(8자리)
            'my_prod': cfg['my_prod'],  # 계좌상품코드(2자리)
            'my_url': cfg['prod']  # 실전투자 도메인 
        }  
    else: # 모의투자인 경우
        d = {
            'my_app': cfg['paper_app'],  # 앱키
            'my_sec': cfg['paper_sec'],  # 앱시크리트
            'my_acct': cfg['my_paper_stock'],  # 종합계좌번호(8자리)
            'my_prod': cfg['my_prod'],  # 계좌상품코드(2자리)
            'my_url': cfg['vps']  # 모의투자 도메인 
        }
    global _TRENV
    _TRENV = nt1(**d) # **는 딕셔너리를 키워드 인자 형태로 풀어서 전달한다는 것

# 토큰이 유효한지 확인
def eval_token():
    try:
        with open(token_tmp, encoding='UTF-8') as f:
            tkg_tmp = yaml.load(f, loader=yaml.FullLoader)
        
        # 토큰 만료 일,시간
        exp_dt = datetime.strptime(str(tkg_tmp['valid-date']), '%Y-%m-%d %H:%M:%S')
        # 현재일자,시간
        now_dt = datetime.now()

        print('\n', 'expire dt: ', exp_dt, ' vs now dt:', now_dt, '\n')
        if exp_dt > now_dt:
            return True
        else:
            return False
    except Exception as e:
        print('eval_token error: ', e)
        return None

def read_token():
    try:
        # 토큰이 저장된 파일 읽기
        with open(token_tmp, encoding='UTF-8') as f:
            tkg_tmp = yaml.load(f, Loader=yaml.FullLoader)

        # 토큰 만료 일,시간
        exp_dt = datetime.strptime(str(tkg_tmp['valid-date']), '%Y-%m-%d %H:%M:%S')
        # 현재일자,시간
        now_dt = datetime.now()
        print('token 작업 중')
        print('expire dt: ', exp_dt, ' vs now dt:', now_dt, '\n')
        # 저장된 토큰 만료일자 체크 (만료일시 > 현재일시 인경우 보관 토큰 리턴)
        if exp_dt > now_dt:
            return tkg_tmp['token']
        else:
            print('Need new token: ', tkg_tmp['valid-date'])
            return None
    except Exception as e:
        print('read token error: ', e)
        return None
    
def _getBaseHeader():
    return copy.deepcopy(_base_headers)

def _getResultObject(json_data):
    _tc_ = namedtuple('res', json_data.keys())
    return _tc_(**json_data)

# 토큰 발급 받아 저장 (토큰값, 토큰 유효시간,1일, 6시간 이내 발급신청시는 기존 토큰값과 동일, 발급시 알림톡 발송)
def save_token(my_token, my_expired):
    valid_date = datetime.strptime(my_expired, '%Y-%m-%d %H:%M:%S')
    print('Save token valid_date: ', valid_date)
    with open(token_tmp, 'w', encoding='utf-8') as f:
        f.write(f'token: {my_token}\n')
        f.write(f'valid-date: {valid_date}\n')

def auth(svr='prod', product='01', url=None):
    '''
    OAuth 관련 메인 함수
    Args:
        svr : 
            'prod': 실전 투자
            'vps': 모의투자
        product: 
            '01':  # 실전투자 주식투자, 위탁계좌, 투자계좌
            '03':  # 실전투자 선물옵션(파생)
        url: 실전: "https://openapi.koreainvestment.com:9443"
             모의: "https://openapivts.koreainvestment.com:29443"
    Returns:
        token 값
    '''
    # _TRENV를 모의투자, 실전투자에 따라 다르게 설정하도록 함
    global _isPaper
    global token_tmp

    if svr == 'prod':
        _isPaper = False
        token_tmp = os.path.join(config_root, 'KIS', 'KItoken_paper.yaml')
    elif svr == 'vps':
        _isPaper = True
        
    _setTRENV(_cfg, _isPaper)

    # 요청 body 구성하기
    p = {
        "grant_type": "client_credentials",
    }

    p["appkey"] = _TRENV.my_app
    p["appsecret"] = _TRENV.my_sec

    # 기존에 발급된 토큰이 있는지 확인
    saved_token = read_token()
    
    if saved_token is None:
        url = f'{_TRENV.my_url}/oauth2/tokenP'
        res = requests.post(url, data=json.dumps(p), headers=_getBaseHeader())
        rescode = res.status_code
        print(rescode)
        if rescode == 200:  # 토큰 정상 발급
            my_token = _getResultObject(res.json()).access_token  # 토큰값 가져오기
            my_expired= _getResultObject(res.json()).access_token_token_expired  # 토큰값 만료일시 가져오기
            save_token(my_token, my_expired)  # 새로 발급 받은 토큰 저장
        else:
            print('Get Authentification token fail!\nYou have to restart your app!!!')
            return
    else:
        my_token = saved_token  # 기존 발급 토큰 확인되어 기존 토큰 사용
    
    _base_headers["authorization"] = saved_token
    _base_headers["appkey"] = _TRENV.my_app
    _base_headers["appsecret"] = _TRENV.my_sec

    return my_token
    
def get_app_key():
    return _TRENV.my_app

def get_app_secret():
    return _TRENV.my_sec


if __name__ == '__main__':
    # 접근토큰발급 저장
    print(auth(svr='vps'))
