import streamlit as st
import requests
import time
from urllib.parse import urlencode, parse_qs
from PIL import Image
import json
import os

# Lambda認証APIのエンドポイント
API_ENDPOINT = os.getenv('AUTH_API_ENDPOINT', 'https://your-api-gateway-endpoint.execute-api.ap-northeast-1.amazonaws.com/prod')

def is_authenticated():
    """認証済みかどうかを確認"""
    return 'token' in st.session_state and st.session_state.token is not None

def handle_callback():
    """認証コールバックを処理"""
    query_params = st.query_params
    
    if 'code' in query_params:
        code = query_params['code']
        
        try:
            # Lambda関数を通じてトークンを取得
            token_response = requests.post(
                f"{API_ENDPOINT}/auth/token",
                json={'code': code},
                headers={'Content-Type': 'application/json'}
            )
            
            if token_response.status_code != 200:
                st.error(f"トークンの取得に失敗しました: {token_response.text}")
                return False
            
            # トークンをセッションに保存
            st.session_state.token = token_response.json()
            # クエリパラメータをクリア
            st.query_params.clear()
            return True
            
        except Exception as e:
            st.error(f"認証処理中にエラーが発生しました: {str(e)}")
            return False
    
    return False

def login():
    """ログインボタンを表示"""
    # Lambda認証APIを使用してログインURLを生成
    login_url = f"{API_ENDPOINT}/auth/login"
    
    # aタグを使用して確実にリンク機能を実装
    login_button_html = f"""
    <style>
    .login-container {{
        text-align: center;
        margin: 1.5rem 0;
    }}
    .login-btn {{
        display: inline-block;
        background-color: #F5F5F5;
        color: #000000 !important;
        padding: 0.7rem 2rem;
        font-size: 1.5rem;
        font-weight: 600;
        border-radius: 6px;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
        cursor: pointer;
        line-height: 1.3;
        text-decoration: none !important;
    }}
    .login-btn:hover {{
        background-color: #E8E8E8;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transform: translateY(-2px);
        text-decoration: none !important;
    }}
    </style>
    <div class="login-container">
        <a href="{login_url}" target="_self" class="login-btn">ログイン</a>
    </div>
    """
    st.markdown(login_button_html, unsafe_allow_html=True)

def check_authentication():
    """認証状態をチェックし、必要に応じてログイン処理を行う
    
    Returns:
        bool: 認証済みの場合はTrue、未認証の場合はFalse
    """
    # 認証チェック
    if not is_authenticated():
        # コールバックパラメータがある場合は処理
        if 'code' in st.query_params:
            if handle_callback():
                st.success("ログインに成功しました！")
                # 3秒後にページを再読み込み
                time.sleep(3)
                st.rerun()  # ページを再読み込み
            else:
                st.error("ログインに失敗しました")
        
        # ログインボタンを表示
        st.title("トロリ線摩耗判定支援システム")
        st.write("### ログインしてください 👇️")
        login()
        cis_image = Image.open('icons/cis_page-eye-catch.png')
        st.image(cis_image, caption='Contact-wire Inspection System')
        return False
    
    return True

def validate_token():
    """現在のトークンの有効性を検証"""
    if not is_authenticated():
        return False
    
    try:
        # アクセストークンを取得
        access_token = st.session_state.token.get('access_token')
        if not access_token:
            return False
        
        # Lambda関数を通じてトークンを検証
        validate_response = requests.get(
            f"{API_ENDPOINT}/auth/validate",
            headers={
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
        )
        
        if validate_response.status_code != 200:
            # トークンが無効の場合はセッションをクリア
            logout()
            return False
        
        return True
        
    except Exception as e:
        st.error(f"トークン検証エラー: {str(e)}")
        return False

def logout():
    """ログアウト処理"""
    if 'token' in st.session_state and st.session_state.token:
        try:
            # リフレッシュトークンがある場合、Lambda関数を通じてログアウト
            refresh_token = st.session_state.token.get('refresh_token')
            if refresh_token:
                requests.post(
                    f"{API_ENDPOINT}/auth/logout",
                    json={'refresh_token': refresh_token},
                    headers={'Content-Type': 'application/json'}
                )
        except Exception as e:
            st.error(f"ログアウト処理中にエラーが発生しました: {str(e)}")
    
    # セッション変数をクリア
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()  # ページを再読み込み

def get_user_info():
    """ユーザー情報を取得"""
    if not is_authenticated():
        return None
    
    try:
        # アクセストークンを取得
        access_token = st.session_state.token.get('access_token')
        if not access_token:
            return None
        
        # Lambda関数を通じてユーザー情報を取得
        validate_response = requests.get(
            f"{API_ENDPOINT}/auth/validate",
            headers={
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
        )
        
        if validate_response.status_code != 200:
            return None
        
        response_data = validate_response.json()
        return response_data.get('user')
        
    except Exception as e:
        st.error(f"ユーザー情報取得エラー: {str(e)}")
        return None 