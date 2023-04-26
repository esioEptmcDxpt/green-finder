import streamlit as st
import os
import re
import datetime
from PIL import Image
from pathlib import Path


'''
Streamlitで共通して使用する機能をまとめたモジュール
'''

# helpers.pyに移植済
def read_markdown_file(markdown_file):
    return Path(markdown_file).read_text()


# helpers.pyに移植済
def read_python_file(python_file):
    return Path(python_file).read_text()


# session_state初期化
def session_state_init():
    # st.write('rail meta is initializing...')
    st.session_state.rail_set = False
    st.session_state.rail_set_onetime = False
    st.session_state.rail = {}
    st.session_state.camera_num_mem = None
    st.session_state.image_list = []
    st.session_state.dir_area = ''    # たぶん不要
    st.session_state.csv_path = None
    st.session_state.trolley_analysis = False
    st.session_state.trolley1 = {}
    st.session_state.trolley2 = {}
    st.session_state.trolley3 = {}
    st.session_state.analysis_message = 'これから解析を始めます'
    st.session_state.input_widget_set = False
    st.session_state.center_set = False
    st.session_state.auto_edge_set = False
    st.session_state.xin = None
    st.session_state.initial_idx = None
    st.session_state.error_flag = False
    return


# config.pyに移植済み
def camera_names():
    camera_names = {
        "HD11": "高(左)",
        "HD12": "高(右)",
        "HD21": "中(左)",
        "HD22": "中(右)",
        "HD31": "低(左)",
        "HD32": "低(右)",
}
    return camera_names


# config.pyに移植済み
def rail_names():
    rail_names = {
        "Kawagoe" : "川越線",
        "Chuo" : "中央線",
        "Utsunomiya" : "宇都宮線",
    }
    return rail_names

# helpers.pyに移植済
def rail_name2jp(rail_name):
    rail_names_dic = rail_names()
    rail_name_jp = rail_names_dic[rail_name]
    return rail_name_jp


# config.pyに移植済み
def station_names():
    station_names = {
        "Tokyo" : "東京",
        "Kanda" : "神田",
        "Ochanomizu" : "御茶ノ水",
        "Suidobashi" : "水道橋",
        "Iidabashi" : "飯田橋",
        "Ichigaya" : "市ヶ谷",
        "Yotsuya" : "四ツ谷",
        "Shinanomachi" : "信濃町",
        "Sendagaya" : "千駄ヶ谷",
        "Yoyogi" : "代々木",
        "Shinjuku" : "新宿",
        "Omiya" : "大宮",
        "Miyahara" : "宮原",
        "Nisshin" : "日進",
        "Nishioomiya" : "西大宮",
        "Sashiougi" : "指扇",
        "Minamifuruya" : "南古谷",
    }
    return station_names


# helpers.pyに移植済み
def station_name2jp(st_name):
    station_names_dic = station_names()
    station_name_jp = station_names_dic[st_name]
    return station_name_jp


# helpers.pyに移植済
def rail_updown(updown_str):
    if updown_str == 'up':
        updown_str_jp = '上り'
    elif updown_str == 'down':
        updown_str_jp = '下り'
    return updown_str_jp


# helpers.pyに移植済
def day_knight(day_knight_str):
    if day_knight_str == 'day':
        day_knight_jp = '昼間'
    elif day_knight_str == 'knight':
        day_knight_jp = '夜間'
    return day_knight_jp


# helpers.pyに移植済み
def rail_message(dir_area):
    str_list = re.split('[_-]', dir_area)
    rail_name = rail_name2jp(str_list[0])
    if str_list[3] == 'St':
        st_name = station_name2jp(str_list[2]) + '構内'
    else:
        st_name = station_name2jp(str_list[2]) + '～' + station_name2jp(str_list[3])
    updown_name = rail_updown(str_list[4])
    date_obj = datetime.datetime.strptime(str_list[5], "%Y%m%d")
    measurement_date = date_obj.strftime("%Y年%m月%d日")    # # yyyy年mm月dd日形式の文字列に変換
    measurement_time = day_knight(str_list[6])
    return rail_name, st_name, updown_name, measurement_date, measurement_time


# helpers.pyに移植済み
def camera_num2name(camera_num):
    camera_names_dict = camera_names()
    camera_name = camera_names_dict[camera_num]
    return camera_name

def get_dir_list(path):
    dir_path = Path(path)
    dir_obj_list = [path for path in dir_path.glob("*") if path.is_dir() and not path.name.startswith(".")]
    dir_list = [image_obj.name for image_obj in dir_obj_list]
    dir_list.sort()
    return dir_list

def get_file_list(path):
    dir_path = Path(path)
    image_obj_list = [path for path in dir_path.glob("*") if path.is_file()]
    image_list = [image_obj.name for image_obj in image_obj_list]
    image_list.sort()
    return image_list

def ohc_image_load(path, main_view):
    try:
        img = Image.open(path)
        st.session_state.result_img_get = True
    except Exception as e:
        img = None
        st.session_state.analysis_messag = "解析対象の画像がありません。"
        st.session_state.result_img_get = False
    return img
