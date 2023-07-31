import os
import numpy as np
from numpy import ma
from PIL import Image
from pykalman import KalmanFilter
from src.config import appProperties
from src.trolley import trolley
from src.logger import my_logger


class kalman(trolley):
    """トロリ情報を継承し、カルマンフィルタの計算用の初期化とアップデートを実施
    Args:
        trolley (class): トロリ線のパラメータ
        appProperties (class) : 計算条件の設定用ファイル
    Parameters:
        missing_threshold (int): 再試行閾値
        brightness_diff_threshold (int): 明るさの差分閾値
        sharpness_threshold (int): 
        missing_count_limit (int): 試行回数のカウント上限
        width_exceed_limit (int): 推定幅の上限閾値
    Methods:
        __init__: 各種パラメータの初期化
        initialize_measurement: 測定条件部分だけの初期化・更新
        finalize_measurement: 測定条件部分だけの最終更新
        update_Kalman: 測定条件のアップデート
        get_measurements:  測定条件の取得
    """
    kalman_config = appProperties('config.yml')
    missing_threshold = kalman_config.missing_threshold
    brightness_diff_threshold = kalman_config.brightness_diff_threshold
    sharpness_threshold = kalman_config.sharpness_threshold
    missing_count_limit = kalman_config.missing_count_limit
    width_exceed_limit = kalman_config.width_exceed_limit

    def __init__(self, trolley_id, y_init_l, y_init_u, x_init):
        super().__init__(trolley_id, y_init_l, y_init_u, x_init)
        self.initial_state_covariance = [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 0.001],
        ]
        self.transition_matrix = [[1, 0, 1], [0, 1, 1], [0, 0, 1]]
        self.transition_covariance = [
            [0.00005, 0, 0],
            [-0.00005, 0, 0],
            [0, 0, 0.00005],
        ]
        self.observation_matrix = [[1, 0, 0], [0, 1, 0]]
        self.observation_covariance = [[3, 0], [0, 3]]
        self.kf_multi = KalmanFilter(
            n_dim_obs=2,
            n_dim_state=3,
            initial_state_mean=self.initial_state_mean,
            initial_state_covariance=self.initial_state_covariance,
            transition_matrices=self.transition_matrix,
            observation_matrices=self.observation_matrix,
            transition_covariance=self.transition_covariance,
            observation_covariance=self.observation_covariance,
        )
        self.current_state = self.initial_state_mean
        self.last_state = np.array(self.initial_state_mean).astype(np.float64).copy()
        self.last_state_covariance = self.initial_state_covariance.copy()
        self.center = np.round(
            0.5 * self.last_state[0]
            + 0.5 * self.last_state[1]
        ).astype(np.int16)
        self.new_measurement = ma.array(np.zeros(2))
        self.missing_count_limit = kalman.missing_count_limit
        self.brightness_diff_threshold = kalman.brightness_diff_threshold
        self.sharpness_threshold = kalman.sharpness_threshold
        self.missing_count_limit = kalman.missing_count_limit
        self.width_exceed_limit = kalman.width_exceed_limit
        self.error_flg = 0

    def initialize_measurement(self):
        self.mask = [False, False]
        self.new_measurement = ma.array(np.zeros(2))
        self.center = np.round(0.5 * self.last_state[0] + 0.5 * self.last_state[1]).astype(np.int16)
        self.end_reason = []

    def finalize_measurement(self, ix):
        """トロリ線の上側のエッジと下側のエッジにおける測定値を調査し、欠損が片方だけなら前回値をセットすることでカルマンフィルタを実行可能とする。
        それでも欠損がmissing_count_limit以上継続している場合はWイヤーなどでトロリ線が消失していると判断する。
        Args:
            ix (class): 呼び出し時のX座標
        Return:
            None
        """
        if self.mask[0] and self.mask[1]:
            self.new_measurement[0] = ma.masked
            self.new_measurement[1] = ma.masked
            self.missingCounts = self.missingCounts + 1
            self.missing_state = 'both'
        elif self.mask[0]:
            self.new_measurement[0] = self.current_state[0]
            self.missingCounts = self.missingCounts + 0.25
            self.missing_state = 'upper'
        elif self.mask[1]:
            self.new_measurement[1] = self.current_state[1]
            self.missingCounts = self.missingCounts + 0.25
            self.missing_state = 'lower'

        if self.missingCounts > self.missing_count_limit:
            self.end_reason = "Exceed missing Counts Limitations"
            self.error_flg = 1

    def update_Kalman(self, ix, img):
        """カルマンフィルタによる更新処理を行う
        Args:
            ix (int): 呼び出し時のX座標
            image_path (str): 画像ファイルのパス
        Return:
            None
        """
        self.current_state, self.current_state_covariance = self.kf_multi.filter_update(
            self.last_state,
            self.last_state_covariance,
            self.new_measurement
        )
        self.last_state = self.current_state.copy()
        self.last_state_covariance = self.current_state_covariance.copy()

        # 型変換
        estimated_upper_edge_variance = self.current_state_covariance[0, 0].astype(np.float16)
        estimated_lower_edge_variance = self.current_state_covariance[1, 1].astype(np.float16)
        estimated_slope_variance = self.current_state_covariance[2, 2].astype(np.float16)

        # 各種特徴量を取り出す
        upper_edge = np.floor(self.current_state[0]).astype(np.int16)
        lower_edge = np.ceil(self.current_state[1]).astype(np.int16)
        width = lower_edge - upper_edge + 2

        if width > self.width_exceed_limit:
            self.end_reason = "Exceed estamated width limitations"
            self.error_flg = 2

        center = np.round((self.current_state[0] + self.current_state[1]) / 2.0).astype(np.int16)
        brightness_center = img[center: center + 1, ix: ix + 1, 0][0][0].astype(np.float16)

        # edge_id=0のとき、ここでエラー
        brightness_mean = np.mean(img[upper_edge: lower_edge + 1, ix: ix + 1, 0]).astype(np.float16)
        brightness_std = np.std(img[upper_edge: lower_edge + 1, ix: ix + 1, 0]).astype(np.float16)
        self.num_obs = self.num_obs + 1

        # Mask Dataを変換
        mask_int = [np.int8(i) for i in self.mask]

        # 保存する
        self.estimated_upper_edge.append(upper_edge)
        self.estimated_lower_edge.append(lower_edge)
        self.estimated_width.append(width)
        self.estimated_slope.append(self.current_state[2])
        self.estimated_upper_edge_variance.append(estimated_upper_edge_variance)
        self.estimated_lower_edge_variance.append(estimated_lower_edge_variance)
        self.estimated_slope_variance.append(estimated_slope_variance)
        self.brightness_center.append(brightness_center)
        self.brightness_mean.append(brightness_mean)
        self.brightness_std.append(brightness_std)
        self.measured_upper_edge.append(self.mxn_slope_iy[0].astype(np.int16))
        self.measured_lower_edge.append(self.mxn_slope_iy[1].astype(np.int16))
        self.mask_edgelog_1.append(mask_int[0])
        self.mask_edgelog_2.append(mask_int[1])
        if len(self.end_reason) > 0:
            self.trolley_end_reason.append(self.end_reason)

    # @my_logger
    def get_measurement(self, img, edge_id, ix):
        """上下のエッジごとに横１ピクセル幅の画像スライスにおけるスキャンを行いエッジの測定を行う
        Args:
            image_path (str): 画像ファイルのパス
            edge_id (int): エッジのID
            ix (int): 呼び出し時のX座標
        Return:
            None
        """
        obs = self.num_obs
        last_brightness = self.last_brightness[edge_id]
        last_boundary_expectation = np.round(self.last_state[edge_id]).astype(np.int16)
        last_watershed = np.round(0.5 * self.last_state[0] + 0.5 * self.last_state[1]).astype(np.int16)

        if edge_id == 0:
            inside_shift_amt = 1
            sort_oder = -1
            box_start = last_boundary_expectation - self.box_width
            box_end = last_watershed + 1
        else:
            inside_shift_amt = -1
            sort_oder = -1
            box_start = last_watershed + 1
            box_end = last_boundary_expectation + self.box_width + 1
        if box_start > box_end:
            box_start, box_end = box_end, box_start

        y_slice = img[box_start:box_end, ix: ix + 1, 0].ravel()

        if (box_start < 0) or (box_end > 2500):
            self.end_reason = "gone out of sight"
            self.error_flg = 3
        else:
            if edge_id == 0:
                dy_slice = np.gradient(np.array(y_slice, dtype=np.int16))
            else:
                dy_slice = abs(np.gradient(np.array(y_slice, dtype=np.int16)))

            dy_argsorted = np.argsort(dy_slice[1: y_slice.size - 1])[::sort_oder]
            mxn_slope_iy_edge = dy_argsorted[0] + box_start + 1
            value_iy = dy_slice[dy_argsorted[0]]
            current_brightness = y_slice[mxn_slope_iy_edge - box_start + inside_shift_amt].astype(np.int16)
            self.mxn_slope_iy[edge_id] = mxn_slope_iy_edge
            self.value_iy[edge_id] = value_iy

            if obs > 2 and (
                abs(mxn_slope_iy_edge - last_boundary_expectation)
                > self.missing_threshold
                or (abs(value_iy) < self.sharpness_threshold)
                or abs(last_brightness - current_brightness) > self.brightness_diff_threshold
            ):

                self.mask[edge_id] = True
                self.new_measurement[edge_id] = ma.masked
                self.last_brightness[edge_id] = last_brightness
            else:
                self.mask[edge_id] = False
                self.new_measurement[edge_id] = mxn_slope_iy_edge
                self.last_brightness[edge_id] = (0.5 * current_brightness + 0.5 * last_brightness)

    # @my_logger
    def infer_trolley_edge(self, image_path):
        """ 各x座標とエッジIDを元にカルマンフィルタの計算を実施
        Args:
            image_path (str): 画像ファイルのパス
        """
        self.initialize_measurement()
        img = np.array(Image.open(image_path))

        for i in range(1000 - self.x_init):
            ix = i + self.x_init
            for edge_id in range(2):
                self.get_measurement(img, edge_id, ix)
            self.finalize_measurement(ix)
            self.update_Kalman(ix, img)

            if len(self.trolley_end_reason) > 0:
                self.ix = ix
                break


if __name__ == '__main__':
    print(os.getcwd())
    trolley_id = "trolley1"
    x_init = 0
    y_init_u = 1000
    y_init_l = 970
    # 再試行閾値 > 100を超える画像
    #image_path = 'imgs/AJ_air_joint_ZIPFILE_jtGlh_202272151236/2021_0696_HD11_01_00020962.jpg'
    
    # 画面上端・下端到達ケースの画像
    #image_path = 'imgs/watari_ZIPFILE_JSlN4_202272151640/2021_0308_HD22_01_00020143.jpg'
    image_path = 'imgs/Chuo_01_Tokyo-St_up_20230201_knight/HD11/2022_0615_HD11_01_00022312.jpg'
    kalman_instance = kalman(trolley_id, y_init_l, y_init_u, x_init)
    kalman_instance.infer_trolley_edge(image_path)