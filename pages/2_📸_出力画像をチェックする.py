import streamlit as st
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def result_image_view(config):
    """ 結果画像を表示させる用のページ
    Args:
        config: ymlファイルを読み込んだ設定値
    """
    # マルチページの設定
    st.set_page_config(page_title="結果画像ビューワー")
    st.sidebar.header("結果画像閲覧システム")

    # メインページのコンテナを配置する
    main_view = st.container()
    # camera_view = st.empty()
    row1 = st.container()
    row2 = st.container()

    # フォルダ直下の画像保管用ディレクトリのリスト
    # images_path = helpers.list_imagespath(config.image_dir)
    # 他ページでの結果を反映するためnonCacheを使用
    images_path = helpers.list_imagespath_nonCache(config.image_dir)

    # 画像保管線区の選択
    st.sidebar.markdown("# ___Step1___ 線区を選択")

    # 検索ボックスによる対象フォルダの絞り込み
    dir_search = st.sidebar.checkbox("検索ボックス表示", value=True)
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

    # メインページにカメラ画像を表示する
    # col1, col2 = camera_view.columns(2)

    st.sidebar.markdown("# ___Step3___ 連結した画像を表示する")
    form_concat = st.sidebar.form(key="img_concat_setup")
    form_concat.markdown("⚠ 連結枚数が多いとエラーになります")
    concat_nums = form_concat.number_input("連結する枚数を入力", 1, len(base_images), 5)
    font_size = form_concat.number_input("画像インデックス文字のサイズを入力", 1, 1000, 50)
    submit = form_concat.form_submit_button("連結画像を作成する")
    if submit:
        with row1:
            st.write("📸カメラ画像")
            # cam_img = vis.ohc_image_load(base_images[idx])
            cam_img = vis.ohc_img_concat(base_images, idx, concat_nums, font_size)
            st.write(f"カメラ:{camera_name} {idx + 1}～{idx + concat_nums}までの画像")
            st.image(cam_img)
        with row2:
            st.write("🖥️解析結果")
            status_view = st.empty()
            status_view.write("解析結果を表示中")
            st.write("解析結果を表示します")
            progress_bar = st.progress(0)
            try:
                out_img = vis.out_image_concat(
                    rail_fpath,
                    dir_area,
                    camera_num,
                    base_images,
                    idx,
                    concat_nums,
                    font_size,
                    config,
                    status_view,
                    progress_bar,
                )
            except Exception as e:
                out_img = []
                st.write(e)
            if not out_img:
                st.error("解析結果がありません")
            else:
                st.image(out_img)
    else:
        row1.error("サイドバーで条件を指定して画像を作成してください")

    # 解析結果があるかをサイドバーに表示する
    st.sidebar.markdown("# 参考 結果有無👇")
    try:
        with open(rail_fpath) as csv:
            st.sidebar.download_button(
                label="CSVファイルをダウンロード",
                data=csv,
                file_name=dir_area + "_" + camera_num + "_output.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.sidebar.error("CSVファイルがありません")
        st.sidebar.write(f"Error> {e}")
    csv_delete_btn = st.sidebar.button("結果CSVデータを削除する")
    if csv_delete_btn:
        if os.path.exists(rail_fpath):
            helpers.file_remove(rail_fpath)
            log_view.error("CSVファイルを削除しました")
        else:
            log_view.error("削除するCSVファイルがありません")
    df = helpers.check_camera_dirs(dir_area, config)
    st.sidebar.dataframe(df)


if __name__ == "__main__":
    config = appProperties('config.yml')
    result_image_view(config)
