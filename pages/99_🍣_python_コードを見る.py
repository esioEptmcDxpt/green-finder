import streamlit as st
import src.helpers as helpers


def show_code():
    """ 各ページ(Pages内)のPythonファイルのコードを表示する
    """
    st.set_page_config(page_title="show code...")
    st.sidebar.header("摩耗判定プログラムのコードを表示しています。")
    dir_select = st.sidebar.selectbox("対象ディレクトリを選択", ["pages", "src"])
    file_list = helpers.get_file_list(dir_select)
    file_name = st.sidebar.selectbox("Pythonファイルを選択", file_list)
    st.code(helpers.read_python_file(dir_select + "/" + file_name))
    return


if __name__ == "__main__":
    show_code()
