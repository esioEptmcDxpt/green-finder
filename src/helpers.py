import os
import glob
import re
import copy
import shutil
import json
import boto3
from botocore.exceptions import NoCredentialsError
from concurrent.futures import ThreadPoolExecutor
import datetime
import shelve
import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image
# from src.logger import my_logger
import random


@st.cache
def list_imagespath(image_dir):
    images_fullpath = glob.glob(os.path.join(image_dir, "*"))
    images_fullpath = [folder for folder in images_fullpath if os.path.isdir(folder)]
    images_path = [os.path.basename(folder) for folder in images_fullpath]
    images_path.sort()
    return images_path


def list_imagespath_nonCache(image_dir):
    """ データダウンロードページ用（キャッシュ無効版）
    """
    images_fullpath = glob.glob(os.path.join(image_dir, "*"))
    images_fullpath = [folder for folder in images_fullpath if os.path.isdir(folder)]
    images_path = [os.path.basename(folder) for folder in images_fullpath]
    images_path.sort()
    return images_path


# @st.cache
def list_images(target_dir):
    base_images = glob.glob(target_dir + "/*.jpg")
    base_images.sort()
    return base_images


def list_csvs(target_dir):                                       # 2024.5.21 -->
    base_csvs = glob.glob(target_dir + "/*.csv")
    base_csvs.sort()
    return base_csvs                                             # --> 2024.5.21


@st.cache
def get_dir_list(path):
    dir_path = Path(path)
    dir_obj_list = [path for path in dir_path.glob("*") if path.is_dir() and not path.name.startswith(".")]
    dir_list = [image_obj.name for image_obj in dir_obj_list]
    dir_list.sort()
    return dir_list


@st.cache
def get_file_list(path):
    dir_path = Path(path)
    image_obj_list = [path for path in dir_path.glob("*") if path.is_file()]
    image_list = [image_obj.name for image_obj in image_obj_list]
    image_list.sort()
    return image_list


@st.cache
def read_markdown_file(markdown_file):
    return Path(markdown_file).read_text()


@st.cache
def read_python_file(python_file):
    return Path(python_file).read_text()


@st.cache
def get_file_content_as_string(filename):
    st.code(filename)


@st.cache
def ohc_image_load(base_images, idx, caption):
    st.text(f'{idx}番目の画像を表示します')
    im_base = Image.open(base_images[idx])
    st.image(im_base, caption=caption)
    return im_base


@st.cache
def rail_name_to_jp(rail_name, config):
    return config.rail_names[rail_name]


@st.cache
def station_name_to_jp(st_name, config):
    return config.station_names[st_name]


@st.cache
def rail_type_to_jp(rail_type, config):
    return config.rail_type_names[rail_type]


@st.cache
def rail_type_name_to_jp(time_band_names, config):
    return config.time_band_names[time_band_names]


@st.cache
def camera_num_to_name(camera_num, config):
    return config.camera_names[camera_num]


# @st.cache
def rail_message(dir_area, config):
    str_list = re.split('[_-]', dir_area)
    rail_name = rail_name_to_jp(str_list[0], config)
    if str_list[3] == 'St' or str_list[3] == 'st':
        st_name = station_name_to_jp(str_list[2], config) + '構内'
    else:
        st_name = station_name_to_jp(str_list[2], config) + '～' + station_name_to_jp(str_list[3], config)
    updown_name = rail_type_to_jp(str_list[4], config)
    date_obj = datetime.datetime.strptime(str_list[5], "%Y%m%d")
    measurement_date = date_obj.strftime("%Y年%m月%d日")    # # yyyy年mm月dd日形式の文字列に変換
    measurement_time = rail_type_name_to_jp(str_list[6], config)
    return rail_name, st_name, updown_name, measurement_date, measurement_time


@st.cache
def rail_camera_initialize(rail, camera_num, base_images, trolley_ids):
    """ railに書き込めるように初期化する
        解析結果が既にある場合は初期化しない
    Args:
        rail (shelve): 解析結果保存用のshelveファイル
        camera_num (str): カメラ番号
        base_images (str): 画像のファイルパスのリスト
        trolley_ids (str): trolley_idのテンプレ (trolley1, trolley2 ...)
    """
    # if len(rail) < 2 or not any(len(rail[camera_num].get(image_path, {})) > 0 for image_path in base_images):
    #     print('rail initilize')
    #     print(f'dir_area: {rail["name"]}')
    #     # railを初期化
    #     rail[camera_num] = {image_path: {trolley_id: {} for trolley_id in trolley_ids} for image_path in base_images}
    
    # 修正前のコード👇
    if len(rail) < 2:    # 初めてrailが生成された場合は"name"だけなのでlen(rail)は1
        rail_check = False
    else:    # 一度でも解析されるとtrolley_idが追加されるため1以上
        # rail_check = any(len(rail[camera_num][image_path]) > 0 for image_path in base_images)
        rail_check = any(key in image_path for key in rail[camera_num].keys() for image_path in base_images)
    if not rail_check:
        # print('rail initilize')
        # print(f'dir_area: {rail["name"]}')
        # railを初期化
        # base_imagesと同じ長さの空のdictionaryを作成してrailを初期化
        blankdict_size = [{}] * len(base_images)
        rail[camera_num] = dict(zip(base_images, blankdict_size))
        # trolley_idsと同じ長さの空のdictionaryを作成してrailを初期化
        blankdict_size = [{}] * len(trolley_ids)
        for image_path in base_images:
            rail[camera_num][image_path] = dict(zip(trolley_ids, blankdict_size))
    return


# @st.experimental_singleton(show_spinner=True)
def get_s3_dir_list(path):
    """ S3バケットのディレクトリ一覧を取得する
    Args:
        path (str): backet内の画像ディレクトリ名(例)imgs
    """
    backet_name = "trolley-monitor"

    s3 = boto3.client('s3')
    rail_list = []
    # S3バケット内のディレクトリ一覧を取得
    response = s3.list_objects_v2(Bucket=backet_name, Prefix=path + "/" , Delimiter='/')
    for content in response.get('CommonPrefixes', []):
        full_path = content.get('Prefix')
        normalized_path = os.path.normpath(full_path)
        rail_list.append(os.path.basename(normalized_path))
    # レスポンスが1000件未満になるまでリクエストを続ける
    while response['IsTruncated']:
        response = s3.list_objects_v2(Bucket=backet_name, Prefix=path + "/" , Delimiter='/', ContinuationToken=response['NextContinuationToken'])
        for content in response.get('CommonPrefixes', []):
            full_path = content.get('Prefix')
            normalized_path = os.path.normpath(full_path)
            rail_list.append(os.path.basename(normalized_path))
    rail_list.sort()
    return rail_list


def get_s3_image_list(path):
    """ S3バケットのカメラフォルダ内のファイル一覧を取得する
    Args:
        path (str): backetを起点としたディレクトリへのパス
                    (例)images/Chuo_01_Tokyo-St_20230201_knight/HD11/
    """
    backet_name = "trolley-monitor"

    s3 = boto3.client('s3')
    image_list = []

    # S3バケット内のファイル一覧を取得
    response = s3.list_objects_v2(Bucket=backet_name, Prefix=path + "/")
    for content in response.get('Contents', []):
        full_path = content.get('Key')
        image_list.append(os.path.basename(full_path))
    # レスポンスが1000件未満になるまでリクエストを続ける
    while response['IsTruncated']:
        response = s3.list_objects_v2(Bucket=backet_name, Prefix=path + "/", ContinuationToken=response['NextContinuationToken'])
        for content in response.get('Contents', []):
            full_path = content.get('Key')
            image_list.append(os.path.basename(full_path))
    image_list.sort()
    return image_list


def list_csv_files(bucket_name, prefix):
    """ S3にあるCSVの一覧をゲット
    """
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')

    csv_files = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                if obj['Key'].endswith('.csv'):
                    csv_files.append(obj['Key'])

    return csv_files


