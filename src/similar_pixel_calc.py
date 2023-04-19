import streamlit as st
import boto3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pykalman import KalmanFilter
import os, glob, random, math, statistics, cv2, time
from PIL import Image
import ipywidgets as widgets
# 以下Bokeh用
from IPython import __version__ as ipython_version
from pandas import __version__ as pandas_version
from bokeh import __version__ as bokeh_version
from bokeh.io import output_notebook, output_file, show
from bokeh.plotting import figure, ColumnDataSource, output_file, reset_output, show
from bokeh.models import RangeTool
from bokeh.sampledata.iris import flowers
from bokeh.layouts import column, row, gridplot
import src.utilsS3_01 as utls3
import src.utilsST_01 as utlst


'''
トロリ線摩耗判定システム用の機能をまとめたモジュール
'''

#---------------------------------------
# 画像
#---------------------------------------
def plot_fig(img):
    dpi = 200
    margin = 0.05 # (5% of the width/height of the figur...)
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
    ax.imshow(img, interpolation='none')
    return fig

def plot_fig_bokeh(img):
    ### 画像の左端での輝度グラフ
    graph_width = 1000
    graph_height = 2048
    
    im_slice = np.copy(img[:, 0, 0])
    x = im_slice
    y = np.array(range(len(im_slice)))
    TOOLTIPS = [
        ('y', '$y'), 
    ]
    brightness_graph = figure(
        title='Brightness at the left edge of the image', plot_width=graph_width, plot_height=graph_height,
        x_axis_label='Brightness', y_axis_label='Position of image',
        y_range=(y[-1], y[-2048]),
        tooltips=TOOLTIPS
    )
    brightness_graph.line(x, y, color='blue', line_width=1)
    show(brightness_graph)
    
    return

def get_picture():
    picture = { #ファイル名、画像の情報
        'file': None,
        'im_org': None,
        'im_trolley': None,
        'im_slice_org':None,
        'im_slice':None
    }
    return picture.copy()

def load_picture(trolley, file):
    '''
    画像ファイルを読み込んで辞書にセットする
    '''
    trolley['picture']['file'] = file
    # trolley['picture']['im_org'] = np.array(utls3.get_image(file))    # S3の場合
    trolley['picture']['im_org'] = np.array(Image.open(file))    # EBSの場合
    trolley['brightness'] = [] #摺面の輝度
    trolley['picture']['im_trolley'] = np.zeros_like(
        trolley['picture']['im_org']).astype(int)
    
    # 画像全体の平均輝度（背景輝度と同等とみなす）を算出
    img = trolley['picture']['im_org']
    im_r = img[:, :, 0].flatten()
    im_random = []
    for i in range(1000): #全画素の平均は処理時間かかるのでランダム1000画素の輝度平均
        x = random.randint(0, 2047999)
        im_random.append(im_r[x])
    trolley['avg_brightness'] = round(np.mean(im_random))
    
    # シグモイド関数を使って理想形のエッジ配列を作成
    sigmoid_max = max(im_r).astype(int)              # 輝度Max値　＝　画像全体の輝度Max値
    sigmoid_min = int(trolley['avg_brightness'])     # 輝度Min値  ＝　背景輝度(画像全体の平均輝度）
    x = np.arange(-7, 8, 1)
    trolley['sigmoid_edge_u'] = (sigmoid_max - sigmoid_min) / (1 + np.exp(-x/0.5) ) + sigmoid_min
    trolley['sigmoid_edge_l'] = (-sigmoid_max + sigmoid_min) / (1 + np.exp(-x/0.5) ) + sigmoid_max
    return

def write_picture(trolley1, trolley2, trolley3):
    im = trolley1['picture']['im_org'] + \
            trolley1['picture']['im_trolley'] + \
            trolley2['picture']['im_trolley'] + \
            trolley3['picture']['im_trolley'] 
    im = np.clip(im, 0, 255)
    im = im.astype("uint8")
    
    path = os.path.dirname(trolley1['result_dict']['outpath'][-1])
    fullpath = trolley1['result_dict']['outpath'][-1]   # ピクセル毎にパスがあるため最新のパスを入手
    
    # パスが存在しなければフォルダ作成
    # utls3.put_s3_dir(path + '/')    # S3の場合
    st.sidebar.text(f'write_picture path:{path + "/"}')
    if not os.path.exists(path + '/'):
        os.makedirs(path + '/')    # EBSの場合
    
    # 画像ファイル出力
    # img = Image.fromarray(im)    # S3の場合
    # utls3.put_s3_img(img, fullpath)    # S3の場合
    Image.fromarray(im).save(fullpath, "PNG")    # EBSの場合
    
#     if os.path.exists(path) == False : os.mkdir(path)  # パスが存在しなければフォルダ作成
# #     Image.fromarray(im).save(fullpath, "JPEG")  # 画像ファイル出力
#     Image.fromarray(im).save(fullpath, "PNG")  # 画像ファイル出力
    return fullpath



#---------------------------------------
# メタデータ作成
#---------------------------------------
def print_files(dir_base, dir_area, CAMERA_NUMS):
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
    dir_name = dir_base + dir_area
    for camera_num in CAMERA_NUMS:
        # image_list = utls3.get_s3_image_list(dir_name + '/' + camera_num + '/')    # S3の場合
        image_list = utlst.get_file_list(dir_name + '/' + camera_num + '/')    # EBSの場合
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
    df=pd.DataFrame.from_dict(dict)
    
    # S3にCSVファイルを保存する
    # csv_data = df.to_csv(index=False)
    # utls3.put_s3_csv(csv_data, f"{dir_name}/{dir_area}_temp_meta.csv")
    # csv_path = f"{dir_name}/{dir_area}_temp_meta.csv"
    
    # EBSにCSVファイルを保存する
    df.to_csv(f"{dir_name}/{dir_area}_temp_meta.csv", index=False)
    csv_path = f"{dir_name}/{dir_area}_temp_meta.csv"

    return csv_path


