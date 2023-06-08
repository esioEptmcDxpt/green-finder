import copy
import pytest
import shelve
from src.kalman import kalman
from src.config import appProperties
from src.kalman_calc import track_kalman


@pytest.mark.parametrize(
    "trolley_id, y_init_u, y_init_l, x_init",
    [('trolley_id_1', 970, 1000, 0),
     ('trolley_id_2', 100, 900, 1)]
)
def test_initDefaultkalman(trolley_id, y_init_u, y_init_l, x_init):
    k = kalman(trolley_id, y_init_u, y_init_l, x_init)
    assert k.trolley_id == trolley_id
    assert k.y_init_u == y_init_u
    assert k.y_init_l == y_init_l

@pytest.fixture(autouse=True)
def readConfig():
    config = appProperties('config.yml')
    return config
    
    
@pytest.fixture(autouse=True)
def readShelve():
    with shelve.open('output/Chuo_01_Tokyo-St_up_20230201_knight/HD11/rail.shelve') as rail:
        trolley_dict = copy.deepcopy(rail['HD11']['imgs/Chuo_01_Tokyo-St_up_20230201_knight/HD11/2022_0615_HD11_01_00022312.jpg'])
    return trolley_dict


@pytest.fixture(params=['None', 'istrolleyID', 'isnottrolleyID'])
def makeShelve(request, tmp_path_factory):
    path = tmp_path_factory.mktemp('sub')
    file = str(path) + '/raildummy.shelve'
    with shelve.open(file) as rail:
        rail["dummy_cameranum"] = {}
        if request.param == 'None':
            trolley_dict = copy.deepcopy(rail['dummy_cameranum'])
        elif request.param == 'istrolleyID':
            rail["dummy_cameranum"] = {'dummy_imgpath': {'trolley_id': 1}}
            trolley_dict = copy.deepcopy(rail['dummy_cameranum'])
        elif request.param == 'isnottrolleyID':
            rail["dummy_cameranum"] = {'dummy_imgpath': None}
            trolley_dict = copy.deepcopy(rail['dummy_cameranum'])            
    return trolley_dict

'''
fixtureを設定した場合、その下の関数がtest前に実行される。
fixture関数を引数に取ると、関数名で呼び出すが、実際の中身はreturnで返されたものになる。
今回の場合、readShelve、の中身は実際にはtrolley_dictの辞書形式に変換された状態でテスト関数には引き渡されている。
'''
def test_isConfig(readConfig):
    assert readConfig is not None

def test_isTrolley(readShelve):
    assert readShelve.keys() is not None

def test_isShelve():
    kalman_instance = kalman('trolley1', 970, 1000, 0)
    kalman_instance.missing_count_limit = 0
    with pytest.raises(TypeError):
        kalman_instance.infer_trolley_edge('imgs/Chuo_01_Tokyo-St_up_20230201_knight/HD11/2022_0615_HD11_01_00022312.jpg')
    

    
    
## test case 1

## test case 2
## test case 3
