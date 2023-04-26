import os
import shelve
import streamlit as st
import time    # デバッグ用、後で削除する
import numpy as np
import datetime
import src.helpers as helpers
import src.visualize as vis
from src.kalman_calc import track_kalman
from src.similar_pixel_calc import track_pixel
# import src.similar_pixel_calc as sim_pix    # 摩耗判定システム機能
import src.utilsST_01 as utlst    # 移行が完了したら削除する
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
    vis.dir_area_view_JP(config, dir_area, main_view)
    
    # 解析対象のカメラ番号を選択する
    camera_num = st.sidebar.selectbox("解析対象のカメラを選択してください", (config.camera_types))
    
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
    
    # base_imagesと同じ長さの空のdictionaryを作成してrailを初期化
    blankdict_size = [{}] * len(base_images)
    rail[camera_num] = dict(zip(base_images, blankdict_size))
    
    # ファイルインデックスを指定する
    st.sidebar.markdown("# ファイルのインデックスを指定してください")
    idx = st.sidebar.number_input(f"インデックス(0～{len(base_images)-1}で指定)",
                                  min_value=0,
                                  max_value=len(base_images) - 1)
    
    # メインページにカメラ画像を表示する
    col1, col2, col3 = camera_view.columns(3)
    
    with col1:
        st.header("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images[idx], main_view)
        st.write(f"カメラ:{helpers.camera_num_to_name(camera_num, config)} {idx + 1}番目の画像です")
        st.image(cam_img)
    with col2:
        st.header("🖥️解析結果")
        st.write("解析結果を表示しています")
        # to be implemented
    with col3:
        st.header("📈メモリ付画像")
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
        submit = form_px.form_submit_button("ピクセルトレース実行")
        if submit:
            with st.spinner("ピクセルトレース実行中"):
                track_pixel(
                    rail,
                    camera_num,
                    base_images,
                    idx,
                    trolley_id,
                    xin,
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
    rail.close()

    return
    
    
if __name__ == "__main__":
    config = appProperties('config.yml')
    ohc_wear_analysis(config)
