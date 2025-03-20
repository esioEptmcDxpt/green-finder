import streamlit as st
from streamlit_authenticator.utilities.hasher import Hasher
import streamlit_authenticator as stauth
import csv
import yaml
from yaml.loader import SafeLoader
import os
from src.config import appProperties
import src.helpers as helpers
import requests
import time
from urllib.parse import urlencode, parse_qs
from PIL import Image
import json
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class AuthenticationManager:
    def __init__(self, yaml_path=".streamlit/user_info.yml", api_key=None):
        # YAML ファイルのパス
        self.yaml_path = yaml_path
        
        # API キー設定
        self.api_key = api_key
        
        # 初期化済みフラグのチェック
        if 'authentication_initialized' not in st.session_state:
            st.session_state['authentication_initialized'] = False
        
        # パスワードリセットモードの切り替え
        if 'password_reset_mode' not in st.session_state:
            st.session_state['password_reset_mode'] = False
        
        # リセット成功フラグの初期化
        if 'reset_success' not in st.session_state:
            st.session_state['reset_success'] = False
        
        # パスワード再設定モードの初期化
        if 'password_change_mode' not in st.session_state:
            st.session_state['password_change_mode'] = False
        
        # リセット後のユーザー名保存
        if 'reset_username' not in st.session_state:
            st.session_state['reset_username'] = None
        
        # ユーザー情報の読み込み
        self.load_user_info()
        
        # 認証ハンドラの初期化
        self.initialize_authenticator()
    
    def load_user_info(self):
        """ユーザー情報を YAML ファイルから読み込む"""
        with open(self.yaml_path) as file:
            self.user_info = yaml.load(file, Loader=SafeLoader)
        
        # API キーがYAMLに設定されている場合は取得
        if not self.api_key and 'api_key' in self.user_info:
            self.api_key = self.user_info['api_key']
    
    def save_user_info(self):
        """ユーザー情報を YAML ファイルに保存"""
        with open(self.yaml_path, 'w') as file:
            yaml.dump(self.user_info, file, default_flow_style=False, allow_unicode=True)
    
    def initialize_authenticator(self):
        """認証ハンドラの初期化"""
        if 'authenticator' not in st.session_state:
            auth_config = {
                'credentials': self.user_info['credentials'],
                'cookie_name': self.user_info['cookie']['name'],
                'cookie_key': self.user_info['cookie']['key'],
                'cookie_expiry_days': self.user_info['cookie']['expiry_days']
            }
            
            # API キーが存在する場合は認証設定に追加
            if self.api_key:
                auth_config['api_key'] = self.api_key
            
            st.session_state['authenticator'] = stauth.Authenticate(**auth_config)
        
        self.authenticator = st.session_state['authenticator']
    
    def update_login_status(self):
        """ログイン状態の更新"""
        if st.session_state.get('authentication_status') and st.session_state.get('username'):
            username = st.session_state.get('username')
            if username in self.user_info['credentials']['usernames']:
                # YAML ファイルのログイン状態を更新
                if not self.user_info['credentials']['usernames'][username].get('logged_in'):
                    self.user_info['credentials']['usernames'][username]['logged_in'] = True
                    self.save_user_info()
    
    def update_logout_status(self, username):
        """ログアウト状態の更新"""
        if username and username in self.user_info['credentials']['usernames']:
            self.user_info['credentials']['usernames'][username]['logged_in'] = False
            self.save_user_info()
            return True
        return False
    
    def check_auto_login(self):
        """自動ログイン処理"""
        for username, user_data in self.user_info['credentials']['usernames'].items():
            if user_data.get('logged_in'):
                # 自動認証処理
                st.session_state['authentication_status'] = True
                st.session_state['name'] = user_data['name']
                st.session_state['username'] = username
                return True
        return False
    
    def render_login_ui(self):
        """ログインUIの表示"""
        st.write("### ログインしてください 👇️")
        self.authenticator.login('main', 'ログイン')
        
        # パスワードを忘れた場合のリンク
        if st.button('パスワードをリセット', key='forgot_password_link'):
            st.session_state['password_reset_mode'] = True
            st.rerun()
        
        # ログインページの画像を表示（複数のパスを試行）
        try:
            import os
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            image_path = os.path.join(base_dir, 'icons', 'cis_page-eye-catch.jpg')
            st.image(image_path, use_container_width=True)
        except Exception as e:
            st.warning(f"画像の読み込みに失敗しました")
    
    def render_reset_password_ui(self):
        """パスワードリセットUIの表示（二段階認証付き）"""
        st.write("### パスワードをリセット 🔄")
        
        # 二段階認証の説明
        if self.api_key:
            st.info("セキュリティのため、認証コードをメールで送信します。事前に登録されたメールに配信されますので、メールのスパムフォルダも含めて確認してください。")
            st.info("登録メールを変更したい場合は、管理者までお問い合わせください。")
        
        try:
            # パスワードリセットフォームを表示（二段階認証とメール送信を有効化）
            forgot_pw_args = {
                'location': 'main',
                'key': 'forgot_pw'
            }
            
            # API キーが設定されている場合のみ二段階認証を有効化
            if self.api_key:
                forgot_pw_args['two_factor_auth'] = True
                forgot_pw_args['send_email'] = True
            
            username_forgot_pw, email_forgot_pw, new_random_pw = self.authenticator.forgot_password(**forgot_pw_args)
            
            if username_forgot_pw:
                # パスワードリセット成功時
                st.session_state['reset_success'] = True
                st.session_state['reset_username'] = username_forgot_pw  # リセットしたユーザー名を保存
                
                st.success('パスワードがリセットされました！')
                
                # メール送信が有効な場合はメッセージを変更
                if self.api_key and 'send_email' in forgot_pw_args and forgot_pw_args['send_email']:
                    st.info(f'新しいパスワードが {email_forgot_pw} 宛にメールで送信されました。')
                else:
                    st.info(f'新しいパスワード: {new_random_pw}')
                    st.warning('このパスワードは一度だけ表示されます。安全な場所に保存してください。')
                
                # パスワード変更フラグをセット
                self.user_info['credentials']['usernames'][username_forgot_pw]['password_reset_required'] = True
                
                # YAMLファイルを更新
                self.save_user_info()
                
            elif username_forgot_pw == False:
                st.error('ユーザー名が見つかりませんでした')
        except Exception as e:
            st.error(f'エラーが発生しました: {e}')
        
        # ログイン画面に戻るボタン
        if st.button('ログインに戻る', key='back_to_login'):
            # パスワード再設定モードに切り替え
            st.session_state['password_reset_mode'] = False
            st.session_state['password_change_mode'] = True
            st.rerun()
    
    def render_password_change_ui(self):
        """リセット後のパスワード再設定UI表示"""
        st.write("### パスワードを再設定してください")
        st.info("リセットされたパスワードでログインし、新しいパスワードを設定してください")
        
        # ユーザー名を自動入力
        username_placeholder = st.empty()
        username_placeholder.text_input("ユーザー名", value=st.session_state['reset_username'], key="auto_username", disabled=True)
        
        # 通常のログインフォーム
        self.authenticator.login('main', 'ログイン')
        
        # ログイン成功後の処理
        if st.session_state.get('authentication_status'):
            # パスワード変更フラグをリセット
            st.session_state['password_change_mode'] = False
            st.session_state['reset_username'] = None
            st.rerun()
        
        # キャンセルボタン
        if st.button("通常ログイン画面に戻る"):
            st.session_state['password_change_mode'] = False
            st.session_state['reset_username'] = None
            st.rerun()
    
    def render_force_password_change_ui(self, username):
        """強制パスワード変更UIの表示"""
        st.title("パスワード変更が必要です")
        st.warning("リセットされたパスワードを使用しているため、パスワードの変更が必要です。")
        
        try:
            if self.authenticator.reset_password(username, 'main', key='force_reset_password'):
                st.success('パスワードが正常に変更されました')
                # パスワード変更フラグを更新
                self.user_info['credentials']['usernames'][username]['password_reset_required'] = False
                # YAML ファイルに書き戻す
                self.save_user_info()
                st.rerun()
        except Exception as e:
            st.error(f'エラーが発生しました: {e}')
    
    def render_sidebar_logout(self, username):
        """サイドバーのログアウトボタン表示"""
        config = appProperties('config.yml')
        st.write(f"ログイン: {helpers.get_office_name_jp(config, st.session_state['name'])}")
        # ログアウトボタン
        self.authenticator.logout('ログアウト', key='logout_button')
        
        # ログアウト操作を検出
        if 'authentication_status' in st.session_state and not st.session_state['authentication_status']:
            # ログアウト時に YAML ファイルを更新
            prev_username = st.session_state.get('previous_username', None)
            if prev_username:
                self.update_logout_status(prev_username)
            st.rerun()
        
        # 現在のユーザー名を保存（ログアウト時に使用）
        if 'username' in st.session_state:
            st.session_state['previous_username'] = st.session_state['username']
    
    def process_logout(self):
        """ログアウト処理"""
        if 'previous_username' in st.session_state:
            username = st.session_state.get('previous_username')
            if self.update_logout_status(username):
                # 前回のユーザー名情報をクリア
                del st.session_state['previous_username']
            
        # ログアウトメッセージ
        st.warning('ログアウトしました' if 'logout' in st.session_state else 'ユーザー名/パスワードが正しくありません')
    
    def authenticate_page(self, title="認証が必要です", render_sidebar=True):
        """ページの認証処理とUI表示を一括で行う
        
        Parameters:
        -----------
        title : str
            ページのタイトル
        render_sidebar : bool
            サイドバーログアウトボタンを表示するかどうか
            
        Returns:
        --------
        bool
            認証状態 (True: 認証済み, False: 未認証)
        """
        # ログイン状態の更新
        self.update_login_status()
        
        # 認証状態に基づいてUIを表示
        if st.session_state.get('authentication_status'):
            username = st.session_state.get('username')
            
            # パスワードリセット後のパスワード変更が必要な場合
            if self.user_info['credentials']['usernames'][username].get('password_reset_required', False):
                self.render_force_password_change_ui(username)
                return False
            else:
                # 通常のログイン成功時UI
                # ページのタイトルはこのメソッドの呼び出し元が設定することにする
                
                # サイドバーにログアウトボタンを表示
                if render_sidebar:
                    with st.sidebar:
                        self.render_sidebar_logout(username)
                
                return True
        
        elif st.session_state.get('authentication_status') is False:
            # ログイン失敗時またはログアウト後
            
            # ログアウト処理
            self.process_logout()
            
            st.title(title)
            
            # パスワード再設定モードの場合
            if st.session_state['password_change_mode'] and st.session_state['reset_username']:
                self.render_password_change_ui()
            
            # パスワードリセットモードの場合
            elif st.session_state['password_reset_mode']:
                self.render_reset_password_ui()
            else:
                # 通常のログインフォーム
                self.render_login_ui()
            
            return False
        
        else:
            # 初期状態（未ログイン）- すでにログイン済みのユーザーを自動認証
            if self.check_auto_login():
                st.rerun()
            
            # ログイン済みユーザーがいない場合はログインフォームを表示
            st.title(title)
            
            # パスワード再設定モードの場合
            if st.session_state['password_change_mode'] and st.session_state['reset_username']:
                self.render_password_change_ui()
            
            # パスワードリセットモードの場合
            elif st.session_state['password_reset_mode']:
                self.render_reset_password_ui()
            else:
                # 通常のログインフォーム
                self.render_login_ui()
                
                # ログイン後の再レンダリング確認
                if st.session_state.get('authentication_status'):
                    st.rerun()
            
            return False


def create_yml():
    users_csv_path = ".streamlit/user_info.csv"
    config_yaml_path = ".streamlit/user_info.yml"

    # ユーザー設定の一覧が記述されたデータを読み込み
    with open(users_csv_path, "r") as f:
        csvreader = csv.DictReader(f)
        users = list(csvreader)

    # yaml 設定一覧が記述されたデータを読み込み
    with open(config_yaml_path,"r") as f:
        yaml_data = yaml.safe_load(f)

    # パスワードのハッシュ化
    users_dict = {}
    for user in users:
        user["password"] = Hasher.hash(user["password"])
        tmp_dict = {
            "name": user["name"],
            "password": user["password"],
            "email": user["email"],
            "logged_in": False,
            "failed_login_attempts": 0,
            "password_reset_required": False,
        }
        users_dict[user["name"]] = tmp_dict

    # yaml 書き込み
    yaml_data["credentials"]["usernames"] = users_dict
    
    # API キーの追加 (既にある場合は更新しない)
    if "api_key" not in yaml_data:
        yaml_data["api_key"] = ""  # 実際の API キーを設定する必要があります
    
    with open(config_yaml_path, "w") as f:
        yaml.dump(yaml_data, f)
        print("完了")

