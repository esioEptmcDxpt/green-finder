import streamlit as st
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def main(config):
    st.set_page_config(page_title="Hello",page_icon="🖐",)
    readme_text = st.markdown(helpers.read_markdown_file(config.readme_md))
    st.sidebar.title("何をしますか？")
    st.sidebar.success("👆アプリを選択してください")


if __name__ == "__main__":
    config = appProperties('config.yml')
    main(config)
