import os
import glob
import re
import copy
import shutil
import boto3
from botocore.exceptions import NoCredentialsError
import datetime
import shelve
import streamlit as st
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image


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
    if str_list[3] == 'St':
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
    if len(rail) < 2:    # 初めてrailが生成された場合は"name"だけなのでlen(rail)は1
        rail_check = False
    else:    # 一度でも解析されるとtrolley1,2,3が追加されるため3以上
        rail_check = any(len(rail[camera_num][image_path]) > 2 for image_path in base_images)
    if not rail_check:
        print('rail initilize')
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
def get_file_content_as_string(img_dir_name, path):
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
    client  = boto3.client('s3')
    # バケット名
    bucket  = 'trolley-monitor'
    
    paginator = client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Prefix=prefix):
        if result.get('Contents') is not None:
            for file in result.get('Contents'):
                if not os.path.exists(os.path.dirname(local + os.sep + file.get('Key'))):
                    os.makedirs(os.path.dirname(local + os.sep + file.get('Key')))
                client.download_file(bucket, file.get('Key'), local + os.sep + file.get('Key'))
        
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


# @st.cache()
def S3_EBS_imgs_dir_Compare(S3_dir_list, EBS_dir_list):
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

    return df


@st.cache()
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
        dir_path = os.path.join(config.output_dir, dir_area, camera_type)
        
        # ディレクトリ内のファイルをチェック
        try:
            for file in os.listdir(dir_path):
                if "rail.shelve" in file:  # ファイル名に"rail.shelve"が含まれるかをチェック
                    result.append([f"{camera_name}_{camera_type}", "○"])
                    break
            else:  # ディレクトリ内に"rail.shelve"が含まれるファイルがない場合
                result.append([f"{camera_name}_{camera_type}", "×"])
        except FileNotFoundError:  # ディレクトリが存在しない場合
            result.append([f"{camera_name}_{camera_type}", "×"])

    # 結果をPandasデータフレームに変換
    df = pd.DataFrame(result, columns=["カメラ番号", "結果有無"])

    return df


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


def trim_trolley_dict(config, trolley_dict, img_path):
    """ shelveから読み取ったtrolley_dictの行数を揃える
    Args:
        config: 設定用ファイル
        trolley_dict(dict): shleveから読み込んだ辞書
        img_path(str): 解析対象の画像パス
    Return:
        trolley_dict(dict): 更新されたtrolley_dict
    Memo:
        デバッグ用のprint文はコメントアウトしています。
        必要な場合は有効化してください。
    """
    for trolley_id in config.trolley_ids:
        # print(trolley_id)
        for key in trolley_dict[img_path][trolley_id].keys():
            if not trolley_dict[img_path][trolley_id][key]:
                # 空のリストの場合
                # print("Empty list")
                trolley_dict[img_path][trolley_id][key] = [np.nan] * config.max_len
            # elif isinstance(trolley_dict[img_path][trolley_id][key], (int, float, str)):
            elif not isinstance(trolley_dict[img_path][trolley_id][key], list):
                # リスト以外(数値等)の場合
                # print("Not list")
                trolley_dict[img_path][trolley_id][key] = [trolley_dict[img_path][trolley_id][key]] + [np.nan] * (config.max_len - 1)
            value_len = len(trolley_dict[img_path][trolley_id][key])
            # print(f"{key} -> type: {type(trolley_dict[img_path][trolley_id][key])}, len:{value_len}")
            if config.max_len < value_len:
                config.max_len = value_len
        # print(f"Max Length: {config.max_len}")
    return trolley_dict


def read_trolley_dict(config, trolley_dict, img_path):
    """ 画像パスごとにデータを読み込む
    Args:
        config: 設定用ファイル
        trolley_dict(dict): shleveから読み込んだ辞書
        img_path(str): 解析対象の画像パス
    Return:
        df_trolley(DataFrame): trolley_dictから作成したデータフレーム
    """
    
    # trolley_dictの行数を揃える
    trim_trolley_dict(config, trolley_dict, img_path)
    
    df_trolley = pd.DataFrame()
    for idx, trolley_id in enumerate(config.trolley_ids):
        column_name = [trolley_id + "_" + key for key in list(trolley_dict[img_path][trolley_id].keys())]
        df = pd.DataFrame(trolley_dict[img_path][trolley_id]).copy()
        df.columns = column_name
        if not idx:
            df_trolley = df.copy()
            df_trolley = df_trolley.rename(columns={trolley_id + "_ix" : 'ix'})
        else:
            df_trolley = pd.concat([df_trolley, df], axis=1).copy()
    # 読み込まれたデータフレームの整形
    # trolleyX_ixの列を削除
    for col in df_trolley.columns:
        # 列名に'_ix'が含まれる場合
        if '_ix' in col:
            # その列を削除
            df_trolley = df_trolley.drop(col, axis=1)
    # 画像名を記録する
    if not "img_path" in df_trolley.columns:
        df_trolley.insert(0, 'img_path', img_path)
    else:
        df_trolley["img_path"] = img_path
    return df_trolley


def trolley_dict_to_csv(config, rail_fpath, camera_num, base_images):
    """ ShelveファイルからCSVファイルを生成する
    Args:
        config: 設定ファイル
        rail_fpath (str): shelveファイルの保存パス
        camera_num (str): 選択されたカメラ番号
    """
    # CSVファイルの保存パスを指定
    csv_fpath = rail_fpath.replace(".shelve", ".csv")
    st.sidebar.write(f"csv_fpath:{csv_fpath}")

    # shelveファイルを読み込む
    with shelve.open(rail_fpath) as rail:
        trolley_dict = copy.deepcopy(rail[camera_num])

    # 読み込んだ辞書からデータフレームを作成する
    dfs = pd.DataFrame()
    for idx, img_path in enumerate(base_images):
        # print(f"{idx}> img_path: {img_path}")
        try:
            df_trolley = read_trolley_dict(config, trolley_dict, img_path).copy()
            # ixの値が連番になるように修正
            df_trolley['ix'] = df_trolley['ix'] + 1000 * idx
            dfs = pd.concat([dfs, df_trolley], ignore_index=True)
        except Exception as e:
            st.sidebar.write(f"解析エラーで中断しました。中断した画像👇")
            st.sidebar.write(f"{idx}> img_path: {img_path}")
            # st.sidebar.error(f"Error> {e}")
            break
    
    # データフレームからCSVファイルを生成してoutputディレクトリ内に保存する
    dfs.to_csv(csv_fpath, encoding='cp932')
    
    return