# @st.experimental_singleton(show_spinner=True)
def get_S3_file_content_as_string(img_dir_name, path):
    """ S3バケットからファイルを取得してくる
    Args:
        img_dir_name (str): backet内の画像ディレクトリ名(例)imgs/
        path (str): 画像ディレクトリ名内のディレクトリ名(例)Chuo_01_Tokyo-St_20230201_knight/
    """
    backet_name = "trolley-monitor"
    dir_path = img_dir_name + path

    s3 = boto3.resource('s3')
    response = s3.Object(backet_name, dir_path).get()['Body']
    return response.read().decode("utf-8")


def get_columns_from_csv(bucket_name, columns_csv_key):
    """ S3からカラム名リストをゲット
    """
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=bucket_name, Key=columns_csv_key)
    columns_df = pd.read_csv(obj['Body'])
    return columns_df.columns.tolist()


def get_KiroTei_dict(config, df):
    """ 走行日・線区ごとのキロ程補正情報を辞書に記録する
    """
    # カメラ番号ごとに、EkiCdのはじめの行をTrueとして記録する
    for camera_num in config.camera_types:
        df[f"EkiCdDiff{camera_num}"] = df.query(f"GazoFileName{camera_num}.notnull()", engine='python')['EkiCd'].diff().map(lambda x: x != 0)
    # 走行日・線区ごとに、画像1枚あたりの幅(m)を算出して辞書に記録する
    result_dict = {}
    for camera_num in config.camera_types:
        grouped_df = df.query(f"GazoFileName{camera_num}.notnull()", engine='python').groupby(['SokuteiDate', 'EkiCd'])['KiroTei'].count()
        for (date, ekicd), count in grouped_df.items():
            if date not in result_dict:
                result_dict[date] = {}
            if ekicd not in result_dict[date]:
                result_dict[date][ekicd] = {}
            # print(f"camera_num: {camera_num}, date: {date}, ekicd: {ekicd}")
            KiroTei_head = df.query(f"EkiCdDiff{camera_num}.notnull() & SokuteiDate == {date} & EkiCd == {ekicd}", engine='python')['KiroTei'].iloc[0]
            KiroTei_tail = df.query(f"EkiCdDiff{camera_num}.notnull() & SokuteiDate == {date} & EkiCd == {ekicd}", engine='python')['KiroTei'].iloc[-1]
            result_dict[date][ekicd][camera_num] = {
                'KiroTei_head': KiroTei_head,
                'KiroTei_tail': KiroTei_tail,
                'KiroTei_dist': round(KiroTei_tail - KiroTei_head, 4),
                'KiroTei_delta': round((KiroTei_tail - KiroTei_head) / (count - 1), 6),
                'count': count
            }
    return df.copy(), result_dict


def set_imgKiro(config, dir_area, df_tdm, KiroTei_dict):
    imgKilo = {}
    for camera_num in config.camera_types:
        # カメラフォルダ内の画像ファイルを取得
        image_dir = f"{config.image_dir}/{dir_area}/{camera_num}/"
        # print(image_dir)
        base_images = list_images(image_dir)
        # print(f"Image counts:{len(list_images)}")

        # 補正後の KiroTei_delta を呼び出すためのキーを取得
        image_name = base_images[0].split('/')[-1]
        date = df_tdm[df_tdm[f'GazoFileName{camera_num}'] == image_name.split(".")[0]].iloc[0]['SokuteiDate']
        ekicd = df_tdm[df_tdm[f'GazoFileName{camera_num}'] == image_name.split(".")[0]].iloc[0]['EkiCd']
        # print(f"debug>>> {dir_area} {camera_num} >>> {date=}, {ekicd=}")

        # 画像ファイル名に対応するキロ程を抽出して辞書型で記録する
        imgKilo_temp = {}
        # imgKilo_temp_values = {}
        # for fname in list_images:
        for idx, fname in enumerate(base_images):
        # for fname in list_images:
            image_name = re.split('[./]', fname)[-2]
            df_tdm_Series = df_tdm[df_tdm[f"GazoFileName{camera_num}"] == image_name].copy()
            if df_tdm_Series.empty:
                continue
            else:
                DenchuNo = df_tdm_Series['DenchuNo'].item()
                # KiroTei = df_tdm_Series['KiroTei'].round(4).item()
                KiroTei = KiroTei_dict[date][ekicd][camera_num]['KiroTei_head'] + KiroTei_dict[date][ekicd][camera_num]['KiroTei_delta'] * idx

            # imgKilo_temp_values["DenchuNo"] = DenchuNo
            # imgKilo_temp_values["KiroTei"] = KiroTei
            # imgKilo_temp[image_name] = imgKilo_temp_values.copy()
            imgKilo_temp[image_name] = {
                "DenchuNo": DenchuNo,
                "KiroTei": KiroTei
            }

        if imgKilo_temp != {}:
            imgKilo[camera_num] = imgKilo_temp.copy()

    return imgKilo


def get_df_tdm(config, csv_file, columns):
    """ 車モニのマスタデータを読み込む
    Args:
        config: 設定データ
        csv_file(str): S3に保存した画像キロ程情報を記録したCSVのprefix
        columns(list): 画像キロ程情報のカラム名
    Return:
        df_tdm(DataFrame): 読み込まれたデータフレーム
    """

    # TDM(車モニCSV)をS3からダウンロードする
    download_path = f"{config.tdm_dir}/temp/{csv_file.split('/')[-1]}"
    # print("車モニのマスターデータを読み込みます ※少し時間がかかります")
    download_file_from_s3(config.bucket, csv_file, download_path)
    # print(f'complete: {download_path=}')

    # CSVからデータフレームを読み込む
    df_tdm = pd.read_csv(download_path, names=columns, delimiter='|')

    # データフレームを整形する
    df_tdm['TimeCode'] = pd.to_datetime(df_tdm['TimeCode'])
    df_tdm = df_tdm.sort_values(by=['SokuteiDate', 'KiroTei'], ignore_index=True)
    # print("車モニのマスターデータを読み込みました")
    # print(f"データフレームのサイズ:{df_tdm.shape}")

    # 欲しい列だけ抽出する
    df_tdm = df_tdm.filter([
        'EkiCd', 'SenbetsuCd', 'SokuteiDate', 'DenchuNo', 'KiroTei',               # Comment Out    'SokuteiYear' 'NennaiSeqNo'は追加されている
        'GazoFileNameHD11', 'GazoFileNameHD12',
        'GazoFileNameHD21', 'GazoFileNameHD22',
        'GazoFileNameHD31', 'GazoFileNameHD32'
    ]).copy()

    # print("必要な情報だけフィルタリングしました")
    # print(f"データフレームのサイズ:{df_tdm.shape}")
    return df_tdm


