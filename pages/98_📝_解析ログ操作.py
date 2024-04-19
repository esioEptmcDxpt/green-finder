import io
import time
import streamlit as st
import pandas as pd
from src.config import appProperties
import src.logger as my_logger


def log_management(config):
    # マルチページの設定
    st.set_page_config(page_title="解析ログ操作")
    st.sidebar.header("トロリ線摩耗検出システム")

    # メインページのコンテナを配置する
    main_view = st.container()
    log_view = st.container()
    log_info = st.expander("ログデータ情報", expanded=False)

    main_view.write("# 実行ログ")
    st.sidebar.markdown("# ログをチェック")

    # メイン処理
    fpath = st.sidebar.text_input("ログファイル名", value="tts.log")
    df = my_logger.load_logs(fpath)
    if len(df.columns) < 2:
        st.warning("ログがありません")
        st.stop()
    df['start_time'] = pd.to_datetime(df['start_time'])
    df = df.dropna(subset=["process_time"])

    # データフレームinfoを文字列で取得する
    buf = io.StringIO()
    df.info(buf=buf)

    # 画面表示部
    log_view.write("# ログデータ")
    log_view.dataframe(data=df, use_container_width=True)
    log_info.write(f"df_info type: {type(buf.getvalue())}")
    log_info.text(buf.getvalue())

    # ログをCSVでダウンロードする
    csv = df.to_csv(index=False).encode('shift-jis')
    st.sidebar.download_button(
        "ログをダウンロード(CSV形式)",
        csv,
        f'tts_logs_{time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))}.csv',
        "text/csv",
        key='download-csv'
    )

    # 解析ログをリセットする
    log_reset_button = st.sidebar.checkbox("解析ログを削除する", value=False, key="log_reset")
    if log_reset_button:
        with log_view.form("log_reset_form"):
            st.error("元に戻せません 本当に削除しますか？？")
            submit = st.form_submit_button("💣 削除 💣")
            if submit:
                log_view.error("デバッグ用 ログを削除しました💥")
                log_view.write("※再度ログを見るときは、チェックを外すか、画面をリロードしてください")
                my_logger.reset_logging()
                st.stop()

    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    log_management(config)