#---------------------------------------
# 線区の情報
#---------------------------------------
def get_rail(metadatafile, dir_area, CAMERA_NUMS):
    rail = { #線区ごとの情報
        'metadata_name':None,
        'upper_boundary1':[], #線区の開始点のトロリ線の上端
        'lower_boundary1':[], #線区の開始点のトロリ線の下端
        'upper_boundary2':[],
        'lower_boundary2':[],
        'upper_boundary3':[],
        'lower_boundary3':[],
        'df':pd.DataFrame()
    }
    # df = utls3.get_s3_csv_asDf(metadatafile)    # S3の場合
    df = pd.read_csv(metadatafile, header=0, dtype={'camera_num':str})    # EBSの場合
    rail['df'] = df
    rail['metadata_name']=metadatafile
    rail['metadata_length']=len(df)
    rail['camera_num'] = df['camera_num'].unique()
    rail['inpath'] = [f'{x[0]}/{x[1]}' for x in zip(df['dirname'].tolist(), df['filename'].tolist())]
    rail['infile'] = df['filename']
    outpath_list = []
    for camera_num in CAMERA_NUMS:
        # outpath_list.append(f'OHCImages/output/{dir_area}/{camera_num}/')    # S3の場合
        outpath_list.append(f'output/{dir_area}/{camera_num}/')    # EBSの場合
    rail['outpath'] = outpath_list
    rail['upper_boundary1'] = df['upper_boundary1'].tolist()
    rail['lower_boundary1'] = df['lower_boundary1'].tolist()
    rail['upper_boundary2'] = df['upper_boundary2'].tolist()
    rail['lower_boundary2'] = df['lower_boundary2'].tolist()
    rail['upper_boundary3'] = df['upper_boundary3'].tolist()
    rail['lower_boundary3'] = df['lower_boundary3'].tolist()
    return rail.copy()


#---------------------------------------
# トロリ線情報
#---------------------------------------
def get_trolley(trolleyID, isInFrame):
    picture = get_picture()
    result_dict = get_result_dic()
    trolley = { #トロリ線ごとの情報
        'trolleyID':trolleyID,
        'global_ix':[],
        'ix':[],
        'file':[],
        'isInFrame':isInFrame,
        'last_state': [],
        'last_state_covariance': [],
        'upper_line': [],
        'lower_line': [],
        'last_upper_line': [],
        'last_lower_line': [],
        'brightness': [], #摺面の輝度
        'new_measurement':np.zeros(2),
        'mask': [False,False],
        'center': 0,
        'last_boundary_expectation': [],
        'last_brightness':[0,0],
        'mxn_slope_iy':[0,0],
        'value_iy':[0,0],
        'box_width': 7,
        'color': [[0, 0, 0],[0, 0, 0]],
        'avg_brightness':0,
        'sigmoid_edge_u':None,
        'sigmoid_edge_l':None,
        'slope_dir':None,
        'edge_std_list_u':[],
        'edge_std_list_l':[],
        'edge_std_u':None,
        'edge_std_l':None,
        'err_log_u':[],              # エラー記録　[err_skip, err_diff, err_edge, err_width(small), err_width(latge)]
        'err_log_l':[],              # エラー記録　[err_skip, err_diff, err_edge, err_width(small), err_width(latge)]
        'err_skip':[0, 0, 0, 0],     # ピクセル飛びエラー  [upper_state(0 or 1), lower_state(0 or 1), upper_count, lower_count]
        'err_diff':[0, 0, 0, 0],     # 差分大エラー        [upper_state(0 or 1), lower_state(0 or 1), upper_count, lower_count]
        'err_edge':[0, 0, 0, 0],     # エッジなしエラー    [upper_state(0 or 1), lower_state(0 or 1), upper_count, lower_count]
        'err_width':[0, 0, 0, 0],    # トロリ線幅エラー    [small_state(0 or 1), large_state(0 or 1), small_count, large_count]
        'err_nan':[0, 0],            # np.nan [tate(0 or 1), count]
        'upper_diff':[],
        'lower_diff':[],
        'w-ear':0,
        'as_aj':0,
        'picture': picture,
        'result_dict':result_dict,
    }
    return trolley.copy()

#---------------------------------------
# トロリ線消失リセット
#---------------------------------------
def reset_trolley(trolley):
    trolley['edge_std_list_u'] = []
    trolley['edge_std_list_l'] = []
    trolley['edge_std_u'] = None
    trolley['edge_std_l'] = None
    trolley['err_skip'] = [0, 0, 0, 0]
    trolley['err_diff'] = [0, 0, 0, 0]
    trolley['err_edge'] = [0, 0, 0, 0]
    trolley['err_width'] = [0, 0, 0, 0]
    trolley['err_nan'] = [0, 0]
    trolley['w-ear'] = 0
    trolley['as_aj'] = 0
    trolley['isInFrame'] = False
    return