def get_img2kiro(config, dir_area, images_path, target_dir, base_images, csv_files):
    """ 線区ごとの画像→キロ程変換データを取得・作成する
    """
    # カラム名をS3から読み込む
    columns_csv_key = f"{config.kiro_prefix}/{config.kiro_columns_name}"
    columns = get_columns_from_csv(config.bucket, columns_csv_key)

    # 行路の条件をフォルダ名から指定する
    image_name = base_images[0].split('/')[-1]
    # st.write(f"{image_name=}")
    meas_year = image_name.split("_")[0]              # 走行年度
    meas_idx = image_name.split("_")[1]               # 年度通番
    meas_senku = dir_area.split('_')[0]      # 線区
    meas_kukan = dir_area.split('_')[2]      # 区間
    # st.write(f"測定年度: {meas_year}  年度通番: {meas_idx}  線区: {meas_senku}  区間: {meas_kukan}")

    # 手持ち線区フォルダと一致するCSVをS3から探す
    for csv_file in csv_files:
        if csv_file[-13:-4] == f"{meas_year}_{meas_idx}":
            # データフレームを読み込む
            df_tdm = get_df_tdm(config, csv_file, columns)

            # 走行日・線区ごとのキロ程補正情報の辞書を作成する
            df_tdm, KiroTei_dict = get_KiroTei_dict(config, df_tdm)

            # 測定日を取得　※１つしかないはず・・・
            date = df_tdm['SokuteiDate'].unique().item()

            # 線別コードを取得
            if dir_area.split('_')[3] == "down":
                SenbetsuCd = 21
            elif dir_area.split('_')[3] == "up":
                SenbetsuCd = 22
            else:
                SenbetsuCd = None                              # 他は？？

            # 基準となる電柱の情報                                                                                               # キロ程オフセット未使用化のため追加
            # ref_point = {
            #     "EkiCd_NEWSS": eki_code[meas_senku][meas_kukan]["EkiCd_NEWSS"],
            #     "pole_num_NEWSS": eki_code[meas_senku][meas_kukan]["pole_num_NEWSS"],
            #     "pole_kilo_NEWSS": eki_code[meas_senku][meas_kukan]["pole_kilo_NEWSS"]
            # }
            
            # print('df_tdm <head>')
            # print(df_tdm.head())

            # pole_kiro_offset = get_Kiro_offset(df_tdm, ref_point, date)                                                        # キロ程オフセット未使用化のため追加

            # kiro_offset_dict = {}                                                                                              # キロ程オフセット未使用化のため追加
            # kiro_offset_dict[date] = pole_kiro_offset                                                                          # キロ程オフセット未使用化のため追加

            # # NEWSSキロ程を計算して 列`KiroTei_NEWSS`に記録する                                                                  # キロ程オフセット未使用化のため追加
            # df_tdm = get_Kiro_NEWSS(df_tdm, kiro_offset_dict)                                                                  # キロ程オフセット未使用化のため追加

            # 確認用にエクセルに出力する
            # df_tdm.to_excel(f"./{config.tdm_dir}/temp/df_tdm_{dir_area}.xlsx")

            # 初期設定の情報を出力
            # print(f"画像フォルダ名：{dir_area}")
            # print(f"基準にする電柱：{ref_point['pole_num_NEWSS']}")                                                             # キロ程オフセット未使用化のため追加
            # print(f"　　　　キロ程：{ref_point['pole_kilo_NEWSS']}")                                                            # キロ程オフセット未使用化のため追加
            # print(f"検測キロ程ズレ：{round(kiro_offset_dict[date], 3)}")                                                        # キロ程オフセット未使用化のため追加

            imgKilo = set_imgKiro(config, dir_area, df_tdm, KiroTei_dict)

            if imgKilo != {}:
                # 結果をJSONファイルに記録する
                dir = f"{config.tdm_dir}/{dir_area}.json"
                with open(dir, mode="wt", encoding="utf-8") as f:
                    json.dump(imgKilo, f, ensure_ascii=False, indent=2, default=default)

            # st.write(f"画像ファイルごとのキロ程情報を{dir}に記録しました")
            break

    return


def download_dir(prefix, local):
    """ バケット内の指定したプレフィックスを持つすべてのオブジェクトをダウンロードします。
    Args:
        prefix (str): S3のフォルダパス
                      (例) imgs/Chuo_01_Tokyo-St_up_20230201_knight/
        local  (str): ローカルディレクトリへのパス
                      (例) ./
    """
    # S3のクライアントを作成
    client = boto3.client('s3')
    # バケット名
    bucket = 'trolley-monitor'

    paginator = client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(local + file.get('Key'))):
                    os.makedirs(os.path.dirname(local + file.get('Key')))
                client.download_file(bucket, file.get('Key'), local + file.get('Key'))

    return


def download_file_from_s3(bucket_name, key, download_path):
    """ S3からダウンロードする
    """
    download_dir = os.path.dirname(download_path)
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    s3 = boto3.client('s3')
    s3.download_file(bucket_name, key, download_path)


# S3バケットに画像ファイルを保存する
def put_s3_img(img, file_full_path):
    # imgは、Pillow Image.open()で読み込まれた形式
    # バイトデータに変換する
    with BytesIO() as output:
        img.save(output, format="JPEG")
        contents = output.getvalue()
    s3 = boto3.client('s3')
    response = s3.put_object(Body=contents, Bucket='k-nagayama', Key=file_full_path)
    return


def imgs_dir_remove(path):
    """ pathで指定したディレクトリを削除する
    Args:
        path (str): 削除したいディレクトリのパス
    """
    try:
        # ディレクトリとその中身をすべて削除
        shutil.rmtree(path)
    except FileNotFoundError:
        st.error("対象のディレクトリが見つかりません")
    except Exception as e:
        print("An error occurred: ", e)
    return

def file_remove(path):
    """ pathで指定したディレクトリを削除する
    Args:
        path (str): 削除したいディレクトリのパス
    """
    try:
        # ファイルを削除
        os.remove(path)
    except FileNotFoundError:
        st.error("対象のファイルが見つかりません")
    except Exception as e:
        print("An error occurred: ", e)
    return


# @st.cache
def S3_EBS_imgs_dir_Compare(S3_dir_list, EBS_dir_list, df_key):
    """ 2つのリストからデータの有無をまとめたデータフレームを作成
    Args:
        S3_dir_list (list): 1つ目のリスト（例）S3内のディレクトリ名のリスト
        EBS_dir_list (list): 2つ目のリスト（例）EBS内のディレクトリ名のリスト
    Return:
        df (DataFrame): 結果をまとめたデータフレーム
    """
    # 線区名リストの作成（S3_dir_listとEBS_dir_listのユニークな要素の合計）
    line_names = list(set(S3_dir_list + EBS_dir_list))
    line_names.sort()

    # データフレームの作成
    df = pd.DataFrame(line_names, columns=['線区名'])

    # S3列とTTS列の作成
    df['S3'] = df['線区名'].apply(lambda x: '○' if x in S3_dir_list else '×')
    df['TTSシステム'] = df['線区名'].apply(lambda x: '○' if x in EBS_dir_list else '×')

    if df_key:
        df_filtered = df[df['線区名'].str.contains(df_key)].copy()
    else:
        df_filtered = df.copy()

    return df_filtered


def rail_csv_concat(outpath):
    """ output/<camera_num>/内にある画像ごとのCSVファイルを結合してデータフレームとして返す
    Args:
        outpath(str): カメラ毎の出力先ディレクトリ
    Return:
        combined_df(DataFrame): 全てのCSVを結合したデータフレーム
    """
    csv_list = glob.glob(f"{outpath}/*.csv")
    csv_list.sort()

    if not csv_list:
        st.sidebar.warning("CSVファイルがみつかりませんでした")
        return pd.DataFrame()

    dfs = []
    for csv_path in csv_list:
        df = pd.read_csv(csv_path)
        dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True).sort_values(by=dfs[0].columns.tolist())

    return combined_df.copy()


def check_camera_dirs(dir_area, config):
    """ Outputディレクトリ内の結果ファイルの有無を確認する
    Args:
        dir_area (str): output内のディレクトリ名
        config: configファイル
    Return:
        df (DataFrame): Pandasデータフレーム形式
    """
    # 結果を格納するリスト
    result = []
    # 各カメラのディレクトリをチェック
    for camera_name, camera_type in config.camera_name_to_type.items():
        # ディレクトリ内のCSVファイルの数を取得
        file_path = f"{config.output_dir}/{dir_area}/{camera_type}/*.csv"
        # file_path = os.path.join(config.output_dir, dir_area, camera_type, "rail.csv")
        # ディレクトリ内のファイルをチェック
        if glob.glob(file_path):
        # if os.path.exists(file_path):
            result.append([f"{camera_name}_{camera_type}", "○"])
        else:
            result.append([f"{camera_name}_{camera_type}", "×"])
    # 結果をPandasデータフレームに変換
    df = pd.DataFrame(result, columns=["カメラ番号", "結果有無"])
    return df

