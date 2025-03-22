import streamlit as st

st.title('リストの数値を表示するアプリ')
text = st.sidebar.text_input('何か数字を入力してください。', 1)
st.text(f'現在の入力は{text}です。')

if 'finalval' in st.session_state:
    st.sidebar.text(f"最後のエラー時の値は{st.session_state['finalval']}でした。")

try:
    st.text('ここに結果を表示します')
    num = int(text)
    st.text(f'現在の数値は{text}')
except:
    st.error('error!、数値でない情報が入力されています！')
    if st.button(f'最後に実行した値を保存して再開しますか?'):
        st.session_state['finalval'] = text
        st.experimental_rerun()
finally:
    st.text(f'最後に実行した値は{text}です。')
    