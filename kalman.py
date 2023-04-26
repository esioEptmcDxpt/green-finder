# -*- coding: utf-8 -*-

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from numpy import ma
import os, urllib, cv2, glob
from PIL import Image
import shelve
import copy
import matplotlib.pyplot as plt
from pykalman import KalmanFilter
import pdb

def finalize_measurement(trolley,trolley_id,missingCountsLimit,ix):
    '''
    トロリ線の上側のエッジと下側のエッジにおける測定値を調査し、欠損が片方だけなら前回値をセットすることでカルマンフィルタを実行可能とする。
    それでも欠損がmissingCountsLimit以上継続している場合はWイヤーなどでトロリ線が消失していると判断する。
    '''
    # st.text("ix: "+str(ix))
    # if trolley['isPaused']:
    #     return
    if trolley[trolley_id]['mask'][0] and trolley[trolley_id]['mask'][1]:
        trolley[trolley_id]['new_measurement'] = ma.masked
        trolley[trolley_id]['missingCounts'] = trolley[trolley_id]['missingCounts']+1
        trolley[trolley_id]['missing_state'].append('both')
    elif trolley[trolley_id]['mask'][0]:
        trolley[trolley_id]['new_measurement'][0] = trolley[trolley_id]['current_state'][0]
        trolley[trolley_id]['missingCounts'] = trolley[trolley_id]['missingCounts']+0.25
        trolley[trolley_id]['missing_state'].append('upper')
    elif trolley[trolley_id]['mask'][1]:
        trolley[trolley_id]['new_measurement'][1] = trolley[trolley_id]['current_state'][1]
        trolley[trolley_id]['missingCounts'] = trolley[trolley_id]['missingCounts']+0.25
        trolley[trolley_id]['missing_state'].append('lower')
        
    if trolley[trolley_id]['missingCounts'] > missingCountsLimit:
        print(f" Tracking failed. trolley Line {trolley_id} disappeard at x={ix},y={trolley[trolley_id]['last_state']}!"
             )
    return trolley

def plot_fig(base_images,idx):
    im_base = Image.open(base_images[idx])
    dpi = 200
    margin = 0.05 # (5% of the width/height of the figure...)
    xpixels, ypixels = 1000, 2200
    mag = 2
    
    # Make a figure big enough to accomodate an axis of xpixels by ypixels
    # as well as the ticklabels, etc...
    figsize = mag*(1 + margin) * ypixels / dpi, mag*(1 + margin) * xpixels / dpi

    fig = plt.figure(figsize=figsize, dpi=dpi)
    # Make the axis the right size...
    ax = fig.add_axes([margin, margin, 1 - 2*margin, 1 - 2*margin])
    ax.set_yticks(range(0,2200,50))
    ax.minorticks_on()
    ax.imshow(im_base, interpolation='none')
    st.pyplot(fig)
    

def initialize_Kalman(trolley, trolley_id):
    '''
    カルマンフィルタを初期化する
    '''
    trolley[trolley_id]['initial_state_covariance'] = [[1, 0, 0],[0, 1, 0],[0, 0, 0.001]]
    trolley[trolley_id]['transition_matrix'] = [[1,0,1],[0,1,1],[0,0,1]]