def check_camera_dirs_addIdxLen(dir_area, config):
    """ Outputディレクトリ内の結果ファイルの有無を確認する
    Args:
        dir_area (str): output内のディレクトリ名
        config: configファイル
    Return:
        df (DataFrame): Pandasデータフレーム形式
    """
    result = []
    # 各カメラのディレクトリをチェック
    with ThreadPoolExecutor(max_workers=6) as executor:
        for camera_name, camera_type in config.camera_name_to_type.items():
            # ディレクトリのパスを作成
            # file_path = os.path.join(config.output_dir, dir_area, camera_type, "rail.csv")
            file_path = f"{config.output_dir}/{dir_area}/{camera_type}"
            res = executor.submit(read_csv_idx, camera_name, camera_type, file_path)
            result.append(res.result())
    # 結果をPandasデータフレームに変換
    df = pd.DataFrame(result, columns=["カメラ番号", "結果有無", "最後のインデックス"])
    return df


def get_max_idx(file_path):
    """ check_camera_dirs_addIdxLen用の関数
    Args:
        file_path(str): CSVファイルの保存パス
    Return:
        max_val(int): image_idxの最大値
    """
    # CSVファイルのimage_idxの最大値を取得する
    flist = glob.glob(f"{file_path}/*.csv")
    flist.sort()
    if not flist:
        return -1    # CSVファイルが無いときはreturn
    max_val = float('-inf')
    # 一番末尾のファイルにおいて、最終のインデックスをチェック
    with open(flist[-1], 'r', encoding="utf-8") as file:
        # Skip header
        file.readline()
        for line in file:
            try:
                value = float(line.split(',', 1)[0])  # Split only at the first comma
                if value > max_val:
                    max_val = value
            except ValueError:
                continue

    # 空のrail.csvの場合の対処
    # max_valが有限の値であることを確認
    if np.isfinite(max_val):
        return int(max_val)
    else:
        return -1    # 後で +1 されるため -1にしておく

def read_csv_idx(camera_name, camera_type, file_path):
    """ check_camera_dirs_addIdxLen用の関数
    Args:
        ile_path(str): CSVファイルの保存パス
    Return:
        result_list(list): 結果データフレーム追記用のリスト
    """
    # if os.path.exists(file_path):
    if glob.glob(file_path):
        max_idx = get_max_idx(file_path)
        result_list = [f"{camera_name}_{camera_type}", "○", int(max_idx) + 1]    # ユーザ向けに+1表示する
    else:
        result_list = [f"{camera_name}_{camera_type}", "×", 0]
    return result_list


def check_camera_results(dir_area, config):
    """ Outputディレクトリ内の結果ファイル＋CSVファイルの有無を確認する
    Args:
        dir_area (str): output内のディレクトリ名
        config: configファイル
    Return:
        df (DataFrame): Pandasデータフレーム形式
    """
    # 結果を格納するリスト
    result = []

    # 各カメラのディレクトリをチェック
    for camera_name, camera_type in config.camera_name_to_type.items():
        # ディレクトリのパスを作成
        dir_path = os.path.join(config.output_dir, dir_area, camera_type)
        # ディレクトリ内のファイルをチェック
        try:
            shelve_check = False
            csv_check = False
            for file in os.listdir(dir_path):
                if "rail.shelve" in file:  # ファイル名に"rail.shelve"が含まれるかをチェック
                    shelve_check = True
                if file.endswith(".csv"):  # ファイルがCSV形式かをチェック
                    csv_check = True
                if shelve_check and csv_check:  # 両方のファイルが存在する場合はループを抜ける
                    break
            result.append([f"{camera_name}_{camera_type}", "○" if shelve_check else "×", "○" if csv_check else "×"])
        except FileNotFoundError:  # ディレクトリが存在しない場合
            result.append([f"{camera_name}_{camera_type}", "×", "×"])

    # 結果をPandasデータフレームに変換
    df = pd.DataFrame(result, columns=["カメラ番号", "結果有無", "CSV変換"])

    return df


# def trim_trolley_dict(config, trolley_dict, img_path):
#     """ shelveから読み取ったtrolley_dictの行数を揃える
#     Args:
#         config: 設定用ファイル
#         trolley_dict(dict): shleveから読み込んだ辞書
#         img_path(str): 解析対象の画像パス
#     Return:
#         trolley_dict(dict): 更新されたtrolley_dict
#     Memo:
#         デバッグ用のprint文はコメントアウトしています。
#         必要な場合は有効化してください。
#     """
#     for trolley_id in config.trolley_ids[:len(trolley_dict[img_path])]:
#         # print(trolley_id)
#         for key in trolley_dict[img_path][trolley_id].keys():
#             if not trolley_dict[img_path][trolley_id][key]:
#                 # 空のリストの場合
#                 trolley_dict[img_path][trolley_id][key] = [np.nan] * config.max_len
#             elif not isinstance(trolley_dict[img_path][trolley_id][key], list):
#                 # リスト以外(数値等)の場合
#                 trolley_dict[img_path][trolley_id][key] = [trolley_dict[img_path][trolley_id][key]] + [np.nan] * (config.max_len - 1)
#             value_len = len(trolley_dict[img_path][trolley_id][key])
#             if config.max_len < value_len:
#                 config.max_len = value_len
#             if value_len < config.max_len:
#                 # 要素がmax_len(例:1000行)未満の場合
#                 if key == "ix":
#                     # 連番で埋める
#                     trolley_dict[img_path][trolley_id][key].extend(range(value_len, config.max_len))
#                 else:
#                     # NaN埋めする
#                     trolley_dict[img_path][trolley_id][key].extend([np.nan] * (config.max_len - value_len))
#     return trolley_dict


# def read_trolley_dict(config, trolley_dict, img_idx, img_path, column_name, thin_out):
#     """ 画像パスごとにデータを読み込む
#     Args:
#         config: 設定用ファイル
#         trolley_dict(dict): shleveから読み込んだ辞書
#         img_path(str): 解析対象の画像パス
#         thin_out(int): 行を間引く間隔(例)50 ⇒ 横50pxずつデータを記録する
#     Return:
#         df_trolley(DataFrame): trolley_dictから作成したデータフレーム
#     """
#     # Step0: trolley_dictの行数を揃える
#     trim_trolley_dict(config, trolley_dict, img_path)

#     # Step1: trolley_dictをデータフレームとして読み込む
#     df_trolley = pd.DataFrame()
#     # trolley_idごとにデータフレームとして読み込む
#     for idx, trolley_id in enumerate(config.trolley_ids):
#         if trolley_id in trolley_dict[img_path]:
#             # trolley_idに対応する結果がある場合
#             # データフレームを読み込む
#             df = pd.DataFrame(trolley_dict[img_path][trolley_id]).copy()
#             # データフレームとresult_keysを比較して、不足する列を追加する
#             diff_list = list(set(config.result_keys) - set(list(df.columns)))
#             for column in diff_list:
#                 df[column] = pd.Series([np.nan]*config.max_len, index=df.index)
#             # result_keysと同じ順番に並び替える
#             df = df.reindex(columns=config.result_keys, copy=False)
#         else:
#             # trolley_idに対応する結果が無い場合
#             # 空のデータフレームを作成する
#             df_forNoneTrolley = pd.DataFrame(index=range(config.max_len), columns=config.result_keys)

#         # dfとdf_trolleyを連結する
#         if not idx:
#             df_trolley = df.copy()
#         else:
#             df_trolley = pd.concat([df_trolley, df], axis=1).copy()

#     # Step2: 読み込まれたデータフレームの列名を変更する
#     df_trolley.columns = column_name

#     # Step3: インデックスや画像名等の情報を記録する
#     # 線区名、カメラ名、画像名を取得
#     dir_area, camera_num = img_path.split("/")[1:3]
#     image_name = img_path.split('/')[-1]

#     # データフレームに挿入する項目・位置を指定
#     columns_to_insert = [("img_idx", img_idx, 0),
#                          ("dir_area", dir_area, 1),
#                          ("camera_num", camera_num, 2),
#                          ("image_name", image_name, 3)]

#     # データフレームにインデックス・画像名等を挿入する
#     for col_name, col_value, idx in columns_to_insert:
#         if col_name not in df_trolley.columns:
#             df_trolley.insert(idx, col_name, col_value)
#         else:
#             df_trolley[col_name] = col_value

