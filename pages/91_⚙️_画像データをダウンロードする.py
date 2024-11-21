import os
import datetime
import copy
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def download_images(config, s3_rail_path):
    """ 指定された線区フォルダの画像データをS3からダウンロード
    Args:
        config(object): 設定ファイル
        s3_rail_path(str): ダウンロード対象のS3 prefix
    """
    dt01 = datetime.datetime.now()
    with st.spinner("S3からダウンロード中"):
        # シングルスレッドでのダウンロード
        # helpers.download_dir(config.image_dir + "/" + s3_rail_path + "/", "./")

        # マルチスレッド化してダウンロード
        with ThreadPoolExecutor(max_workers=10) as executor:
            for folder in config.camera_types:
                s3_dir = config.image_dir + "/" + s3_rail_path + "/" + folder + "/"
                ebs_dir = "./"
                executor.submit(helpers.download_dir, s3_dir, ebs_dir)

    st.success("TISにダウンロードしました")
    dt02 = datetime.datetime.now()
    prc_time = dt02 - dt01
    st.write(f"(参考)処理時間> {prc_time}")


def delete_images(config, ebs_rail_path):
    """ システム上に保存されている画像データを削除する
    Args:
        config(object): 設定ファイル
        ebs_rail_path(str): ダウンロード対象のパス
    """
    with st.spinner("TTSの画像を削除中"):
        helpers.imgs_dir_remove(config.image_dir + "/" + ebs_rail_path + "/")
    st.warning("TTSの画像データを削除しました")


def data_loader(config):
    # マルチページの設定
    st.set_page_config(page_title="画像データダウンロード", layout="wide")

    modes = ("画像をダウンロード", "不要なファイルを削除")
    mode = st.sidebar.radio("操作方法を選択", modes)

    if modes.index(mode) == 0:
        mode_info = "# 画像データをダウンロード"
        mode_type = "ダウンロード"
    elif modes.index(mode) == 1:
        mode_info = "# 不要な画像を削除する"
        mode_type = "削除"
    else:
        st.error("予期せぬエラーが発生しました")

    # 線区を選択
    st.sidebar.write(mode_info)
    is_search_box_visible = st.sidebar.checkbox("検索ボックスを表示する", key="search_check")
    if is_search_box_visible:
        # 線名を指定
        rail_key_jpn = st.sidebar.selectbox("線区を選択", list(config.rail_names.values()), key="rail_key")
        rail_key = [key for key, value in config.rail_names.items() if value == rail_key_jpn][0]
        # 線別を指定
        rail_type_jpn = st.sidebar.selectbox("線別を選択", list(config.rail_type_names.values()), key="type_key")
        rail_type = [key for key, value in config.rail_type_names.items() if value == rail_type_jpn][0]
        if modes.index(mode) == 0:
            rail_list = helpers.get_s3_dir_list(config.image_dir)
        elif modes.index(mode) == 1:
            rail_list = helpers.list_imagespath_nonCache(config.image_dir)
        target_rail_list = [item for item in rail_list if item.split('_')[0] == rail_key and rail_type in item]
    else:
        if modes.index(mode) == 0:
            target_rail_list = helpers.get_s3_dir_list(config.image_dir)
        elif modes.index(mode) == 1:
            target_rail_list = helpers.list_imagespath_nonCache(config.image_dir)
        else:
            target_rail_list = []

    # st.write(target_rail_list)

    st.sidebar.write(f"## ___Step1___ {mode_type}する線区を選択する")
    rail_path = st.sidebar.selectbox("線区フォルダ", target_rail_list, key="rail_path")
    info_view = st.container()
    if target_rail_list:
        st.sidebar.write("## ___Step2___ 選んだ線区をチェック")
        st.sidebar.write("___メイン画面の線区表示をチェック↗___")
        st.warning("<参考用>線区フォルダの情報👇")
        # 解析対象のカメラ番号を選択する
        camera_name = st.sidebar.selectbox(
                        "確認したいカメラを選択",
                        zip(config.camera_names, config.camera_types)
                        )[0]
        camera_path = config.camera_name_to_type[camera_name]
        if modes.index(mode) == 0:
            # 画像リスト
            image_list = helpers.get_s3_image_list(config.image_dir + "/" + rail_path + "/" + camera_path)
        elif modes.index(mode) == 1:
            base_images = helpers.list_images(config.image_dir + "/" + rail_path + "/" + camera_path)
            image_list = [os.path.basename(path) for path in base_images]
        if image_list:
            with st.sidebar.expander("画像リスト", expanded=False):
                st.write(image_list, key="S3_image_list")
        else:
            st.sidebar.warning("画像がありません")

        vis.rail_info_view(rail_path, config, info_view)

        st.sidebar.write("## ___Step3___ 問題なければ👇を押す")
        if st.sidebar.button(f"線区フォルダのデータを{mode_type}する"):
            if modes.index(mode) == 0:
                download_images(config, rail_path)
            elif modes.index(mode) == 1:
                delete_images(config, rail_path)
    else:
        info_view.error(f"この条件では{mode_type}できる画像データがありません")
        info_view.warning("別の線区フォルダを選択してください")

    st.sidebar.write('---')

    # S3とEBSのimgsディレクトリ内の線区リストを表示する
    st.header("ダウンロードされたデータのチェック")

    df_key = st.text_input("検索キーワード(線区名を英語で入力してください)")
    col1, col2 = st.columns(2)
    start_date = col1.date_input("期間を指定(始)", datetime.date(2024,4,1))
    end_date = col2.date_input("期間を指定(終)", datetime.date(2024,6,30))
    try:
        if modes.index(mode) == 0:
            EBS_rail_list = helpers.list_imagespath_nonCache(config.image_dir)
            df = helpers.S3_EBS_imgs_dir_Compare(target_rail_list, EBS_rail_list, df_key, start_date, end_date)
        else:
            S3_rail_list = helpers.get_s3_dir_list(config.image_dir)
            df = helpers.S3_EBS_imgs_dir_Compare(S3_rail_list, target_rail_list, df_key, start_date, end_date)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error("該当するデータがありません")
        st.error(f"Error message> {e}")


if __name__ == "__main__":
    config = appProperties('config.yml')
    data_loader(config)
