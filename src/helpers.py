import os
import glob
import re
import datetime
import pandas as pd
import streamlit as st
from pathlib import Path
from PIL import Image


# @st.cache
def list_imagespath(image_dir):
    images_fullpath = glob.glob(os.path.join(image_dir, "*"))
    images_fullpath = [folder for folder in images_fullpath if os.path.isdir(folder)]
    images_path = [os.path.basename(folder) for folder in images_fullpath]
    images_path.sort()
    return images_path


# @st.cache
def list_images(target_dir):
    base_images = glob.glob(target_dir + "/*.jpg")
    base_images.sort()
    return base_images


# @st.cache
def get_dir_list(path):
    dir_path = Path(path)
    dir_obj_list = [path for path in dir_path.glob("*") if path.is_dir() and not path.name.startswith(".")]
    dir_list = [image_obj.name for image_obj in dir_obj_list]
    dir_list.sort()
    return dir_list


# @st.cache
def get_file_list(path):
    dir_path = Path(path)
    image_obj_list = [path for path in dir_path.glob("*") if path.is_file()]
    image_list = [image_obj.name for image_obj in image_obj_list]
    image_list.sort()
    return image_list


# @st.cache
def read_markdown_file(markdown_file):
    return Path(markdown_file).read_text()


# @st.cache
def read_python_file(python_file):
    return Path(python_file).read_text()


# @st.cache
def get_file_content_as_string(filename):
    st.code(filename)


# @st.cache
def ohc_image_load(base_images, idx, caption):
    st.text(f'{idx}番目の画像を表示します')
    im_base = Image.open(base_images[idx])
    st.image(im_base, caption=caption)
    return im_base


# @st.cache
def rail_name_to_jp(rail_name, config):
    return config.rail_names[rail_name]


# @st.cache
def station_name_to_jp(st_name, config):
    return config.station_names[st_name]


# @st.cache
def rail_type_to_jp(rail_type, config):
    return config.rail_type_names[rail_type]


# @st.cache
def rail_type_name_to_jp(time_band_names, config):
    return config.time_band_names[time_band_names]


# @st.cache
def camera_num_to_name(camera_num, config):
    return config.camera_names[camera_num]


# @st.cache
def rail_message(dir_area, config):
    str_list = re.split('[_-]', dir_area)
    rail_name = rail_name_to_jp(str_list[0], config)
    if str_list[3] == 'St':
        st_name = station_name_to_jp(str_list[2], config) + '構内'
    else:
        st_name = station_name_to_jp(str_list[2], config) + '～' + station_name_to_jp(str_list[3], config)
    updown_name = rail_type_to_jp(str_list[4], config)
    date_obj = datetime.datetime.strptime(str_list[5], "%Y%m%d")
    measurement_date = date_obj.strftime("%Y年%m月%d日")    # # yyyy年mm月dd日形式の文字列に変換
    measurement_time = rail_type_name_to_jp(str_list[6], config)
    return rail_name, st_name, updown_name, measurement_date, measurement_time


# @st.cache
def print_files(dir_name, csvname, cam):
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
    files = sorted(glob.glob(f"{dir_name}/{cam}/*.jpg"))
    for file in files:
        dict["dirname"].append(os.path.dirname(file))
        dict["filename"].append(os.path.basename(file))
        dict["camera_num"].append(cam)
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
    print(f"output file is: {dir_name}temp_meta.csv")
    df.to_csv(f"{dir_name}/{csvname}_temp_meta.csv", index=False)
    return


