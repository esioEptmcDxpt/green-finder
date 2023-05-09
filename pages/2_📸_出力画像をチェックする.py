import shelve
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def result_image_view():
    # マルチページの設定
    st.set_page_config(page_title="結果画像ビューワー")
    st.sidebar.header("結果画像閲覧システム")
    
    # メインページのコンテナを配置する
    main_view = st.container()
    camera_view = st.empty()
    
    # フォルダ直下の画像保管用ディレクトリのリスト
    images_path = helpers.list_imagespath(config.image_dir)
    
    # 画像保管線区の選択
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
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num    # (長山)"/camera_num"を追加
    
    # outputディレクトリの設定
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num
    
    # 既存のresultがあれば読み込み
    rail = shelve.open(outpath + "/rail.shelve")
    
    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)
    
    # ファイルインデックスを指定する
    st.sidebar.markdown("# ファイルのインデックスを指定してください")
    idx = st.sidebar.number_input(f"インデックス(0～{len(base_images)-1}で指定)",
                                  min_value=0,
                                  max_value=len(base_images) - 1)
    
    # メインページにカメラ画像を表示する
    col1, col2 = camera_view.columns(2)
    
    with col1:
        st.write("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images, idx)
        st.write(f"カメラ:{camera_name} {idx + 1}番目の画像です")
        st.image(cam_img)
    with col2:
        st.write("🖥️解析結果")
        st.write("解析結果を表示しています")
        out_img = vis.out_image_load(rail, camera_num, base_images, idx)
        if not out_img:
            st.error("解析結果がありません")
        st.image(out_img)
    
    rail.close()
    

if __name__ == "__main__":
    config = appProperties('config.yml')
    result_image_view()

