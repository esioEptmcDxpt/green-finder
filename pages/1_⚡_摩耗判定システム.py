import os
import shelve
import streamlit as st
import numpy as np
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
    
    # フォルダ直下の画像保管用ディレクトリのリスト
    images_path = helpers.list_imagespath(config.image_dir)
    
    # 画像保管線区の選択
    dir_area = st.sidebar.selectbox("線区のフォルダ名を選択してください", images_path)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")
    
    # 選択された線区情報を表示する
    vis.rail_info_view(dir_area, config, main_view)
    
    # 解析対象のカメラ番号を選択する
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    zip(config.camera_names, config.camera_types)
                    )[0]
    camera_num = config.camera_name_to_type[camera_name]
    
    # 解析対象の画像フォルダを指定
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num    # (長山)"/camera_num"を追加
    
    # outputディレクトリの準備
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num
    os.makedirs(outpath, exist_ok=True)
    
    # 既存のresultがあれば読み込み、なければ作成
    rail = shelve.open(outpath + "/rail.shelve", writeback=True)
    rail["name"] = dir_area
    
    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)
    
    # railに書き込めるように初期化する
    # 解析結果が既にある場合は初期化しない
    helpers.rail_camera_initialize(rail, camera_num, base_images, config.trolley_ids)
    
    # ファイルインデックスを指定する
    st.sidebar.markdown("# ファイルのインデックスを指定してください")
    idx = st.sidebar.number_input(f"インデックス(0～{len(base_images)-1}で指定)",
                                  min_value=0,
                                  max_value=len(base_images) - 1)
    
    # メインページにカメラ画像を表示する
    col1, col2, col3 = camera_view.columns(3)
    
    with col1:
        st.write("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images, idx)
        st.write(f"カメラ:{camera_name} {idx + 1}番目の画像")
        st.image(cam_img)
    with col2:
        st.write("🖥️解析結果")
        st.write("解析結果を表示中")
        
        # vis.out_image_loadだと遅い？？
        # image_path = base_images[idx]
        # try:
        #     out_img = rail[camera_num][image_path]['out_image']
        # except Exception as e:
        #     out_img = []
            
        # out_img = vis.out_image_load(rail, camera_num, base_images, idx)
        # st.image(out_img)
    with col3:
        st.write("📈メモリ付画像")
        st.write("初期値入力用の画像")
        fig = vis.plot_fig(base_images, idx)
        st.pyplot(fig)
    
    trace_method = st.sidebar.radio(
        "システムを選択", 
        ("ピクセルトレース", "カルマンフィルタ")
    )
    
    # ピクセルトレースを実行
    if trace_method == "ピクセルトレース":
        form_px = st.sidebar.form(key="similar_pixel_init")
        xin = form_px.number_input("トロリ線の中心位置を入力(0～2048)", 0, 2048, 1024)
        test_num = form_px.number_input(f"解析する画像枚数を入力(1～{len(base_images)-idx})", 1, len(base_images)-idx, len(base_images)-idx)
        submit = form_px.form_submit_button("ピクセルトレース実行")
        if submit:
            with st.spinner("ピクセルトレース実行中"):
                track_pixel(
                    rail,
                    camera_num,
                    base_images,
                    idx,
                    xin,
                    test_num,
                )
    # カルマンフィルタを実行
    elif trace_method == "カルマンフィルタ":
        # カルマンフィルタの初期値設定
        form = st.sidebar.form(key="kalman_init")
        trolley_id = form.selectbox("トロリ線のIDを入力してください", ("trolley1", "trolley2"))
        x_init = form.number_input("横方向の初期座標を入力してください", 0, 999)
        y_init_u = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください", 0, 1999)
        y_init_l = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください", 0, 1999)
        submit = form.form_submit_button("カルマンフィルタ実行")

        if submit:
            with st.spinner("カルマンフィルタ実行中"):
                track_kalman(
                    rail,
                    camera_num,
                    base_images,
                    idx,
                    trolley_id,
                    x_init,
                    y_init_u,
                    y_init_l,
                )
    # st.write("rail.close start")
    # rail.close()
    # st.write("rail.close end")

    
if __name__ == "__main__":
    config = appProperties('config.yml')
    ohc_wear_analysis(config)
