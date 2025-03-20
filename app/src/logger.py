import time
import os
import logging
import sys
from pythonjsonlogger import jsonlogger
import pandas as pd
from dateutil import tz
import src.helpers as helpers
import streamlit as st


def my_logger(func):
    """ for DEBUG 関数の実行時間を標準出力で出力する
    Args:
        func(func): 計測対象の関数
    Return:
        wrapper(func): 関数の実行結果
    """
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(f"関数{func.__name__}の実行時間は{time.time() - start}")
        return result

    return wrapper


def get_log_path(office=None, date=None):
    """ ログファイルのパスを取得する
    Args:
        office(str): オフィス名 (例: "shinagawa/shinagawa")
        date(str): 日付（指定しない場合は今日の日付）
    Return:
        file_path(str): ログファイルのパス
    """
    # 日付が指定されていない場合は今日の日付を使用
    if date is None:
        date = time.strftime('%Y%m%d', time.localtime())
    
    # ファイル名の作成
    filename = f"cis_{date}.log"
    
    if office is None:
        # オフィスが指定されていない場合はルートに保存
        return filename
    
    # オフィス情報からログディレクトリのパスを構築
    log_dir = os.path.join("logs", office)
    
    # ディレクトリが存在しなければ作成
    os.makedirs(log_dir, exist_ok=True)
    
    # ログファイルのパスを返す
    return os.path.join(log_dir, filename)


def setup_logging(log_level=logging.INFO, office=None):
    """ ロギングの初期設定を実行
    Args:
        log_level(int): ログレベル
        office(str): オフィス名 (例: "shinagawa/shinagawa")
    """
    handlers = []
    formatter = jsonlogger.JsonFormatter("%(levelname)%(exc_info)%(message)")
    # 標準出力でのログ
    # sh = logging.StreamHandler(sys.stdout)
    # sh.setFormatter(formatter)
    # sh.setLevel(log_level)
    # handlers.append(sh)

    file_path = get_log_path(office)

    # 既存のログファイルが無かったら作成する
    if not os.path.exists(file_path):
        # ディレクトリも確認して作成（親ディレクトリが存在する場合のみ）
        parent_dir = os.path.dirname(file_path)
        if parent_dir:  # 親ディレクトリが空でない場合のみmakedirsを実行
            os.makedirs(parent_dir, exist_ok=True)
        with open(file_path, "w") as f:
            pass  # 空のファイルを作成

    # JSONでのログ
    h = logging.FileHandler(file_path, mode="a")
    h.setFormatter(jsonlogger.JsonFormatter())
    h.setLevel(log_level)
    handlers.append(h)

    logging.basicConfig(level=log_level, handlers=handlers, force=True)
    

def reset_logging(office=None, date=None):
    """ 既存のログファイルを初期化する
    Args:
        office(str): オフィス名 (例: "shinagawa/shinagawa")
        date(str): 日付（指定しない場合は今日の日付）
    """
    fpath = get_log_path(office, date)
    # ログファイルを初期化する
    with open(fpath, "w") as f:
        f.write("")
    st.error("ログファイルを削除しました")
    st.stop()


def load_logs(office=None, date=None):
    """ ログファイルをデータフレームとして読み込む
    Args:
        office(str): オフィス名 (例: "shinagawa/shinagawa")
        date(str): 日付（指定しない場合は今日の日付）
    Return:
        df(DataFrame): ログファイルを読み込んだデータフレーム
    """
    # ログファイルのパスを取得
    fpath = get_log_path(office, date)
    
    # ログファイルが存在しない場合は空のデータフレームを返す
    if not os.path.exists(fpath):
        return pd.DataFrame()
    
    # ログファイルを読み込む
    logs = []
    with open(fpath, 'r') as f:
        for line in f:
            try:
                log = eval(line)
                logs.append(log)
            except:
                pass
    # DataFrameを出力
    return pd.DataFrame(logs)


def preprocess_log_data(df):
    # 最初にデータフレームのコピーを作成
    df = df.copy()
    
    # データフレームが空の場合は空のデータフレームを返す
    if df.empty:
        return df

    df['start_time'] = pd.to_datetime(df['start_time'])

    # UTCタイムゾーンを設定
    df['start_time'] = df['start_time'].dt.tz_localize('UTC')
    jst = tz.gettz('Asia/Tokyo')

    df['start_time'] = df['start_time'].dt.tz_convert(jst)
    df = df.dropna(subset=["process_time"])

    # 新しいカラム`analysis_time`を計算
    df['analysis_time'] = df['process_time'].diff()
    mask = df['start_time'] != df['start_time'].shift(1)
    df.loc[mask, 'analysis_time'] = df.loc[mask, 'process_time']

    # `analysis_time`カラムを`process_time`の右側に挿入
    column_index = df.columns.get_loc('process_time') + 1
    df = df.reindex(columns=list(df.columns[:column_index]) + ['analysis_time'] + list(df.columns[column_index:-1]))

    return df.copy()


def put_log(level, message, start, method, image_path, trolley_id, idx, count, error_message=None, office=None):
    """ ログファイルに記録する
    Args:
        level(str): ログのレベル
        message(str): ログに記録する第1パラメータ
        start(datetime): 処理の開始時刻
        method(str): 利用したアルゴリズム (kalman等)
        image_path(str): 画像ファイルのパス
        trolley_id(str): トロリーID
        idx(int): 画像インデックス
        count(int): 何枚目の画像を処理したときのログか
        error_message(str): エラーメッセージ
        office(str): オフィス名 (例: "shinagawa/shinagawa")
    """
    # ログ設定を適用（officeパラメータを追加）
    setup_logging(office=office)
    
    logger = logging.getLogger()

    image_name = image_path.split('/')[-1]
    dir_area, camera_num = image_path.split("/")[1:3]

    extra = {
        "log_level": level.upper(),
        "start_time": time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(start)),
        "process_time": time.time() - start,
        "method": method,
        "measurement_area": dir_area,
        "camera_num": camera_num,
        "image_name": image_name,
        "trolley_id": trolley_id,
        "image_idx": idx + count - 1,
        "image_count": count
    }

    if error_message:
        extra["error"] = error_message

    if level == "info":
        logger.info(message, extra=extra)
    # 基本はログレベルがINFOのためコメントアウト
    # elif level == "debug":
    #     logger.debug(message, extra=extra)
    elif level == "warning":
        logger.warning(message, extra=extra)
    elif level == "error":
        logger.error(message, extra=extra)

    return
