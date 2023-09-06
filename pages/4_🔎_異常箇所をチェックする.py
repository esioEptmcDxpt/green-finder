import streamlit as st
from PIL import Image
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def eda_tool(config):
    # マルチページの設定
    st.set_page_config(page_title="異常値箇所チェック")
    st.sidebar.header("異常箇所チェックツール")
    
    # メインページのコンテナを配置する
    main_view = st.container()
    
    # 作成中メッセージ
    main_view.warning("# 一生懸命プログラムを作成中です")
    img_sorry = Image.open('icons/sorry_panda.jpg')
    main_view.image(img_sorry, caption='We are working very hard on the program!')
    
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

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # 結果保存用のCSVファイル(rail)の保存パスを指定
    # rail_fpath = outpath + "/rail.shelve"
    rail_fpath = outpath + "/rail.csv"
        
    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    eda_tool(config)