import streamlit as st
import src.helpers as helpers
import src.visualize as vis
import src.auth as auth
from src.config import appProperties
import os
import io


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


def result_image_view(config):
    """ 解析結果画像を表示させる用のページ
    Args:
        config: ymlファイルを読み込んだ設定値
    """
    st.set_page_config(page_title="解析結果ビューワー", layout="wide")

    # 認証マネージャーの初期化
    auth_manager = auth.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return

    st.sidebar.header("解析結果閲覧システム")

    # メインページのコンテナを配置する
    main_view = st.container()
    # camera_view = st.empty()
    row1 = st.container()
    row2 = st.container()
    graph_view = st.empty()

    # 箇所名を選択
    if 'office' not in st.session_state:
        st.session_state.office = None

    # 技セ・MCを選択
    if "office_dialog" not in st.session_state:
        if st.sidebar.button("技セ・MCを選択"):
            set_office(config, st.session_state['name'])

    # 選択された技セ・MCを表示
    if not st.session_state.office:
        st.sidebar.error("技セ・MCを選択してください")
        st.stop()
    else:
        st.sidebar.write(f"選択箇所: {helpers.get_office_message(config, st.session_state.office)}")

    # 線区フォルダの選択
    images_path = helpers.list_imagespath_nonCache(f"{config.image_dir}/{st.session_state.office}")
    main_view.markdown("# ___Step1___ 線区を選択")
    st.sidebar.markdown("# ___Step1___ 線区を選択")
    st.sidebar.write(f"解析対象の線区フォルダを指定👉️")

    # 検索ボックスによる対象フォルダの絞り込み
    dir_search = st.sidebar.checkbox("検索ボックス表示", value=False)
    if dir_search:
        dir_area_key = main_view.text_input("線区 検索キーワード(英語で入力)").lower()
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
    dir_area = main_view.selectbox("線区のフォルダ名を選択してください", images_path_filtered)
    if dir_area is None:
        st.error("CIS に画像データがダウンロードされていません。 __⚙️ データ管理__ を開いて、画像をダウンロードしてください。")
        st.stop()

    # 選択された線区情報を表示する
    vis.rail_info_view(dir_area, config, main_view)

    # 解析対象のカメラ番号を選択する
    camera_name_list = helpers.get_camera_list(config)
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    camera_name_list
                    ).split(':')[0]
    st.sidebar.write(f"カメラ番号: {camera_name}")
    camera_num = config.camera_name_to_type[camera_name]

    # 解析対象の画像フォルダを指定
    target_dir = f"{config.image_dir}/{st.session_state.office}/{dir_area}/{camera_num}"

    # outputディレクトリを指定
    outpath = f"{config.output_dir}/{st.session_state.office}/{dir_area}/{camera_num}"

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # 結果保存用のCSVファイル(rail)の保存パスを指定
    rail_fpath = f"{outpath}/rail.csv"

    # グラフ作成フォーム
    st.sidebar.markdown("# ___Step2___ グラフを表示する")
    ix_set_flag = st.sidebar.checkbox("横方向の表示範囲を指定", value=False)
    form_graph = st.sidebar.form(key="graph_init")
    graph_height = form_graph.number_input("グラフの表示高さを指定する(単位:px)",
                                           min_value=1,
                                           value=200)    # bokeh
                                           # value=10)    # pyplot
    graph_width = form_graph.number_input("グラフの表示幅を指定する(単位:px)",
                                          min_value=1,
                                          value=700)    # bokeh
                                          # value=8)    # pyplot
    scatter_size = form_graph.number_input("グラフのプロットサイズを指定する", min_value=1, value=10)
    if ix_set_flag:
        form_graph.write("表示範囲の画像インデックスを指定")
        ix_view_range_start = form_graph.number_input("開始インデックス",
                                                     min_value=1,
                                                     max_value=len(base_images),
                                                     value=1)
        ix_view_range_end = form_graph.number_input("終了インデックス",
                                                     min_value=1,
                                                     max_value=len(base_images),
                                                     value=len(base_images))
    else:
        ix_view_range_start = 0
        ix_view_range_end = len(base_images)
    ix_view_range = (ix_view_range_start, ix_view_range_end)
    graph_thinout = form_graph.number_input("表示データ間引き間隔(基本:100, 間引き無し:1)",
                                       min_value=1,
                                       # max_value=1000,
                                       value=100)
    form_graph.write("⚠ 間引き間隔での最大値を表示します")


    # 連結画像の表示
    st.sidebar.markdown("# ___Step3___ 連結した画像を表示する")
    graph_add_flag = st.sidebar.checkbox("グラフも表示する", value=False)
    form_concat = st.sidebar.form(key="img_concat_setup")
    # 画像結合フォーム
    if graph_add_flag:
        form_concat.markdown("## ① 画像連結の条件指定")
    else:
        form_concat.markdown("## 画像連結の条件指定")
    # ファイルインデックスを指定する
    if not base_images:
        main_view.error("画像がありません")
        st.stop()
    else:
        idx = form_concat.number_input(f"1枚目のインデックス(1～{len(base_images)})を指定",
                                      min_value=1,
                                      max_value=len(base_images))
        # form_concat.write(f"(参考)ファイルパス:{base_images[idx]}")
        # 画像ファイル名を取得
        image_name = base_images[idx].split('/')[-1]
    form_concat.markdown("⚠ 連結枚数が多いとエラーになります")
    concat_nums = form_concat.number_input("連結する枚数を入力", 1, len(base_images), 5)
    font_size = form_concat.number_input("画像インデックス文字の大きさを入力", 1, 1000, 50)
    if graph_add_flag:
        form_concat.markdown("## ② グラフ作成条件")
        graph_height = form_concat.number_input("グラフの表示高さを指定する(単位:px)",
                                               min_value=1,
                                               value=200)    # bokeh
                                               # value=10)    # pyplot
        graph_width = form_concat.number_input("グラフの表示幅を指定する(単位:px)",
                                              min_value=1,
                                              value=700)    # bokeh
                                              # value=8)    # pyplot
        scatter_size = form_concat.number_input("グラフのプロットサイズを指定する", min_value=1, value=10)
        graph_thinout = form_concat.number_input("表示データ間引き間隔(基本:100, 間引き無し:1)",
                                           min_value=1,
                                           # max_value=1000,
                                           value=100)
        form_concat.write("⚠ 間引き間隔での最大値を表示します")
        # 横方向の表示範囲を指定するためのフラグ
        ix_set_flag = True
        # 画像インデックスに合わせて表示範囲を指定
        ix_view_range_start = idx
        ix_view_range_end = idx + concat_nums - 1
    # 実行ボタンを配置
    submit_concat = form_concat.form_submit_button("連結画像を作成する")


    # グラフだけ表示する
    submit_graph = form_graph.form_submit_button("グラフを作成する")
    if submit_graph:
        if ix_view_range_start <= ix_view_range_end:
            ix_view_range = (ix_view_range_start, ix_view_range_end)
        else:
            st.error("横方向の表示位置の入力が誤っています")
            st.stop()
        
        # outputに解析結果があるかどうか確認                        # 2024.5.22 -->
        exist_csv = helpers.search_csv(outpath)
        if not exist_csv:
            st.error("解析結果がありません。")
            st.stop()                                             # --> 2024.5.22
            
        with st.spinner("グラフ作成中"):
            # グラフデータを作成する
            # for bokeh
            # grid = vis.plot_fig_bokeh(
            #     config,
            #     rail_fpath,
            #     graph_height,
            #     graph_width,
            #     graph_thinout,
            #     ix_set_flag,
            #     ix_view_range,
            #     scatter_size
            # )
            # -----------------------------------------------
            # 高崎検証のためコメントアウト
            # 車モニ マスターデータが必須
            # -----------------------------------------------
            grid = vis.experimental_plot_fig_bokeh(
                config,
                outpath,
                graph_height,
                graph_width,
                graph_thinout,
                ix_set_flag,
                ix_view_range,
                scatter_size
            )
            if grid is None:
                st.error("# 🙇🏻‍♂️ グラフを作成できませんでした。")
            else:
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
            # fig, fig_config = vis.experimental_plot_fig_plotly(
            #     config,
            #     outpath,
            #     graph_height,
            #     graph_width,
            #     graph_thinout,
            #     ix_set_flag,
            #     ix_view_range,
            #     scatter_size
            # )
            # graph_view.plotly_chart(fig, use_container_width=True, config=fig_config)

    # 画像を出力する
    if submit_concat:
        with row1:
            st.write("📸カメラ画像")
            # cam_img = vis.ohc_image_load(base_images[idx])
            cam_img = vis.ohc_img_concat(base_images, idx - 1, concat_nums, font_size)
            st.write(f"カメラ:{camera_name} {idx}～{idx + concat_nums - 1}までの画像")
            st.image(cam_img)
            cam_img_name = f"downloaded_image_{idx}-{idx + concat_nums - 1}.png"
            vis.download_image(cam_img, cam_img_name)
        with row2:
            st.write("🖥️解析結果")
            status_view = st.empty()
            status_view.write("解析結果を表示中")
            st.write("解析結果を表示します")
            progress_bar = st.progress(0)
            try:
                out_img = vis.out_image_concat(
                    rail_fpath,
                    dir_area,
                    camera_num,
                    base_images,
                    idx - 1,
                    concat_nums,
                    font_size,
                    config,
                    status_view,
                    progress_bar,
                    outpath
                )
            except Exception as e:
                out_img = []
                st.write(e)
            if not out_img:
                st.error("解析結果がありません")
            else:
                st.image(out_img)
                out_img_name = f"downloaded_image_{idx}-{idx + concat_nums - 1}_analized.png"
                vis.download_image(out_img, out_img_name)
                
                # 2つの画像をまとめてダウンロードするボタンを追加
                st.write("複数ファイルのダウンロード:")
                vis.download_images_zip(
                    cam_img, 
                    cam_img_name, 
                    out_img, 
                    out_img_name, 
                    f"images_{idx}-{idx + concat_nums - 1}.zip"
                )
        if graph_add_flag:
            with st.spinner("グラフ作成中"):
                if ix_view_range_start <= ix_view_range_end:
                    ix_view_range = (ix_view_range_start, ix_view_range_end)
                else:
                    st.error("横方向の表示位置の入力が誤っています")
                    st.stop()
                # grid = vis.plot_fig_bokeh(
                #     config,
                #     rail_fpath,
                #     graph_height,
                #     graph_width,
                #     graph_thinout,
                #     ix_set_flag,
                #     ix_view_range,
                #     scatter_size
                # )
                grid = vis.experimental_plot_fig_bokeh(
                    config,
                    outpath,
                    graph_height,
                    graph_width,
                    graph_thinout,
                    ix_set_flag,
                    ix_view_range,
                    scatter_size
                )
                if grid is None:
                    st.error("# 🙇🏻‍♂️ グラフを作成できませんでした。")
                else:
                    graph_view.bokeh_chart(grid, use_container_width=True)
                    
                    # 画像2つとHTMLファイルをまとめてダウンロードするボタンを追加
                    st.write("画像と解析グラフをまとめてダウンロード:")
                    vis.download_images_and_html_zip(
                        cam_img, 
                        cam_img_name, 
                        out_img, 
                        out_img_name, 
                        'graph_recent.html',
                        f"images_graph_{idx}-{idx + concat_nums - 1}.zip"
                    )
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
    else:
        if not submit_graph:
            row1.error("サイドバーで条件を指定してグラフや画像を作成してください")


    # 解析結果があるかをサイドバーに表示する
    st.sidebar.markdown("# 参考 結果有無👇")
    # try:                                                                     # 2024.5.22 -->
    #     with open(rail_fpath) as csv:
    #         st.sidebar.download_button(
    #             label="CSVファイルをダウンロード",
    #             data=csv,
    #             file_name=dir_area + "_" + camera_num + "_output.csv",
    #             mime="text/csv"
    #         )
    # except Exception as e:
    exist_csv = helpers.search_csv(outpath)
    if not exist_csv:
        st.sidebar.error("CSVファイルがありません")
        # st.sidebar.write(f"Error> {e}")                                       # --> 2024.5.22
    csv_delete_btn = st.sidebar.button("結果CSVデータを削除する")
    if csv_delete_btn:
        if os.path.exists(rail_fpath):
            helpers.file_remove(rail_fpath)
            st.error("CSVファイルを削除しました")
        else:
            st.error("削除するCSVファイルがありません")
    idx_result_check = st.sidebar.checkbox("解析済みインデックスを表示する", value=True)
    if idx_result_check:
        df = helpers.check_camera_dirs_addIdxLen(dir_area, st.session_state.office, config)
    else:
        df = helpers.check_camera_dirs(dir_area, st.session_state.office, config)
    st.sidebar.dataframe(df)

    # ログアウトボタン
    if st.sidebar.button("ログアウト"):
        auth.logout()


if __name__ == "__main__":
    config = appProperties('config.yml')
    result_image_view(config)
