import streamlit as st
from PIL import Image
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties
import src.auth_aws as auth

import os
import re
import csv
import pandas as pd
from glob import glob
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib


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


def extract_filename_without_extension(filepath):
    # ファイルパスの最後の要素（ファイル名）を取得
    filename = os.path.basename(filepath)

    # ファイル名から拡張子を除去
    filename_without_extension = os.path.splitext(filename)[0]

    return filename_without_extension


def extract_info(file_path):
    # より汎用的な正規表現パターンを定義
    pattern = r'output/EDA_result/result_HD\d+_(.*?)\.csv'
    
    # パターンにマッチする部分を抽出
    match = re.search(pattern, file_path)
    
    if match:
        # マッチした部分（グループ1）を返す
        return match.group(1)
    else:
        # マッチしない場合はNoneを返す
        return None


def analysis_anomaly_df(result_path, output_path):
    dir_area = extract_filename_without_extension(output_path)

    # 異常検出結果を読み込む
    df = pd.read_csv(result_path)

    # 異常検出結果を標準出力する
    # 表示が不要な場合は、コメントアウトする
    log_path = f"output/{dir_area}_log.csv"
    image_list = sorted(df['image_name'].unique())

    data = [
        [f"線区フォルダ名: {dir_area}", "", "", ""],
        [f"対象画像：{len(image_list)}枚", "", "", ""],
        ["画像ファイル名", "Twins電柱番号", "異常_開始キロ程", "異常_終了キロ程"]
    ]

    with open(log_path, "w", newline='', encoding='shift-jis') as file:
        writer = csv.writer(file)
        for image_name in image_list:
            # print(f"{image_name} >>> キロ程範囲 {df[df['image_name'] == image_name]['kiro_tei'].min()} ～ {df[df['image_name'] == image_name]['kiro_tei'].max()}\n")
            data.append([
                f"{image_name}",
                int(df[df['image_name'] == image_name]['pole_num'].unique()[0]),
                df[df['image_name'] == image_name]['kiro_tei'].min(),
                df[df['image_name'] == image_name]['kiro_tei'].max()
            ])
        # データを一行ずつ書き込む
        for row in data:
            writer.writerow(row)
    print(f"異常検出結果を {log_path} に出力しました")

    # もとの解析結果を読み込む
    df_output = pd.read_csv(output_path)

    # 異常検出結果があるかを基のデータフレームに追記する
    df_output['Anomaly'] = False
    # df_output の ix 列の値が df の ix 列のいずれかの値と一致する場合、Anomaly を True に設定
    df_output.loc[df_output['ix'].isin(df['ix']), 'Anomaly'] = True

    # グラフを出力する
    create_graph(df, df_output, output_path)


def create_graph(df, df_output, output_path, main_view):
    dir_area = extract_filename_without_extension(output_path)

    # フォントサイズ変更
    plt.rcParams["font.size"] = 18

    # プロットの作成
    plt.figure(figsize=(20, 8))  # グラフのサイズを設定

    # estimated_width の線グラフをプロット
    plt.plot(df_output['kiro_tei'], df_output['estimated_width'], label='Estimated Width')

    # Anomaly が True の点を赤丸でプロット
    anomalies = df_output[df_output['Anomaly'] == True]
    plt.scatter(anomalies['kiro_tei'], anomalies['estimated_width'], color='red', s=50, label='Anomaly')

    # グラフの設定
    plt.xlabel('キロ程(km)')
    plt.ylabel('画像におけるトロリ線摺動面幅(px)')
    plt.title(f'摺動面幅での異常検出結果: {dir_area}')
    plt.legend()

    # グリッドの追加
    plt.grid(True, linestyle='--', alpha=0.7)

    # x軸の目盛りを調整（必要に応じて）
    plt.xticks(rotation=45)

    # グラフのレイアウトを調整
    plt.tight_layout()

    # グラフを画像として保存
    save_path = f'output/{dir_area}_width.png'
    plt.savefig(save_path)
    main_view.write(f"グラフを {save_path} に出力しました")

    # グラフを表示
    # plt.show()
    main_view.pyplot(plt)


def get_file_list():
    result_list = sorted(glob("output/EDA_result/*.csv"))
    graph_list = sorted(glob("output/EDA_result/*.png"))
    return result_list, graph_list


def highlight_rows(s, highlight_string):
    return ['background-color: pink; color: black' if s['画像ファイル名'] == highlight_string else '' for _ in s]


def find_indices(word_list, target_string):
    """ リストの要素に一致するインデックスを返す
    """
    return [index for index, word in enumerate(word_list) if target_string in word]