#     # Step4: データを間引く
#     # df_trolley = df_trolley[::thin_out]

#     return df_trolley


# def trolley_dict_fillna(img_idx, img_path, dfs_columns):
#     """
#     Args:
#         img_idx (int): 画像ファイルのインデックス
#         img_path (str): 画像ファイルのパス
#         dfs_columns(DataFrame columns): 結合先の列名
#     Return:
#         df_trolley(DataFrame): NaN埋めされたデータフレーム
#     """
#     df_trolley = pd.DataFrame(columns=dfs_columns)
#     df_trolley['ix'] = range(img_idx * 1000, img_idx * 1000 + 1000)
#     df_trolley.fillna(np.nan)
#     dir_area, camera_num = img_path.split("/")[1:3]
#     image_name = img_path.split('/')[-1]
#     # データフレームに挿入する項目・位置を指定
#     columns_to_insert = [("img_idx", img_idx, 0),
#                          ("dir_area", dir_area, 1),
#                          ("camera_num", camera_num, 2),
#                          ("image_name", image_name, 3)]

#     # データフレームにインデックス・画像名等を挿入する
#     for col_name, col_value, idx in columns_to_insert:
#         if col_name not in df_trolley.columns:
#             df_trolley.insert(idx, col_name, col_value)
#         else:
#             df_trolley[col_name] = col_value
    
#     return df_trolley

# @my_logger
def result_csv_load(config, rail_fpath):
    """ 結果CSVファイルをデータフレームとして読み込む
    Args:
        config(instance): 設定ファイル
        rail_fpath(str) : 結果ファイルの保存パス
    Return:
        df_csv(DataFrame): CSVファイルから作成したデータフレーム
    """
    # 結果CSVファイルがあれば読み込む
    # 無ければ空のデータフレームを作成する
    if os.path.exists(rail_fpath):
        df_csv = pd.read_csv(rail_fpath)
    else:
        df_csv = pd.DataFrame(columns=config.columns_list)
    return df_csv


# @my_logger
def result_csv_crop(df_csv, dir_area, camera_num, image_name, trolley_id):
    """ 解析対象画像の結果だけにデータフレームの行を絞り込む
    Args:
        df_csv(DataFrame): 対象のデータフレーム
        dir_area(str)    : 線区名
        camera_num(str)  : カメラ番号
        image_name(str)  : 画像ファイル名（拡張子付き）
        trolley_id(str)  : トロリーID
    Return:
        df_csv_crop(DataFrame): 絞込み後のデータフレーム
    """
    condition = (
        (df_csv['measurement_area'] == dir_area) &
        (df_csv['camera_num'] == camera_num) &
        (df_csv['image_name'] == image_name) &
        (df_csv['trolley_id'] == trolley_id)
    )
    # conditionで指定した条件に合う行だけを抽出してコピー
    return df_csv.loc[condition, :].copy()


def result_csv_drop(rail_fpath, dir_area, camera_num, image_name, trolley_id, config):
    """ 画像1枚・カメラ番号・TrolleyID単位で結果を削除する
    Args:
        rail_fpath(str)  : 結果CSVのファイルパス
        dir_area(str)    : 線区名
        camera_num(str)  : カメラ番号
        image_name(str)  : 画像ファイル名（拡張子付き）
        trolley_id(str)  : トロリーID
        config(instance) : 設定ファイル
    Return:
        None
    """
    df_csv = result_csv_load(config, rail_fpath)
    condition = (
        (df_csv['measurement_area'] == dir_area) &
        (df_csv['camera_num'] == camera_num) &
        (df_csv['image_name'] == image_name) &
        (df_csv['trolley_id'] == trolley_id)
    )
    df_csv.drop(df_csv[condition].index).to_csv(rail_fpath, index = False)
    return None


# @my_logger
def result_dict_to_csv(config, result_dict, idx, count, dir_area, camera_num, image_name, trolley_id, ix_list):
    """ 解析後のインスタンスから作成した辞書ファイルを結果CSVファイルに保存する
    Args:
        config(instance) : 設定ファイル
        df_csv(DataFrame): 結果CSVファイルから作成したデータフレーム
        rail_fpath(str)  : 結果CSVファイルの保存パス
        result_dict(dict): インスタンスから生成した辞書
        idx(int)         : 画像インデックス
        image_path(str)  : 画像パス
        image_name(str)  : 画像ファイル名
        trolley_id(str)  : トロリーID
        window(int)      : 標準偏差を計算するときのウィンドウサイズ
    Return:
        df_csv(DataFrame): 結果を更新後のデータフレーム
    """
    # インスタンスの内容をデータフレームとして読み込む
    df = pd.DataFrame.from_dict(result_dict[trolley_id], orient='index').T

    # データフレームにインデックス・画像名等を挿入
    df.insert(0, 'image_idx', idx + count - 1)
    df.insert(1, 'ix', ix_list[:len(df)])
    df['ix'] = df['ix'] + (idx + count - 1) * 1000
    df.insert(2, 'measurement_area', dir_area)
    df.insert(3, 'camera_num', camera_num)
    df.insert(4, 'image_name', image_name)
    df.insert(5, 'trolley_id', trolley_id)
    df.insert([df.columns.get_loc(c) for c in df.columns if 'estimated_lower_edge' in c][0] + 1,
              'estimated_width', df['estimated_lower_edge'] - df['estimated_upper_edge'])

    # 不足する列を追加する
    for i, col in enumerate(config.columns_list):
        if col not in df.columns:
            df.insert(i, col, pd.NA)

    return df

