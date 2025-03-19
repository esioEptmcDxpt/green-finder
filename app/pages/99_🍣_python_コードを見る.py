import streamlit as st
import src.helpers as helpers
import src.auth as auth


def show_code():
    """ 各ページ(Pages内)のPythonファイルのコードを表示する
    """
    st.set_page_config(page_title="show code...", layout="wide")
    # 認証チェック
    if not auth.check_authentication():
        return
    st.sidebar.header("摩耗判定プログラムのコードを表示しています。")
    dir_select = st.sidebar.selectbox("対象ディレクトリを選択", ["pages", "src"])
    file_list = helpers.get_file_list(dir_select)
    file_name = st.sidebar.selectbox("Pythonファイルを選択", file_list)
    st.code(helpers.read_python_file(dir_select + "/" + file_name))

    # ログアウトボタン
    if st.sidebar.button("ログアウト"):
        auth.logout()

    return


if __name__ == "__main__":
    show_code()
