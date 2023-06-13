import os
import streamlit as st
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def data_loader(config):
    # マルチページの設定
    st.set_page_config(page_title="画像データダウンロード")
    st.sidebar.header("画像データダウンロード")
    
    col1, col2 = st.columns(2)
    with col1:
        col1_cont = st.container()
    with col2:
        col2_cont = st.container()
    
    with col1_cont:
        # S3の情報を表示する
        st.header("S3アップ済ファイル")
        
        # 線区
        rail_list = helpers.get_s3_dir_list(config.image_dir)
        s3_rail_path = st.selectbox("S3> 線区フォルダ", rail_list)

        # カメラ
        s3_camera_list = helpers.get_s3_dir_list(config.image_dir + "/" + s3_rail_path)
        s3_camera_path = st.selectbox("S3> カメラフォルダ", s3_camera_list)

        # 画像リスト
        image_list = helpers.get_s3_image_list(config.image_dir + "/"  + s3_rail_path + "/" + s3_camera_path)
        st.selectbox("S3> 画像リスト", image_list)

        # S3からダウンロード
        if st.button("線区フォルダのデータをダウンロードする"):
            with st.spinner("S3からダウンロード中"):
                # st.write(f's3_path:{config.image_dir + "/" + s3_rail_path + "/"}')
                # st.write(f'local_path:{config.image_dir + "/"}')
                # helpers.download_dir(config.image_dir + "/" + s3_rail_path + "/", config.image_dir + "/")
                helpers.download_dir(config.image_dir + "/" + s3_rail_path + "/", "./")
            st.success("TTSにダウンロードしました")


    with col2_cont:
        # EBSの情報を表示する
        st.header("TTSダウンロード済")

        # 線区
        # フォルダ直下の画像保管用ディレクトリのリスト
        images_path = helpers.list_imagespath_nonCache(config.image_dir)
        ebs_rail_path = st.selectbox("TTS> 線区フォルダ", images_path)

        if images_path:
            # カメラ
            ebs_camera_list = helpers.list_imagespath(config.image_dir + "/" + ebs_rail_path)
            ebs_camera_path = st.selectbox("TTS> カメラフォルダ", ebs_camera_list)

            # 画像リスト
            base_images = helpers.list_images(config.image_dir + "/" + ebs_rail_path + "/" + ebs_camera_path)
            image_list = [os.path.basename(path) for path in base_images]
            image_path = st.selectbox("TTS> 画像リスト", image_list)

            # EBSから削除する
            if st.button("線区フォルダのデータを削除する"):
                helpers.imgs_dir_remove(config.image_dir + "/" + ebs_rail_path + "/")
                st.warning("TTSの画像データを削除しました")
        else:
            st.error("TTSに線区データがありません")
            st.warning("S3からダウンロードしてください")

    # S3とEBSのimgsディレクトリ内の線区リストを表示する
    st.header("ダウンロードされたデータのチェック")
    try:
        df = helpers.S3_EBS_imgs_dir_Compare(rail_list, images_path)
        st.dataframe(df)
    except Exception as e:
        st.error("該当するデータがありません")
        st.error(f"Error> {e}")


if __name__ == "__main__":
    config = appProperties('config.yml')
    data_loader(config)