#    trolley['transition_covariance'] = [[0.000005, 0, 0],[-0.000005, 0, 0],[0, 0, 0.000005]]
    trolley[trolley_id]['transition_covariance'] = [[0.00005, 0, 0],[-0.00005, 0, 0],[0, 0, 0.00005]]
    trolley[trolley_id]['observation_matrix'] = [[1,0,0],[0,1,0]]
    trolley[trolley_id]['observation_covariance'] = [[3,0],[0,3]]
    trolley[trolley_id]['kf_multi'] = KalmanFilter(
        n_dim_obs = 2,
        n_dim_state=3,
        initial_state_mean=trolley[trolley_id]['initial_state_mean'],
        initial_state_covariance=trolley[trolley_id]['initial_state_covariance'],
        transition_matrices = trolley[trolley_id]['transition_matrix'],
        observation_matrices = trolley[trolley_id]['observation_matrix'],
        transition_covariance = trolley[trolley_id]['transition_covariance'],
        observation_covariance = trolley[trolley_id]['observation_covariance'],
    )
    trolley[trolley_id]['current_state'] = trolley[trolley_id]['initial_state_mean'].copy()
    trolley[trolley_id]['last_state'] = np.array(trolley[trolley_id]['initial_state_mean']).astype(np.float64).copy()
    trolley[trolley_id]['last_state_covariance'] = trolley[trolley_id]['initial_state_covariance'].copy()
    trolley[trolley_id]['center'] = np.round(0.5*trolley[trolley_id]['last_state'][0]+0.5*trolley[trolley_id]['last_state'][1]).astype(np.int16)
    trolley[trolley_id]['new_measurement']=ma.array(np.zeros(2))

    return
        
def initialize_trolley(trolley_id,y_init_u,y_init_l):
    trolley = { #トロリ線ごとの情報
        trolley_id : {
            # 'isPaused':isPaused,
            'num_obs':0,
            'missingCounts':0,
            'initial_state_covariance': [], #
            'initial_state_mean': [y_init_u,y_init_l,0],
            'transition_matrix': [],
            'transition_covariance': [],
            'observation_matrix': [],
            'observation_covariance': [],
            'kf_multi': None,
            'current_state': [],
            'last_state': [0,0],
            'last_state_covariance': [],
            'estimated_upper_edge':[],
            'estimated_lower_edge':[],
            'estimated_width':[],
            'estimated_slope':[],
            'estimated_upper_edge_variance':[],
            'estimated_lower_edge_variance':[],
            'estimated_slope_variance':[],
            'blightness_center':[],
            'blightness_mean':[],
            'blightness_std':[], 
            'measured_upper_edge':[],
            'measured_lower_edge':[],
            'missing_state':[],
            'trolley_end_reason':[],
            'brightness': [], #境界面上端外側の輝度
            'new_measurement':ma.array(np.zeros(2)),
            'mask': [False,False],
            'center': 0,
            'last_boundary_expectation': [],
            'last_brightness':[0,0],
            'mxn_slope_iy':[0,0],
            'value_iy':[0,0],
            'box_width': 20,
        }
    }
    initialize_Kalman(trolley,trolley_id)
            
    return trolley.copy()


def initialize_measurement(trolley, trolley_id):
    '''
    新たな画像に対する初期化を実施する
    '''
    # st.text(trolley[trolley_id])
    trolley[trolley_id]['new_measurement']=ma.array(np.zeros(2))
    trolley[trolley_id]['center'] = np.round(0.5*trolley[trolley_id]['last_state'][0]+0.5*trolley[trolley_id]['last_state'][1]).astype(np.int16)
    return

