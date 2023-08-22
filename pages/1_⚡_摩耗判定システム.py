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
    st.set_page_config(page_title="トロリ線摩耗検出システム")
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
    dir_search = st.sidebar.checkbox("検索ボックス表示")
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
    os.makedirs(outpath, exist_ok=True)

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # 結果保存用のshelveファイル(rail)の保存パスを指定
    rail_fpath = outpath + "/rail.shelve"
    # with shelve.open(rail_fpath) as rail:
    #     # 線区名を記録する
    #     rail["name"] = dir_area
    #     # 解析結果が既にある場合は初期化しない
    #     helpers.rail_camera_initialize(rail, camera_num, base_images, config.trolley_ids)

    # ファイルインデックスを指定する
    if not base_images:
        st.sidebar.error("画像がありません")
        st.stop()
    else:
        idx = st.sidebar.number_input(f"インデックス(1～{len(base_images)}で指定)",
                                      min_value=1,
                                      max_value=len(base_images)) - 1
        st.sidebar.write(f"ファイル名:{base_images[idx]}")

    # メインページにカメラ画像を表示する
    col1, col2 = camera_view.columns(2)

    with col1:
        st.write("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images[idx])
        st.write(f"カメラ:{camera_name} {idx + 1}番目の画像")
        st.image(cam_img)
    with col2:
        st.write("🖥️解析結果")
        st.write("解析結果を表示中")
        try:
            out_img = vis.out_image_load(rail_fpath, camera_num, base_images[idx], cam_img, config)
        except Exception as e:
            out_img = []
        if not out_img:
            st.error("解析結果がありません")
        else:
            st.image(out_img)

    st.sidebar.markdown("# ___Step3___ 解析を実行する")
    trace_method = st.sidebar.radio(
        "システムを選択",
        ("ピクセルトレース", "カルマンフィルタ")
    )

    # メモリ付き画像を表示
    support_line = st.sidebar.checkbox("補助線を使用")
    if support_line:
        form_support_line = st.sidebar.form(key="support_line_form")
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
        if spline_submit:
            fig = vis.plot_fig(base_images[idx], vert_pos, hori_pos)
            log_view.pyplot(fig)
    else:
        hori_pos = 0
        vert_pos = [0, 0]
        if st.sidebar.button("📈初期値入力用メモリ付画像を表示する"):
            fig = vis.plot_fig(base_images[idx], vert_pos, hori_pos)
            log_view.pyplot(fig)

    # ピクセルトレースを実行
    if trace_method == "ピクセルトレース":
        form_px = st.sidebar.form(key="similar_pixel_init")
        xin = form_px.number_input("トロリ線の中心位置を入力(0～2048)", 0, 2048, 1024)
        test_num = form_px.number_input(f"解析する画像枚数を入力(1～{len(base_images)-idx})", 1, len(base_images)-idx, len(base_images)-idx)
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
        form = st.sidebar.form(key="kalman_init")
        trolley_id = form.selectbox("トロリ線のIDを入力してください", ("trolley1", "trolley2", "trolley3"))
        x_init = form.number_input("横方向の初期座標を入力してください", 0, 999)
        y_init_l = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください", 0, 1999)
        y_init_u = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください", 0, 1999)
        submit = form.form_submit_button("カルマンフィルタ実行")

        if submit:
            # outputディレクトリの準備
            os.makedirs(outpath, exist_ok=True)

            # shelveファイルの初期化
            with shelve.open(rail_fpath) as rail:
                # 線区名を記録する
                rail["name"] = dir_area
                # 解析結果が既にある場合は初期化しない
                helpers.rail_camera_initialize(rail, camera_num, base_images, config.trolley_ids)

            # 選択画像における処理結果が既に存在しているかチェック
            trolley_dict = helpers.load_shelves(rail_fpath, camera_num, base_images, idx)

            if trolley_id in trolley_dict.keys():
                st.warning('既に同じ画像での結果が存在していますが、初期化して実行します')

                if st.button('計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                    st.stop()
                    st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

                with st.spinner("カルマンフィルタ実行中"):
                    track_kalman(
                            rail_fpath,
                            camera_num,
                            base_images,
                            idx,
                            trolley_id,
                            x_init,
                            y_init_u,
                            y_init_l,
                        )
            else:
                if st.button(f'計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                    st.stop()
                    st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

                with st.spinner("カルマンフィルタ実行中"):
                    track_kalman(
                        rail_fpath,
                        camera_num,
                        base_images,
                        idx,
                        trolley_id,
                        x_init,
                        y_init_u,
                        y_init_l,
                    )

    # 解析結果があるかをサイドバーに表示する
    st.sidebar.markdown("# 参考 結果有無👇")
    df = helpers.check_camera_dirs(dir_area, config)
    st.sidebar.dataframe(df)


if __name__ == "__main__":
    config = appProperties('config.yml')
    ohc_wear_analysis(config)
