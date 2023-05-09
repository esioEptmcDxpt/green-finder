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
    def __init__(self, trolley_id, y_init_u, y_init_l):    # 
        # トロリ線の識別＜共通＞
        self.trolley_id = trolley_id
        self.isInFrame = None       # ピクセルエッジでのみ使用？
        
        # 解析結果＜共通＞
        self.ix = []
        self.estimated_upper_edge = []
        self.estimated_lower_edge = []
        self.estimated_width = []
        self.estimated_slope = []    # (メモ)どんな結果が格納される？ ピクセルエッジでも使うか？
        self.blightness_center = []
        self.blightness_mean = []
        self.blightness_std = []
        
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
        
        
        # 作業中のためメモを残していますが、後で削除します。
        # ↓元々はtrolleyのやつ
        # self.picture = {    # ファイル名、画像の情報を記録する
        #                     'file': None,
        #                     'im_org': None,
        #                     'im_trolley': None,
        #                     'im_slice_org':None,
        #                     'im_slice':None
        #                 }
        # self.result_dict = {    # 出力用データフレーム
        #                         'inpath':[],
        #                         'outpath':[],
        #                         'infile':[],
        #                         'camera_num':[],
        #                         'global_ix':[],
        #                         'ix':[],
        #                         'upper_edge1':[],          # -> estimated_upper_edge
        #                         'lower_edge1':[],          # -> estimated_lower_edge
        #                         'width1':[],               # -> estimated_width
        #                         'blightness_center1':[],   # -> brightness_center
        #                         'blightness_mean1':[],     # -> brightness_mean
        #                         'blightness_std1':[],      # -> brightness_std
        #                         'upper_edge2':[],
        #                         'lower_edge2':[],
        #                         'width2':[],
        #                         'blightness_center2':[],
        #                         'blightness_mean2':[],
        #                         'blightness_std2':[],
        #                         'upper_edge3':[],
        #                         'lower_edge3':[],
        #                         'width3':[],
        #                         'blightness_center3':[],
        #                         'blightness_mean3':[],
        #                         'blightness_std3':[]
        #                     }
        # ↓元々はmetafileで定義していたやつ（print_files） ※おそらく不要
        # dict = {
        #     "dirname":[],
        #     "filename":[],
        #     "camera_num":[],
        #     "upper_boundary1":[],
        #     "lower_boundary1":[],
        #     "upper_diff1":[],
        #     "lower_diff1":[],
        #     "upper_boundary2":[],
        #     "lower_boundary2":[],
        #     "upper_diff2":[],
        #     "lower_diff2":[],
        #     "upper_boundary3":[],
        #     "lower_boundary3":[],
        #     "upper_diff3":[],
        #     "lower_diff3":[]
        # }
        # files = sorted(glob.glob(f"{dir_name}/{cam}/*.jpg"))
        # for file in files:
        #     dict["dirname"].append(os.path.dirname(file))
        #     dict["filename"].append(os.path.basename(file))
        #     dict["camera_num"].append(cam)
        #     dict["upper_boundary1"].append(None)
        #     dict["lower_boundary1"].append(None)
        #     dict["upper_diff1"].append(None)
        #     dict["lower_diff1"].append(None)
        #     dict["upper_boundary2"].append(None)
        #     dict["lower_boundary2"].append(None)
        #     dict["upper_diff2"].append(None)
        #     dict["lower_diff2"].append(None)
        #     dict["upper_boundary3"].append(None)
        #     dict["lower_boundary3"].append(None)
        #     dict["upper_diff3"].append(None)
        #     dict["lower_diff3"].append(None)
        # df=pd.DataFrame.from_dict(dict)
        # print(f"output file is: {dir_name}temp_meta.csv")
        # df.to_csv(f"{dir_name}/{csvname}_temp_meta.csv", index=False)
        # 
        # def get_picture(self):
        #     """
        #     ファイル名、画像の情報を記録する
        #     """
        #     picture = {
        #         'file': None,
        #         'im_org': None,
        #         'im_trolley': None,
        #         'im_slice_org':None,
        #         'im_slice':None
        #     }
        #     return picture.copy()
        #
        #
        # def get_result_dic(self):
        #     """
        #     出力用データフレーム
        #     """
        #     dic = {
        #         'inpath':[],
        #         'outpath':[],
        #         'infile':[],
        #         'camera_num':[],
        #         'global_ix':[],
        #         'ix':[],
        #         'upper_edge1':[],
        #         'lower_edge1':[],
        #         'width1':[],
        #         'blightness_center1':[],
        #         'blightness_mean1':[],
        #         'blightness_std1':[],
        #         'upper_edge2':[],
        #         'lower_edge2':[],
        #         'width2':[],
        #         'blightness_center2':[],
        #         'blightness_mean2':[],
        #         'blightness_std2':[],
        #         'upper_edge3':[],
        #         'lower_edge3':[],
        #         'width3':[],
        #         'blightness_center3':[],
        #         'blightness_mean3':[],
        #         'blightness_std3':[]
        #     }
        #     return dic.copy()
        


if __name__ == '__main__':
    trolley_id = "trolley1"
    y_init_u = 0
    y_init_l = 1
    trolley = trolley(trolley_id, y_init_l, y_init_u)
    print(vars(trolley))
