import numpy as np
from numpy import ma


class trolley(object):
    """トロリ線の初期パラメータを設定

    Args:
        trolley_id: トロリー線のID
        y_init_u:   入力初期値（水平方向）
        y_init_l:   入力初期値（垂直方向）
    Parameter:
        err_log_u, err_log_l:
            エラー記録[
                        err_skip,
                        err_diff,
                        err_edge,
                        err_width(small),
                        err_width(latge)
            ]
        err_skip, err_diff, err_edge, err_width:
            エラー内容[
                        upper_state(0 or 1),
                        lower_state(0 or 1),
                        upper_count,
                        lower_count
            ]
    """
    def __init__(self, trolley_id, y_init_u, y_init_l):
        self.trolley_id = trolley_id
        self.isInFrame = []
        self.last_state = []
        self.upper_line = []
        self.lower_line = []
        self.last_upper_line = []
        self.last_lower_line = []
        self.brightness = []
        self.avg_brightness = []
        self.sigmoid_edge_u = None
        self.sigmoid_edge_l = None
        self.slope_dir = None
        self.edge_std_list_u = []
        self.edge_std_list_l = []
        self.edge_std_u = None
        self.edge_std_l = None
        self.err_log_u = []    # Error log on Upper edge
        self.err_log_l = []    # Error log on Lower edge
        self.err_skip = [0, 0, 0, 0]    # pixel skip error
        self.err_diff = [0, 0, 0, 0]    # Difference too large error
        self.err_edge = [0, 0, 0, 0]    # No edge error
        self.err_width = [0, 0, 0, 0]    # trolley wear width error
        self.err_nan = [0, 0]
        self.upper_diff = []
        self.lower_diff = []
        self.w_ear = 0
        self.as_aj = 0
        
        # self.y_init_u = y_init_u
        # self.y_init_l = y_init_l
        # self.num_obs = 0
        # self.missingCounts = 0
        # self.initial_state_covariance = []
        # self.initial_state_mean = [self.y_init_u, self.y_init_l, 0]
        # self.transition_matrix = []
        # self.transition_covariance = []
        # self.kf_multi = []
        # self.current_state = []
        # self.last_state = [0, 0]
        # self.last_state_covariance = []
        # self.estimated_upper_edge = []
        # self.estimated_lower_edge = []
        # self.estimated_width = []
        # self.estimated_slope = []
        # self.estimated_upper_edge_variance = []
        # self.estimated_lower_edge_variance = []
        # self.estimated_slope_variance = []
        # self.blightness_center = []
        # self.blightness_mean = []
        # self.blightness_std = []
        # self.measured_upper_edge = []
        # self.measured_lower_edge = []
        # self.missing_state = []
        # self.trolley_end_reason = []
        # self.brightness = []
        # self.new_measurement = ma.array(np.zeros(2))
        # self.mask = [False, False]
        # self.center = 0
        # self.last_boundary_expectation = []
        # self.last_brightness = [0, 0]  # list[0, 0] = list[edge_id1, edge_id2]
        # self.mxn_slope_iy = [0, 0]
        # self.value_iy = [0, 0]
        # self.box_width = 20


if __name__ == '__main__':
    trolley_id = "trolley1"
    y_init_u = 0
    y_init_l = 1
    trolley = trolley(trolley_id, y_init_l, y_init_u)
    print(vars(trolley))
