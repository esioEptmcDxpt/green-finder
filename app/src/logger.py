import time
import os
import logging
import sys
from pythonjsonlogger import jsonlogger
import pandas as pd
from dateutil import tz
import src.helpers as helpers


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


def setup_logging(log_level=logging.INFO):
    """ ロギングの初期設定を実行
    """
    handlers = []
    formatter = jsonlogger.JsonFormatter("%(levelname)%(exc_info)%(message)")
    # 標準出力でのログ
    # sh = logging.StreamHandler(sys.stdout)
    # sh.setFormatter(formatter)
    # sh.setLevel(log_level)
    # handlers.append(sh)

    file_path = "tts.log"

    # 既存のログファイルが無かったら作成する
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            pass  # 空のファイルを作成

    # JSONでのログ
    h = logging.FileHandler(file_path, mode="a")
    h.setFormatter(jsonlogger.JsonFormatter())
    h.setLevel(log_level)
    handlers.append(h)

    logging.basicConfig(level=log_level, handlers=handlers, force=True)
    

def reset_logging():
    """ 既存のログファイルを初期化する
    """
    fpath = "tts.log"
    # tts.logを初期化する
    with open(fpath, "w") as f:
        f.write("")
    st.error("ログファイルを削除しました")
    st.stop()


def load_logs(fpath):
    """ ログファイルをデータフレームとして読み込む
    Args:
        fpath(str): ログファイルのパス
    Return:
        df(DataFrame): ログファイルを読み込んだデータフレーム
    """
    # ログファイルを読み込む
    logs = []
    with open('tts.log', 'r') as f:
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


def put_log(level, message, start, method, image_path, trolley_id, idx, count, error_message=None):
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
        kiro_dict(dict): キロ程情報（車モニから取得）
        error_message(str): エラーメッセージ
    """
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
