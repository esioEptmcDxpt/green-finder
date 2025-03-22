import pytest
import src.config as Config


@pytest.fixture()
def trolleyId():
    trolley_id = 'trolley1'
    return trolley_id


@pytest.fixture()
def imgPath():
    img_path = 'imgs/Chuo_01_Tokyo-St_up_20230201_knight/HD11/2022_0615_HD11_01_00022312.jpg'
    return img_path


@pytest.fixture(autouse=True)
def readConfig():
    config = Config.appProperties('config.yml')
    return config