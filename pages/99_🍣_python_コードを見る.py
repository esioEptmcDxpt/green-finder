import streamlit as st
import src.utilsS3_01 as utls3
import src.utilsST_01 as utlst


def show_code():
    st.set_page_config(page_title="show code...", page_icon="🍣")
    st.sidebar.header("摩耗判定プログラムのコードを表示しています。")
    # st.code(get_file_content_as_string("1_TTS摩耗判定プログラム.py"))
    file_list = utlst.get_file_list("pages")
    file_name = st.sidebar.selectbox("Pythonファイルを選択", file_list)
    st.code(utlst.read_python_file("pages/" + file_name))
    return

if __name__ == "__main__":
    show_code()
