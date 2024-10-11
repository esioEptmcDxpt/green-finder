import os
import shelve
import copy
import streamlit as st
import src.helpers as helpers
import src.visualize as vis
from src.kalman_calc import track_kalman
from src.similar_pixel_calc import track_pixel
from src.config import appProperties


def ohc_wear_analysis(config):
    # マルチページの設定
    st.set_page_config(page_title="トロリ線摩耗検出システム", layout="centered")
    st.sidebar.header("トロリ線摩耗検出システム")

    # メインページのコンテナを配置する
    main_view = st.container()
    camera_view = st.empty()
    log_view = st.container()

    # フォルダ直下の画像保管用ディレクトリのリスト
    # images_path = helpers.list_imagespath(config.image_dir)
    # 他ページでの結果を反映するためnonCacheを使用
    images_path = helpers.list_imagespath_nonCache(config.image_dir)

    # 画像保管線区の選択
    st.sidebar.markdown("# ___Step1___ 線区を選択")

    # 検索ボックスによる対象フォルダの絞り込み
    dir_search = st.sidebar.checkbox("検索ボックス表示", value=False)
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

    meas_quater = st.sidebar.selectbox("走行タイミング", config.quarter_measurements)

    # 対象フォルダの選択
    dir_area = st.sidebar.selectbox("線区のフォルダ名を選択してください", images_path_filtered)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")
        st.stop()

    # 選択された線区情報を表示する
    vis.rail_info_view(dir_area, config, main_view)

    st.sidebar.markdown("# ___Step2___ 解析条件を設定")
    # 解析対象のカメラ番号を選択する
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    zip(config.camera_names, config.camera_types)
                    )[0]
    camera_num = config.camera_name_to_type[camera_name]

    # 解析対象の画像フォルダを指定
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num

    # outputディレクトリを指定
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # ファイルインデックスを指定する
    if not base_images:
        st.sidebar.error("画像がありません")
        st.stop()
    else:
        idx = st.sidebar.number_input(f"インデックス(1～{len(base_images)}で指定)",
                                      min_value=1,
                                      max_value=len(base_images)) - 1
        st.sidebar.write(f"ファイルパス:{base_images[idx]}")
        # 画像ファイル名を取得
        image_name = base_images[idx].split('/')[-1]
    
    # キロ程情報チェック
    img2kiro_tdm_prefix = f"{config.kiro_prefix}/{meas_quater}/csv/"
    csv_files = helpers.list_csv_files(config.bucket, img2kiro_tdm_prefix)
    if not csv_files:
        main_view.error("##### ⚠️ 選択された走行タイミングの画像->キロ程情報がデータベースにありません。管理者に問い合わせてください。")

    # 結果保存用のCSVファイル(rail)の保存パスを指定
    image_name_noExtension = os.path.splitext(os.path.basename(base_images[idx]))[0]
    rail_fpath = f"{outpath}/{config.csv_fname}_{image_name_noExtension}.csv"

    # 表示中の画像、カメラ番号を対象に、トロリーIDを指定して結果を削除する
    result_del = st.sidebar.checkbox("表示中の結果を削除", value=False, key='result_del')
    if result_del:
        result_del_form = st.sidebar.form("(💣注意 結果削除)")
        del_trolley_id = result_del_form.selectbox("トロリ線のIDを入力してください", config.trolley_ids)
        result_del_form.warning("元に戻せません 本当に削除しますか？")
        result_del_submit = result_del_form.form_submit_button("💣 削除 💣")
        if result_del_submit:
            helpers.result_csv_drop(rail_fpath, dir_area, camera_num, image_name, del_trolley_id, config)
            main_view.error(f"💥 {idx+1}枚目 {del_trolley_id} の結果を削除しました 💥")

    # メインページにカメラ画像を表示する
    col1, col2 = camera_view.columns(2)

    with col1:
        st.write("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images[idx])
        st.write(f"カメラ:{camera_name} {idx + 1}番目の画像")
        st.image(cam_img)
        cam_img_name = f"downloaded_image_{idx}.png"
        vis.download_image(cam_img, cam_img_name)
    with col2:
        st.write("🖥️解析結果")
        st.write("解析結果を表示中")
        try:
            out_img, colors = vis.out_image_load(rail_fpath, dir_area, camera_num, image_name, cam_img, config, outpath)
        except Exception as e:
            out_img = []
            colors = []
            st.write(e)
        if not out_img:
            st.error("解析結果がありません")
        else:
            st.image(out_img)
            out_img_name = f"downloaded_image_{idx}_analized.png"
            vis.download_image(out_img, out_img_name)
    if out_img:
        with st.sidebar.expander("解析結果の凡例", expanded=True):
            trolley_ids_legend = "<span>トロリ線の描画色</span>"
            for trolley_id, color in zip(config.trolley_ids, colors):
                trolley_ids_legend += f'<br><span style="color:rgb{color};">{trolley_id}</span>'
            st.markdown(trolley_ids_legend, unsafe_allow_html=True)

    st.sidebar.markdown("# ___Step3___ 解析を実行する")
    # 暫定的にカルマンフィルタに限定

    trace_method = st.sidebar.radio(
        "システムを選択", 
        ("カルマンフィルタ", "ピクセルトレース")
    )
    # trace_method = "カルマンフィルタ"
    
    # キロ程情報の使用有無
    kiro_data = st.sidebar.checkbox("キロ程情報を使用", value=True)

    # メモリ付き画像を表示
    support_line = st.sidebar.checkbox("補助線を使用")
    if support_line:
        # 補助線を使用する場合
        form_support_line = st.sidebar.form(key="support_line_form")
        result_line_draw = form_support_line.checkbox("結果を重ねて描画", value=True)
        form_support_line.write(" 0 にすると線を表示しません")
        hori_pos = form_support_line.number_input("補助線の横位置", 0, 999, 0)
        # 選択したシステムによって横線の本数を変更
        vert_pos = [0, 0]
        if trace_method == "ピクセルトレース":
            vert_pos[0] = form_support_line.number_input("補助線の縦位置", 0, 2047, 1000)
        if trace_method == "カルマンフィルタ":
            vert_pos[0] = form_support_line.number_input("補助線の縦位置(上側)", 0, 2047, 1000)
            vert_pos[1] = form_support_line.number_input("補助線の縦位置(下側)", 0, 2047, 1500)
        spline_submit = form_support_line.form_submit_button("📈初期値入力用メモリ付画像を表示する")
        # グラフ付画像の描画を実行
        if spline_submit:
            if (not result_line_draw) | (not out_img):
                # 元のカメラ画像 または 結果が無い場合
                fig = vis.plot_fig(cam_img, vert_pos, hori_pos)
            else:
                fig = vis.plot_fig(out_img, vert_pos, hori_pos)
            log_view.pyplot(fig)
    else:
        form_graph_img = st.sidebar.form(key="graph_img_form")
        result_line_draw = form_graph_img.checkbox("結果を重ねて描画", value=True)
        # 補助線を使用しない場合
        hori_pos = 0
        vert_pos = [0, 0]
        spline_submit = form_graph_img.form_submit_button("📈初期値入力用メモリ付画像を表示する")
        if spline_submit:
            if (not result_line_draw) | (not out_img):
                # 元のカメラ画像 または 結果が無い場合
                fig = vis.plot_fig(cam_img, vert_pos, hori_pos)
            else:
                fig = vis.plot_fig(out_img, vert_pos, hori_pos)
            log_view.pyplot(fig)

    # ピクセルトレースを実行
    if trace_method == "ピクセルトレース":
        form_px = st.sidebar.form(key="similar_pixel_init")
        xin = form_px.number_input("トロリ線の中心位置を入力(0～2048)", 0, 2048, 1024)
        test_num = form_px.number_input(f"解析する画像枚数を入力(1～{len(base_images)-idx})",
                                        1,
                                        len(base_images)-idx,
                                        len(base_images)-idx
                                       )
        submit = form_px.form_submit_button("ピクセルトレース実行")
        if submit:
            # outputディレクトリの準備
            os.makedirs(outpath, exist_ok=True)

            # shelveファイルの初期化
            with shelve.open(rail_fpath) as rail:
                # 線区名を記録する
                rail["name"] = dir_area
                # 解析結果が既にある場合は初期化しない
                helpers.rail_camera_initialize(rail, camera_num, base_images, config.trolley_ids)
            if st.button('計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                st.stop()
                st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

            with st.spinner("ピクセルトレース実行中"):
                track_pixel(
                    rail_fpath,
                    camera_num,
                    base_images,
                    idx,
                    xin,
                    test_num,
                    log_view,
                )

    # カルマンフィルタを実行
    elif trace_method == "カルマンフィルタ":
        # カルマンフィルタの初期値設定
        detect_edge = st.sidebar.checkbox("自動で初期値を入力しますか？", value=True)
        # form_support_line = st.sidebar.form(key="detect_edge_form")    # 試作（初期エッジ自動検出）用フォーム
        # form_detect = st.sidebar.form(key="kalman_init_detect")
        form = st.sidebar.form(key="kalman_init")

        trolley_id = form.selectbox("トロリ線のIDを入力してください", config.trolley_ids)
        x_init = form.number_input("横方向の初期座標を入力してください", 0, 999)

        # 初期値自動入力フォーム
        # -----------------------------------------------
        if detect_edge:
            candidate_init = helpers.detect_init_edge(cam_img, x_init)    # x_initに対応
            candidate_len = len(candidate_init)
            if x_init:
                candidate_init = helpers.detect_init_edge(cam_img, x_init)    # x_initに対応
                candidate_len = len(candidate_init)

            # num_init = form_support_line.number_input("初期値候補を選択してください", 1, candidate_len)
            num_init = form.number_input("初期値候補を選択してください", 1, candidate_len) - 1
            # num_init = num_init -1
            # init_edge_submit = form_support_line.form_submit_button("📈自動で初期値を入力する")
            init_edge_submit = form.form_submit_button("📈自動で初期値を入力する")
            if init_edge_submit and candidate_len != 0:
                vis.draw_marker(candidate_init, num_init, cam_img, col1, x_init)    # x_initに対応
                print(f'else num:{num_init}')
            elif init_edge_submit and candidate_len == 0:
                st.write("初期値を検出できませんでした・・・")
        # -----------------------------------------------
        else:
            candidate_len = 0

        if candidate_len == 0:
            y_init_l = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください", 0, 1999)
            y_init_u = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください", 0, 1999)
        else:
            y_init_l = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください",
                                         min_value=0, max_value=1999,
                                         value=candidate_init[num_init][0])
            y_init_u = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください",
                                         min_value=0, max_value=1999,
                                         value=candidate_init[num_init][1])

        test_num = form.number_input(f"解析する画像枚数を入力してください(1～{len(base_images)-idx})",
                                     1, len(base_images)-idx,
                                     len(base_images)-idx)
        submit = form.form_submit_button("カルマンフィルタ実行")

        # デバッグ用
        # ----------------------------------------------------
        # st.sidebar.write(f"x_init  ={x_init}")
        # st.sidebar.write(f"y_init_l={y_init_l}")
        # st.sidebar.write(f"y_init_u={y_init_u}")
        # st.sidebar.write(f"candidate_init={candidate_init}")
        # ----------------------------------------------------

        if submit:
            # outputディレクトリの準備
            os.makedirs(outpath, exist_ok=True)

            # 画像キロ程情報の処理
            # とりあえず、一度でも画像キロ程jsonを作成していればスキップする
            # 画像キロ程jsonの削除は手動対応…
            if not os.path.exists(f"{config.tdm_dir}/{dir_area}.json"):
                with st.spinner("検測車マスタデータからキロ程情報をリンクしています（お待ちください）"):
                    helpers.get_img2kiro(config, dir_area, images_path, target_dir, base_images, csv_files)

            # 選択画像における処理結果が既に存在しているかチェック
            # trolley_dict = helpers.load_shelves(rail_fpath, camera_num, base_images, idx)
            df_csv = helpers.result_csv_load(config, rail_fpath)
            # df_csvで、指定された条件に一致する行を特定する用の条件
            image_name = base_images[idx].split('/')[-1]
            condition = (
                (df_csv['measurement_area'] == dir_area) &
                (df_csv['camera_num'] == camera_num) &
                (df_csv['image_name'] == image_name) &
                (df_csv['trolley_id'] == trolley_id)
            )

            status_view = st.empty()
            status_view.write(f"{idx+1}/{len(base_images)}枚目の画像を解析します🔍")
            progress_bar = log_view.progress(0)
            # if trolley_id in trolley_dict.keys():
            if len(df_csv.loc[condition, :]) > 0:
                st.warning('既に同じ画像での結果が存在していますが、上書きして実行します')

                if st.button('計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                    st.stop()
                    st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

                with st.spinner("カルマンフィルタ実行中"):
                    track_kalman(
                            outpath,
                            camera_num,
                            base_images,
                            df_csv,
                            idx,
                            test_num,
                            trolley_id,
                            x_init,
                            y_init_u,
                            y_init_l,
                            status_view,
                            progress_bar,
                            kiro_data
                        )
                    camera_view.success("# 解析が終了しました")
            else:
                if st.button(f'計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                    st.stop()
                    st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

                with st.spinner("カルマンフィルタ実行中"):
                    track_kalman(
                        outpath,
                        camera_num,
                        base_images,
                        df_csv,
                        idx,
                        test_num,
                        trolley_id,
                        x_init,
                        y_init_u,
                        y_init_l,
                        status_view,
                        progress_bar,
                        kiro_data
                    )
                    camera_view.success("# 解析が終了しました")

    # 解析結果があるかをサイドバーに表示する
    st.sidebar.markdown("# 参考 結果有無👇")
    csv_downloader = st.sidebar.checkbox("CSVファイルをダウンロード")
    if csv_downloader:
        with st.spinner("一生懸命CSVを準備しています🐭"):
            df_csv = helpers.rail_csv_concat(outpath)
            csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
        try:
            with open(rail_fpath) as csv:
                st.sidebar.download_button(
                    label="CSVファイルをダウンロード",
                    data=csv_data,
                    file_name=dir_area + "_" + camera_num + "_output.csv",
                    mime="text/csv"
                )
        except Exception as e:
            st.sidebar.error("解析後にCSVをダウンロードできます")
            # st.sidebar.write(f"Error> {e}")
    idx_result_check = st.sidebar.checkbox("解析済みインデックスを表示する", value=True)
    if idx_result_check:
        df = helpers.check_camera_dirs_addIdxLen(dir_area, config)
    else:
        df = helpers.check_camera_dirs(dir_area, config)
    st.sidebar.dataframe(df)
    csv_delete_btn = st.sidebar.button("結果CSVデータを削除する")
    if csv_delete_btn:
        if os.path.exists(outpath):
            # helpers.file_remove(rail_fpath)
            helpers.imgs_dir_remove(outpath)
            log_view.error("CSVファイルを削除しました")
        else:
            log_view.error("削除するCSVファイルがありません")

    # st.write("画像ファイルリスト👇")
    # # image_list_for_view = []
    # for idx, image_path in enumerate(base_images):
    #     image_name = image_path.split('/')[-1]
    #     # image_list_for_view.append([idx + 1, image_name])
    #     st.text(f"{idx + 1},{image_name}")


if __name__ == "__main__":
    config = appProperties('config.yml')
    ohc_wear_analysis(config)
