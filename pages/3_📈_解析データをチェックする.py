import streamlit as st
import time
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def check_graph(config):
    """ グラフ表示ページ
    Args:
        config: ymlファイルを読み込んだ設定値
    """
    # マルチページの設定
    st.set_page_config(page_title="解析データチェッカー")
    st.sidebar.markdown("# 解析データチェッカー")
    st.sidebar.write("👇順番に実行")

    # メインページのコンテナを配置する
    main_view = st.container()
    graph_view = st.empty()
    log_view = st.container()

    # フォルダ直下の画像保管用ディレクトリのリスト
    images_path = helpers.list_imagespath_nonCache(config.output_dir)

    # 画像保管線区の選択
    st.sidebar.markdown("# ① 解析対象を指定する")
    dir_area = st.sidebar.selectbox("線区のフォルダ名を選択してください", images_path)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")

    rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
    with main_view.container():
        st.write(f"現在の線区：{rail_name} {st_name}({updown_name})")
        st.write(f"　　測定日：{measurement_date} ＜{measurement_time}＞")
        st.success("##### 👈別の線区を表示する場合は、再度「線区フォルダを決定」してください")

    # 解析対象のカメラ番号を選択する
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    zip(config.camera_names, config.camera_types)
                    )[0]
    camera_num = config.camera_name_to_type[camera_name]

    # 解析対象の画像フォルダを指定
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num

    # outputディレクトリの設定
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # 結果保存用のshelveファイル(rail)の保存パスを指定
    rail_fpath = outpath + "/rail.shelve"

    # 解析結果があるかをサイドバーに表示する
    df = helpers.check_camera_results(dir_area, config)
    st.sidebar.dataframe(df)

    # CSV変換
    st.sidebar.markdown("# ② グラフ用CSVデータを作成")
    thin_out = st.sidebar.number_input("画像間引き間隔(1～1000で指定)",
                                       min_value=1,
                                       max_value=1000,
                                       value=100)
    # window = st.sidebar.number_input("標準偏差計算のウィンドウサイズを指定",
    #                                 min_value=1,
    #                                 value=1000)
    if st.sidebar.button("グラフ用CSVファイルを作成"):
        try:
            log_view.write("変換ステータス...")
            progress_bar = log_view.progress(0)
            with st.spinner("CSVファイルに変換中..."):
                helpers.trolley_dict_to_csv(
                    config,
                    rail_fpath,
                    camera_num,
                    base_images,
                    thin_out,
                    thin_out,    # ウィンドウサイズを指定する場合はwindowにする
                    log_view,
                    progress_bar)
            log_view.success("グラフ用CSVファイルを作成しました")
        except Exception as e:
            log_view.error("解析結果ファイルがありません")
            log_view.write(f"Error> {e}")

    # CSVダウンロード
    csv_fpath = rail_fpath.replace(".shelve", ".csv")
    try:
        with open(csv_fpath) as csv:
            st.sidebar.download_button(
                label="グラフ用CSVファイルをダウンロード",
                data=csv,
                file_name=dir_area + "_" + camera_num + "_output.csv",
                mime="text/csv"
            )
    except Exception as e:
        log_view.error("グラフ用CSVファイルがありません")
        log_view.write(f"Error> {e}")

    # グラフ表示
    # スライダーでグラフ化する範囲を指定（サイドバーに表示）
    st.sidebar.markdown("# ③ グラフを表示する")
    form_graph = st.sidebar.form(key="graph_init")
    # img_num = form_graph.select_slider("グラフ化する画像を指定",
    #                                    options=list(range(len(base_images))),
    #                                    value=(0, 50))
    graph_height = form_graph.text_input("グラフの表示高さを指定する(単位:px)", "200")
    graph_width = form_graph.text_input("グラフの表示幅を指定する(単位:px)", "700")
    form_graph.warning("＜確認＞CSVは作成済ですか？")
    submit = form_graph.form_submit_button("グラフを作成する")
    if submit:
        with st.spinner("グラフ作成中"):
            # グラフデータを作成する
            grid = vis.plot_fig_bokeh(
                config,
                rail_fpath,
                graph_height,
                graph_width
            )
            # グラフを表示
            graph_view.bokeh_chart(grid, use_container_width=True)
    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    check_graph(config)