def eda_tool(config):
    # マルチページの設定
    st.set_page_config(page_title="異常値箇所チェック", layout="wide")

    # 認証マネージャーの初期化
    auth_manager = auth.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return

    # 認証情報からユーザー名を取得
    username = auth_manager.authenticator.get_username()

    st.sidebar.header("異常箇所チェックツール")
    
    # メインページのコンテナを配置する
    main_view = st.container()
    col1, col2 = st.columns([2, 1])
    with col1:
        col1_cont = st.container()
    with col2:
        col2_cont = st.container()
    
    # 作成中メッセージ
    main_view.warning("# 一生懸命プログラムを作成中です")
    img_sorry = Image.open('icons/sorry_panda.jpg')
    main_view.image(img_sorry, caption='We are working very hard on the program!')


    # 箇所名を選択
    if 'office' not in st.session_state:
        st.session_state.office = None

    # 技セ・MCを選択
    if "office_dialog" not in st.session_state:
        if st.sidebar.button("技セ・MCを選択"):
            set_office(config, username)

    # 選択された技セ・MCを表示
    if not st.session_state.office:
        st.sidebar.error("技セ・MCを選択してください")
        st.stop()
    else:
        st.sidebar.write(f"選択箇所: {helpers.get_office_message(config, st.session_state.office)}")

    # フォルダ直下の画像保管用ディレクトリのリスト
    # images_path = helpers.list_imagespath(config.image_dir)
    # 他ページでの結果を反映するためnonCacheを使用
    images_path = helpers.list_imagespath_nonCache(config.image_dir)

    # 画像保管線区の選択
    st.sidebar.markdown("# ___Step1___ 線区を選択")

    # 検索ボックスによる対象フォルダの絞り込み
    dir_search = st.sidebar.checkbox("検索ボックス表示", value=False)
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
    dir_area = main_view.selectbox("線区のフォルダ名を選択してください", images_path_filtered)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")
        st.stop()

    # 選択された線区情報を表示する
    vis.rail_info_view(dir_area, config, main_view)

    st.sidebar.markdown("# ___Step2___ 解析条件を設定")
    # 解析対象のカメラ番号を選択する
    camera_name_list = helpers.get_camera_list(config)
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    camera_name_list
                    ).split(':')[0]
    st.sidebar.write(f"カメラ番号: {camera_name}")
    camera_num = config.camera_name_to_type[camera_name]

    # 解析対象の画像フォルダを指定
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num

    # outputディレクトリを指定
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)


    # EDA結果ファイルのリストを読み込む
    result_list, graph_list = get_file_list()
    result_path = [fpath for fpath in result_list if f"{dir_area}_{camera_num}" in fpath]
    graph_path = [fpath for fpath in graph_list if f"{dir_area}_{camera_num}" in fpath]

    if not result_path:
        main_view.error("異常値検出結果がありません。線区 or カメラ番号を変更してください。")
        st.stop()
    else:
        result_path = result_path[0]
        main_view.success(f"選択されたCSV: {result_path}")

    df = pd.read_csv(result_path, header=2, encoding="shift-jis")
    pole_nums = df['Twins電柱番号'].unique().tolist()
    images = df['画像ファイル名'].unique().tolist()
    
    with col1_cont:
        st.write("# 異常値検出結果")

        st.write("## 異常値検出グラフ")
        st.image(graph_path, caption="検出された外れ値をプロットしています")

        st.write("## 異常値検出データ")
        st.selectbox("異常が検出された電柱番号　※重複なし チェック用", pole_nums)
        
        image_idx = st.number_input(f"異常が検出された画像を番号で選択({len(images)}枚)",
                                   min_value=1,
                                   max_value=len(images)) - 1
        image_path = images[image_idx]
        st.write(f"表示する画像: {find_indices(base_images, image_path)}> {image_path} 👉")
        # image_path = st.selectbox(f"異常が検出された画像({len(images)}枚)　選択した画像が表示されます👉", images)
        styled_df = df.style.apply(highlight_rows, axis=1, highlight_string=image_path)
        st.dataframe(styled_df)
        # st.write(df)
    
    with col2_cont:
        st.write("# 🖥️カメラ画像")
        st.write("解析結果を表示中")
        st.write(f"画像ファイル: {find_indices(base_images, image_path)}> {image_path}")
        try:
            csv_path = image_path.replace('.jpg', '.csv')
            image_name = image_path.split('.')[0]
            rail_fpath = f"{outpath}/{config.csv_fname}_{csv_path}"
            cam_img = vis.ohc_image_load(f"{target_dir}/{image_path}")
            out_img = vis.out_image_load(rail_fpath, dir_area, camera_num, image_path, cam_img, config, outpath)
        except Exception as e:
            out_img = []
            st.write(e)
        if not out_img:
            st.error("解析結果がありません")
        else:
            st.image(out_img)
            out_img_name = f"downloaded_image_{image_path}"
            vis.download_image(out_img, out_img_name)
    
    st.write("# 連結画像を出力する")

    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    eda_tool(config)