#---------------------------------------
# 初期画像の初期設定
#--------------------------------------- 
def set_init_val(rail, trolley, ix, img, search_list, auto_edge):
    if auto_edge:
        rail['upper_boundary1'][ix] = search_list[0][0]
        rail['lower_boundary1'][ix] = search_list[0][1]
        trolley['last_state'] = search_list[0][0:2]
        trolley['slope_dir'] = search_list[0][2]
    elif st.session_state.xin != '':
        # 画像1の中心点設定と輝度の立上り／立下りサーチ範囲の設定
        width = 34
        start = int(st.session_state.xin)  - width // 2
        end = int(st.session_state.xin)  + width // 2
        # 画像1のトロリ線境界位置の初期値
        im_slice = np.copy(img[:, 0, 0])
        # 傾きから初期値算出
        slope = np.gradient(im_slice[start:end].astype(np.int16))
        slope_max = start + np.argmax(slope)
        slope_min = start + np.argmin(slope)
        upper = min([slope_max, slope_min])
        lower = max([slope_max, slope_min])
        rail['upper_boundary1'][ix] = upper
        rail['lower_boundary1'][ix] = lower
        trolley['last_state'] = [upper, lower]
        # 初期値から輝度の向きを確認
        trolley['slope_dir'] = 1 if slope_max < slope_min else -1
    else:
        st.warning('トロリ線の初期値が正しく設定できませんでした。\nやり直してください。')
    return 



