import streamlit as st
import os
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
    st.sidebar.header("解析データチェッカー")

    # メインページのコンテナを配置する
    main_view = st.container()
    graph_view = st.empty()
    log_view = st.container()

    # フォルダ直下の画像保管用ディレクトリのリスト
    images_path = helpers.list_imagespath_nonCache(config.output_dir)

    # 画像保管線区の選択
    st.sidebar.markdown("# ___Step1___ 線区を選択")

    # 検索ボックスによる対象フォルダの絞り込み
    dir_search = st.sidebar.checkbox("検索ボックス表示", value=True)
    if dir_search:
        dir_area_key = st.sidebar.text_input("線区 検索キーワード").lower()
        images_path_filtered = [path for path in images_path if dir_area_key in path.lower()]
        if dir_area_key:
            if not images_path_filtered:
                st.sidebar.error("対象データがありません。検索キーワードを変更してください。")
                st.stop()
        else:
            images_path_filtered = images_path
    else:
        images_path_filtered = images_path

    # 対象フォルダの選択
    dir_area = st.sidebar.selectbox("線区のフォルダ名を選択してください", images_path_filtered)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")
        st.stop()

    # 選択された線区情報を表示する
    vis.rail_info_view(dir_area, config, main_view)
    
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
    # rail_fpath = outpath + "/rail.shelve"
    rail_fpath = outpath + "/rail.csv"

    # # CSV変換
    # st.sidebar.markdown("# ___Step2___ 結果をCSVデータに変換")
    # # thin_out = st.sidebar.number_input("画像間引き間隔(1～1000で指定)",
    # #                                    min_value=1,
    # #                                    max_value=1000,
    # #                                    value=100)
    # window = st.sidebar.number_input("標準偏差計算のウィンドウサイズを指定",
    #                                 min_value=1,
    #                                 value=100)
    # if st.sidebar.button("CSVファイルを作成"):
    #     try:
    #         log_view.write("一生懸命変換しています🐁...")
    #         progress_bar = log_view.progress(0)
    #         with st.spinner("CSVファイルに変換中..."):
    #             helpers.trolley_dict_to_csv(
    #                 config,
    #                 rail_fpath,
    #                 camera_num,
    #                 base_images,
    #                 # thin_out,
    #                 window,    # ウィンドウサイズを指定する場合はwindowにする
    #                 log_view,
    #                 progress_bar)
    #         log_view.success("CSVファイルを作成しました")
    #     except Exception as e:
    #         log_view.error("解析結果ファイルがありません")
    #         log_view.write(f"Error> {e}")

    # CSVダウンロード
    # csv_fpath = rail_fpath.replace(".shelve", ".csv")
    # try:
    #     with open(csv_fpath) as csv:
    #         st.sidebar.download_button(
    #             label="CSVファイルをダウンロード",
    #             data=csv,
    #             file_name=dir_area + "_" + camera_num + "_output.csv",
    #             mime="text/csv"
    #         )
    # except Exception as e:
    #     log_view.error("CSVファイルがありません")
    #     log_view.write(f"Error> {e}")
    # # CSV削除
    # csv_delete_btn = st.sidebar.button("CSVファイルを削除する")
    # if csv_delete_btn:
    #     if os.path.exists(rail_fpath):
    #         helpers.file_remove(rail_fpath)
    #         log_view.error("CSVファイルを削除しました")
    #     else:
    #         log_view.error("削除するCSVファイルがありません")

    # グラフ表示
    # スライダーでグラフ化する範囲を指定（サイドバーに表示）
    st.sidebar.markdown("# ___Step2___ グラフを表示する")
    ix_set_flag = st.sidebar.checkbox("横方向の表示範囲を指定")
    form_graph = st.sidebar.form(key="graph_init")
    # img_num = form_graph.select_slider("グラフ化する画像を指定",
    #                                    options=list(range(len(base_images))),
    #                                    value=(0, 50))
    # グラフサイズ単位 bokeh:px, pyplot:インチ
    graph_height = form_graph.number_input("グラフの表示高さを指定する(単位:px)",
                                           min_value=1,
                                           value=200)    # bokeh
                                           # value=10)    # pyplot
    graph_width = form_graph.number_input("グラフの表示幅を指定する(単位:px)",
                                          min_value=1,
                                          value=700)    # bokeh
                                          # value=8)    # pyplot
    if ix_set_flag:
        ix_view_range_start = form_graph.number_input("横方向の表示位置を指定(開始)",
                                                     min_value=0,
                                                     value=0)
        ix_view_range_end = form_graph.number_input("横方向の表示位置を指定(終了)",
                                                     min_value=0,
                                                     value=10000000)
    else:
        ix_view_range_start = 0
        ix_view_range_end = 100
    graph_thinout = form_graph.number_input("表示データ間引き間隔(基本:100, 間引き無し:1)",
                                       min_value=1,
                                       # max_value=1000,
                                       value=100)
    form_graph.warning("＜確認＞CSVは作成済ですか？")
    submit = form_graph.form_submit_button("グラフを作成する")
    if submit:
        if ix_view_range_start <= ix_view_range_end:
            ix_view_range = (ix_view_range_start, ix_view_range_end)
            # log_view.write(f'ix_view_range:{ix_view_range} {type(ix_view_range)}')
        else:
            log_view.error("横方向の表示位置の入力が誤っています")
            st.stop()
        with st.spinner("グラフ作成中"):
            # グラフデータを作成する
            # for bokeh
            grid = vis.plot_fig_bokeh(
                config,
                rail_fpath,
                graph_height,
                graph_width,
                graph_thinout,
                ix_set_flag,
                ix_view_range
            )
            graph_view.bokeh_chart(grid, use_container_width=True)
            # for matplotlib
            # fig, (ax1, ax2, ax3, ax4) = vis.plot_fig_plt(
            #     config,
            #     rail_fpath,
            #     camera_num,
            #     graph_height,
            #     graph_width,
            #     graph_thinout,
            #     ix_set_flag,
            #     ix_view_range
            # )
            # graph_view.pyplot(fig)


    # 解析結果があるかをサイドバーに表示する
    st.sidebar.markdown("# 参考 結果有無👇")
    try:
        with open(rail_fpath) as csv:
            st.sidebar.download_button(
                label="CSVファイルをダウンロード",
                data=csv,
                file_name=dir_area + "_" + camera_num + "_output.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.sidebar.error("CSVファイルがありません")
        st.sidebar.write(f"Error> {e}")
    csv_delete_btn = st.sidebar.button("結果CSVデータを削除する")
    if csv_delete_btn:
        if os.path.exists(rail_fpath):
            helpers.file_remove(rail_fpath)
            log_view.error("CSVファイルを削除しました")
        else:
            log_view.error("削除するCSVファイルがありません")
    df = helpers.check_camera_dirs(dir_area, config)
    st.sidebar.dataframe(df)

    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    check_graph(config)
