import yaml


class appProperties:
    """config.ymlからの設定値読み取り
    Arg:
        None
    Methods:
        __init__: 初期化関数
        image_dir: 画像ディレクトリのパス
        output_dir: 出力ディレクトリのパス
        camera_type: カメラ種類
        trolley_ids: トロリ線IDのリスト(trolley1, trolley2...)
        camera_names: カメラ名称の辞書(HD11->高(左))
        rail_names: 線区名称の辞書(Chuo->中央線)
        station_names: 駅名称の辞書(Tokyo->東京)
        rail_type_names: 線別の辞書(up->上り)
        time_band_names: 時間帯の辞書(day->昼間)
    Parameters:
        max_len: 画像1枚あたりの横ピクセル数（結果データフレーム作成で使用）
    """
    def __init__(self, config_path):
        with open(config_path, 'r', encoding="utf-8") as yml:
            self.config = yaml.safe_load(yml)

        self.missing_threshold = self.config['measurement']['missing_threshold']
        self.brightness_diff_threshold = self.config['measurement']['brightness_diff_threshold']
        self.sharpness_threshold = self.config['measurement']['sharpness_threshold']
        self.missing_count_limit = self.config['measurement']['missing_count_limit']
        self.width_exceed_limit = self.config['measurement']['width_exceed_limit']
        self.max_len = self.config['results']['max_len']
        self.img_width = self.config['results']['img_width']
        self.img_height = self.config['results']['img_height']
        self.ix_list = self.config['results']['ix_list']

    @property
    def image_dir(self):
        return self.config['default']['image_dir']

    @property
    def output_dir(self):
        return self.config['default']['output_dir']

    @property
    def img2kiro(self):
        return self.config['default']['img2kiro']
    
    @property
    def csv_fname(self):
        return self.config['default']['csv_fname']

    @property
    def tdm_dir(self):
        return self.config['default']['tdm_dir']

    @property
    def bucket(self):
        return self.config['default']['bucket']
    
    @property
    def kiro_prefix(self):
        return self.config['default']['kiro_prefix']
    
    @property
    def kiro_columns_name(self):
        return self.config['default']['kiro_columns_name']

    @property
    def readme_md(self):
        return self.config['default']['readme_md']

    @property
    def quarter_measurements(self):
        return self.config['default']['quarter_measurements']
    
    @property
    def camera_types(self):
        return self.config['default']['camera_types']

    @property
    def camera_names(self):
        return self.config['default']['camera_names']

    @property
    def trolley_ids(self):
        return self.config['default']['trolley_ids']

    @property
    def result_keys(self):
        return self.config['default']['result_keys']

    @property
    def result_keys_kalman(self):
        return self.config['default']['result_keys_kalman']

    @property
    def columns_list(self):
        return self.config['default']['columns_list']

    @property
    def csv_dtype(self):
        return self.config['default']['csv_dtype']

    @property
    def camera_name_to_type(self):
        return self.config['format_func']['camera_name_to_type']

    @property
    def rail_names(self):
        return self.config['format_func']['rail_names']

    @property
    def station_names(self):
        return self.config['format_func']['station_names']

    @property
    def rail_type_names(self):
        return self.config['format_func']['rail_type_names']

    @property
    def time_band_names(self):
        return self.config['format_func']['time_band_names']

    @property
    def SenbetsuCd(self):
        return self.config['format_func']['SenbetsuCd']

if __name__ == "__main__":
    config = appProperties('config.yml')
    print(config.image_dir)
    print(config.output_dir)
    print(config.readme_md)
    print(config.camera_types)
    print(config.trolley_ids)
    print(config.camera_names)
    print(config.rail_names)
    print(config.station_names)
    print(config.rail_type_names)
    print(config.time_band_names)
    print(config.missing_count_limit)