#---------------------------------------
# 摺面エッジ初期位置の自動サーチ
#--------------------------------------- 
def search_trolley_init(trolley, ix, img):
    # 横1ピクセル、縦全ピクセル切り出し
    # img = trolley['picture']['im_org']
    im_slice_org = np.copy(img[:, ix, 0])
    im_slice = np.copy(img[:, ix, 0])
    
    # サーチ範囲
    st = 7
    ed = 2040

    # 切り出した縦ピクセルのノイズを除去
    im_slice[st:ed] = [round(np.mean(im_slice_org[i-1:i+2])) for i in range(st, ed)]
    
    # st.write(f'im_slice:{im_slice}')

    # 理想的なエッジ配列に近い場所をサーチ
    slope_val_u, slope_val_l, slope_idx_u, slope_idx_l  = [], [], [], []
    for i in range(st, ed):
        diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - trolley['sigmoid_edge_u'].astype(int)))
        slope_val_u.append(diff1)
        slope_idx_u.append(i)
        diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - trolley['sigmoid_edge_l'].astype(int)))
        slope_val_l.append(diff2)
        slope_idx_l.append(i)
    slope_val_u = np.array(slope_val_u)
    slope_val_l = np.array(slope_val_l)
    slope_sort_u = np.argsort(slope_val_u)
    slope_sort_l = np.argsort(slope_val_l)
    
    list_idx,list_val = [],[]
    for idx_u, val_u in enumerate(slope_val_u):
        for idx_l, val_l in enumerate(slope_val_l):
            if (
                idx_u < idx_l and                         # ピクセル位置は upper < lowerであること
                0 <= (idx_u - idx_u) <= 35 and            # 摺面幅が明らかにあり得ない場合を除外
                (val_u + val_l) <= 400                    # 誤差が大きい場合は除外
            ):
                list_idx.append([idx_u+st, idx_l+st, 1])  # 摺面が立上り→立下りの場合
                list_val.append(val_u + val_l)
            elif (
                idx_l < idx_u and                          # ピクセル位置は lower < upperであること
                0 <= (idx_u - idx_l) <= 35 and             # 摺面幅が明らかにあり得ない場合を除外
                (val_u + val_l) <= 400                     # 誤差が大きい場合は除外
            ):
                list_idx.append([idx_l+st, idx_u+st, -1])  # 摺面が立下り→立上りの場合
                list_val.append(val_u + val_l)
          
    search_list = []
    for i in np.argsort(list_val):
        search_list.append(list_idx[i])

    # （補正）検出した点を傾きの中心にする
    for i, edge in enumerate(search_list):
        if edge[2] == 1:
            center_u = (max(im_slice[edge[0]-2:edge[0]+8]).astype(np.int16) + min(im_slice[edge[0]-7:edge[0]+3]).astype(np.int16)) / 2
            idx_uu = np.argmin(im_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
            idx_ul = np.argmax(im_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
            center_l = (max(im_slice[edge[1]-7:edge[1]+3]).astype(np.int16) + min(im_slice[edge[1]-2:edge[1]+8]).astype(np.int16)) / 2
            idx_lu = np.argmax(im_slice[edge[1]-7:edge[1]+3]) + (edge[1]-7)
            idx_ll = np.argmin(im_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
        elif edge[2] == -1:
            center_u = (max(im_slice[edge[0]-7:edge[0]+3]).astype(np.int16) + min(im_slice[edge[0]-2:edge[0]+8]).astype(np.int16)) / 2
            idx_uu = np.argmax(im_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
            idx_ul = np.argmin(im_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
            center_l = (max(im_slice[edge[1]-2:edge[1]+8]).astype(np.int16) + min(im_slice[edge[1]-7:edge[1]+3]).astype(np.int16)) / 2
            idx_lu = np.argmin(im_slice[edge[1]-7:edge[1]+2]) + (edge[1]-7)
            idx_ll = np.argmax(im_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
        diff1 = abs(im_slice[idx_uu:idx_ul+1] - center_u)
        idx_u_new = np.argmin(diff1) + idx_uu
        diff2 = abs(im_slice[idx_lu:idx_ll+1] - center_l) 
        idx_l_new = np.argmin(diff2) + idx_lu
        search_list[i][0:2] = [idx_u_new, idx_l_new]
    return search_list


#-----------------------------------------------
# 画像の平均画素を算出（背景画素と同等とみなす）
#-----------------------------------------------
def mean_brightness(trolley, img):
    # img = trolley['picture']['im_org']
    im_r = img[:, :, 0].flatten()
    im_random = []
    for i in range(1000): #全画素の平均は処理時間かかるのでランダム1000画素の平均
        x = random.randint(0, 2047999)
        im_random.append(im_r[x])
    trolley['avg_brightness'] = round(np.mean(im_random))
    return


#-----------------------------------------------
# 検出値を記録
#-----------------------------------------------
def write_value(trolley, value_u, value_l):
    trolley['upper_line'].append(value_u)
    trolley['lower_line'].append(value_l)
    if len(trolley['last_upper_line']) == 5:
        trolley['last_upper_line'].pop(0)
    trolley['last_upper_line'].append(value_u)
    if len(trolley['last_lower_line']) == 5:
        trolley['last_lower_line'].pop(0)
    trolley['last_lower_line'].append(value_l)
    return


#----------------------------------------------- 
# トロリ線検出
#-----------------------------------------------
def search_trolley(rail, trolley, file_idx, ix):
    if (
        trolley['trolleyID'] == 1 or
        (trolley['trolleyID'] == 2 and trolley['w-ear'] >= 1) or
        (trolley['trolleyID'] == 3 and trolley['as_aj'] >= 1)
    ):
        # 新規画像はエラーをリセット
        if file_idx == 0 and ix == 0:
#         if file_idx == 331 and ix == 0:
            trolley['err_skip'] = [0, 0, 0, 0]
            trolley['err_diff'] = [0, 0, 0, 0]
            trolley['err_edge'] = [0, 0, 0, 0]
            trolley['err_width'] = [0, 0, 0, 0]
            trolley['err_nan'] = [0, 0]
        
        # 前回の検出値（上端、下端、中心）
        upper = np.round(trolley['last_state'][0]).astype(np.int16)
        lower = np.round(trolley['last_state'][1]).astype(np.int16)
        center = round((upper + lower) / 2)
        
        # 過去5ピクセル平均値（上端、下端、中心）（初回のみ初期値）
        # "upper_line"が空の場合と、"upper_line"にnanが含まれる場合
        if (
            len(trolley['last_upper_line']) == 0 or
            np.isnan(trolley['last_upper_line'][-5:]).any(axis=0)
           ):
            upper_avg = upper
            lower_avg = lower
        else:
            # 直前の値を優先した平均
            upper_avg = np.mean(np.append([trolley['last_upper_line']], trolley['last_upper_line'][-1])).astype(np.int16)
            lower_avg = np.mean(np.append([trolley['last_lower_line']], trolley['last_lower_line'][-1])).astype(np.int16)
        center_avg = np.mean([upper_avg, lower_avg]).astype(np.int16)

        # 横1ピクセル、縦全ピクセル切り出し
        img = trolley['picture']['im_org']
        im_slice_org = np.copy(img[:, ix, 0])
        im_slice = np.copy(img[:, ix, 0])

        # 切り出した縦ピクセルのノイズを除去（トロリ線を検出した周辺に限定）
        st = upper - 20 if upper >= 21 else 1
        ed = lower + 21 if lower <= 2025 else 2045
        im_slice[st:ed] = [round(np.mean(im_slice_org[i-1:i+2])) for i in range(st, ed)]

        # エッジ基準を作成
        if file_idx == 0 and ix == 0:
#         if file_idx == 145 and ix == 0:  # 途中画像から実施の場合
            trolley['edge_std_list_u'].append(im_slice[upper-7:upper+8])
            trolley['edge_std_list_l'].append(im_slice[lower-7:lower+8])
        trolley['edge_std_u'] = np.mean(trolley['edge_std_list_u'], axis=0).astype(np.int16)
        trolley['edge_std_l'] = np.mean(trolley['edge_std_list_l'], axis=0).astype(np.int16)

        # 前回値から上下5ピクセルがサーチ範囲
        st1 = (upper - 5) if upper >= 12 else 7
        ed1 = (upper + 5) if upper <= 2035 else 2040
        st2 = (lower - 5) if lower >= 12 else 7
        ed2 = (lower + 5) if lower <= 2035 else 2040

        # 元のトロリ線の境界と近い場所をサーチ
        diff_val_u, diff_val_l, diff_idx_u, diff_idx_l  = [], [], [], []
        for i in range(st1, ed1):
            diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - trolley['edge_std_u'].astype(int)))
            diff_val_u.append(diff1)
            diff_idx_u.append(i)
        for i in range(st2, ed2):
            diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - trolley['edge_std_l'].astype(int)))
            diff_val_l.append(diff2)
            diff_idx_l.append(i)
        diff_val_u = np.array(diff_val_u)
        diff_val_l = np.array(diff_val_l)
        diff_sort_u = np.argsort(diff_val_u)
        diff_sort_l = np.argsort(diff_val_l)
        idx_u = diff_idx_u[diff_sort_u[0]]
        val_u = diff_val_u[diff_sort_u[0]]
        idx_l = diff_idx_l[diff_sort_l[0]]
        val_l = diff_val_l[diff_sort_l[0]]

        # 標準偏差を算出
        stdev_u = round(statistics.stdev(im_slice[upper-3:upper+4], 3))
        stdev_l = round(statistics.stdev(im_slice[lower-3:lower+4], 3))

        # エラーを記録
        trolley['err_skip'][0] = 1 if idx_u <= (upper-2) or idx_u >= (upper+2) else 0  # ピクセル飛び（上）
        trolley['err_skip'][1] = 1 if idx_l <= (lower-2) or idx_l >= (lower+2) else 0  # ピクセル飛び（下）
        trolley['err_diff'][0] = 1 if val_u >= 200 else 0   # 差分大（上）
        trolley['err_diff'][1] = 1 if val_l >= 200 else 0   # 差分大（下）
        trolley['err_edge'][0] = 1 if stdev_u < 10 else 0   # 標準偏差極小 → 輝度がほぼ平坦 → エッジなし（上）
        trolley['err_edge'][1] = 1 if stdev_l < 10 else 0   # 標準偏差極小 → 輝度がほぼ平坦 → エッジなし（下）

        # エラーがある場合は過去の平均値を参照
        if trolley['err_skip'][0] == 1 or trolley['err_diff'][0] == 1 or trolley['err_edge'][0] == 1:
#             idx_u = upper
            idx_u = upper_avg
        if trolley['err_skip'][1] == 1 or trolley['err_diff'][1] == 1 or trolley['err_edge'][1] == 1:
#             idx_l = lower
            idx_l = lower_avg

        # 立ち上がりの向き確認
        # 前回からエッジの傾きが反転していたら'slope_dir'を変更
        if trolley['err_edge'][0:2] == [0, 0]:
            slope_u = np.gradient(im_slice[idx_u-1:idx_u+2].astype(np.int16))
            slope_l = np.gradient(im_slice[idx_l-1:idx_l+2].astype(np.int16))
            if trolley['slope_dir'] == 1 and slope_u[1] < 0 and slope_l[1] > 0:
                trolley['slope_dir'] = -1
            elif trolley['slope_dir'] == -1 and slope_u[1] > 0 and slope_l[1] < 0:
                trolley['slope_dir'] = 1

        # （補正）検出した点を傾きの中心にする
#         if trolley['err_diff'][0] == 0 and trolley['err_edge'][0] == 0:  # test
        if trolley['err_edge'][0] == 0:  # test
            if trolley['slope_dir'] == 1:
                center_u = (max(im_slice[idx_u-2:idx_u+8]).astype(np.int16) + min(im_slice[idx_u-7:idx_u+3]).astype(np.int16)) / 2  # test
#                 valmax = max(im_slice[idx_u-2:idx_u+8]).astype(np.int16)  # test
#                 valmin = min(im_slice[idx_u-7:idx_u+3]).astype(np.int16)  # test
#                 center_u = valmin + (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                idx_uu = np.argmin(im_slice[idx_u-7:idx_u+3]) + (upper-7) # 追加
                idx_ul = np.argmax(im_slice[idx_u-2:idx_u+8]) + (upper-2) # 追加
            elif trolley['slope_dir'] == -1:
                center_u = (max(im_slice[idx_u-7:idx_u+3]).astype(np.int16) + min(im_slice[idx_u-2:idx_u+8]).astype(np.int16)) / 2  # test
#                 valmax = max(im_slice[idx_u-7:idx_u+3]).astype(np.int16)  # test
#                 valmin = min(im_slice[idx_u-2:idx_u+8]).astype(np.int16)  # test
#                 center_u = valmax - (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                idx_uu = np.argmax(im_slice[idx_u-7:idx_u+3]) + (upper-7) # 追加
                idx_ul = np.argmin(im_slice[idx_u-2:idx_u+8]) + (upper-2) # 追加
#             diff1 = abs(im_slice[idx_u-1:idx_u+2] - center_u)
            if idx_uu < idx_ul:
                diff1 = abs(im_slice[idx_uu:idx_ul+1] - center_u)
                idx_u = np.argmin(diff1) + idx_uu
#         if trolley['err_diff'][1] == 0 and trolley['err_edge'][1] == 0:  # test
        if trolley['err_edge'][1] == 0:  # test
            if trolley['slope_dir'] == 1:
                center_l = (max(im_slice[idx_l-7:idx_l+3]).astype(np.int16) + min(im_slice[idx_l-2:idx_l+8]).astype(np.int16)) / 2  # test
#                 valmax = max(im_slice[idx_l-7:idx_l+3]).astype(np.int16)  # test
#                 valmin = min(im_slice[idx_l-2:idx_l+8]).astype(np.int16)  # test
#                 center_l = valmin + (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                idx_lu = np.argmax(im_slice[idx_l-7:idx_l+3]) + (lower-7) # 追加
                idx_ll = np.argmin(im_slice[idx_l-2:idx_l+8]) + (lower-2) # 追加
            elif trolley['slope_dir'] == -1:
                center_l = (max(im_slice[idx_l-2:idx_l+8]).astype(np.int16) + min(im_slice[idx_l-7:idx_l+3]).astype(np.int16)) / 2  # test
#                 valmax = max(im_slice[idx_l-2:idx_l+8]).astype(np.int16)  # test
#                 valmin = min(im_slice[idx_l-7:idx_l+3]).astype(np.int16)  # test
#                 center_l = valmax - (valmax + valmin) * 0.3               # 中心から外にずらし中央へのズレを防止  # test
                idx_lu = np.argmin(im_slice[idx_l-7:idx_l+2]) + (lower-7) # 追加
                idx_ll = np.argmax(im_slice[idx_l-2:idx_l+8]) + (lower-2) # 追加
#             diff2 = abs(im_slice[idx_l-1:idx_l+2] - center_l)
            if idx_lu < idx_ll:
                diff2 = abs(im_slice[idx_lu:idx_ll+1] - center_l) 
                idx_l = np.argmin(diff2) + idx_lu

        # （補正）変化は±1とする
        if (int(idx_u) - upper) <= -2:
            idx_u = upper - 1
        elif (int(idx_u) - upper) >= 2:
            idx_u = upper + 1
        else:
            idx_u = int(idx_u)
        if (int(idx_l) - lower) <= -2:
            idx_l = lower - 1
        elif (int(idx_l) - lower) >= 2:
            idx_l = lower + 1
        else:
            idx_l = int(idx_l)
        
        # （補正）
        # 過去の平均中心点を基準に検出したidx_uとidx_lが上下に分かれていることを確認
        # そうでない場合は過去の平均値とする
        if not (idx_u < center_avg):
            idx_u = upper_avg
        if not (idx_l > center_avg):
            idx_l = lower_avg

        # 検出値を記録
        # 上下ともエッジが検出できなければ欠損値とする
        if trolley['err_edge'][0:2] == [1, 1]:
            write_value(trolley, np.nan, np.nan)
            trolley['err_nan'][0] = 1
            trolley['err_nan'][1] += 1
        else:
            write_value(trolley, idx_u, idx_l)
            trolley['err_nan'][0] = 0
            
        # トロリ線幅が極端に小さい場合と大きい場合エラーとしカウント
        if (trolley['last_state'][1] - trolley['last_state'][0]) <= 1:
            trolley['err_width'][0] = 1
            trolley['err_width'][2] += 1
        else:
            trolley['err_width'][0] = 0
        if (trolley['last_state'][1] - trolley['last_state'][0]) >= 28:
            trolley['err_width'][1] = 1
            trolley['err_width'][3] += 1
        else:
            trolley['err_width'][1] = 0

        # エッジ基準を更新
        # ただし、エッジが検出できない場合は更新しない
        if trolley['err_edge'][0] == 0:
            if len(trolley['edge_std_list_u']) == 10:
                trolley['edge_std_list_u'].pop(0)
            trolley['edge_std_list_u'].append(im_slice[idx_u-7:idx_u+8])
        if trolley['err_edge'][1] == 0:
            if len(trolley['edge_std_list_l']) == 10:
                trolley['edge_std_list_l'].pop(0)
            trolley['edge_std_list_l'].append(im_slice[idx_l-7:idx_l+8])

        # 検出したエッジの色変更
        if math.isnan(trolley['upper_line'][-1]) == False:
            trolley['picture']['im_trolley'][int(idx_u), ix, :] = [-250, 250, -250]   # 正常に検出した場合「緑」
        elif math.isnan(trolley['upper_line'][-1]) == True:
            trolley['picture']['im_trolley'][int(idx_u), ix, :] = [255, -250, -250]   # 輝度が背景に近い場合場合「赤」
        if math.isnan(trolley['lower_line'][-1]) == False:
            trolley['picture']['im_trolley'][int(idx_l), ix, :] = [-250, 250, -250]   # 正常に検出した場合「緑」
        elif math.isnan(trolley['lower_line'][-1]) == True:
            trolley['picture']['im_trolley'][int(idx_l), ix, :] = [255, -250, -250]   # 輝度が背景に近い場合場合「赤」

        # その他検出値等を記録
        trolley['last_state'] = [idx_u, idx_l]
        trolley['upper_diff'].append(val_u)
        trolley['lower_diff'].append(val_l)
        trolley['picture']['im_slice_org'] = im_slice_org
        trolley['picture']['im_slice'] = im_slice
    
    else:
        write_value(trolley, np.nan, np.nan)
        trolley['err_skip'][0:2] = [0 ,0]
        trolley['err_diff'][0:2] = [0 ,0]
        trolley['err_edge'][0:2] = [0 ,0]
        trolley['err_nan'][0:2] = [0 ,0]
        
    trolley['err_log_u'].append([trolley['err_skip'][0], trolley['err_diff'][0], trolley['err_edge'][0]])
    trolley['err_log_l'].append([trolley['err_skip'][1], trolley['err_diff'][1], trolley['err_edge'][1]])
    
    return


#---------------------------------------
# 2本目のトロリ線検出（Wイヤー、ASAJ） & 
#---------------------------------------
def search_second_trolley(rail, trolley1, trolley2, file_idx, ix):
    if (
        (ix % 5 == 0) and 
        ((trolley2['trolleyID'] == 2 and trolley2['w-ear'] == 0) or
        (trolley2['trolleyID'] == 3 and trolley2['as_aj'] == 0))
    ):
        upper = np.round(trolley1['last_state'][0]).astype(np.int16)
        lower = np.round(trolley1['last_state'][1]).astype(np.int16)
        im_slice = trolley1['picture']['im_slice']

        if trolley2['trolleyID'] == 2:
            # サーチ範囲（Ｗイヤー）の場合
            # メインのトロリ線から上下50ピクセル
            # ただし元のトロリ線直近の5ピクセルを除く
            st1 = (upper - 40) if upper >= 47 else 7
            ed1 = (upper - 5) if upper >= 13 else 8
            st2 = (lower + 5) if lower <= 2034 else 2039
            ed2 = (lower + 40) if lower <= 2000 else 2040
        elif trolley2['trolleyID'] == 3:
            # サーチ範囲（AS・AJ）
            # メインのトロリ線から上下700ピクセル
            # ただし元のトロリ線直近の50ピクセルを除く
            st1 = (upper - 700) if upper >= 707 else 7
            ed1 = (upper - 50) if upper >= 58 else 8
            st2 = (lower + 50) if lower <= 1989 else 2039
            ed2 = (lower + 700) if lower <= 1340 else 2040

        # 元のトロリ線の境界と近い場所をサーチ
        diff_val_u, diff_val_l, diff_idx_u, diff_idx_l  = [], [], [], []
        for area in [[st1, ed1],[st2, ed2]]:
            for i in range(area[0], area[1]):
                diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - trolley1['edge_std_u'].astype(int)))
                diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - trolley1['edge_std_l'].astype(int)))
                if diff1 <= 200: # 150 => 200 (2022.10.04)
                    diff_val_u.append(diff1)
                    diff_idx_u.append(i)
                if diff2 <= 200: # 150 => 200 (2022.10.04)
                    diff_val_l.append(diff2)
                    diff_idx_l.append(i)
        if len(diff_val_u) > 0:
            diff_val_u = np.array(diff_val_u)
            diff_sort_u = np.argsort(diff_val_u)
        if len(diff_val_l) > 0:
            diff_val_l = np.array(diff_val_l)
            diff_sort_l = np.argsort(diff_val_l)

        # 平行トロリ線が存在するかどうか判断
        idx_u, idx_l, val_u, val_l = 0, 0, 0, 0
        if len(diff_val_u) > 0 and len(diff_val_l) > 0:
            for u in diff_sort_u:
                for l in diff_sort_l:
                    if 35 > (diff_idx_l[l] - diff_idx_u[u]) > 0:
                        idx_u = diff_idx_u[u]
                        val_u = diff_val_u[u]
                        idx_l = diff_idx_l[l]
                        val_l = diff_val_l[l]
                        break
                if idx_u != 0:
                    break
            if idx_u != 0 and trolley2['trolleyID'] == 2:
                trolley2['w-ear'] = 1
                trolley2['isInFrame'] = True
            if idx_u != 0 and trolley2['trolleyID'] == 3:
                trolley2['as_aj'] = 1
                trolley2['isInFrame'] = True

        # 検出値等を記録
        trolley2['last_state'] = [idx_u, idx_l]
        
        # 立ち上がりの向きをメインのトロリ線に合わせる
        trolley2['slope_dir'] = trolley1['slope_dir']

        # エッジ基準を作成
        if trolley2['isInFrame'] == True:
            if len(trolley2['edge_std_list_u']) == 10:
                trolley2['edge_std_list_u'].pop(0)
            trolley2['edge_std_list_u'].append(im_slice[idx_u-7:idx_u+8])
            if len(trolley2['edge_std_list_l']) == 10:
                trolley2['edge_std_list_l'].pop(0)
            trolley2['edge_std_list_l'].append(im_slice[idx_l-7:idx_l+8])
        
    elif (
        (trolley2['trolleyID'] == 2 and trolley2['w-ear'] >= 1) or
        (trolley2['trolleyID'] == 3 and trolley2['as_aj'] >= 1)
    ):
        # 一定上のエラー数でトロリ線（メイン）の消失（もしくは誤検出）と判断
        if (
            trolley2['err_width'][2] >= 150 or
            trolley2['err_width'][3] >= 150 or
            trolley2['err_nan'][1] >= 100
        ):
            reset_trolley(trolley2)
        else:
            if trolley2['trolleyID'] == 2:
                trolley2['w-ear'] += 1
            elif trolley2['trolleyID'] == 3:
                trolley2['as_aj'] += 1
            
    return