def experimental_result_dict_to_csv(config, result_dict, kiro_dict, kiro_init_dict, idx, count, dir_area, camera_num, image_name, trolley_id, x_init, ix_list):
    """ 解析後のインスタンスから作成した辞書ファイルを結果CSVファイルに保存する
        ※高崎検証用 一部線区でのみ使用可能
    Args:
        config(instance) : 設定ファイル
        result_dict(dict): インスタンスから生成した辞書
        kiro_dict(dict)  : 画像ごとのキロ程情報の辞書
        kiro_init_dict(dict): 画像ファイル名がkiro_dictに含まれる範囲の情報を記録した辞書
        idx(int)         : 画像インデックス
        image_path(str)  : 画像パス
        image_name(str)  : 画像ファイル名
        trolley_id(str)  : トロリーID
        window(int)      : 標準偏差を計算するときのウィンドウサイズ
        x_init(int)      : 分析を開始したx座標
        ix_list(list)    : ix入力用のリスト
    Return:
        df_csv(DataFrame): 結果を更新後のデータフレーム
    """
    # 画像ファイルとキロ程を紐づけるためのJSONファイルを辞書として読み込む
    # with open(f"{config.tdm_dir}/{dir_area}.json", 'r') as file:
    #     kiro_dict = json.load(file)

    # インスタンスの内容をデータフレームとして読み込む
    df = pd.DataFrame.from_dict(result_dict[trolley_id], orient='index').T
    # df.to_csv("temp.csv", index=False)    # デバッグ用

    # デバッグ用
    # ---------------------------------------
    # st.write(ix_list[x_init:(x_init+len(df))])
    # st.write(f"x_init = {x_init}")
    # st.write(f"len(df) = {len(df)}")
    # st.write(f"x_init+len(df) = {x_init+len(df)}")
    # st.write(f"len(ix_list[x_init:(x_init+len(df))]) = {len(ix_list[x_init:(x_init+len(df))])}")
    # ---------------------------------------

    # データフレームにインデックス・画像名等を挿入
    df.insert(0, 'image_idx', idx + count - 1)
    # st.write(df)    # デバッグ用
    if count == 1:
        df.insert(1, 'ix', ix_list[x_init:(x_init + len(df))])
    else:
        df.insert(1, 'ix', ix_list[:len(df)])
    df['ix'] = df['ix'] + (idx + count - 1) * 1000
    fname = image_name.split(".")[0]

    # -----------------------------------
    """
    画像ファイル名がマッチしない範囲のキロ程を計算して記録するコードを修正中
    """
    # -----------------------------------
    if kiro_dict:
        # キロ程の境界条件を取得
        kiro_tei_init_head = kiro_init_dict['KiroTei_init'][0]
        kiro_tei_init_tail = kiro_init_dict['KiroTei_init'][1]
        if fname in kiro_dict[camera_num].keys():
            DenchuNo = kiro_dict[camera_num][fname]['DenchuNo']
            kiro_tei = kiro_dict[camera_num][fname]['KiroTei']
            # st.write(f"Match   > kiro_tei: {kiro_tei}")
        else:
            # 画像ファイル名がマッチしない場合のキロ程を指定
            if idx + count - 1 <= kiro_init_dict['image_idx_init'][0]:
                DenchuNo = 0
                kiro_tei = kiro_tei_init_head - (kiro_init_dict['image_idx_init'][0] - (idx + count - 1)) * 2 / config.img_width
            else:
                DenchuNo = 1000
                kiro_tei = kiro_tei_init_tail + ((idx + count - 1) - kiro_init_dict['image_idx_init'][1]) * 2 / config.img_width
        kiro_tei_list = [kiro_tei + ix / config.img_width / 1000 * 2 for ix in config.ix_list]
        df.insert(2, 'pole_num', DenchuNo)
        if count == 1:
            df.insert(3, 'kiro_tei', kiro_tei_list[x_init:(x_init+len(df))])
        else:
            df.insert(3, 'kiro_tei', kiro_tei_list[:len(df)])
    else:
        df.insert(2, 'pole_num', "Empty")
        # if count == 1:
        #     df.insert(3, 'kiro_tei', ix_list[x_init:(x_init + len(df))])
        # else:
        #     df.insert(3, 'kiro_tei', ix_list[:len(df)])
        df.insert(3, 'kiro_tei', df['ix'] / 500000)

    df.insert(4, 'measurement_area', dir_area)
    df.insert(5, 'camera_num', camera_num)
    df.insert(6, 'image_name', image_name)
    df.insert(7, 'trolley_id', trolley_id)
    df.insert([df.columns.get_loc(c) for c in df.columns if 'estimated_lower_edge' in c][0] + 1,
              'estimated_width', df['estimated_lower_edge'] - df['estimated_upper_edge'])

    # 不足する列を追加する
    for i, col in enumerate(config.columns_list):
        if col not in df.columns:
            df.insert(i, col, pd.NA)

    return df

def experimental_get_image_match(list_images, kiro_dict, camera_num):
    """ ローカルの画像ファイル名リストについて、キロ程情報の辞書に含まれる範囲を取得する
    Args:
        list_images(list): ディレクトリ内のファイル名リスト
        kiro_dict(dict): 車モニのデータベースから作成したキロ程情報の辞書
        camera_num(str): 解析中のカメラ番号 (例)HD11
    Return:
        kiro_init_dict(dict): マッチした情報の辞書
            keys:
                image_name_init(list): 画像ファイル名[開始, 終了]
                image_idx_init(list): 画像インデックス[開始, 終了]
                DenchuNo_init(list): 電柱番号[開始, 終了]
                KiroTei_init(list): キロ程[開始, 終了]
    """
    find_kiro_idx_head = 0
    find_kiro_idx_tail = 0
    find_image_name_head = ""
    find_image_name_tail = ""
    kiro_keys = set(kiro_dict[camera_num].keys())  # 辞書のキーをセットに変換

    # find_kiro_idx_headを見つける
    for idx, fname in enumerate(list_images):
        image_name = re.split('[./]', fname)[-2]
        if image_name.split(".")[0] in kiro_keys:
            find_kiro_idx_head = idx
            find_image_name_head = image_name
            break

    # find_kiro_idx_tailを見つける
    for idx, fname in reversed(list(enumerate(list_images))):
        image_name = re.split('[./]', fname)[-2]
        if image_name.split(".")[0] in kiro_keys:
            find_kiro_idx_tail = idx
            find_image_name_tail = image_name
            break

    # find_kiro_idx_headが設定されていない場合の処理
    if not find_kiro_idx_head:
        find_kiro_idx_tail = len(list_images) - 1

    kiro_init_dict = {
        'image_name_init': [find_image_name_head, find_image_name_tail],
        'image_idx_init': [find_kiro_idx_head, find_kiro_idx_tail],
        'DenchuNo_init': [
            kiro_dict[camera_num][find_image_name_head]['DenchuNo'],
            kiro_dict[camera_num][find_image_name_tail]['DenchuNo']
        ],
        'KiroTei_init': [
            kiro_dict[camera_num][find_image_name_head]['KiroTei'],
            kiro_dict[camera_num][find_image_name_tail]['KiroTei']
        ],
    }
    return kiro_init_dict


# @my_logger
def dfcsv_update(config, df_csv, df):
    """ 解析結果dfの内容をdf_csvに追記/更新する
    Args:
        df_csv(DataFrame): 結果CSVファイルを読み込んだデータフレーム
        df(DataFrame): インスタンスから変換したデータフレーム（画像ごと）
        x_init(int): 解析開始時のx座標
        condition(Pandas Series): 指定条件への一致状態を記録した変数（画像ごと）
        count(int): 解析開始からの画像カウント（1枚目はcount=1）
    Return:
        merged(DataFrame): 結果CSVファイルを読み込んだデータフレーム
    """
    # グループ化のためのキーを定義
    grouping_keys = ['measurement_area', 'camera_num', 'image_name', 'trolley_id', 'ix']

    # 指定のキーに基づいてdfをdf_csvにマージ
    merged = pd.merge(df_csv, df, on=['measurement_area', 'camera_num', 'image_name', 'trolley_id', 'ix'], 
                      how='outer', suffixes=('', '_new'))

    # 一致する行があれば、dfの値でdf_csvの値を上書き
    for col in df.columns:
        if col not in grouping_keys:
            if col in merged.columns and (col + '_new') in merged.columns:
                # 2回目以降の実行用: colとcol+'_new'がカラム名にある場合だけ処理する
                merged[col] = merged[col + '_new'].combine_first(merged[col])
                merged.drop(col + '_new', axis=1, inplace=True)

    # df_csv(merged)のカラムの順番を合わせる
    merged = merged[config.columns_list]

    return merged

# @my_logger
def window2min_periods(window):
    """ 標準偏差を計算するためのウィンドウサイズからmin_periodsを設定する
    Args:
        window(int): ウィンドウサイズ
    Return:
        min_periods(int): 最小計算範囲
    """
    if window <= 2:
        window = 2
        min_periods = 1
    elif window > 2:
        min_periods = int(window / 2)
    return min_periods

def dfcsv_std_calc(df_csv, col_name, col_name_std, window, min_periods, col_name_ref):
    """ df_csvにおけるwidthの標準偏差を計算してdf_csvに追記する
    Args:
        df_csv(DataFrame): 結果CSVファイルを読み込んだデータフレーム
        col_name(str): 計算対象の列名
        col_name_std(str): 標準偏差を記録する列名
        window(int): ウィンドウサイズ
        min_periods(int): 最小計算範囲
        col_name_ref(str): NaNが含まれる行を除外する際に確認対象にする列名
    Return:
        df_csv(DataFrame): 標準偏差を追記したデータフレーム
    """
    # estimated_upper_edgeがNaNでない行だけ選択して標準偏差を計算
    non_nan_rows = df_csv[col_name_ref].notna()
    df_csv.loc[non_nan_rows, col_name_std] = df_csv.loc[non_nan_rows, col_name].rolling(window=window, min_periods=min_periods).std()
    return df_csv

