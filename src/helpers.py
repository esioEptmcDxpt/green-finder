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
from src.logger import my_logger


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
        print('rail initilize')
        print(f'dir_area: {rail["name"]}')
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
        # ディレクトリのパスを作成
        file_path = os.path.join(config.output_dir, dir_area, camera_type, "rail.csv")
        # ディレクトリ内のファイルをチェック
        if os.path.exists(file_path):
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
            file_path = os.path.join(config.output_dir, dir_area, camera_type, "rail.csv")
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
    max_val = float('-inf')
    with open(file_path, 'r', encoding="utf-8") as file:
        # Skip header
        file.readline()
        for line in file:
            try:
                value = float(line.split(',', 1)[0])  # Split only at the first comma
                if value > max_val:
                    max_val = value
            except ValueError:
                continue
    return max_val

def read_csv_idx(camera_name, camera_type, file_path):
    """ check_camera_dirs_addIdxLen用の関数
    Args:
        ile_path(str): CSVファイルの保存パス
    Return:
        result_list(list): 結果データフレーム追記用のリスト
    """
    if os.path.exists(file_path):
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

def experimental_result_dict_to_csv(config, result_dict, kiro_dict, kiro_init_dict, idx, count, dir_area, camera_num, image_name, trolley_id, ix_list):
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
    Return:
        df_csv(DataFrame): 結果を更新後のデータフレーム
    """
    # 画像ファイルとキロ程を紐づけるためのJSONファイルを辞書として読み込む
    # with open(f"{config.tdm_dir}/{dir_area}.json", 'r') as file:
    #     kiro_dict = json.load(file)

    # キロ程の境界条件を取得
    kiro_tei_init_head = kiro_init_dict['KiroTei_init'][0]
    kiro_tei_init_tail = kiro_init_dict['KiroTei_init'][1]

    # インスタンスの内容をデータフレームとして読み込む
    df = pd.DataFrame.from_dict(result_dict[trolley_id], orient='index').T

    # データフレームにインデックス・画像名等を挿入
    df.insert(0, 'image_idx', idx + count - 1)
    df.insert(1, 'ix', ix_list[:len(df)])
    df['ix'] = df['ix'] + (idx + count - 1) * 1000
    fname = image_name.split(".")[0]

    # -----------------------------------
    """
    画像ファイル名がマッチしない範囲のキロ程を計算して記録するコードを修正中
    """
    # -----------------------------------

    if fname in kiro_dict[camera_num].keys():
        DenchuNo = kiro_dict[camera_num][fname]['DenchuNo']
        kiro_tei = kiro_dict[camera_num][fname]['KiroTei']
        st.write(f"Match   > kiro_tei: {kiro_tei}")
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
    df.insert(3, 'kiro_tei', kiro_tei_list[:len(df)])
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
    print(f'csv file convert -> {csv_fpath}')

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