#---------------------------------------
# トロリ線の切り替え
#---------------------------------------
def change_trolley(trolley1, trolley2, trolley3):
    # トロリ線（Wイヤー）とトロリ線（ASAJ）の両方が存在するとき
    # エラーの数を比較して誤検出と思われる側をリセット
    if trolley2['isInFrame'] == True and trolley3['isInFrame'] == True:
        cnt_err2 = trolley2['err_width'][2] + trolley2['err_width'][3] + trolley2['err_nan'][1]
        cnt_err3 = trolley3['err_width'][2] + trolley3['err_width'][3] + trolley3['err_nan'][1]
        if cnt_err2 < cnt_err3:
            reset_trolley(trolley3)
        elif cnt_err2 > cnt_err3:
            reset_trolley(trolley2)
    
    # 一定上のエラー数でトロリ線（メイン）の消失と判断
    if (
        trolley1['err_width'][2] >= 150 or  # トロリ線幅（小） 判定基準は適当
        trolley1['err_width'][3] >= 150 or   # トロリ線幅（大） 判定基準は適当
        trolley1['err_nan'][1] >= 100        # エッジ検出無し　判定基準は適当
    ):
        reset_trolley(trolley1)
        print('Reset Trolley1')
       
    # トロリ線（メイン）の切り替え
    if trolley1['isInFrame'] == False and trolley2['isInFrame'] == True:
        trolley1['edge_std_list_u'] = trolley2['edge_std_list_u'].copy()
        trolley1['edge_std_list_l'] = trolley2['edge_std_list_l'].copy()
        trolley1['edge_std_u'] = trolley2['edge_std_u'].copy()
        trolley1['edge_std_l'] = trolley2['edge_std_l'].copy()
        trolley1['last_state'] = trolley2['last_state'].copy()
        trolley1['last_upper_line'] = trolley2['last_upper_line'].copy()
        trolley1['last_lower_line'] = trolley2['last_lower_line'].copy()
        trolley1['isInFrame'] = True
        print('Change Trolley -> 2')
        reset_trolley(trolley2)
    elif trolley1['isInFrame'] == False and trolley3['isInFrame'] == True:
        trolley1['edge_std_list_u'] = trolley3['edge_std_list_u'].copy()
        trolley1['edge_std_list_l'] = trolley3['edge_std_list_l'].copy()
        trolley1['edge_std_u'] = trolley3['edge_std_u'].copy()
        trolley1['edge_std_l'] = trolley3['edge_std_l'].copy()
        trolley1['last_state'] = trolley3['last_state'].copy()
        trolley1['last_upper_line'] = trolley3['last_upper_line'].copy()
        trolley1['last_lower_line'] = trolley3['last_lower_line'].copy()
        trolley1['isInFrame'] = True
        reset_trolley(trolley3)
        print('Change Trolley -> 3')
    return
        

