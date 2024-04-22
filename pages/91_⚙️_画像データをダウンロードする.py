import os
import datetime
import copy
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def data_loader(config):
    # マルチページの設定
    st.set_page_config(page_title="画像データダウンロード", layout="wide")
    st.sidebar.header("画像データダウンロード")

    col1, col2 = st.columns(2)
    with col1:
        col1_cont = st.container()
    with col2:
        col2_cont = st.container()

    with col1_cont:
        # S3の情報を表示する
        st.header("S3アップ済ファイル")
        s3_search = st.checkbox("検索ボックスを表示する", key="S3_search_check")

        if s3_search:
            # 検索用
            st.write("検索用👇")
            # 線名
            rail_key_jpn = st.selectbox("線区", list(config.rail_names.values()), key="S3_rail_key")
            rail_key = [key for key, value in config.rail_names.items() if value == rail_key_jpn][0]
            # 線別
            rail_type_jpn = st.selectbox("線別", list(config.rail_type_names.values()), key="S3_type_key")
            rail_type = [key for key, value in config.rail_type_names.items() if value == rail_type_jpn][0]
            
            # 線区
            rail_list_s3 = helpers.get_s3_dir_list(config.image_dir)
            target_rail_list_s3 = [item for item in rail_list_s3 if item.split('_')[0] == rail_key and rail_type in item]
            
        else:
            # 線区
            rail_list_s3 = helpers.get_s3_dir_list(config.image_dir)
            target_rail_list_s3 = helpers.get_s3_dir_list(config.image_dir)

        st.success("ダウンロード先を指定👇")
        s3_rail_path = st.selectbox("<対象>線区フォルダ", target_rail_list_s3, key="S3_rail_path")

        if target_rail_list_s3:
            # S3からダウンロード
            if st.button("線区フォルダのデータをダウンロードする"):
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

                st.success("TTSにダウンロードしました")
                dt02 = datetime.datetime.now()
                prc_time = dt02 - dt01
                st.write(f"(参考)処理時間> {prc_time}")

            st.warning("<参考用>線区フォルダの情報👇")
            # カメラ
            s3_camera_list = helpers.get_s3_dir_list(config.image_dir + "/" + s3_rail_path)
            s3_camera_path = st.selectbox("<参考>カメラフォルダ", s3_camera_list, key="S3_camera_path")

            # 画像リスト
            image_list = helpers.get_s3_image_list(config.image_dir + "/" + s3_rail_path + "/" + s3_camera_path)
            if image_list:
                st.selectbox("画像リスト", image_list, key="S3_image_list")
            else:
                st.warning("画像がありません")
        else:
            st.error("S3に線区データがありません")
            st.warning("別のフォルダを選択してください")

    with col2_cont:
        # EBSの情報を表示する
        st.header("TTSダウンロード済")
        ebs_search = st.checkbox("検索ボックスを表示する", key="EBS_search_check")

        if ebs_search:
            # 検索用
            st.write("検索用👇")
            # 線名
            dir_key_jpn = st.selectbox("線区", list(config.rail_names.values()), key="EBS_rail_key")
            dir_key = [key for key, value in config.rail_names.items() if value == dir_key_jpn][0]
            # 線別
            dir_type_jpn = st.selectbox("線別", list(config.rail_type_names.values()), key="EBS_type_key")
            dir_type = [key for key, value in config.rail_type_names.items() if value == dir_type_jpn][0]

            # 線区
            # フォルダ直下の画像保管用ディレクトリのリスト
            images_path = helpers.list_imagespath_nonCache(config.image_dir)
            target_images_path = [item for item in images_path if item.split('_')[0] == dir_key and dir_type in item]

        else:
            # 線区
            # フォルダ直下の画像保管用ディレクトリのリスト
            images_path = helpers.list_imagespath_nonCache(config.image_dir)
            target_images_path = helpers.list_imagespath_nonCache(config.image_dir)
        
        st.error("削除する対象を指定👇")
        ebs_rail_path = st.selectbox("<対象>線区フォルダ", target_images_path, key="EBS_rail_path")

        if target_images_path:
            # EBSから削除する
            if st.button("線区フォルダのデータを削除する"):
                with st.spinner("TTSの画像を削除中"):
                    helpers.imgs_dir_remove(config.image_dir + "/" + ebs_rail_path + "/")
                st.warning("TTSの画像データを削除しました")
            
            st.warning("<参考用>線区フォルダの情報👇")
            # カメラ
            ebs_camera_list = helpers.list_imagespath(config.image_dir + "/" + ebs_rail_path)
            ebs_camera_path = st.selectbox("カメラフォルダ", ebs_camera_list, key="EBS_camera_path")

            # 画像リスト
            base_images = helpers.list_images(config.image_dir + "/" + ebs_rail_path + "/" + ebs_camera_path)
            image_list = [os.path.basename(path) for path in base_images]
            st.selectbox("画像リスト", image_list, key="EBS_image_path")

            
        else:
            st.error("TTSに線区データがありません")
            st.warning("S3からダウンロードしてください")

    # S3とEBSのimgsディレクトリ内の線区リストを表示する
    st.header("ダウンロードされたデータのチェック")
    
    df_key = st.text_input("検索キーワード(線区名を英語で入力してください)")
    try:
        df = helpers.S3_EBS_imgs_dir_Compare(rail_list_s3, images_path, df_key)
        st.dataframe(df)
    except Exception as e:
        st.error("該当するデータがありません")
        st.error(f"Error> {e}")


if __name__ == "__main__":
    config = appProperties('config.yml')
    data_loader(config)
