import random
import statistics
import streamlit as st
import math
import numpy as np
from PIL import Image
from src.config import appProperties
from src.trolley import trolley
from src.logger import my_logger


class pixel(trolley):
    """ トロリ情報を継承し、類似ピクセルの計算用の初期化とアップデートを実施
    Args:
        trolley (class): トロリ線のパラメータ
        appProperties (class) : 計算条件の設定用ファイル
    Parameters:

    Methods:
        __init__: 各種パラメータの初期化
    """
    config = appProperties('config.yml')

    def __init__(self, trolley_id, y_init_l, y_init_u):
        super().__init__(trolley_id, y_init_l, y_init_u)
        # ピクセルエッジ検出検出向け
        # 検出結果
        self.search_list = []    # トロリ線検出位置
        self.last_state = []    # 過去1px分の検出位置
        self.upper_line = []    # 画像内の検出位置
        self.lower_line = []    # 画像内の検出位置
        self.upper_diff = []    # 検出位置の差分
        self.lower_diff = []    # 検出位置の差分
        self.w_ear = 0
        self.as_aj = 0
        # 解析用の属性
        self.upper_boundary = []    # 輝度の立上り／立下りサーチ範囲の設定
        self.lower_boundary = []    # 輝度の立上り／立下りサーチ範囲の設定
        self.avg_brightness = []    # 画面全体の平均輝度
        self.sigmoid_edge_u = None    # 理想形のエッジ配列
        self.sigmoid_edge_l = None    # 理想形のエッジ配列
        self.last_upper_line = []    # 過去5pxの検出位置
        self.last_lower_line = []    # 過去5pxの検出位置
        self.edge_std_list_u = []    # 過去10px分のトロリ線周りの輝度配列
        self.edge_std_list_l = []    # 過去10px分のトロリ線周りの輝度配列
        self.edge_std_u = None    # 過去10px分のトロリ線周りの輝度配列の平均
        self.edge_std_l = None    # 過去10px分のトロリ線周りの輝度配列の平均
        self.slope_dir = None    # 立上りの向き (旧)slope_max < slope_min: 1 else -1
        # 解析用 元picture
        self.im_org = None    # 解析対象画像のnumpy配列
        self.im_trolley = None    # 検出した位置の情報（画像色入れ用）
        self.im_slice_org = None    # 左端縦1px分の輝度情報（計算前の値を格納）
        self.im_slice = None    # 左端縦1px分の輝度情報
        # エラーログ
        self.err_log_u = []    # Error log on Upper edge
        self.err_log_l = []    # Error log on Lower edge
        self.err_skip = [0, 0, 0, 0]    # pixel skip error
        self.err_diff = [0, 0, 0, 0]    # Difference too large error
        self.err_edge = [0, 0, 0, 0]    # No edge error
        self.err_width = [0, 0, 0, 0]    # trolley wear width error
        self.err_nan = [0, 0]    # Error count

        if trolley_id == 1:
            self.isInFrame = True
        else:
            self.isInFrame = False

    def reset_trolley(self):
        """ トロリ線消失リセット
        """
        self.edge_std_list_u = []
        self.edge_std_list_l = []
        self.edge_std_u = None
        self.edge_std_l = None
        self.err_skip = [0, 0, 0, 0]
        self.err_diff = [0, 0, 0, 0]
        self.err_edge = [0, 0, 0, 0]
        self.err_width = [0, 0, 0, 0]
        self.err_nan = [0, 0]
        self.w_ear = 0
        self.as_aj = 0
        self.isInFrame = False
        return

    def reload_image_init(self):
        """ 次の画像に移行したときに結果保存用の属性を初期化する
        """
        # self.reset_trolley()
        # 解析結果
        self.ix = []
        self.estimated_upper_edge = []
        self.estimated_lower_edge = []
        self.estimated_width = []
        self.estimated_slope = []    # (メモ)どんな結果が格納される？ ピクセルエッジでも使うか？
        self.brightness_center = []
        self.brightness_mean = []
        self.brightness_std = []
        # 内部変数
        self.upper_line = []    # 画像内の検出位置
        self.lower_line = []    # 画像内の検出位置
        self.upper_diff = []    # 検出位置の差分
        self.lower_diff = []    # 検出位置の差分
        self.w_ear = 0
        self.as_aj = 0
        # 解析用の属性
        self.upper_boundary = []    # 輝度の立上り／立下りサーチ範囲の設定
        self.lower_boundary = []    # 輝度の立上り／立下りサーチ範囲の設定
        self.avg_brightness = []    # 画面全体の平均輝度
        self.sigmoid_edge_u = None    # 理想形のエッジ配列
        self.sigmoid_edge_l = None    # 理想形のエッジ配列
        # self.last_upper_line = []    # 過去5pxの検出位置
        # self.last_lower_line = []    # 過去5pxの検出位置
        # self.edge_std_list_u = []    # 過去10px分のトロリ線周りの輝度配列
        # self.edge_std_list_l = []    # 過去10px分のトロリ線周りの輝度配列
        # self.edge_std_u = None    # 過去10px分のトロリ線周りの輝度配列の平均
        # self.edge_std_l = None    # 過去10px分のトロリ線周りの輝度配列の平均
        # self.slope_dir = None    # 立上りの向き (旧)slope_max < slope_min: 1 else -1
        # 解析用 元picture
        self.im_org = None    # 解析対象画像のnumpy配列
        self.im_trolley = None    # 検出した位置の情報（画像色入れ用）
        self.im_slice_org = None    # 左端縦1px分の輝度情報（計算前の値を格納）
        self.im_slice = None    # 左端縦1px分の輝度情報
        return

    @my_logger
    def load_picture(self, im_org):
        # ピクセル配列を格納する
        self.im_org = im_org
        self.im_trolley = np.zeros_like(self.im_org).astype(int)

        # 画面全体の平均輝度（背景輝度と同等とみなす）を算出
        img = self.im_org
        im_r = img[:, :, 0].flatten()
        im_random = []
        for i in range(1000):  # 全画素の平均は処理時間かかるのでランダム1000画素の輝度平均
            x = random.randint(0, 2047999)
            im_random.append(im_r[x])
        self.avg_brightness = round(np.mean(im_random))

        # シグモイド関数を使って理想形のエッジ配列を作成
        sigmoid_max = max(im_r).astype(int)      # 輝度Max値 ＝ 画像全体の輝度Max値
        sigmoid_min = int(self.avg_brightness)   # 輝度Min値 ＝ 背景輝度(画像全体の平均輝度）
        x = np.arange(-7, 8, 1)
        self.sigmoid_edge_u = (sigmoid_max - sigmoid_min) / (1 + np.exp(-x/0.5)) + sigmoid_min
        self.sigmoid_edge_l = (-sigmoid_max + sigmoid_min) / (1 + np.exp(-x/0.5)) + sigmoid_max
        return

    @my_logger
    def load_picture_duplicate(self, trolley1):
        self.im_org = trolley1.im_org
        self.im_trolley = trolley1.im_trolley
        self.avg_brightness = trolley1.avg_brightness
        self.sigmoid_edge_u = trolley1.sigmoid_edge_u
        self.sigmoid_edge_l = trolley1.sigmoid_edge_l
        return

    @my_logger
    def set_init_val(self, ix, xin, auto_edge):
        img = self.im_org
        if auto_edge:
            self.upper_boundary = self.search_list[0][0]
            self.lower_boundary = self.search_list[0][1]
            self.last_state = self.search_list[0][0:2]
            self.slope_dir = self.search_list[0][2]
        elif xin:
            # 画像1の中心点設定と輝度の立上り／立下りサーチ範囲の設定
            width = 34
            start = int(xin) - width // 2
            end = int(xin) + width // 2
            # 画像1のトロリ線境界位置の初期値
            im_slice = np.copy(img[:, 0, 0])
            # 傾きから初期値算出
            slope = np.gradient(im_slice[start:end].astype(np.int16))
            slope_max = start + np.argmax(slope)
            slope_min = start + np.argmin(slope)
            upper = min([slope_max, slope_min])
            lower = max([slope_max, slope_min])
            self.upper_boundary = upper
            self.lower_boundary = lower
            self.last_state = [upper, lower]
            # 初期値から輝度の向きを確認
            self.slope_dir = 1 if slope_max < slope_min else -1
        else:
            st.warning('トロリ線の初期値が正しく設定できませんでした。やり直しえてください。')
            st.stop()
        return

    @my_logger
    def search_trolley_init(self, ix):
        """ 摺面エッジ初期位置の自動サーチ
        Args:
            ix (int): エッジ検索するx座標(基本は0 ※左端)
        """
        # 横1ピクセル、縦全ピクセル切り出し
        # img = self.im_org
        im_slice_org = np.copy(self.im_org[:, ix, 0])
        im_slice = np.copy(self.im_org[:, ix, 0])

        # サーチ範囲
        st = 7
        ed = 2040

        # 切り出した縦ピクセルのノイズを除去
        # im_slice[st:ed] = [round(np.mean(im_slice_org[i-1:i+2])) for i in range(st, ed)]

        # 高速化のために修正中👇
        kernel = np.ones(3) / 3
        im_slice_padded = np.pad(im_slice_org, (1, 1), 'constant', constant_values=0)
        im_slice[st:ed] = np.round(np.convolve(im_slice_padded, kernel, 'valid')[st-1:ed-1])

        # 理想的なエッジ配列に近い場所をサーチ
        # ここから元のコード
        # slope_val_u, slope_val_l, slope_idx_u, slope_idx_l = [], [], [], []
        # for i in range(st, ed):
        #     diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.sigmoid_edge_u.astype(int)))
        #     slope_val_u.append(diff1)
        #     slope_idx_u.append(i)
        #     diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.sigmoid_edge_l.astype(int)))
        #     slope_val_l.append(diff2)
        #     slope_idx_l.append(i)
        # slope_val_u = np.array(slope_val_u)
        # slope_val_l = np.array(slope_val_l)
        # # slope_sort_u = np.argsort(slope_val_u)    # 未使用
        # # slope_sort_l = np.argsort(slope_val_l)    # 未使用
        # ここまで元のコード👆
        
        # 高速化のために修正中👇
        window_size = 15  # window size is 15 in the original code because i-7:i+8 creates a window of size 15
        im_slice_windows = np.lib.stride_tricks.sliding_window_view(im_slice.astype(int), (window_size,))

        diff_u = np.abs(im_slice_windows - self.sigmoid_edge_u.astype(int))
        slope_val_u = np.sum(diff_u, axis=1)

        diff_l = np.abs(im_slice_windows - self.sigmoid_edge_l.astype(int))
        slope_val_l = np.sum(diff_l, axis=1)
        # ここまで修正中👆

        # ここから元のコード
        list_idx, list_val = [], []
        for idx_u, val_u in enumerate(slope_val_u):
            for idx_l, val_l in enumerate(slope_val_l):
                if (
                    idx_u < idx_l and                         # ピクセル位置は upper < lowerであること
                    0 <= (idx_u - idx_u) <= 35 and            # 摺面幅が明らかにあり得ない場合を除外
                    (val_u + val_l) <= 400                    # 誤差が大きい場合は除外
                ):
                    list_idx.append([idx_u+st, idx_l+st, 1])  # 摺面が立ち上があり→立下りの場合
                    list_val.append(val_u + val_l)
                elif (
                    idx_l < idx_u and                          # ピクセル位置は lower < upperであること
                    0 <= (idx_u - idx_l) <= 35 and             # 摺面幅が明らかにあり得ない場合を除外
                    (val_u + val_l) <= 400                     # 誤差が大きい場合は除外
                ):
                    list_idx.append([idx_l+st, idx_u+st, -1])  # 摺面が立ち下があり→立上りの場合
                    list_val.append(val_u + val_l)
        # ここまで元のコード👆
        
        # 高速化のために修正中👇
        idx_u, idx_l = np.ogrid[:len(slope_val_u), :len(slope_val_l)]
        val_u, val_l = slope_val_u[:, None], slope_val_l[None, :]
        total_val = val_u + val_l

        # Conditions for the upper < lower case
        cond1 = (idx_u < idx_l) & (0 <= (idx_l - idx_u) <= 35) & (total_val <= 400)
        list_idx1 = np.array([idx_u[cond1]+st, idx_l[cond1]+st, np.ones(np.sum(cond1))]).T
        list_val1 = total_val[cond1]

        # Conditions for the lower < upper case
        cond2 = (idx_l < idx_u) & (0 <= (idx_u - idx_l) <= 35) & (total_val <= 400)
        list_idx2 = np.array([idx_l[cond2]+st, idx_u[cond2]+st, -np.ones(np.sum(cond2))]).T
        list_val2 = total_val[cond2]

        # Combine the results
        list_idx = np.concatenate([list_idx1, list_idx2])
        list_val = np.concatenate([list_val1, list_val2])
        # ここまで修正中👆

        search_list = []
        for i in np.argsort(list_val):
            search_list.append(list_idx[i])

        # （補正）検出した点を傾きの中心にする
        for i, edge in enumerate(search_list):
            if edge[2] == 1:
                center_u = (max(im_slice[edge[0]-2:edge[0]+8]).astype(np.int16) + min(im_slice[edge[0]-7:edge[0]+3]).astype(np.int16)) / 2
                idx_uu = np.argmin(im_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
                idx_ul = np.argmax(im_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
                center_l = (max(im_slice[edge[1]-7:edge[1]+3]).astype(np.int16) + min(im_slice[edge[1]-2:edge[1]+8]).astype(np.int16)) / 2
                idx_lu = np.argmax(im_slice[edge[1]-7:edge[1]+3]) + (edge[1]-7)
                idx_ll = np.argmin(im_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
            elif edge[2] == -1:
                center_u = (max(im_slice[edge[0]-7:edge[0]+3]).astype(np.int16) + min(im_slice[edge[0]-2:edge[0]+8]).astype(np.int16)) / 2
                idx_uu = np.argmax(im_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
                idx_ul = np.argmin(im_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
                center_l = (max(im_slice[edge[1]-2:edge[1]+8]).astype(np.int16) + min(im_slice[edge[1]-7:edge[1]+3]).astype(np.int16)) / 2
                idx_lu = np.argmin(im_slice[edge[1]-7:edge[1]+2]) + (edge[1]-7)
                idx_ll = np.argmax(im_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
            diff1 = abs(im_slice[idx_uu:idx_ul+1] - center_u)
            idx_u_new = np.argmin(diff1) + idx_uu
            diff2 = abs(im_slice[idx_lu:idx_ll+1] - center_l)
            idx_l_new = np.argmin(diff2) + idx_lu
            search_list[i][0:2] = [idx_u_new, idx_l_new]

        # search_listを更新する
        self.search_list = search_list
        return

    def mean_brightness(self):
        """ 画像内の平均輝度を計算(背景とみなす)
        """
        # img = self.picture['im_org']
        img = self.im_org
        im_r = img[:, :, 0].flatten()
        im_random = []
        for i in range(1000):  # 全画素の平均は処理時間かかるのでランダム1000画素の平均
            x = random.randint(0, 2047999)
            im_random.append(im_r[x])
        self.avg_brightness = round(np.mean(im_random))
        return

    def search_trolley(self, ix):
        """ トロリ線摺動面を検出する
        Args:
            ix (int): x座標値
        """
        if (
            self.trolley_id == 1 or
            (self.trolley_id == 2 and self.w_ear >= 1) or
            (self.trolley_id == 3 and self.as_aj >= 1)
        ):
            # (old) 新規画像はエラーをリセット
            # (old) if file_idx == 0 and ix == 0:
            # 画像左端の場合はエラーをリセットする
            if ix == 0:
                self.err_skip = [0, 0, 0, 0]
                self.err_diff = [0, 0, 0, 0]
                self.err_edge = [0, 0, 0, 0]
                self.err_width = [0, 0, 0, 0]
                self.err_nan = [0, 0]

            # 前回の検出値（上端、下端、中心）
            upper = np.round(self.last_state[0]).astype(np.int16)
            lower = np.round(self.last_state[1]).astype(np.int16)
            # center = round((upper + lower) / 2)    # 未使用

            # 過去5ピクセル平均値（上端、下端、中心）（初回のみ初期値）
            # "upper_line"が空の場合と、"upper_line"にnanが含まれる場合
            if (
                len(self.last_upper_line) == 0 or
                np.isnan(self.last_upper_line[-5:]).any(axis=0)
               ):
                upper_avg = upper
                lower_avg = lower
            else:
                # 直前の値を優先した平均
                upper_avg = np.mean(np.append([self.last_upper_line], self.last_upper_line[-1])).astype(np.int16)
                lower_avg = np.mean(np.append([self.last_lower_line], self.last_lower_line[-1])).astype(np.int16)
            center_avg = np.mean([upper_avg, lower_avg]).astype(np.int16)

            # 横1ピクセル、縦全ピクセル切り出し
            img = self.im_org
            im_slice_org = np.copy(img[:, ix, 0])
            im_slice = np.copy(img[:, ix, 0])

            # 切り出した縦ピクセルのノイズを除去（トロリ線を検出した周辺に限定）
            st = upper - 20 if upper >= 21 else 1
            ed = lower + 21 if lower <= 2025 else 2045
            im_slice[st:ed] = [round(np.mean(im_slice_org[i-1:i+2])) for i in range(st, ed)]

            # エッジ基準を作成
            # if file_idx == 0 and ix == 0:
            if ix == 0:
                self.edge_std_list_u.append(im_slice[upper-7:upper+8])
                self.edge_std_list_l.append(im_slice[lower-7:lower+8])
            self.edge_std_u = np.mean(self.edge_std_list_u, axis=0).astype(np.int16)    # ここでエラーが発生する？
            self.edge_std_l = np.mean(self.edge_std_list_l, axis=0).astype(np.int16)

            # 前回値から上下5ピクセルがサーチ範囲
            st1 = (upper - 5) if upper >= 12 else 7
            ed1 = (upper + 5) if upper <= 2035 else 2040
            st2 = (lower - 5) if lower >= 12 else 7
            ed2 = (lower + 5) if lower <= 2035 else 2040

            # 元のトロリ線の境界と近い場所をサーチ
            diff_val_u, diff_val_l, diff_idx_u, diff_idx_l = [], [], [], []
            for i in range(st1, ed1):
                diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.edge_std_u.astype(int)))
                diff_val_u.append(diff1)
                diff_idx_u.append(i)
            for i in range(st2, ed2):
                diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.edge_std_l.astype(int)))
                diff_val_l.append(diff2)
                diff_idx_l.append(i)
            diff_val_u = np.array(diff_val_u)
            diff_val_l = np.array(diff_val_l)
            diff_sort_u = np.argsort(diff_val_u)
            diff_sort_l = np.argsort(diff_val_l)
            idx_u = diff_idx_u[diff_sort_u[0]]
            val_u = diff_val_u[diff_sort_u[0]]
            idx_l = diff_idx_l[diff_sort_l[0]]
            val_l = diff_val_l[diff_sort_l[0]]

            # 標準偏差を算出
            stdev_u = round(statistics.stdev(im_slice[upper-3:upper+4], 3))
            stdev_l = round(statistics.stdev(im_slice[lower-3:lower+4], 3))

            # エラーを記録
            self.err_skip[0] = 1 if idx_u <= (upper-2) or idx_u >= (upper+2) else 0  # ピクセル飛び（上）
            self.err_skip[1] = 1 if idx_l <= (lower-2) or idx_l >= (lower+2) else 0  # ピクセル飛び（下）
            self.err_diff[0] = 1 if val_u >= 200 else 0   # 差分大（上）
            self.err_diff[1] = 1 if val_l >= 200 else 0   # 差分大（下）
            self.err_edge[0] = 1 if stdev_u < 10 else 0   # 標準偏差極小 → 輝度がほぼ平坦 → エッジなし（上）
            self.err_edge[1] = 1 if stdev_l < 10 else 0   # 標準偏差極小 → 輝度がほぼ平坦 → エッジなし（下）

            # エラーがある場合は過去の平均値を参照
            if self.err_skip[0] == 1 or self.err_diff[0] == 1 or self.err_edge[0] == 1:
                # idx_u = upper
                idx_u = upper_avg
            if self.err_skip[1] == 1 or self.err_diff[1] == 1 or self.err_edge[1] == 1:
                # idx_l = lower
                idx_l = lower_avg

            # 立ち上がりの向き確認
            # 前回からエッジの傾きが反転していたら'slope_dir'を変更
            if self.err_edge[0:2] == [0, 0]:
                slope_u = np.gradient(im_slice[idx_u-1:idx_u+2].astype(np.int16))
                slope_l = np.gradient(im_slice[idx_l-1:idx_l+2].astype(np.int16))
                if self.slope_dir == 1 and slope_u[1] < 0 and slope_l[1] > 0:
                    self.slope_dir = -1
                elif self.slope_dir == -1 and slope_u[1] > 0 and slope_l[1] < 0:
                    self.slope_dir = 1

            # （補正）検出した点を傾きの中心にする
            # if trolley['err_diff'][0] == 0 and trolley['err_edge'][0] == 0:  # test
            if self.err_edge[0] == 0:  # test
                if self.slope_dir == 1:
                    center_u = (max(im_slice[idx_u-2:idx_u+8]).astype(np.int16) + min(im_slice[idx_u-7:idx_u+3]).astype(np.int16)) / 2  # test
                    # valmax = max(im_slice[idx_u-2:idx_u+8]).astype(np.int16)  # test
                    # valmin = min(im_slice[idx_u-7:idx_u+3]).astype(np.int16)  # test
                    # center_u = valmin + (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                    idx_uu = np.argmin(im_slice[idx_u-7:idx_u+3]) + (upper-7)  # 追加
                    idx_ul = np.argmax(im_slice[idx_u-2:idx_u+8]) + (upper-2)  # 追加
                elif self.slope_dir == -1:
                    center_u = (max(im_slice[idx_u-7:idx_u+3]).astype(np.int16) + min(im_slice[idx_u-2:idx_u+8]).astype(np.int16)) / 2  # test
                    # valmax = max(im_slice[idx_u-7:idx_u+3]).astype(np.int16)  # test
                    # valmin = min(im_slice[idx_u-2:idx_u+8]).astype(np.int16)  # test
                    # center_u = valmax - (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                    idx_uu = np.argmax(im_slice[idx_u-7:idx_u+3]) + (upper-7)  # 追加
                    idx_ul = np.argmin(im_slice[idx_u-2:idx_u+8]) + (upper-2)  # 追加
                    # diff1 = abs(im_slice[idx_u-1:idx_u+2] - center_u)
                if idx_uu < idx_ul:
                    diff1 = abs(im_slice[idx_uu:idx_ul+1] - center_u)
                    idx_u = np.argmin(diff1) + idx_uu
            # if trolley['err_diff'][1] == 0 and trolley['err_edge'][1] == 0:  # test
            if self.err_edge[1] == 0:  # test
                if self.slope_dir == 1:
                    center_l = (max(im_slice[idx_l-7:idx_l+3]).astype(np.int16) + min(im_slice[idx_l-2:idx_l+8]).astype(np.int16)) / 2  # test
                    # valmax = max(im_slice[idx_l-7:idx_l+3]).astype(np.int16)  # test
                    # valmin = min(im_slice[idx_l-2:idx_l+8]).astype(np.int16)  # test
                    # center_l = valmin + (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                    idx_lu = np.argmax(im_slice[idx_l-7:idx_l+3]) + (lower-7)  # 追加
                    idx_ll = np.argmin(im_slice[idx_l-2:idx_l+8]) + (lower-2)  # 追加
                elif self.slope_dir == -1:
                    center_l = (max(im_slice[idx_l-2:idx_l+8]).astype(np.int16) + min(im_slice[idx_l-7:idx_l+3]).astype(np.int16)) / 2  # test
                    # valmax = max(im_slice[idx_l-2:idx_l+8]).astype(np.int16)  # test
                    # valmin = min(im_slice[idx_l-7:idx_l+3]).astype(np.int16)  # test
                    # center_l = valmax - (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                    idx_lu = np.argmin(im_slice[idx_l-7:idx_l+2]) + (lower-7)  # 追加
                    idx_ll = np.argmax(im_slice[idx_l-2:idx_l+8]) + (lower-2)  # 追加
                    # diff2 = abs(im_slice[idx_l-1:idx_l+2] - center_l)
                if idx_lu < idx_ll:
                    diff2 = abs(im_slice[idx_lu:idx_ll+1] - center_l)
                    idx_l = np.argmin(diff2) + idx_lu

            # （補正）変化は±1とする
            if (int(idx_u) - upper) <= -2:
                idx_u = upper - 1
            elif (int(idx_u) - upper) >= 2:
                idx_u = upper + 1
            else:
                idx_u = int(idx_u)
            if (int(idx_l) - lower) <= -2:
                idx_l = lower - 1
            elif (int(idx_l) - lower) >= 2:
                idx_l = lower + 1
            else:
                idx_l = int(idx_l)

            # （補正）
            # 過去の平均中心点を基準に検出したidx_uとidx_lが上下に分かれていることを確認
            # そうでない場合は過去の平均値とする
            if not (idx_u < center_avg):
                idx_u = upper_avg
            if not (idx_l > center_avg):
                idx_l = lower_avg

            # 検出値を記録
            # 上下ともエッジが検出できなければ欠損値とする
            if self.err_edge[0:2] == [1, 1]:
                self.write_value(np.nan, np.nan)
                self.err_nan[0] = 1
                self.err_nan[1] += 1
            else:
                self.write_value(idx_u, idx_l)
                self.err_nan[0] = 0

            # トロリ線幅が極端に小さい場合と大きい場合エラーとしカウント
            if (self.last_state[1] - self.last_state[0]) <= 1:
                self.err_width[0] = 1
                self.err_width[2] += 1
            else:
                self.err_width[0] = 0
            if (self.last_state[1] - self.last_state[0]) >= 28:
                self.err_width[1] = 1
                self.err_width[3] += 1
            else:
                self.err_width[1] = 0

            # エッジ基準を更新
            # ただし、エッジが検出できない場合は更新しない
            if self.err_edge[0] == 0:
                if len(self.edge_std_list_u) == 10:
                    self.edge_std_list_u.pop(0)
                self.edge_std_list_u.append(im_slice[idx_u-7:idx_u+8])
            if self.err_edge[1] == 0:
                if len(self.edge_std_list_l) == 10:
                    self.edge_std_list_l.pop(0)
                self.edge_std_list_l.append(im_slice[idx_l-7:idx_l+8])

            # 検出したエッジの色変更
            if not math.isnan(self.upper_line[-1]):
                self.im_trolley[int(idx_u), ix, :] = [-250, 250, -250]   # 正常に検出した場合「緑」
            elif math.isnan(self.upper_line[-1]):
                self.im_trolley[int(idx_u), ix, :] = [255, -250, -250]   # 輝度が背景に近い場合場合「赤」
            if not math.isnan(self.lower_line[-1]):
                self.im_trolley[int(idx_l), ix, :] = [-250, 250, -250]   # 正常に検出した場合「緑」
            elif math.isnan(self.lower_line[-1]):
                self.im_trolley[int(idx_l), ix, :] = [255, -250, -250]   # 輝度が背景に近い場合場合「赤」

            # その他検出値等を記録
            self.last_state = [idx_u, idx_l]
            self.upper_diff.append(val_u)
            self.lower_diff.append(val_l)
            self.im_slice_org = im_slice_org
            self.im_slice = im_slice

        else:
            self.write_value(np.nan, np.nan)
            self.err_skip[0:2] = [0, 0]
            self.err_diff[0:2] = [0, 0]
            self.err_edge[0:2] = [0, 0]
            self.err_nan[0:2] = [0, 0]

        self.err_log_u.append([self.err_skip[0], self.err_diff[0], self.err_edge[0]])
        self.err_log_l.append([self.err_skip[1], self.err_diff[1], self.err_edge[1]])

        return

    def search_second_trolley(self, trolley2, ix):
        """ 2本目のトロリ線検出（Wイヤー、ASAJ）
            1本目のトロリ線用のピクセルインスタンスでの使用を想定
        Args:
            trolley2 (pixel instance): ピクセルインスタンス
            ix (int): x座標値
        """
        if (
            (ix % 5 == 0) and
            ((trolley2.trolley_id == 2 and trolley2.w_ear == 0) or
             (trolley2.trolley_id == 3 and trolley2.as_aj == 0))
        ):
            upper = np.round(self.last_state[0]).astype(np.int16)
            lower = np.round(self.last_state[1]).astype(np.int16)
            im_slice = self.im_slice

            if trolley2.trolley_id == 2:
                # サーチ範囲（Ｗイヤー）の場合
                # メインのトロリ線から上下50ピクセル
                # ただし元のトロリ線直近の5ピクセルを除く
                st1 = (upper - 40) if upper >= 47 else 7
                ed1 = (upper - 5) if upper >= 13 else 8
                st2 = (lower + 5) if lower <= 2034 else 2039
                ed2 = (lower + 40) if lower <= 2000 else 2040
            elif trolley2.trolley_id == 3:
                # サーチ範囲（AS・AJ）
                # メインのトロリ線から上下700ピクセル
                # ただし元のトロリ線直近の50ピクセルを除く
                st1 = (upper - 700) if upper >= 707 else 7
                ed1 = (upper - 50) if upper >= 58 else 8
                st2 = (lower + 50) if lower <= 1989 else 2039
                ed2 = (lower + 700) if lower <= 1340 else 2040

            # 元のトロリ線の境界と近い場所をサーチ
            diff_val_u, diff_val_l, diff_idx_u, diff_idx_l = [], [], [], []
            for area in [[st1, ed1], [st2, ed2]]:
                for i in range(area[0], area[1]):
                    diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.edge_std_u.astype(int)))
                    diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.edge_std_l.astype(int)))
                    if diff1 <= 200:    # 150 => 200 (2022.10.04)
                        diff_val_u.append(diff1)
                        diff_idx_u.append(i)
                    if diff2 <= 200:    # 150 => 200 (2022.10.04)
                        diff_val_l.append(diff2)
                        diff_idx_l.append(i)
            if len(diff_val_u) > 0:
                diff_val_u = np.array(diff_val_u)
                diff_sort_u = np.argsort(diff_val_u)
            if len(diff_val_l) > 0:
                diff_val_l = np.array(diff_val_l)
                diff_sort_l = np.argsort(diff_val_l)

            # 平行トロリ線が存在するかどうか判断
            # idx_u, idx_l, val_u, val_l = 0, 0, 0, 0    # 元のコード
            idx_u, idx_l = 0, 0
            if len(diff_val_u) > 0 and len(diff_val_l) > 0:
                for upper in diff_sort_u:
                    for lower in diff_sort_l:
                        if 35 > (diff_idx_l[lower] - diff_idx_u[upper]) > 0:
                            idx_u = diff_idx_u[upper]
                            # val_u = diff_val_u[upper]    # 不要？
                            idx_l = diff_idx_l[lower]
                            # val_l = diff_val_l[lower]    # 不要？
                            break
                    if idx_u != 0:
                        break
                if idx_u != 0 and trolley2.trolley_id == 2:
                    trolley2.w_ear = 1
                    trolley2.isInFrame = True
                if idx_u != 0 and trolley2.trolley_id == 3:
                    trolley2.as_aj = 1
                    trolley2.isInFrame = True

            # 検出値等を記録
            trolley2.last_state = [idx_u, idx_l]

            # 立ち上がりの向きをメインのトロリ線に合わせる
            trolley2.slope_dir = self.slope_dir

            # エッジ基準を作成
            if trolley2.isInFrame:
                if len(trolley2.edge_std_list_u) == 10:
                    trolley2.edge_std_list_u.pop(0)
                trolley2.edge_std_list_u.append(im_slice[idx_u-7:idx_u+8])
                if len(trolley2.edge_std_list_l) == 10:
                    trolley2.edge_std_list_l.pop(0)
                trolley2.edge_std_list_l.append(im_slice[idx_l-7:idx_l+8])

        elif (
            (trolley2.trolley_id == 2 and trolley2.w_ear >= 1) or
            (trolley2.trolley_id == 3 and trolley2.as_aj >= 1)
        ):
            # 一定上のエラー数でトロリ線（メイン）の消失（もしくは誤検出）と判断
            if (
                trolley2.err_width[2] >= 150 or
                trolley2.err_width[3] >= 150 or
                trolley2.err_nan[1] >= 100
            ):
                trolley2.reset_trolley()
            else:
                if trolley2.trolley_id == 2:
                    trolley2.w_ear += 1
                elif trolley2.trolley_id == 3:
                    trolley2.as_aj += 1

        return

    def update_result_dic(self, ix):
        """ トロリ線検出結果を更新する
            trolley1インスタンスでの実行を想定
        Args:
            ix (int): x座標値
        """
        img = self.im_org
        upper_edge = self.last_state[0]
        lower_edge = self.last_state[1]
        center_trolley = (lower_edge + upper_edge) // 2
        # if ix % 100 == 0:
        #     print(f"{ix}> upper_edge          :{upper_edge}")
        self.ix.append(ix)
        self.estimated_upper_edge.append(upper_edge)
        self.estimated_lower_edge.append(lower_edge)
        self.estimated_width.append(lower_edge - upper_edge)
        self.brightness_center.append(img[center_trolley, ix, 0])
        self.brightness_mean.append(np.mean(img[upper_edge:lower_edge+1, ix, 0]))
        self.brightness_std.append(np.std(img[upper_edge:lower_edge+1, ix, 0]))
        return

    def change_trolley(self, trolley2, trolley3):
        """ トロリ線の切り替え
            トロリ線（Wイヤー）とトロリ線（ASAJ）の両方が存在するとき
            エラーの数を比較して誤検出と思われる側をリセット
            trolley1インスタンスでの実行を想定
        Args:
            trolley2 (pixel instance): ピクセルインスタンス
            trolley3 (pixel instance): ピクセルインスタンス
        """
        if trolley2.isInFrame and trolley3.isInFrame:
            cnt_err2 = trolley2.err_width[2] + trolley2.err_width[3] + trolley2.err_nan[1]
            cnt_err3 = trolley3.err_width[2] + trolley3.err_width[3] + trolley3.err_nan[1]
            if cnt_err2 < cnt_err3:
                trolley3.reset_trolley()
            elif cnt_err2 > cnt_err3:
                trolley2.reset_trolley()

        # 一定上のエラー数でトロリ線（メイン）の消失と判断
        if (
            self.err_width[2] >= 150 or  # トロリ線幅（小） 判定基準は適当
            self.err_width[3] >= 150 or   # トロリ線幅（大） 判定基準は適当
            self.err_nan[1] >= 100        # エッジ検出無し　判定基準は適当
        ):
            self.reset_trolley()
            print('Reset Trolley1')

        # トロリ線（メイン）の切り替え
        if not self.isInFrame and trolley2.isInFrame:
            self.edge_std_list_u = trolley2.edge_std_list_u.copy()
            self.edge_std_list_l = trolley2.edge_std_list_l.copy()
            self.edge_std_u = trolley2.edge_std_u.copy()
            self.edge_std_l = trolley2.edge_std_l.copy()
            self.last_state = trolley2.last_state.copy()
            self.last_upper_line = trolley2.last_upper_line.copy()
            self.last_lower_line = trolley2.last_lower_line.copy()
            self.isInFrame = True
            print('Change Trolley -> 2')
            trolley2.reset_trolley()
        elif not self.isInFrame and trolley3.isInFrame:
            self.edge_std_list_u = trolley3.edge_std_list_u.copy()
            self.edge_std_list_l = trolley3.edge_std_list_l.copy()
            self.edge_std_u = trolley3.edge_std_u.copy()
            self.edge_std_l = trolley3.edge_std_l.copy()
            self.last_state = trolley3.last_state.copy()
            self.last_upper_line = trolley3.last_upper_line.copy()
            self.last_lower_line = trolley3.last_lower_line.copy()
            self.isInFrame = True
            trolley3.reset_trolley()
            print('Change Trolley -> 3')
        return

    def write_picture(self, trolley2, trolley3):
        """ 検出後の画像を作成して配列として出力する
            trolley1インスタンスでの実行を想定
        Args:
            trolley2 (pixel instance): ピクセルインスタンス
            trolley3 (pixel instance): ピクセルインスタンス
        """
        im = self.im_org + self.im_trolley + trolley2.im_trolley + trolley3.im_trolley
        im = np.clip(im, 0, 255)
        im = im.astype("uint8")
        return im

    def write_value(self, value_u, value_l):
        """ 検出値を記録
        """
        self.upper_line.append(value_u)
        self.lower_line.append(value_l)
        if len(self.last_upper_line) == 5:
            self.last_upper_line.pop(0)
        self.last_upper_line.append(value_u)
        if len(self.last_lower_line) == 5:
            self.last_lower_line.pop(0)
        self.last_lower_line.append(value_l)
        return

    @my_logger
    def infer_trolley_edge(self, trolley2, trolley3):
        """ 各x座標ごとにピクセルエッジの計算を実施
            trolley1インスタンスでの実行を想定
        Args:
            image_path (str): 画像ファイルのパス
            trolley2 (pixel instance): ピクセルインスタンス
            trolley3 (pixel instance): ピクセルインスタンス
        """
        # print(f"image_path:{image_path}")
        # 画像の平均画素を算出（背景画素と同等とみなす）
        self.mean_brightness()

        # x座標(ix)ごとにトロリ線検出
        for ix in range(1000):
            self.search_trolley(ix)

            # 2本目のトロリ線検出
            self.search_second_trolley(trolley2, ix)
            self.search_second_trolley(trolley3, ix)

            trolley2.search_trolley(ix)
            trolley3.search_trolley(ix)

            # 検出結果を更新する
            self.update_result_dic(ix)
            trolley2.update_result_dic(ix)
            trolley3.update_result_dic(ix)

        return


if __name__ == '__main__':
    print('set similar_pixel class')