# 並行区間検出用データの保存先初期設定
def init_xl():
    wb = openpyxl.Workbook()
    ws1 = wb.create_sheet(title="Result")
    ws1.cell(row=1, column=1, value="Parallel")
    ws2 = wb.create_sheet(title="correlation")
    ws2.cell(row=1, column=1, value="Pic Name")
    title_list = ["Last_state", "Index", "Diff", "Avg", "Max", "Min", "Slope_Max", "Slope_Min"]
    column = 2
    for uplow in ["(Up)", "(Lo)"]:
        for title in title_list:
            ws2.cell(row=1, column=column, value=(title + uplow))
            column = (column+2) if title == title_list[-1] else (column+1)
    ws = wb["Sheet"]
    wb.remove(ws)
    return wb, ws1, ws2

# ------------------------------------------------------------
# 出力データフレーム
# ------------------------------------------------------------
def get_result_dic():
    dic = {
        'inpath':[],
        'outpath':[],
        'infile':[],
        'camera_num':[],
        'global_ix':[],
        'ix':[],
        'upper_edge1':[],
        'lower_edge1':[],
        'width1':[],
        'blightness_center1':[],
        'blightness_mean1':[],
        'blightness_std1':[],
        'upper_edge2':[],
        'lower_edge2':[],
        'width2':[],
        'blightness_center2':[],
        'blightness_mean2':[],
        'blightness_std2':[],
        'upper_edge3':[],
        'lower_edge3':[],
        'width3':[],
        'blightness_center3':[],
        'blightness_mean3':[],
        'blightness_std3':[]
    }
    return dic.copy()


