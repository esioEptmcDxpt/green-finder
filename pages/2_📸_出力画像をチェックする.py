import streamlit as st
import boto3
import numpy as np
import matplotlib.pyplot as plt
import os, glob, random, urllib, cv2, datetime, statistics, math
from PIL import Image
from io import BytesIO
# import src.utilsS3_01 as utls3
import src.utilsST_01 as utlst


def result_image_view():
    
    st.set_page_config(page_title="結果画像ビューワー", page_icon="📸")
    st.sidebar.header("結果画像閲覧システム")
   
    # 変数宣言＆session_state初期化
    CAMERA_NUMS = ['HD11','HD12','HD21','HD22','HD31','HD32']
    if 'rail_set' not in st.session_state:
        utlst.session_state_init()
        
    # メインページのコンテナを配置する
    main_view = st.container()
    camera_view = st.empty()
        
    # 線区を指定
    rail_set_form(CAMERA_NUMS, main_view)
    
    if st.session_state.rail_set:
        # メインページに設定した線区等の情報を表示する
        rail_name, st_name, updown_name, measurement_date, measurement_time = utlst.rail_message(st.session_state.dir_area)
        with main_view.container():
            st.markdown(f"### 現在の線区：{rail_name} {st_name}({updown_name})")
            st.markdown(f"### 　　測定日：{measurement_date} ＜{measurement_time}＞")
            st.success("##### 👆別の線区を表示する場合は、再度「線区フォルダを決定」してください") 
    else:
    # 線区が指定されていなければストップ
        main_view.success('💡線区フォルダを選択')
        st.stop()
        
    # カメラ画像選択フォームを表示
    file_idx, cam_img, result_img_path = camera_set_form(CAMERA_NUMS, main_view)

    main_view.write(f'st.session_state.result_img_get:{st.session_state.result_img_get}')
    
    # カメラビューを表示する
    if not st.session_state.result_img_get:
        main_view.write(f'st.session_state.result_img_get is False? ->{st.session_state.result_img_get}')
        st.session_state.analysis_message = '解析後の画像が見つかりません'
        column_view(main_view, camera_view, file_idx, cam_img, '', '')
    else:
        column_view(main_view, camera_view, file_idx, cam_img, result_img_path, '')

    return

# 線区を指定 Forms->Submit後にメタデータを生成する
def rail_set_form(CAMERA_NUMS, main_view):
    '''
    サイドバーの入力フォーム
    線区をフォームで指定する
    '''
    with main_view.container():
        with st.form('解析する線区を指定する', clear_on_submit=False):
            # rail_list = utls3.get_s3_dir_list('OHCImages/images/')    # S3の場合
            rail_list = utlst.get_dir_list('images/')    # EBSの場合
            dir_area = st.selectbox('線区フォルダ名を選んで決定してください', rail_list)
            rail_set = st.form_submit_button('線区フォルダを決定')
    if rail_set:
        # 線区フォルダ決定後に実行
        st.session_state.rail_set = True
        st.session_state.dir_area = dir_area
    return

# カメラ画像をセット
def camera_set_form(CAMERA_NUMS, main_view):
    '''
    サイドバーの入力フォーム
    カメラ番号を切替える
    '''
    result_img = None
    # カメラを選択する
    camera_names = utlst.camera_names()
    camera_name_list = [camera_names[camera_name] for camera_name in camera_names]
    camera_name = st.sidebar.selectbox("解析対象のカメラを選択してください", camera_name_list)
    camera_num = CAMERA_NUMS[camera_name_list.index(camera_name)]   # 内部ではHD11,12,21,22,31,32で処理する
    
    # st.selectbox('(デバッグ用)image_list', st.session_state.image_list)
    
    # 既にセットされている線区・カメラ番号と異なっていれば実行
    if st.session_state.camera_num_mem != camera_num:
        # カメラごとの画像ファイルのリストを取得
        # st.session_state.image_list = utls3.get_s3_image_list("OHCImages/images/" + st.session_state.dir_area + "/" + camera_num + "/")    # S3の場合
        st.session_state.image_list = utlst.get_file_list("images/" + st.session_state.dir_area + "/" + camera_num + "/")    # EBSの場合

        # if not st.session_state.image_list:
            # main_view.write(f'image_list is empty')
            # main_view.write('解析対象の画像がありません。別の線区・カメラを選択してください。')
            # st.stop()
        # 次のためにimage_listを作成したcamera_numをsession_stateに記録しておく
        st.session_state.camera_num_mem = camera_num
    
#     main_view.write(f'[after] camera_num:{camera_num}, session_state:{st.session_state.camera_num_mem}')
    
    
    # idx選択ウィジェット
    idx = st.sidebar.number_input(f'画像インデックスを選択(1～{len(st.session_state.image_list)}で指定)', 1, len(st.session_state.image_list), 1)
    
    # 画像位置を表示
    img_count = len(st.session_state.image_list)
    progress_text = f'表示中の位置(画像枚数：{idx}/{img_count})'
    main_view.write(progress_text)
    camera_view_bar = main_view.progress(idx/img_count)
    
    # 解析前の画像を取得
    # cam_img = utls3.ohc_image_load("OHCImages/images/" + st.session_state.dir_area + "/" + camera_num + "/" + st.session_state.image_list[idx - 1], main_view)    # S3の場合
    cam_img = utlst.ohc_image_load("images/" + st.session_state.dir_area + "/" + camera_num + "/" + st.session_state.image_list[idx - 1], main_view)    # EBSの場合
    
    # 解析後の画像を取得
    # S3の場合
    # result_img_path = 'OHCImages/output/' + st.session_state.dir_area + '/' + camera_num + '/out_' + st.session_state.image_list[idx-1]
    # result_img = utls3.ohc_image_load(result_img_path, main_view)
    # EBSの場合
    result_img_path = "output/" + st.session_state.dir_area + "/" + camera_num + "/out_" + st.session_state.image_list[idx - 1]
    # result_img = utlst.ohc_image_load(result_img_path, main_view)
    
    main_view.write(f'(camera_set_form)st.session_state.result_img_get:{st.session_state.result_img_get}')

    return idx-1, cam_img, result_img_path

# メインページにカラム表示する
def column_view(main_view, camera_view, file_idx, cam_img, result_img_path, fig):
    col1, col2 = camera_view.columns(2)
    with col1:
        st.header("📸カメラ画像")
        st.write(f"カメラ:{utlst.camera_num2name(st.session_state.camera_num_mem)} {file_idx + 1}番目の画像です")
        st.image(cam_img)
    with col2:
        st.header("🖥️解析結果")
        st.write(f"{st.session_state.analysis_message}")
        if result_img_path != '' and fig == '':
            # result_img = utls3.ohc_image_load(result_img_path)    # S3の場合
            result_img = utlst.ohc_image_load(result_img_path, main_view)    # EBSの場合
            st.image(result_img)
        elif fig != '':
            st.pyplot(fig)
    return


if __name__ == "__main__":
    result_image_view()