def get_measurement(image_path, trolley, trolley_id, edge_id, ix, missing_threshold, brightness_diff_threshold,sharpness_threshold):
    '''
    上下のエッジごとに横１ピクセル幅の画像スライスにおけるスキャンを行いエッジの測定を行う
    '''
    
    obs=trolley[trolley_id]['num_obs']
    last_brightness=copy.deepcopy(trolley[trolley_id]['last_brightness'][edge_id])
    last_boundary_expectation = np.round(trolley[trolley_id]['last_state'][edge_id]).astype(np.int16)
    last_watershed = np.round(
        0.5*trolley[trolley_id]['last_state'][0]+0.5*trolley[trolley_id]['last_state'][1]
    ).astype(np.int16)
    
    if edge_id == 0:
        inside_shift_amt = 1
        sort_oder = -1
        box_start = last_boundary_expectation - trolley[trolley_id]['box_width']
        box_end = last_watershed + 1
    else:
        inside_shift_amt = -1
        sort_oder = -1
        box_start = last_watershed + 1
        box_end = last_boundary_expectation + trolley[trolley_id]['box_width'] + 1
    
    if (box_start<0) or (box_end>2500):    # トロリ線が画角外に出てしまった場合
        st.text(f" trolley Line {trolley_id} frame out at x={ix},y={trolley[trolley_id]['last_state'][edge_id]},box_start={box_start},box_end={box_end}"
             )
        trolley[trolley_id]['end_reason']='gone out of sight'
        # raise Exception
        return

    img = np.array(Image.open(image_path))
    if box_start > box_end:
        box_start, box_end = box_end, box_start

    y_slice = img[box_start:box_end,ix:ix+1,0].ravel() #該当部分の輝度取得
    
    if edge_id == 0:
        dy_slice = np.gradient(np.array(y_slice, dtype=np.int16)) #yの差分（＝傾き）を算出
    else:
        dy_slice = abs(np.gradient(np.array(y_slice, dtype=np.int16))) #yの差分（＝傾き）を算出          
    
    dy_argsorted = np.argsort(dy_slice[1:y_slice.size - 1])[::sort_oder]
    mxn_slope_iy = dy_argsorted[0] + box_start + 1
    value_iy = dy_slice[dy_argsorted[0]]
    current_brightness = y_slice[mxn_slope_iy-box_start+inside_shift_amt].astype(np.int16)
    trolley[trolley_id]['mxn_slope_iy'][edge_id]=mxn_slope_iy
    trolley[trolley_id]['value_iy'][edge_id]=value_iy

    # 観測値が正常条件をみたさないときは欠損扱いする
    if obs>2 \
        and (
        #エッジの検出位置の差
               abs(mxn_slope_iy - last_boundary_expectation) > missing_threshold \
        #エッジの隣のピクセルとの輝度差
            or ( abs(value_iy) < sharpness_threshold ) \
        # 摺面の前回輝度の差
            or abs(last_brightness - current_brightness) > brightness_diff_threshold 
        ): 
        trolley[trolley_id]['mask'][edge_id] = True
        trolley[trolley_id]['new_measurement'][edge_id] = ma.masked
        trolley[trolley_id]['last_brightness'][edge_id] = last_brightness
        # trolley[trolley_id]['color'][edge_id] = [255,0,127] - img[mxn_slope_iy.astype(int), ix] # Red
    else:
        trolley[trolley_id]['mask'][edge_id] = False
        trolley[trolley_id]['new_measurement'][edge_id] = mxn_slope_iy
        trolley[trolley_id]['last_brightness'][edge_id]=0.5*current_brightness+0.5*last_brightness # 平均を取る
    # st.text("new_measurement: "+str(trolley[trolley_id]['new_measurement']))
    
    return trolley


