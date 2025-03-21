import streamlit as st
import src.helpers as helpers
import src.auth as auth
import src.auth_aws as auth_aws
import src.visualize as visualize
from src.config import appProperties
import time


def main(config):
    st.set_page_config(page_title="Hello", page_icon="🖐",)

    # 認証マネージャーの初期化
    auth_manager = auth_aws.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return
    
    # サイドバーに追加のナビゲーション
    with st.sidebar:
        st.title("何をしますか？")
        st.success("👆アプリを選択してください")
    
    # ようこそページを表示
    visualize.display_welcome_page()

    # (管理用) ユーザ情報を作成
    # st.sidebar.title("管理用")
    # st.sidebar.write("ユーザ情報を作成します。すべてのユーザ情報がCSVファイルに従って初期化されるので注意して使用してください。")
    # if st.sidebar.button("ユーザ情報を作成"):
    #     auth.create_yml()


if __name__ == "__main__":
    config = appProperties('config.yml')
    main(config)
