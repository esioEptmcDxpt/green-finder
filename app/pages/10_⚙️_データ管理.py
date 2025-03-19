import os
import datetime
import copy
import streamlit as st
from concurrent.futures import ThreadPoolExecutor
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties
import src.auth as auth


@st.dialog("技セ・MCを選択")
def set_office(_config, office_default):
    office_names = helpers.get_office_names_jp(_config)
    office_default_jp = _config.office_names[office_default]["name"]
    office_names_default_index = office_names.index(office_default_jp)
    office_name_jp = st.selectbox("技セを選択", office_names, index=office_names_default_index)
    office_name = helpers.get_office_name(_config, office_name_jp)
    mc_name_jp = st.selectbox("MCを選択", helpers.get_mc_names_jp(_config, office_name_jp))
    mc_name = helpers.get_mc_name(_config, office_name_jp, mc_name_jp)
    if st.button("設定"):
        st.session_state.office = f"{office_name}/{mc_name}"
        st.rerun()


def download_images(config, office, s3_rail_path):
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
                s3_dir = f"{config.image_dir}/{office}/{s3_rail_path}/{folder}/"
                ebs_dir = "./"
                executor.submit(helpers.download_dir, config.bucket, s3_dir, ebs_dir)

    st.success("CISにダウンロードしました")
    dt02 = datetime.datetime.now()
    prc_time = dt02 - dt01
    st.write(f"(参考)処理時間> {prc_time}")


def delete_images(config, office, ebs_rail_path):
    """ システム上に保存されている画像データを削除する
    Args:
        config(object): 設定ファイル
        ebs_rail_path(str): ダウンロード対象のパス
    """
    with st.spinner("CISに保存されている画像を削除中"):
        helpers.imgs_dir_remove(f"{config.image_dir}/{office}/{ebs_rail_path}/")
    st.warning("CISに保存されている画像データを削除しました")


def upload_results(config, office, s3_rail_path):
    """ 解析結果をS3にアップロードする
    Args:
        config(object): 設定ファイル
        s3_rail_path(str): アップロード対象のS3 prefix
    """
    dt01 = datetime.datetime.now()
    with st.spinner("解析結果をS3にアップロード中"):
        # シングルスレッドでのアップロード
        # helpers.upload_dir(config.bucket, f"{config.output_dir}/{office}/{s3_rail_path}/", "./")

        # マルチスレッド化してアップロード
        with ThreadPoolExecutor(max_workers=10) as executor:
            for folder in config.camera_types:
                s3_dir = f"{config.output_dir}/{office}/{s3_rail_path}/{folder}"
                # ebs_dir = "./"
                # executor.submit(helpers.upload_dir, config.bucket, s3_dir, ebs_dir)

    st.success("解析結果をS3にアップロードしました")
    dt02 = datetime.datetime.now()
    prc_time = dt02 - dt01
    st.write(f"(参考)処理時間> {prc_time}")