def update_Kalman(trolley,trolley_id,ix,image_path):
    '''
    カルマンフィルタによる更新処理を行う
    '''
    trolley[trolley_id]['current_state'], trolley[trolley_id]['current_state_covariance'] = trolley[trolley_id]['kf_multi'].filter_update(
        trolley[trolley_id]['last_state'], trolley[trolley_id]['last_state_covariance'], trolley[trolley_id]['new_measurement']
    )
    trolley[trolley_id]['last_state'] = trolley[trolley_id]['current_state'].copy()
    trolley[trolley_id]['last_state_covariance'] = trolley[trolley_id]['current_state_covariance'].copy()
     
    # 各種特徴量を取り出す
    upper_edge = np.floor(trolley[trolley_id]['current_state'][0]).astype(np.int16) # pick inside pixcel
    lower_edge = np.ceil(trolley[trolley_id]['current_state'][1]).astype(np.int16) # pick inside pixcel
    width = lower_edge - upper_edge + 2
    center =  np.round((trolley[trolley_id]['current_state'][0]+trolley[trolley_id]['current_state'][1])/2.0).astype(np.uint16)
    
    img = np.array(Image.open(image_path))

    blightness_center = img[center:center+1,ix:ix+1,0][0][0]
    blightness_mean = np.mean(img[upper_edge:lower_edge+1,ix:ix+1,0])
    blightness_std = np.std(img[upper_edge:lower_edge+1,ix:ix+1,0]) 
    trolley[trolley_id]['num_obs'] = trolley[trolley_id]['num_obs'] + 1

    # 保存する
    trolley[trolley_id]['estimated_upper_edge'].append(upper_edge)
    trolley[trolley_id]['estimated_lower_edge'].append(lower_edge)
    trolley[trolley_id]['estimated_width'].append(width)
    trolley[trolley_id]['estimated_slope'].append(trolley[trolley_id]['current_state'][2])
    trolley[trolley_id]['estimated_upper_edge_variance'].append(trolley[trolley_id]['current_state_covariance'][0,0])
    trolley[trolley_id]['estimated_lower_edge_variance'].append(trolley[trolley_id]['current_state_covariance'][1,1])
    trolley[trolley_id]['estimated_slope_variance'].append(trolley[trolley_id]['current_state_covariance'][2,2])
    trolley[trolley_id]['blightness_center'].append(blightness_center)
    trolley[trolley_id]['blightness_mean'].append(blightness_mean)
    trolley[trolley_id]['blightness_std'].append(blightness_std)
    trolley[trolley_id]['measured_upper_edge'].append(trolley[trolley_id]['mxn_slope_iy'][0])   # 実測値
    trolley[trolley_id]['measured_lower_edge'].append(trolley[trolley_id]['mxn_slope_iy'][1])   # 実測値
    # trolley[trolley_id]['missing_state'].append(trolley[trolley_id]['missing_state'])
    trolley[trolley_id]['trolley_end_reason'].append(trolley[trolley_id]['trolley_end_reason'])    

    return
    
def infer_trolley_edge(trolley, trolley_id, image_path, x, y_u, y_l):
    initialize_measurement(trolley, trolley_id)
    for ix in range(1000):
        if ix == 0:
            st.text(f"phase-03 file_idx:{image_path}")
        
        missing_threshold=5
        brightness_diff_threshold=255
        sharpness_threshold=1
        missing_count_limit=100
        
        for edge_id in range(2):
            trolley = get_measurement(image_path, trolley, trolley_id, edge_id, ix, missing_threshold, brightness_diff_threshold,sharpness_threshold)

        trolley = finalize_measurement(trolley, trolley_id, missing_count_limit, ix)
        update_Kalman(trolley,trolley_id,ix,image_path)            
    return trolley
    
def track_kalman(rail, camera_num, base_images, idx, trolley_id, x_init, y_init_u, y_init_l):
    x = x_init
    y_u = y_init_u
    y_l = y_init_l
    
    try:
        for image_path in base_images[idx:]:
            tmp_trolley = rail[camera_num][image_path].get(trolley_id)
            if not tmp_trolley:
                trolley = initialize_trolley(trolley_id, y_u, y_l)
            else:
                trolley = tmp_trolley

            trolley = infer_trolley_edge(trolley, trolley_id, image_path, x, y_u, y_l)
            # 書き込み 
            rail[camera_num][image_path]=trolley            

            x = 0
            y_u = trolley[trolley_id]['estimated_upper_edge'][-1]
            y_l = trolley[trolley_id]['estimated_upper_edge'][-1]

    except Exception as e:
        # 途中で妙な値を拾った場合
        st.exception(e)
        st.error(f'処理が途中で終了しました。')
    finally:
        # 最後まで完了した値を書き込み
        rail[camera_num][image_path]=trolley
        # rail[camera_num][image_path].setdefault(trolley_id, trolley[trolley_id])
        st.stop()
    
    rail.close()
    


# Streamlit encourages well-structured code, like starting execution in a main() function.
def main():
    # Render the readme as markdown using st.markdown.
    readme_text = st.markdown("## 左のメニューから操作してください")


    # Once we have the dependencies, add a selector for the app mode on the sidebar.
    st.sidebar.title("What to do")
    app_mode = st.sidebar.selectbox("Choose the app mode",
        ["ガイド（作成中）", "カルマンフィルタ実行", "カルマンフィルタ実行結果確認"])
    if app_mode == "ガイド（作成中）":
        st.sidebar.success('実行するには"カルマンフィルタ実行"を選択してください')
    elif app_mode == "カルマンフィルタ実行結果確認":
        readme_text.empty()
        st.code(get_file_content_as_string("kalman.py"))
    elif app_mode == "カルマンフィルタ実行":
        readme_text.empty()
        run_the_app()


