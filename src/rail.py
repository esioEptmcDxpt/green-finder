import pandas as pd


class rail(object):
    """トロリ線の初期パラメータを設定

    Args: カルマンフィルタでのみ使用
        trolley_id: トロリー線のID
        y_init_u:   入力初期値（水平方向）
        y_init_l:   入力初期値（垂直方向
    Parameter: 類似ピクセルでのみ使用
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
    
    def __init__(self, dir_area, CAMERA_NUMS):
        dict = {
            "dirname":[],
            "filename":[],
            "camera_num":[],
            "upper_boundary1":[],
            "lower_boundary1":[],
            "upper_diff1":[],
            "lower_diff1":[],
            "upper_boundary2":[],
            "lower_boundary2":[],
            "upper_diff2":[],
            "lower_diff2":[],
            "upper_boundary3":[],
            "lower_boundary3":[],
            "upper_diff3":[],
            "lower_diff3":[]
        }
        
        # print_fileから移植
        dir_name = dir_base + dir_area
        for camera_num in CAMERA_NUMS:
            image_list = utlst.get_file_list(dir_name + '/' + camera_num + '/')
            for file in image_list:
                dict["dirname"].append(os.path.dirname(dir_name + '/' + camera_num + '/' + file))
                dict["filename"].append(os.path.basename(file))
                dict["camera_num"].append(camera_num)
                dict["upper_boundary1"].append(None)
                dict["lower_boundary1"].append(None)
                dict["upper_diff1"].append(None)
                dict["lower_diff1"].append(None)
                dict["upper_boundary2"].append(None)
                dict["lower_boundary2"].append(None)
                dict["upper_diff2"].append(None)
                dict["lower_diff2"].append(None)
                dict["upper_boundary3"].append(None)
                dict["lower_boundary3"].append(None)
                dict["upper_diff3"].append(None)
                dict["lower_diff3"].append(None)
        self.df=pd.DataFrame.from_dict(dict, dtype={'camera_num':str})
        
        # get_railから移植
        self.df = pd.read_csv(metadatafile, header=0, dtype={'camera_num':str})
        self.metadata_name = metadatafile
        self.metadata_length = len(df)
        self.camera_num = df['camera_num'].unique()
        self.inpath = [f'{x[0]}/{x[1]}' for x in zip(df['dirname'].tolist(), df['filename'].tolist())]
        self.infile = df['filename']
        outpath_list = []
        for camera_num in CAMERA_NUMS:
            outpath_list.append(f'output/{dir_area}/{camera_num}/')
        self.outpath = outpath_list
        self.upper_boundary1 = df['upper_boundary1'].tolist()
        self.lower_boundary1 = df['lower_boundary1'].tolist()
        self.upper_boundary2 = df['upper_boundary2'].tolist()
        self.lower_boundary2 = df['lower_boundary2'].tolist()
        self.upper_boundary3 = df['upper_boundary3'].tolist()
        self.lower_boundary3 = df['lower_boundary3'].tolist()
        
if __name__ == '__main__':
    rail = rail()
    print(vars(rail))
    