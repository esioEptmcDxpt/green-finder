import numpy as np
from numpy import ma


class trolley(object):
    """トロリ線の初期パラメータを設定
    Args: カルマンフィルタでのみ使用？
          👇引数を別々にできる？出来なければピクセルエッジ検出でもダミーで入力するようにする
        trolley_id: トロリー線のID
        y_init_u:   入力初期値（水平方向）
        y_init_l:   入力初期値（垂直方向
        isInFrame:  画像内にトロリ線があるかのフラグ
    Error log: ピクセルエッジ検出でのみ使用
        エラー記録(err_log_u,l):
            [err_skip, err_diff, err_edge, err_width(small), err_width(latge)]
        ピクセル飛びエラー(err_skip):
            [upper_state(0 or 1), lower_state(0 or 1), upper_count, lower_count]
        差分大エラー(err_diff):
            [upper_state(0 or 1), lower_state(0 or 1), upper_count, lower_count]
        エッジなしエラー(err_edge):
            [upper_state(0 or 1), lower_state(0 or 1), upper_count, lower_count]
        トロリ線幅エラー(err_width):
            [small_state(0 or 1), large_state(0 or 1), small_count, large_count]
    """
    def __init__(self, trolley_id, y_init_u, y_init_l):
        # トロリ線の識別＜共通＞
        self.trolley_id = trolley_id
        self.isInFrame = None       # ピクセルエッジでのみ使用？

        # 解析結果＜共通＞
        self.ix = []
        self.estimated_upper_edge = []
        self.estimated_lower_edge = []
        self.estimated_width = []
        self.estimated_slope = []    # (メモ)どんな結果が格納される？ ピクセルエッジでも使うか？
        self.brightness_center = []
        self.brightness_mean = []
        self.brightness_std = []

        # カルマンフィルタ向け
        self.y_init_u = y_init_u
        self.y_init_l = y_init_l
        self.num_obs = 0
        self.missingCounts = 0
        self.initial_state_covariance = []
        self.initial_state_mean = [self.y_init_u, self.y_init_l, 0]
        self.transition_matrix = []
        self.transition_covariance = []
        self.kf_multi = []
        self.current_state = []
        self.last_state = [0, 0]
        self.last_state_covariance = []
        self.estimated_upper_edge_variance = []
        self.estimated_lower_edge_variance = []
        self.estimated_slope_variance = []
        self.measured_upper_edge = []
        self.measured_lower_edge = []
        self.missing_state = []
        self.trolley_end_reason = []
        self.brightness = []
        self.new_measurement = ma.array(np.zeros(2))
        self.mask = [False, False]
        self.center = 0
        self.last_boundary_expectation = []
        self.last_brightness = [0, 0]  # list[0, 0] = list[edge_id1, edge_id2]
        self.mxn_slope_iy = [0, 0]
        self.value_iy = [0, 0]
        self.box_width = 20


if __name__ == '__main__':
    trolley_id = "trolley1"
    y_init_u = 0
    y_init_l = 1
    trolley = trolley(trolley_id, y_init_l, y_init_u)
    print(vars(trolley))
