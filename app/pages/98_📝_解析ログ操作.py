import io
import time
import streamlit as st
import streamlit.components.v1 as components
import pygwalker as pyg
import pandas as pd
from src.config import appProperties
import src.logger as my_logger
import src.auth_aws as auth
import src.helpers as helpers
import os
import datetime


@st.dialog("技セ・MCを選択")
def set_office(_config, office_default):
    office_names = helpers.get_office_names_jp(_config)
    office_default_jp = _config.office_names[office_default]["name"]
    office_names_default_index = office_names.index(office_default_jp)
    office_name_jp = st.selectbox("技セを選択", office_names, index=office_names_default_index)
    office_name = helpers.get_office_name(_config, office_name_jp)
    mc_name_jp = st.selectbox("MCを選択", helpers.get_mc_names_jp(_config, office_name_jp))
    mc_name = helpers.get_mc_name(_config, office_name_jp, mc_name_jp)
    if st.button("設定"):
        st.session_state.office = f"{office_name}/{mc_name}"
        st.rerun()


def log_management(config):
    # マルチページの設定
    st.set_page_config(page_title="解析ログ操作", layout="wide")
    st.logo("icons/cis_page-eye-catch.jpg", size="large")
    # 認証マネージャーの初期化
    auth_manager = auth.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return

    # 認証情報からユーザー名を取得
    username = auth_manager.authenticator.get_username()

    st.sidebar.header("トロリ線摩耗検出システム")

    # 箇所名を選択
    if 'office' not in st.session_state:
        st.session_state.office = None

    # 技セ・MCを選択
    if "office_dialog" not in st.session_state:
        if st.sidebar.button("技セ・MCを選択"):
            set_office(config, username)

    # 選択された技セ・MCを表示
    if not st.session_state.office:
        st.sidebar.error("技セ・MCを選択してください")
        st.stop()
    else:
        st.sidebar.write(f"選択箇所: {helpers.get_office_message(config, st.session_state.office)}")

    # メイン処理
    # 現在の日付をデフォルトとして設定
    today = datetime.date.today()
    selected_date = st.sidebar.date_input(
        "ログ日付を選択", 
        value=today,
        max_value=today
    )
    date_str = selected_date.strftime('%Y%m%d')

    # 選択された日付に基づいてログファイルのパスを取得
    log_path = my_logger.get_log_path(office=st.session_state.office, date=date_str, config=config)
    st.sidebar.info(f"解析ログファイル: {log_path}")

    # ログファイルの存在確認
    if not os.path.exists(log_path):
        st.warning(f"ログファイルが存在しません: {log_path}")
        st.stop()
    
    # ログの読み込み
    df = my_logger.load_logs(office=st.session_state.office, date=date_str, config=config)
    if len(df.columns) < 2:
        st.warning("ログがありません")
        st.stop()
    df = my_logger.preprocess_log_data(df)

    # データフレームinfoを文字列で取得する
    buf = io.StringIO()
    df.info(buf=buf)

    # 画面表示部
    # ---------------------------------------
    # Pygwalkerを使用してHTMLを生成する
    st.title("📈実行ログ分析ツール")

    bi_height = int(st.sidebar.number_input("分析ツール高さ", value=1000))

    # PyGWalker初期設定用コード
    # 別のグラフをデフォルトにしたいときは、PyGWalkerから出力したコードに更新する
    # vis_spec = r"""{"config":[{"config":{"defaultAggregated":false,"geoms":["auto"],"coordSystem":"generic","limit":-1,"timezoneDisplayOffset":0},"encodings":{"dimensions":[{"fid":"message","name":"message","basename":"message","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"log_level","name":"log_level","basename":"log_level","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"start_time","name":"start_time","basename":"start_time","semanticType":"temporal","analyticType":"dimension","offset":0},{"fid":"method","name":"method","basename":"method","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"measurement_area","name":"measurement_area","basename":"measurement_area","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"camera_num","name":"camera_num","basename":"camera_num","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"image_name","name":"image_name","basename":"image_name","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"trolley_id","name":"trolley_id","basename":"trolley_id","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"error","name":"error","basename":"error","semanticType":"nominal","analyticType":"dimension","offset":0},{"fid":"gw_mea_key_fid","name":"Measure names","analyticType":"dimension","semanticType":"nominal"}],"measures":[{"fid":"process_time","name":"process_time","basename":"process_time","analyticType":"measure","semanticType":"quantitative","aggName":"sum","offset":0},{"fid":"analysis_time","name":"analysis_time","basename":"analysis_time","analyticType":"measure","semanticType":"quantitative","aggName":"sum","offset":0},{"fid":"image_idx","name":"image_idx","basename":"image_idx","analyticType":"measure","semanticType":"quantitative","aggName":"sum","offset":0},{"fid":"image_count","name":"image_count","basename":"image_count","analyticType":"measure","semanticType":"quantitative","aggName":"sum","offset":0},{"fid":"gw_count_fid","name":"Row count","analyticType":"measure","semanticType":"quantitative","aggName":"sum","computed":true,"expression":{"op":"one","params":[],"as":"gw_count_fid"}},{"fid":"gw_mea_val_fid","name":"Measure values","analyticType":"measure","semanticType":"quantitative","aggName":"sum"}],"rows":[{"fid":"analysis_time","name":"analysis_time","basename":"analysis_time","analyticType":"measure","semanticType":"quantitative","aggName":"sum","offset":0}],"columns":[{"fid":"image_idx","name":"image_idx","basename":"image_idx","analyticType":"measure","semanticType":"quantitative","aggName":"sum","offset":0}],"color":[{"fid":"log_level","name":"log_level","basename":"log_level","semanticType":"nominal","analyticType":"dimension","offset":0}],"opacity":[],"size":[],"shape":[],"radius":[],"theta":[],"longitude":[],"latitude":[],"geoId":[],"details":[],"filters":[],"text":[]},"layout":{"showActions":false,"showTableSummary":false,"stack":"stack","interactiveScale":false,"zeroScale":true,"size":{"mode":"full","width":320,"height":200},"format":{},"geoKey":"name","resolve":{"x":false,"y":false,"color":false,"opacity":false,"shape":false,"size":false}},"visId":"gw_Ta6C","name":"Chart 1"}],"chart_map":{},"workflow_list":[{"workflow":[{"type":"view","query":[{"op":"raw","fields":["log_level","image_idx","analysis_time"]}]}]}],"version":"0.4.8"}"""

    # pyg_html = pyg.to_html(df, spec=vis_spec)
    # HTMLをStreamlitアプリケーションに埋め込む
    # components.html(pyg_html, height=bi_height, scrolling=True)

    # データフレーム用のコンテナを配置する
    log_view = st.container()
    log_info = st.expander("ログデータ情報", expanded=False)

    st.sidebar.markdown("# ログをチェック")

    log_view.write("# ログデータ")
    log_view.dataframe(data=df, use_container_width=True)
    log_info.write(f"df_info type: {type(buf.getvalue())}")
    log_info.text(buf.getvalue())

    # ログをCSVでダウンロードする
    csv = df.to_csv(index=False).encode('shift-jis')
    st.sidebar.download_button(
        "ログをダウンロード(CSV形式)",
        csv,
        f'cis_logs_{time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time()))}.csv',
        "text/csv",
        key='download-csv'
    )

    # 解析ログをリセットする
    log_reset_button = st.sidebar.toggle("解析ログを削除する", value=False, key="log_reset")
    if log_reset_button:
        with log_view.form("log_reset_form"):
            st.error("元に戻せません 本当に削除しますか？？")
            submit = st.form_submit_button("💣 削除 💣")
            if submit:
                log_view.error("デバッグ用 ログを削除しました💥")
                log_view.write("※再度ログを見るときは、チェックを外すか、画面をリロードしてください")
                my_logger.reset_logging(office=st.session_state.office, config=config)
                st.stop()

    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    log_management(config)