def data_loader(config):
    # マルチページの設定
    st.set_page_config(page_title="データ管理", layout="wide")
    # 認証チェック
    if not auth.check_authentication():
        return
    st.sidebar.header("画像データダウンロード")

    info_view = st.container()
    df_view = st.container()

    # デフォルトの技セを設定
    # 仮に設定： Cognito ユーザ名から取得する用に変更する
    office_default = "takasaki"

    # 箇所名を選択
    if 'office' not in st.session_state:
        st.session_state.office = None

    # 技セ・MCを選択
    if "office_dialog" not in st.session_state:
        if st.sidebar.button("技セ・MCを選択"):
            set_office(config, office_default)

    # 選択された技セ・MCを表示
    if not st.session_state.office:
        st.sidebar.error("技セ・MCを選択してください")
        st.stop()
    else:
        st.sidebar.write(f"選択箇所: {helpers.get_office_message(config, st.session_state.office)}")

    # modes = ("画像をダウンロード", "不要なファイルを削除", "解析結果をアップロード")    # アップロード機能が追加できたら有効化する
    modes = ("画像をダウンロード", "不要なファイルを削除")
    mode = st.sidebar.radio("操作方法を選択", modes)

    if modes.index(mode) == 0:
        mode_info = "# 画像データをダウンロード"
        mode_type = "ダウンロード"
    elif modes.index(mode) == 1:
        mode_info = "# 不要な画像を削除する"
        mode_type = "削除"
    elif modes.index(mode) == 2:
        mode_info = "# 画像データをアップロード"
        mode_type = "アップロード"
    else:
        st.error("予期せぬエラーが発生しました")

    # # 箇所名を選択
    # office_name = st.sidebar.selectbox("箇所名", helpers.get_office_names_jp(config))
    # office = [k for k, v in config.office_names.items() if v == office_name][0]
    # # st.sidebar.write(f"選択された箇所名: {office}")

    # 線区を選択
    info_view.write(mode_info)
    is_search_box_visible = st.sidebar.checkbox("検索ボックスを表示する", key="search_check")
    if is_search_box_visible:
        # 線名を指定
        rail_key_jpn = st.sidebar.selectbox("線区を選択", list(config.rail_names.values()), key="rail_key")
        rail_key = [key for key, value in config.rail_names.items() if value == rail_key_jpn][0]
        # 線別を指定
        rail_type_jpn = st.sidebar.selectbox("線別を選択", list(config.rail_type_names.values()), key="type_key")
        rail_type = [key for key, value in config.rail_type_names.items() if value == rail_type_jpn][0]
        if modes.index(mode) == 0:
            rail_list = helpers.get_s3_dir_list(f"{config.image_dir}/{st.session_state.office}", config.bucket)
        elif modes.index(mode) == 1 or modes.index(mode) == 2:
            rail_list = helpers.list_imagespath_nonCache(f"{config.image_dir}/{st.session_state.office}")
        target_rail_list = [item for item in rail_list if item.split('_')[0] == rail_key and rail_type in item]
    else:
        if modes.index(mode) == 0:
            target_rail_list = helpers.get_s3_dir_list(f"{config.image_dir}/{st.session_state.office}", config.bucket)
        elif modes.index(mode) == 1 or modes.index(mode) == 2:
            target_rail_list = helpers.list_imagespath_nonCache(f"{config.image_dir}/{st.session_state.office}")
        else:
            target_rail_list = []

    # st.write(target_rail_list)

    info_view.write(f"## ___Step1___ {mode_type}する線区を選択する")
    rail_path = info_view.selectbox("線区フォルダ", target_rail_list, key="rail_path")

    info_view.warning(f"## ✔ {mode_type}する線区は合っていますか？")
    if target_rail_list:
        st.sidebar.write("## (参考) 選択中の線区に含まれるデータ")
        # 解析対象のカメラ番号を選択する
        camera_name_list = helpers.get_camera_list(config)
        camera_name = st.sidebar.selectbox(
                        "確認したいカメラを選択",
                        camera_name_list
                        ).split(':')[0]
        camera_path = config.camera_name_to_type[camera_name]
        if modes.index(mode) == 0:
            # 画像リスト
            image_list = helpers.get_s3_image_list(config.image_dir + "/" + rail_path + "/" + camera_path)
        elif modes.index(mode) == 1 or modes.index(mode) == 2:
            base_images = helpers.list_images(config.image_dir + "/" + rail_path + "/" + camera_path)
            image_list = [os.path.basename(path) for path in base_images]
        if image_list:
            with st.sidebar.expander("画像リスト", expanded=False):
                st.write(image_list)
        else:
            st.sidebar.warning("画像がありません")

        vis.rail_info_view_fileio(rail_path, config, info_view)

        st.write("## ___Step2___ 問題なければ👇を押す")
        if modes.index(mode) == 1:
            st.write("⚠️ CISに保存されているデータを削除します（サーバ(S3)のデータは削除されません）")
        if st.button(f"線区フォルダのデータを{mode_type}する"):
            if modes.index(mode) == 0:
                download_images(config, st.session_state.office, rail_path)
            elif modes.index(mode) == 1:
                delete_images(config, st.session_state.office, rail_path)
            elif modes.index(mode) == 2:
                upload_results(config, st.session_state.office, rail_path)
        if modes.index(mode) == 0:
            info_view.warning("__📤️ 新しい画像をサーバー(S3)にアップロードする場合は、別途配布するツールを使用して車モニの画像をアップロードしてください。__")
    else:
        info_view.error(f"""
この条件では{mode_type}できる画像データがありません。別の線区フォルダを選択してください

箇所名や検索条件（線区や線別）を変更して試してください。
""")

    st.sidebar.write('---')

    # S3とEBSのimgsディレクトリ内の線区リストを表示する
    if modes.index(mode) == 2:
        st.header("アップロードするデータのチェック")
    else:
        st.header("ダウンロードされたデータのチェック")
    st.write("【凡例】 ○: データ有 ×: データ無")

    df_key = df_view.text_input("検索キーワード(線区名を英語で入力してください)")
    col1, col2 = df_view.columns(2)
    start_date = col1.date_input("期間を指定(始)", datetime.date(2024,4,1))
    end_date = col2.date_input("期間を指定(終)", datetime.date(2024,6,30))
    try:
        if modes.index(mode) == 0:
            EBS_rail_list = helpers.list_imagespath_nonCache(f"{config.image_dir}/{st.session_state.office}")
            df = helpers.S3_EBS_imgs_dir_Compare(target_rail_list, EBS_rail_list, df_key, start_date, end_date)
        elif modes.index(mode) == 1:
            S3_rail_list = helpers.get_s3_dir_list(f"{config.image_dir}/{st.session_state.office}", config.bucket)
            df = helpers.S3_EBS_imgs_dir_Compare(S3_rail_list, target_rail_list, df_key, start_date, end_date)
        elif modes.index(mode) == 2:
            S3_rail_list = helpers.get_s3_dir_list(f"{config.output_dir}/{st.session_state.office}", config.bucket)
            df = helpers.S3_EBS_imgs_dir_Compare(S3_rail_list, target_rail_list, df_key, start_date, end_date)
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error("該当するデータがありません")
        st.error(f"Error message> {e}")


    # ログアウトボタン
    if st.sidebar.button("ログアウト"):
        auth.logout()


if __name__ == "__main__":
    config = appProperties('config.yml')
    data_loader(config)
