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
    """
    def __init__(self, config_path):
        with open(config_path, 'r') as yml:
            self.config = yaml.safe_load(yml)

        self.missing_threshold = self.config['measurement']['missing_threshold']
        self.brightness_diff_threshold = self.config['measurement']['brightness_diff_threshold']
        self.sharpness_threshold = self.config['measurement']['sharpness_threshold']
        self.missing_count_limit = self.config['measurement']['missing_count_limit']

    @property
    def image_dir(self):
        return self.config['default']['image_dir']

    @property
    def output_dir(self):
        return self.config['default']['output_dir']

    @property
    def readme_md(self):
        return self.config['default']['readme_md']

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