# ------------------------------------------------------------
# 出力データフレーム
# ------------------------------------------------------------
def update_result_dic(rail, trolley1, trolley2, trolley3, file, outpath, file_idx, ix):
    img1 = trolley1['picture']['im_org']
    img2 = trolley2['picture']['im_org']
    img3 = trolley2['picture']['im_org']
    upper_edge1 = trolley1['last_state'][0]
    lower_edge1 = trolley1['last_state'][1]
#     center_trolley1 = lower_edge1 - upper_edge1
    center_trolley1 = (lower_edge1 + upper_edge1) // 2
    upper_edge2 = trolley2['last_state'][0]
    lower_edge2 = trolley2['last_state'][1]
#     center_trolley2 = lower_edge2 - upper_edge2
    center_trolley2 = (lower_edge2 + upper_edge2) // 2
    upper_edge3 = trolley3['last_state'][0]
    lower_edge3 = trolley3['last_state'][1]
#     center_trolley3 = lower_edge3 - upper_edge3
    center_trolley3 = (lower_edge3 + upper_edge3) // 2
    
    dic = trolley1['result_dict']
    dic['inpath'].append(rail['inpath'][file_idx])
    dic['outpath'].append(outpath + 'out_' + [s for s in rail['infile'] if st.session_state.camera_num_mem in s][file_idx])
    dic['infile'].append(rail['infile'][file_idx])
    dic['camera_num'].append(st.session_state.camera_num_mem)
    dic['global_ix'].append(file_idx * 1000 + ix)
    dic['ix'].append(ix)
    dic['upper_edge1'].append(upper_edge1)
    dic['lower_edge1'].append(lower_edge1)
    dic['width1'].append(lower_edge1 - upper_edge1)
    dic['blightness_center1'].append(img1[center_trolley1, ix, 0])
    dic['blightness_mean1'].append(np.mean(img1[upper_edge1:lower_edge1+1, ix, 0]))
    dic['blightness_std1'].append(np.std(img1[upper_edge1:lower_edge1+1, ix, 0]))
    dic['upper_edge2'].append(upper_edge2)
    dic['lower_edge2'].append(lower_edge2)
    dic['width2'].append(lower_edge2 - upper_edge2)
    dic['blightness_center2'].append(img2[center_trolley2, ix, 0])
    dic['blightness_mean2'].append(np.mean(img2[upper_edge2:lower_edge2+1, ix, 0]))
    dic['blightness_std2'].append(np.std(img2[upper_edge2:lower_edge2+1, ix, 0]))
    dic['upper_edge3'].append(upper_edge3)
    dic['lower_edge3'].append(lower_edge3)
    dic['width3'].append(lower_edge3 - upper_edge3)
    dic['blightness_center3'].append(img3[center_trolley3, ix, 0])
    dic['blightness_mean3'].append(np.mean(img3[upper_edge3:lower_edge3+1, ix, 0]))
    dic['blightness_std3'].append(np.std(img3[upper_edge3:lower_edge3+1, ix, 0]))
    return 

