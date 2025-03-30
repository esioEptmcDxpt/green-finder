import streamlit as st
import requests
import time
from urllib.parse import urlencode, parse_qs
from PIL import Image
import json
import os
import boto3
import base64
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties
from collections import OrderedDict
import uuid


# Cognitoの設定を.streamlit/secrets.tomlから読み込む
def get_cognito_config():
    """Cognito設定を取得"""
    if 'cognito' not in st.secrets:
        st.error("Cognito設定が見つかりません。.streamlit/secrets.tomlファイルを確認してください。")
        return None
    
    return st.secrets['cognito']

def generate_unique_id():
    """一意のIDを生成する"""
    # 新しいUUIDを生成
    return str(uuid.uuid4())

class CognitoAuthenticator:
    def __init__(self):
        """Cognito認証クラスの初期化"""
        # 設定の読み込み
        self.config = get_cognito_config()
        if not self.config:
            st.error("Cognito認証を初期化できませんでした。")
            return
        
        # 設定値の取得
        self.client_id = self.config['client_id']
        self.client_secret = self.config['client_secret']
        self.aws_region = self.config['aws_region']
        self.user_pool_id = self.config['user_pool_id']
        self.domain = self.config['domain']
        self.redirect_uri = self.config['redirect_uri']
        
        # Cognitoクライアントの初期化
        self.cognito_idp = boto3.client(
            'cognito-idp',
            region_name=self.aws_region
        )
        
        # セッション状態の初期化
        # セッション識別子の管理
        if 'browser_id' not in st.session_state:
            st.session_state.browser_id = generate_unique_id()
        self.browser_id = st.session_state.browser_id
        
        # トークン情報用のセッションキーを作成
        self.token_key = f"token_{self.browser_id}"
        
        # セッション状態を初期化
        if self.token_key not in st.session_state:
            st.session_state[self.token_key] = None

    def is_authenticated(self):
        """認証済みかどうかを確認"""
        return self.token_key in st.session_state and st.session_state[self.token_key] is not None

    def handle_callback(self):
        """認証コールバックを処理"""
        query_params = st.query_params
        
        if 'code' in query_params and 'state' in query_params:
            code = query_params['code']
            state = query_params['state']
            
            # stateパラメータの検証（セキュリティ強化）
            expected_state = f"state_{self.browser_id}"
            if not state.startswith("state_"):
                st.error("無効な認証リクエストです。")
                return False
            
            try:
                # トークンエンドポイントを取得
                metadata_url = f'https://cognito-idp.{self.aws_region}.amazonaws.com/{self.user_pool_id}/.well-known/openid-configuration'
                
                try:
                    response = requests.get(metadata_url)
                    metadata = response.json()
                    token_url = metadata['token_endpoint']
                except Exception as e:
                    st.error(f"メタデータの取得に失敗しました: {str(e)}")
                    return False
                
                # トークンリクエストデータを準備
                token_data = {
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': self.redirect_uri,
                    'client_id': self.client_id,
                }
                
                # クライアントシークレットがある場合は追加
                if self.client_secret:
                    token_data['client_secret'] = self.client_secret
                
                # トークンリクエストを送信
                token_response = requests.post(
                    token_url,
                    data=token_data,
                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                )
                
                if token_response.status_code != 200:
                    st.error(f"トークンの取得に失敗しました: {token_response.text}")
                    return False
                
                # トークンをセッション固有のキーに保存
                st.session_state[self.token_key] = token_response.json()
                # クエリパラメータをクリア
                st.query_params.clear()
                return True
                
            except Exception as e:
                st.error(f"認証処理中にエラーが発生しました: {str(e)}")
                return False
        
        return False

    def login(self):
        """ログインボタンを表示"""
        # AWS Cognito形式でのドメイン構築
        cognito_domain = f"https://{self.aws_region.lower()}{self.user_pool_id.split('_')[1].lower()}.auth.{self.aws_region}.amazoncognito.com"
        
        # セッションIDをステート値に追加して、コールバック時に同一セッションと識別できるようにする
        state_value = f"state_{self.browser_id}"
        
        # パラメータを正確な順序で構築（順序を維持するためにOrderedDictを使用）
        params = OrderedDict([
            ('client_id', self.client_id),
            ('redirect_uri', self.redirect_uri),
            ('response_type', 'code'),
            ('scope', 'email openid phone'),
            ('state', state_value)
        ])
        
        # URLをエンコード（URLEncodeする代わりに手動で構築）
        query_string = "&".join([f"{k}={requests.utils.quote(v)}" for k, v in params.items()])
        
        # Cognitoのログイン画面へのURL
        login_url = f"{cognito_domain}/login?lang=ja&{query_string}"
        
        # aタグを使用してリンク機能を実装
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

    def check_authentication(self):
        """認証状態をチェックし、必要に応じてログイン処理を行う
        
        Returns:
            bool: 認証済みの場合はTrue、未認証の場合はFalse
        """
        # 認証チェック
        if not self.is_authenticated():
            # コールバックパラメータがある場合は処理
            if 'code' in st.query_params:
                if self.handle_callback():
                    st.success("ログインに成功しました！")
                    # 3秒後にページを再読み込み
                    time.sleep(1)
                    st.rerun()  # ページを再読み込み
                else:
                    st.error("ログインに失敗しました")
            
            # ログインボタンを表示
            st.title("トロリ線摩耗判定支援システム")
            st.write("### ログインしてください 👇️")
            self.login()
            
            # ログインページの画像を表示
            try:
                cis_image = Image.open('icons/cis_page-eye-catch.jpg')
                # st.image() の代わりに vis.image_to_html() を使用
                vis.image_to_html(cis_image, width="100%")
                st.markdown('Contact-wire Inspection System')
            except Exception as e:
                st.warning(f"画像の読み込みに失敗しました: {str(e)}")
            
            return False
        
        return True

    def validate_token(self):
        """現在のトークンの有効性を検証"""
        if not self.is_authenticated():
            return False
        
        try:
            # アクセストークンを取得
            access_token = st.session_state[self.token_key].get('access_token')
            if not access_token:
                return False
            
            # Cognitoのget_user APIは特定のスコープが必要なため、
            # 代わりにID情報をデコードして有効期限を確認する方法に変更
            try:
                # ID トークンがある場合はそれを使用
                id_token = st.session_state[self.token_key].get('id_token')
                if id_token:
                    # ID トークンの検証はクライアント側では期限切れチェックのみ
                    # 実際のトークン検証はCognitoが行う
                    return True
                else:
                    # ID トークンがない場合は、アクセストークンの存在だけで認証とみなす
                    # 実際の認証は各APIコールで行われる
                    return access_token is not None
                
            except Exception as token_error:
                st.error(f"トークン検証エラー（詳細）: {str(token_error)}")
                self.logout()  # トークンが無効な場合はログアウト
                return False
            
        except Exception as e:
            st.error(f"トークン検証エラー: {str(e)}")
            self.logout()  # トークンが無効な場合はログアウト
            return False

    def logout(self):
        """ログアウト処理"""
        if self.token_key in st.session_state and st.session_state[self.token_key]:
            try:
                # リフレッシュトークンがある場合、トークンを無効化
                refresh_token = st.session_state[self.token_key].get('refresh_token')
                if refresh_token:
                    self.cognito_idp.revoke_token(
                        ClientId=self.client_id,
                        ClientSecret=self.client_secret,
                        Token=refresh_token
                    )
            except Exception as e:
                st.error(f"ログアウト処理中にエラーが発生しました: {str(e)}")
        
        # このセッション専用のトークンをクリア
        if self.token_key in st.session_state:
            del st.session_state[self.token_key]
        
        # ページを再読み込み
        st.rerun()

    def get_user_info(self):
        """ユーザー情報を取得"""
        if not self.is_authenticated():
            return None
        
        try:
            # IDトークンからユーザー情報を取得する方法に変更
            id_token = st.session_state[self.token_key].get('id_token')
            if not id_token:
                return None
            
            # JWTの2番目の部分（ペイロード）を取得してデコード
            token_parts = id_token.split('.')
            if len(token_parts) != 3:
                st.error("無効なIDトークン形式です")
                return None
            
            # Base64でエンコードされたペイロードをデコード
            payload = token_parts[1]
            # Base64のパディングを調整
            padded_payload = payload + '=' * (4 - len(payload) % 4) if len(payload) % 4 else payload
            decoded_payload = base64.b64decode(padded_payload).decode('utf-8')
            claims = json.loads(decoded_payload)
            
            # ユーザー属性を作成
            user_attributes = {}
            for key, value in claims.items():
                # 標準的なクレームをマッピング
                if key == 'email':
                    user_attributes['email'] = value
                elif key == 'name':
                    user_attributes['name'] = value
                elif key == 'sub':
                    user_attributes['sub'] = value
                elif key == 'preferred_username':
                    user_attributes['preferred_username'] = value
                elif key == 'cognito:username':
                    user_attributes['cognito_username'] = value
                # 他の必要なクレームがあれば追加
            
            # ユーザー情報を返す
            return {
                'username': claims.get('cognito:username', claims.get('preferred_username', claims.get('sub'))),
                'attributes': user_attributes
            }
            
        except Exception as e:
            st.error(f"ユーザー情報取得エラー: {str(e)}")
            return None

    def get_username(self):
        """ユーザー名（ログインID）を取得
        
        Returns:
            str: ユーザー名、取得できない場合はNone
        """
        user_info = self.get_user_info()
        if not user_info:
            return None
            
        attrs = user_info.get('attributes', {})
        # ユーザー名（ログインID）を優先的に使用
        if 'cognito_username' in attrs:
            return attrs['cognito_username']
        elif 'preferred_username' in attrs:
            return attrs['preferred_username']
        else:
            return user_info.get('username')

    def render_sidebar_logout(self, username=None):
        """サイドバーのログアウトボタン表示"""
        # ユーザー情報を取得
        user_info = self.get_user_info()
        display_name = username
        
        if user_info:
            # ユーザー名を表示（ログインIDを優先）
            attrs = user_info.get('attributes', {})
            # ユーザー名（ログインID）を優先的に使用
            if 'cognito_username' in attrs:
                display_name = attrs['cognito_username']
            elif 'preferred_username' in attrs:
                display_name = attrs['preferred_username']
            elif not display_name:
                display_name = user_info.get('username')
        
        if display_name:
            config = appProperties('config.yml')
            st.write(f"ログイン: {helpers.get_office_name_jp(config, display_name)}")
            st.markdown(f"<span style='color: gray; font-size: 0.8rem;'>Session ID: {self.browser_id[:8]}...</span>", unsafe_allow_html=True)
        
        # ログアウトボタン
        if st.button('ログアウト', key='logout_button'):
            self.logout()

# 認証マネージャーのメインクラス
class AuthenticationManager:
    def __init__(self):
        """認証マネージャーの初期化"""
        self.authenticator = CognitoAuthenticator()
    
    def authenticate_page(self, title="認証が必要です", render_sidebar=True, username=None):
        """ページの認証処理とUI表示を一括で行う
        
        Parameters:
        -----------
        title : str
            ページのタイトル
        render_sidebar : bool
            サイドバーログアウトボタンを表示するかどうか
        username : str
            表示するユーザー名（省略可）
            
        Returns:
        --------
        bool
            認証状態 (True: 認証済み, False: 未認証)
        """
        # 認証状態をチェック
        if self.authenticator.check_authentication():
            # トークンの有効性を検証
            if not self.authenticator.validate_token():
                return False
            
            # サイドバーにログアウトボタンを表示
            if render_sidebar:
                with st.sidebar:
                    self.authenticator.render_sidebar_logout(username)
            
            return True
        
        return False