# @my_logger
def trolley_dict_to_csv(config, rail_fpath, camera_num, base_images, window, log_view, progress_bar):
    """ ShelveファイルからCSVファイルを生成する
    Args:
        config: 設定ファイル
        rail_fpath (str): shelveファイルの保存パス
        camera_num (str): 選択されたカメラ番号
        base_images (list): カメラ番号に対応する画像パスのリスト
        thin_out (int): CSVの行を間引く間隔 (例)50 ⇒ 横50pxずつデータを記録する
        window (int): 標準偏差の計算に用いるウィンドウサイズ
        log_view(st.empty): Streamlitのコンテナ（ログ表示用のエリアを指定）
        progress_bar(st.progress): Streamlitのプログレスバー
    """
    # CSVファイルの保存パスを指定
    csv_fpath = rail_fpath.replace(".shelve", ".csv")
    log_view.write(f"csv_fpath:{csv_fpath}")
    
    # 標準偏差計算用>ウィンドウサイズからスライドウィンドウの最小計算単位を指定
    # min_periodsの指定値以下で標準偏差を計算する場合はNaNになる
    if window <= 2:
        window = 2
        min_periods = 1
    elif window > 2:
        min_periods = int(window / 2)
    # st.sidebar.write(f"window:{window}")
    # st.sidebar.write(f"min_periods:{min_periods}")

    # shelveファイルを読み込む
    with shelve.open(rail_fpath, flag='r', encoding="utf-8") as rail:
        # trolley_dict = copy.deepcopy(rail[camera_num])
        trolley_dict = rail[camera_num]

    df_concat = pd.DataFrame(columns=config.columns_list)
    for idx, image_path in enumerate(trolley_dict.keys()):
        # プログレスバーを更新
        progress_bar.progress(idx / len(base_images))

        # 線区名等の情報を取得
        dir_area, camera_num = image_path.split("/")[1:3]
        image_name = image_path.split('/')[-1]

        # shelveの中身をデータフレームにコピー
        for trolleyid in trolley_dict[image_path].keys():
            # print(f'trolley ID> {trolleyid}')
            df = pd.DataFrame.from_dict(trolley_dict[image_path][trolleyid], orient='index').T
            # <データ整形>データ数が1000行未満の場合に空白行を追加する
            if len(df) < 1000:
                num_rows_to_add = config.max_len - df.shape[0]
                if num_rows_to_add > 0:
                    empty_df = pd.DataFrame(np.nan, index=range(num_rows_to_add), columns=df.columns)
                    df = pd.concat([df, empty_df], ignore_index=True)
                    
            # データフレームにインデックス・画像名等を挿入
            df.insert(0, 'image_idx', idx)
            df.insert(1, 'ix', config.ix_list)
            df['ix'] = df['ix'] + idx * 1000
            df.insert(2, 'measurement_area', dir_area)
            df.insert(3, 'camera_num', camera_num)
            df.insert(4, 'image_name', image_name)
            df.insert(5, 'trolley_id', trolleyid)
            df.insert([df.columns.get_loc(c) for c in df.columns if 'estimated_lower_edge' in c][0] + 1,
                      'estimated_width', df['estimated_lower_edge'] - df['estimated_upper_edge'])

            # df['ix'] = ix_list
            # df['ix'] = df['ix'] + idx * 1000
            # df['estimated_width'] = df['estimated_lower_edge'] - df['estimated_upper_edge']
            # df['image_path'] = image_path
            # df['trolley_id'] = trolleyid
            try:
                df_concat = pd.concat([df_concat, df], ignore_index=True)
            except:
                print("concat error -> skip")

    # # estimated_widthの標準偏差を計算して記録する
    df_concat['estimated_width_std'] = df_concat['estimated_width'].rolling(window=window, min_periods=min_periods).std()

    # print(df_concat.shape)
    df_concat.to_csv(csv_fpath, encoding='cp932')
    # print(f'csv file convert -> {csv_fpath}')

    # 👇以前のコード
#     # 読み込んだ辞書からデータフレームを作成
#     dfs = pd.DataFrame()
#     # CSVの列名を準備する
#     column_name = [
#         f"{trolley_id}_{key}"
#         for trolley_id in config.trolley_ids
#         for key in config.result_keys
#     ]
#     # trolley_dictの内容を読み込む
#     for img_idx, img_path in enumerate(base_images):
#         # 変換の進捗をプログレスバーに表示する
#         progress_bar.progress(img_idx / len(base_images))
#         # img_pathの結果が空でないときに実行する
#         # log_view.write(f"{img_idx}> img_path: {img_path}")
#         if len(trolley_dict[img_path]):
#             # 解析結果があるとき
#             df_trolley = read_trolley_dict(config, trolley_dict, img_idx, img_path, column_name, thin_out).copy()
#         elif img_idx:
#             # img_pathの結果が空のとき & img_idxが0以外のとき
#             df_trolley = trolley_dict_fillna(img_idx, img_path, dfs.columns).copy()
#         elif img_idx:
#             # 1枚目の画像でエラーになる
#             print("解析結果がないため、CSVファイルを生成できませんでした。")
#             break
#         # df_trolleyを結合する
#         dfs = pd.concat([dfs, df_trolley], ignore_index=True)

#     # estimated_widthの標準偏差を計算して追記する
#     dfs = width_std_calc(config, dfs, window)

#     # データを間引く
#     dfs = dfs[::thin_out]

#     # データフレームからCSVファイルを生成してoutputディレクトリ内に保存する
#     dfs.to_csv(csv_fpath, encoding='cp932')

    return

# def width_std_calc(config, dfs, window):
#     """ estimated_widthの標準偏差を計算して追記する
#     Args:
#         config(dict)    : 設定ファイル
#         dfs(DataFrame)  : 計算対象のデータフレーム
#         window(int)   : スライドウィンドウのサイズ
#     Return:
#         dfs(DataFrame)  : 標準偏差を追記したデータフレーム
#     """
#     # ウィンドウサイズからスライドウィンドウの最小計算単位を指定
#     # min_periodsの指定値以下で標準偏差を計算する場合はNaNになる
#     if window <= 2:
#         window = 2
#         min_periods = 1
#     elif window > 2:
#         min_periods = int(window / 2)
#     # st.sidebar.write(f"window:{window}")
#     # st.sidebar.write(f"min_periods:{min_periods}")

#     # estimated_widthの列を取得
#     insert_positions = [
#         dfs.columns.get_loc(c) for c in dfs.columns if 'estimated_width' in c
#     ]

#     # 標準偏差を計算してwidthの右隣りに追記する
#     for trolley_id, insert_position in zip(config.trolley_ids, insert_positions):
#         width_col = trolley_id + "_estimated_width"
#         width_std_col = trolley_id + "_estimated_width_std"

#         # print(f"width_col    :{width_col}")
#         # print(f"width_std_col:{width_std_col}")

#         width_std_col_values = (
#             dfs[width_col]
#             .rolling(window=window, min_periods=min_periods)
#             .std()
#         )
#         dfs.insert(insert_position + 1, width_std_col, width_std_col_values)

#     return dfs


def load_shelves(rail_fpath, camera_num, base_images, idx):
    image_path = base_images[idx]
    with shelve.open(rail_fpath, writeback=True, encoding="utf-8") as rail:
        trolley_dict = copy.deepcopy(rail[camera_num][image_path])
    return trolley_dict



def default(o):
    # 車モニの情報からJSONファイルを作成するときに使用
    # JSONをdumpするときの対策
    # 参考：https://qiita.com/yuji38kwmt/items/0a1503f127fc3be17be0
    # print(f"{type(o)=}")
    if isinstance(o, np.int64):
        return int(o)
    elif isinstance(o, np.bool_):
        return bool(o)
    elif isinstance(o, np.ndarray):
        return list(o)
    raise TypeError(repr(o) + " is not JSON serializable")

    
