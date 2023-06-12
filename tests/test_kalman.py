import pytest
from src.kalman import kalman


# 正常系のテスト
@pytest.mark.parametrize(
    "trolley_id, y_init_u, y_init_l, x_init",
    [('trolley1', 970, 1000, 0),
     ('trolley2', 100, 900, 1)]
)
def test_initKalman(trolley_id, y_init_u, y_init_l, x_init):
    # Given: Initialize kalman instance
    k = kalman(trolley_id, y_init_u, y_init_l, x_init=x_init)
    
    # WHEN and THEN: Expected equals to instance variables and input variables
    assert k.trolley_id == trolley_id
    assert k.y_init_u == y_init_u
    assert k.y_init_l == y_init_l
    assert k.x_init == x_init
    
@pytest.mark.parametrize(
    "trolley_id, y_init_u, y_init_l, x_init",
    [('trolley1', 970, 1000, 0)]
)
def test_initConfigKalman(trolley_id, y_init_u, y_init_l, x_init, readConfig):
    # Given: Initialize kalman instance
    k = kalman(trolley_id, y_init_u, y_init_l, x_init)
    
    # WHEN and THEN: Expected equals to instance variables and input config variables
    assert k.missing_threshold == readConfig.missing_threshold
    assert k.brightness_diff_threshold == readConfig.brightness_diff_threshold
    assert k.sharpness_threshold == readConfig.sharpness_threshold
    assert k.missing_count_limit == readConfig.missing_count_limit
    assert k.width_exceed_limit == readConfig.width_exceed_limit


@pytest.mark.parametrize(
    "trolley_id, y_init_u, y_init_l, x_init",
    [('trolley1', 970, 1000, 0),
     ('trolley1', 970, 1000, 10),
     ('trolley1', 970, 1000, 500),
     ('trolley2', 970, 1000, 0)]
)
def test_normalKalman(trolley_id, y_init_u, y_init_l, x_init, imgPath, readConfig):
    # Given: Initialize kalman instance
    k = kalman(trolley_id, y_init_u, y_init_l, x_init)
    
    # WHEN infer_trolley_edge calculations
    k.infer_trolley_edge(imgPath)
    
    # THEN the variables are expected values
    assert k.missingCounts < readConfig.missing_count_limit
    assert k.error_flg == 0
    assert k.num_obs == 1000 - x_init


# 異常系のテスト
def test_exceedMissingCountError(trolleyId, imgPath, readConfig):
    '''Test for estimated width exceed limitation
    GIVEN: A kalman instance initialize using parameters
    WEHN: we call infer_trolley_edge function for calculating an image using kalman filter
    THEN: we have expecation about exceed width limitations 
    '''
    kalman_instance = kalman(trolleyId, 970, 1000, 0)
    kalman_instance.missing_count_limit = 0
    kalman_instance.missing_threshold = 0
    expected = 'Exceed missing Counts Limitations'
    kalman_instance.infer_trolley_edge(imgPath)
    assert kalman_instance.missing_count_limit < kalman_instance.missingCounts
    assert expected == kalman_instance.trolley_end_reason[0]
    

def test_exceedWidthError(trolleyId, imgPath):
    '''Test for estimated width exceed limitation
    GIVEN: A kalman instance initialize using parameters
    WEHN: we call infer_trolley_edge function for calculating an image using kalman filter
    THEN: we have expecation about exceed width limitations 
    '''    
    kalman_instance = kalman(trolleyId, 900, 1000, 0)
    kalman_instance.infer_trolley_edge(imgPath)
    expected = 'Exceed estamated width limitations'
    assert expected == kalman_instance.trolley_end_reason[0]


def test_exceedRangeError(trolleyId, imgPath):
    '''Test for estimated width exceed limitation
    GIVEN: A kalman instance initialize using over range parameters
    WEHN: we call infer_trolley_edge function for calculating an image using kalman filter
    THEN: we have expecation about exceed width limitations 
    '''
    kalman_instance = kalman(trolleyId, 2550, 2600, 0)
    kalman_instance.infer_trolley_edge(imgPath)
    expected = 'gone out of sight'
    assert expected == kalman_instance.trolley_end_reason[0]