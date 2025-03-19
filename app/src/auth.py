import streamlit as st
from urllib.parse import urlencode
import requests
import time
from PIL import Image


def setup_cognito_auth():
    if 'auth_config' not in st.session_state:
        # secretsファイルから認証情報を読み込む
        cognito = st.secrets.cognito
        aws_region = cognito.aws_region
        user_pool_id = cognito.user_pool_id
        
        st.session_state.auth_config = {
            'authority': f'https://cognito-idp.{aws_region}.amazonaws.com/{user_pool_id}',
            'client_id': cognito.client_id,
            'client_secret': cognito.client_secret,
            'metadata_url': f'https://cognito-idp.{aws_region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration',
            'domain': cognito.domain,
            'scope': cognito.scope,
            'redirect_uri': cognito.redirect_uri
        }
    return st.session_state.auth_config


def is_authenticated():
    return 'token' in st.session_state and st.session_state.token is not None


def handle_callback():
    auth_config = setup_cognito_auth()
    query_params = st.query_params
    
    if 'code' in query_params:
        code = query_params['code']
        
        # メタデータからトークンエンドポイントを取得
        try:
            metadata_resp = requests.get(auth_config['metadata_url'])
            if metadata_resp.status_code != 200:
                st.error("認証サービスのメタデータを取得できませんでした")
                return False
            
            metadata = metadata_resp.json()
            token_url = metadata['token_endpoint']
            
            # トークンを取得
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': auth_config['redirect_uri'],
                'client_id': auth_config['client_id'],
                'client_secret': auth_config['client_secret']
            }
            
            token_resp = requests.post(token_url, data=token_data)
            if token_resp.status_code != 200:
                st.error(f"トークンの取得に失敗しました: {token_resp.text}")
                return False
            
            # トークンをセッションに保存
            st.session_state.token = token_resp.json()
            # クエリパラメータをクリア
            st.query_params.clear()
            return True
            
        except Exception as e:
            st.error(f"認証処理中にエラーが発生しました: {str(e)}")
            return False
    
    return False


def login():
    auth_config = setup_cognito_auth()
    
    # Cognitoのホスト名を取得
    cognito_domain = auth_config['domain']
    
    # 認証URLを構築
    params = {
        'client_id': auth_config['client_id'],
        'response_type': 'code',
        'scope': auth_config['scope'],
        'redirect_uri': auth_config['redirect_uri'],
    }
    
    # Cognitoのログイン画面へのURLを生成
    login_url = f"{cognito_domain}/login?{urlencode(params)}"
    
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
    
    # デバッグ情報
    # if st.checkbox("デバッグ情報を表示"):
    #     st.write("ログインURL:", login_url)
    #     st.write("パラメータ:", params)


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


def logout():
    # セッション変数をクリア
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()  # ページを再読み込み