def detect_init_edge(img, x_init):
    # 画像全体の平均輝度（背景輝度と同等とみなす）を算出
    img_array = np.array(img)
    img_flat = img_array[:, :, 0].flatten()
    img_random = []
    for i in range(1000): #全画素の平均は処理時間かかるのでランダム1000画素の輝度平均
        x = random.randint(0, 2047999)
        img_random.append(img_flat[x])

    # そのままの平均輝度
    avg_brightness1 = round(np.mean(img_random))

    # 標準偏差σ2をMaxに変換
    peakval = avg_brightness1 + np.std(img_flat) * 2.0
    img_random2 = [val if val <= peakval else peakval for val in img_random]

    # 標準偏差σ2をMaxに平均輝度を調整（そのままだと少し高めになってしまうため）
    avg_brightness2 = round(np.mean(img_random2))
    
    # img_slice = np.copy(img_array[:, 0, 0])
    img_slice = np.copy(img_array[:, x_init, 0])       # x_initに対応

    # 基準値の設定
    base_max = max(img_slice).astype(int)              # 輝度Max値　＝　画像全体の輝度Max値
    base_min = int(avg_brightness2)                    # 平均輝度

    # 輝度データの平滑化
    img_smooth1 = np.copy(img_slice)
    img_smooth1[1:2046] = [round(np.mean(img_smooth1[idx-1:idx+2])) for idx in range(1, 2046)]
    
    img_flat = np.std(img_flat)
    ex_center = round((base_max + base_min)/2)
    ex_max = base_max - img_flat
    ex_min = base_min + img_flat

    img_smooth2 = np.copy(img_smooth1)

#     # 一定以上の輝度変化は輝度Maxもしくは平均輝度に張り付ける
#     # 輝度変化の位置と幅を記録
#     candidate_init = []
#     high_point = [None, None, None, 1]    # トロリ線摺面を記録する箱（通常の摺面が周囲より明るい場合）
#     low_point = [None, None, None, -1]    # トロリ線摺面を記録する箱（輝度反転で摺面が周囲より暗い場合）
#     # for idx in range(len(img_smooth1)):
#     for idx in range(1999):
#         # 中途半端な輝度（ex_centerより高輝度）はbase_maxに変換
#         if ex_max > img_smooth1[idx] > ex_center:
#             img_smooth2[idx] = base_max
#         # 中途半端な輝度（ex_centerより低輝度）はbase_minに変換
#         elif ex_min < img_smooth1[idx] <= ex_center:
#             img_smooth2[idx] = base_min

#         # 輝度立ち上がり箇所を検出
#         if idx >= 1 and img_smooth2[idx] >= ex_max and img_smooth2[idx-1] <= ex_min:
#             high_point[0] = idx
#             low_point[1] = idx
#             if low_point[0] != None and abs(low_point[0] - low_point[1]) < 20:                # 摺面幅として明らかにあり得ない場合は除く
#                 low_point[2] = abs(low_point[0] - low_point[1])                               # 摺面幅
#                 candidate_init.append(low_point)
#             low_point = [None, None, None, -1]
            
#         # 輝度立ち下がり箇所を検出
#         elif idx >= 1 and img_smooth2[idx] <= ex_min and img_smooth2[idx-1] >= ex_max:
#             high_point[1] = idx
#             low_point[0] = idx
#             if high_point[0] != None and abs(high_point[0] - high_point[1]) < 20:              # 摺面幅として明らかにあり得ない場合は除く
#                 high_point[2] = abs(high_point[0] - high_point[1])                             # 摺面幅
#                 candidate_init.append(high_point)
#             high_point = [None, None, None, 1]

    candidate_init = search_candidate(img_smooth1, base_max, base_min, ex_max, ex_min, ex_center)
    
    # （検討中）初期値候補が見つからなかった場合の対処
    #           ex_centerを変えることで対処可能？？
    # search_state = False
    # while not search_state:
    #     candidate_init = search_candidate(img_smooth1, base_max, base_min, ex_max, ex_min, ex_center)
    #     candidate_len = len(candidate_init)
    #     if candidate_len != 0:
    #         search_state = True
    #     elif candidate_len == 0:
            
            
    # （補正）検出した点を傾きの中心にする
    # for i, edge in enumerate(search_list):
    for i, edge in enumerate(candidate_init):
        if edge[3] == 1:
            center_u = (max(img_slice[edge[0]-2:edge[0]+8]).astype(np.int16) + min(img_slice[edge[0]-7:edge[0]+3]).astype(np.int16)) / 2
            idx_uu = np.argmin(img_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
            idx_ul = np.argmax(img_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
            center_l = (max(img_slice[edge[1]-7:edge[1]+3]).astype(np.int16) + min(img_slice[edge[1]-2:edge[1]+8]).astype(np.int16)) / 2
            idx_lu = np.argmax(img_slice[edge[1]-7:edge[1]+3]) + (edge[1]-7)
            idx_ll = np.argmin(img_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
        elif edge[3] == -1:
            center_u = (max(img_slice[edge[0]-7:edge[0]+3]).astype(np.int16) + min(img_slice[edge[0]-2:edge[0]+8]).astype(np.int16)) / 2
            idx_uu = np.argmax(img_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
            idx_ul = np.argmin(img_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
            center_l = (max(img_slice[edge[1]-2:edge[1]+8]).astype(np.int16) + min(img_slice[edge[1]-7:edge[1]+3]).astype(np.int16)) / 2
            idx_lu = np.argmin(img_slice[edge[1]-7:edge[1]+2]) + (edge[1]-7)
            idx_ll = np.argmax(img_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
        if idx_uu < idx_ul:
            diff1 = abs(img_slice[idx_uu:idx_ul+1] - center_u)
            idx_u_new = np.argmin(diff1) + idx_uu
        else:
            idx_u_new = edge[0]
        if idx_lu < idx_ll:
            diff2 = abs(img_slice[idx_lu:idx_ll+1] - center_l) 
            idx_l_new = np.argmin(diff2) + idx_lu
        else:
            idx_l_new = edge[1]
        candidate_init[i][0:2] = [idx_u_new, idx_l_new]
    return candidate_init


def search_candidate(img_smooth2, base_max, base_min, ex_max, ex_min, ex_center):
    # 一定以上の輝度変化は輝度Maxもしくは平均輝度に張り付ける
    # 輝度変化の位置と幅を記録
    candidate_init = []
    high_point = [None, None, None, 1]    # 輝度変化の位置を記録する箱（周囲より明るい変化の場合）
    low_point = [None, None, None, -1]    # 輝度変化の位置を記録する箱（周囲より暗い変化の場合） ※輝度反転
    # for idx in range(len(img_smooth1)):
    for idx in range(1999):
        # 中途半端な輝度（ex_centerより高輝度）はbase_maxに変換
        if ex_max > img_smooth2[idx] > ex_center:
            img_smooth2[idx] = base_max
        # 中途半端な輝度（ex_centerより低輝度）はbase_minに変換
        elif ex_min < img_smooth2[idx] <= ex_center:
            img_smooth2[idx] = base_min

        # 輝度立ち上がり箇所を検出
        if idx >= 1 and img_smooth2[idx] >= ex_max and img_smooth2[idx-1] <= ex_min:
            high_point[0] = idx
            low_point[1] = idx
            if low_point[0] != None and abs(low_point[0] - low_point[1]) < 20:                # 摺面幅として明らかにあり得ない場合は除く
                low_point[2] = abs(low_point[0] - low_point[1])                               # 摺面幅
                candidate_init.append(low_point)
            low_point = [None, None, None, -1]
            
        # 輝度立ち下がり箇所を検出
        elif idx >= 1 and img_smooth2[idx] <= ex_min and img_smooth2[idx-1] >= ex_max:
            high_point[1] = idx
            low_point[0] = idx
            if high_point[0] != None and abs(high_point[0] - high_point[1]) < 20:              # 摺面幅として明らかにあり得ない場合は除く
                high_point[2] = abs(high_point[0] - high_point[1])                             # 摺面幅
                candidate_init.append(high_point)
            high_point = [None, None, None, 1]
    return candidate_init


def search_csv(outpath):                 # 2024.5.22 -->
    exist_csv = False
    list_csv = list_csvs(outpath)
    for file in list_csv:
        if 'rail_' and '.csv' in file:
            exist_csv = True
            break
    return exist_csv                     # --> 2024.5.22