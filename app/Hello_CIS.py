import streamlit as st
import src.helpers as helpers
import src.auth as auth
from src.config import appProperties


def main(config):
    st.set_page_config(page_title="Hello", page_icon="🖐",)
    # 認証チェック
    if not auth.check_authentication():
        return
    
    # 認証済みの場合、通常のアプリケーション表示
    readme_text = st.markdown(helpers.read_markdown_file(config.readme_md))
    st.sidebar.title("何をしますか？")
    st.sidebar.success("👆アプリを選択してください")
    
    # ログアウトボタン
    if st.sidebar.button("ログアウト"):
        auth.logout()


if __name__ == "__main__":
    config = appProperties('config.yml')
    main(config)
