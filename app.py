# -*- coding: utf-8 -*-
import os
import shelve
import streamlit as st
import src.helpers as helpers
import src.visualize as vis
from src.kalman_calc import track_kalman
from src.config import appProperties


def main(config):
    readme_text = st.markdown("## 左のメニューから操作してください")
    st.sidebar.title("What to do")
    app_mode = st.sidebar.selectbox("Choose the app mode",
                                    ["ガイド（作成中）", "カルマンフィルタ実行", "カルマンフィルタ実行結果確認"])
    if app_mode == "ガイド（作成中）":
        st.sidebar.success('実行するには"カルマンフィルタ実行"を選択してください')
    elif app_mode == "カルマンフィルタ実行結果確認":
        readme_text.empty()
    elif app_mode == "カルマンフィルタ実行":
        st.sidebar.markdown("# 線区・カメラの選択")

        # フォルダ直下の画像保管用ディレクトリのリスト
        images_path = helpers.list_imagespath(config.image_dir)

        # 画像保管線区の選択
        dir_area = st.sidebar.selectbox("imagesフォルダ直下のフォルダ名を選択してください", images_path)
        if dir_area is None:
            st.error("No frames fit the criteria. Please select different label or number.")

        # 解析対象のカメラ番号を選択する
        camera_num = st.sidebar.selectbox("解析対象のカメラを選択してください", (config.camera_types))

        # 解析対象の画像フォルダを指定
        target_dir = config.image_dir + "/" + dir_area

        # outputディレクトリの準備
        outpath = config.output_dir + "/" + dir_area + "/" + camera_num
        os.makedirs(outpath, exist_ok=True)

        # 既存のresultがあれば読み込み、なければ作成
        rail = shelve.open(outpath + "/rail.shelve", writeback=True)
        rail["name"] = dir_area

        # imagesフォルダ内の画像一覧取得
        base_images = helpers.list_images(target_dir)

        # base_imagesと同じ長さの空のdictionaryを作成して初期化
        blankdict_size = [{}] * len(base_images)
        rail[camera_num] = dict(zip(base_images, blankdict_size))

        # ファイルインデックスを指定する
        st.sidebar.markdown("# ファイルのインデックスを指定してください")
        idx = st.sidebar.number_input("Image index",
                                      min_value=0,
                                      max_value=len(base_images) - 1)

        # メインページを等分で分割
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### 車モニ画像")
            fig = vis.plot_fig(base_images, idx)
            st.pyplot(fig)

        with col2:
            st.markdown("### 摩耗検出結果")
            # to be implemented

        with col3:
            st.markdown("#### (参考)画像左端の輝度値")
            # to be implemented

        st.sidebar.markdown("# カルマンフィルタの初期値設定")

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


if __name__ == '__main__':
    config = appProperties('config.yml')
    main(config)
