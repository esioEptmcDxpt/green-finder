import streamlit as st
import src.helpers as helpers
import src.auth as auth


def show_code():
    """ 各ページ(Pages内)のPythonファイルのコードを表示する
    """
    st.set_page_config(page_title="show code...", layout="wide")

    # 認証マネージャーの初期化
    auth_manager = auth.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return

    st.sidebar.header("摩耗判定プログラムのコードを表示しています。")
    dir_select = st.sidebar.selectbox("対象ディレクトリを選択", ["pages", "src"])
    file_list = helpers.get_file_list(dir_select)
    file_name = st.sidebar.selectbox("Pythonファイルを選択", file_list)
    st.code(helpers.read_python_file(dir_select + "/" + file_name))

    return


if __name__ == "__main__":
    show_code()
