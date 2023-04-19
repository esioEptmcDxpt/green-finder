import numpy as np
import cv2
from PIL import Image
from .config import appProperties
from .trolley import trolley


class similar_pixel(trolley):
    """トロリ情報を継承し、類似ピクセルの計算用の初期化とアップデートを実施
    Args:
        trolley (class): トロリ線のパラメータ
        appProperties (class) : 計算条件の設定用ファイル
    Parameters:

    Methods:
        __init__: 各種パラメータの初期化
    """
    
    def __init__(self):
        print("init")
    
    
if __name__ == '__main__':
    print('set similar_pixel class')
    