def write_result_dic_to_csv(rail, trolley, dir_area, main_view):
    dic = trolley['result_dict']
    df = pd.DataFrame.from_dict(dic)
    # カメラ番号が一致するoutpathを取得する
    # outpath = rail['outpath']
    outpath = [s for s in rail['outpath'] if st.session_state.camera_num_mem in s][0]
    # main_view.write(f'outpath:{outpath}')
    # main_view.write(f'df.to_csv path: {outpath}result_{dir_area}_{st.session_state.camera_num_mem}.csv')
    df.to_csv(f'{outpath}result_{dir_area}_{st.session_state.camera_num_mem}.csv', index=False)
    main_view.success(f'CSVファイルが出力されました 保存場所☞{outpath}result_{dir_area}_{st.session_state.camera_num_mem}.csv')
    return


def check_default(img, center):
    # 矢印画像作成
    img_zero1 = np.zeros((2048, 200, 3)) + 255
    img_zero1 = img_zero1.astype("uint8")
    for i in range(5):
        img_zero1[1024+i-2, :, :] = [255, 0, 0]
    for i in range(70):
        img_zero1[1024-i-2:1024-i+2, (199-i), :] = [255, 0, 0]
        img_zero1[1024+i+2:1024+i+6, (199-i), :] = [255, 0, 0]

    # 三角線画像作成
    img_zero2 = np.zeros((2048, 200, 3)) + 255
    img_zero2 = img_zero2.astype("uint8")
    for i in range(2048):
        if i <= center:
            xt = round(199 / center * i)
        else:
            xt = round(199 - 199 / (2047 - center) * (i-center))
        img_zero2[i, xt, :] = [255, 0, 0]

    # 拡大画像作成
    img_zoom = img[center-256:center+256, 0:100, :]
    img_zoom = cv2.resize(img_zoom, (400, 2048))

    # 画像の結合
    list_img = []
    list_img.append(img_zero1)
    list_img.append(img_zoom)
    list_img.append(img_zero2)
    list_img.append(img)
    img_join = cv2.hconcat(list_img)
    img_join = cv2.resize(img_join, (250, 512))
    
    return img_join