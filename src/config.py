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
    def camera_types(self):
        return self.config['default']['camera_types']


if __name__ == "__main__":
    config = appProperties('config.yml')
    print(config.camera_types)
    print(config.missing_count_limit)