def run_the_app():
    dir_area, camera_num, idx = railcam_selector_ui(DATA_URL_ROOT)
    if dir_area == None:
        st.error("No frames fit the criteria. Please select different label or number.")
        return
    

# This sidebar UI is a little search engine to find certain object types.
def railcam_selector_ui(DATA_URL_ROOT):
    st.sidebar.markdown("# 線区・カメラの選択")
    
    images_fullpath = glob.glob(os.path.join(DATA_URL_ROOT, "*"))
    images_fullpath = [folder for folder in images_fullpath if os.path.isdir(folder)]
    images_path = [os.path.basename(folder) for folder in images_fullpath]
    images_path.sort()

    # The user can pick which type of object to search for.
    dir_area = st.sidebar.selectbox('imagesフォルダ直下のフォルダ名を選択してください',images_path)

    ## 解析対象のカメラ番号を選択する
    camera_num = st.sidebar.selectbox('解析対象のカメラを選択してください', ('HD11','HD12','HD21','HD22','HD31','HD32'))
    
    ## 解析対象フォルダ
    dir_name = DATA_URL_ROOT + '/' + dir_area
    target_dir = dir_name + '/' + camera_num

    ## outputディレクトリの準備
    outpath = 'output/' + dir_area + '/' + camera_num
    os.makedirs(outpath, exist_ok=True)

    # 既存のresultがあれば読み込み、なければ作成
    if os.path.isfile(outpath + 'rail.shelve'):
        rail = shelve.open(outpath + '/rail.shelve', writeback=True)
    else:
        rail = shelve.open(outpath + '/rail.shelve', writeback=True)
        rail['name'] = dir_area
        # imagesフォルダ内の画像一覧取得
        base_images = glob.glob(target_dir + '/*.jpg')
        base_images.sort()
        # base_imagesと同じ長さの空のdictionaryを作成して初期化
        l = [{}] * len(base_images)
        rail[camera_num]=dict(zip(base_images, l))

    # ファイルインデックスを指定する
    st.sidebar.markdown('# ファイルのインデックスを指定してください')
    idx = st.sidebar.number_input('Image index', 0, len(base_images)-1, 0)
    
    
    # メインページを等分で分割
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('### 車モニ画像')
        plot_fig(base_images, idx)

    with col2:
        st.markdown('### 摩耗検出結果')
        #to be implemented

    with col3:
        st.markdown('#### (参考)画像左端の輝度値')
        #to be implemented
    
    ## 
    st.sidebar.markdown('# カルマンフィルタの初期値設定')

    ## カルマンフィルタの初期値設定
    form = st.sidebar.form(key='kalman_init')
    trolley_id = form.selectbox('トロリ線のIDを入力してください',('trolley1','trolley2'))
    x_init = form.number_input('横方向の初期座標を入力してください',0,999)
    y_init_u = form.number_input('上記X座標でのエッジ位置（上端）の座標を入力してください',0,1999)
    y_init_l = form.number_input('上記X座標でのエッジ位置（下端）の座標を入力してください',0,1999)
    submit = form.form_submit_button('カルマンフィルタ実行')
    
    if submit:
        with st.spinner("カルマンフィルタ実行中"):
            # time.sleep(3)
    
            track_kalman(rail, camera_num, base_images, idx, trolley_id, x_init, y_init_u, y_init_l)
    
    if len(dir_area) < 1:
        return None, None, None

    rail.close()
    return dir_name, camera_num, idx

# Path to the Streamlit public S3 bucket
# DATA_URL_ROOT = "https://streamlit-self-driving.s3-us-west-2.amazonaws.com/"
DATA_URL_ROOT = "images/AJ_air_joint_ZIPFILE_jtGlh_202272151236"


if __name__ == "__main__":
    main()