import os
import shelve
import streamlit as st
import time    # デバッグ用、後で削除する
import numpy as np
import datetime
import src.helpers as helpers
import src.visualize as vis
from src.kalman_calc import track_kalman
from src.similar_pixel_calc import track_pixel
# import src.similar_pixel_calc as sim_pix    # 摩耗判定システム機能
import src.utilsST_01 as utlst    # 移行が完了したら削除する
from src.config import appProperties


def ohc_wear_analysis(config):
    # マルチページの設定
    st.set_page_config(page_title="トロリ線摩耗検出システム")
    st.sidebar.header("トロリ線摩耗検出システム")
        
    # メインページのコンテナを配置する
    main_view = st.container()
    camera_view = st.empty()
    
    # フォルダ直下の画像保管用ディレクトリのリスト
    images_path = helpers.list_imagespath(config.image_dir)
    
    # 画像保管線区の選択
    dir_area = st.sidebar.selectbox("線区のフォルダ名を選択してください", images_path)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")
    vis.dir_area_view_JP(config, dir_area, main_view)
    
    # 解析対象のカメラ番号を選択する
    camera_num = st.sidebar.selectbox("解析対象のカメラを選択してください", (config.camera_types))
    
    # 解析対象の画像フォルダを指定
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num    # (長山)"/camera_num"を追加
    
    # outputディレクトリの準備
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num
    os.makedirs(outpath, exist_ok=True)
    
    # 既存のresultがあれば読み込み、なければ作成
    rail = shelve.open(outpath + "/rail.shelve", writeback=True)
    rail["name"] = dir_area
    
    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)
    
    # base_imagesと同じ長さの空のdictionaryを作成してrailを初期化
    blankdict_size = [{}] * len(base_images)
    rail[camera_num] = dict(zip(base_images, blankdict_size))
    
    # ファイルインデックスを指定する
    st.sidebar.markdown("# ファイルのインデックスを指定してください")
    idx = st.sidebar.number_input(f"インデックス(0～{len(base_images)-1}で指定)",
                                  min_value=0,
                                  max_value=len(base_images) - 1)
    
    # メインページにカメラ画像を表示する
    col1, col2, col3 = camera_view.columns(3)
    
    with col1:
        st.header("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images[idx], main_view)
        st.write(f"カメラ:{helpers.camera_num_to_name(camera_num, config)} {idx + 1}番目の画像です")
        st.image(cam_img)
    with col2:
        st.header("🖥️解析結果")
        st.write("解析結果を表示しています")
        # to be implemented
    with col3:
        st.header("📈メモリ付画像")
        fig = vis.plot_fig(base_images, idx)
        st.pyplot(fig)
    
    trace_method = st.sidebar.radio(
        "システムを選択", 
        ("ピクセルトレース", "カルマンフィルタ")
    )
    
    # ピクセルトレースを実行
    if trace_method == "ピクセルトレース":
        form_px = st.sidebar.form(key="similar_pixel_init")
        xin = form_px.number_input("トロリ線の中心位置を入力(0～2048)", 0, 2048, 1024)
        submit = form_px.form_submit_button("ピクセルトレース実行")
        if submit:
            with st.spinner("ピクセルトレース実行中"):
                track_pixel(
                    rail,
                    camera_num,
                    base_images,
                    idx,
                    trolley_id,
                    xin,
                )
    # カルマンフィルタを実行
    elif trace_method == "カルマンフィルタ":
        # カルマンフィルタの初期値設定
        form = st.sidebar.form(key="kalman_init")
        trolley_id = form.selectbox("トロリ線のIDを入力してください", ("trolley1", "trolley2"))
        x_init = form.number_input("横方向の初期座標を入力してください", 0, 999)
        y_init_u = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください", 0, 1999)
        y_init_l = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください", 0, 1999)
        submit = form.form_submit_button("カルマンフィルタ実行")

        if submit:
            with st.spinner("カルマンフィルタ実行中"):
                track_kalman(
                    rail,
                    camera_num,
                    base_images,
                    idx,
                    trolley_id,
                    x_init,
                    y_init_u,
                    y_init_l,
                )
    rail.close()

    st.stop()    # (編集中)強制ストップ
    '''
    以下、以前のコード
    '''
    # 線区セットフォームを表示（線区決定後に線区のメタデータcsvを生成する）
    rail_set_form(config, main_view)

    if st.session_state.rail_set:
        # メインページに設定した線区等の情報を表示する
        rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
        with main_view.container():
            st.markdown(f"### 現在の線区：{rail_name} {st_name}({updown_name})")
            st.markdown(f"### 　　測定日：{measurement_date} ＜{measurement_time}＞")
            st.success("##### 👆別の線区を表示する場合は、再度「線区フォルダを決定」してください") 
    
    # カメラ画像を指定 Form->Submit後に解析を開始する
    if st.session_state.rail_set:
        # カメラセットフォームを表示
        image_list, file_idx, cam_img = camera_set_form(config, main_view)

    # 解析ボタンを押したら動かしたいプログラム↓
    if st.session_state.trolley_analysis:
        # 解析開始時のイニシャライズ
        st.session_state.error_flag = False
        img_count = len(image_list) - file_idx
        progress_text = f'解析中です。完了するまでお待ちください。(画像枚数：{img_count})'
        main_view.write(progress_text)
        my_bar = main_view.progress(0)
        if main_view.button('解析結果をCSVに出力する ⚠️解析後に実行'):
            st.session_state.initial_idx = None
            st.session_state.center_set = False
            st.session_state.auto_edge_set = False
            main_view.write(f'【デバッグ用】st.session_state.dir_area:{st.session_state.dir_area}')
            sim_pix.write_result_dic_to_csv(st.session_state.rail, st.session_state.trolley1, st.session_state.dir_area, main_view)
            st.stop()

        outpath = [s for s in st.session_state.rail["outpath"] if st.session_state.camera_num_mem in s][0]
        while file_idx <= len(image_list) - 1:
            dt01 = datetime.datetime.now()
            # カメラ番号が一致するファイルを取得する
            file = [s for s in st.session_state.rail["inpath"] if st.session_state.camera_num_mem in s][file_idx]
            if file_idx == st.session_state.initial_idx:
                # トロリ線情報の作成
                trolley1 = sim_pix.get_trolley(trolleyID=1, isInFrame=True)
                trolley2 = sim_pix.get_trolley(trolleyID=2, isInFrame=False)
                trolley3 = sim_pix.get_trolley(trolleyID=3, isInFrame=False)

                # 画像ファイルを読み込む
                sim_pix.load_picture(trolley1, file)
                sim_pix.load_picture(trolley2, file)
                sim_pix.load_picture(trolley3, file)

                # 初期画像を表示
                img = trolley1["picture"]["im_org"]
                fig = sim_pix.plot_fig(img)
                st.session_state.analysis_message = "画像左端でのトロリ線中心位置を指定します"

                # 画像左端のエッジを自動検出
                search_list = sim_pix.search_trolley_init(trolley1, 0, img)
                if len(search_list) != 0:
                    center = np.sum(search_list[0][0:2]) // 2

                # 画像左端でのトロリ線の位置を設定するフォーム
                with st.sidebar.form('画像左端のトロリ線の中心位置を指定してください', clear_on_submit=False):
                    xin = st.number_input("トロリ線の中心位置を入力(0～2048)", 0, 2048, 1024)
                    center_set = st.form_submit_button('左端のトロリ線中心位置を指定')
                    if search_list:
                        st.write(f"自動検出位置: {search_list[0][0:2]}")
                    else:
                        st.write("自動検出位置: 未検出")
                    edge_set = st.form_submit_button('自動検出エッジで指定する')
                    
                    # 押されたフォームボタンによってフラグを変更する
                    if center_set:
                        st.session_state.center_set = True
                        st.session_state.auto_edge_set = False
                    if edge_set:
                        st.session_state.center_set = False
                        st.session_state.auto_edge_set = True

                if st.session_state.center_set:
                    st.sidebar.write("解析ログ👇")
                    st.session_state.xin = xin
                    st.sidebar.write(f"トロリ線中心を{st.session_state.xin}に設定しました")
                    sim_pix.set_init_val(st.session_state.rail, trolley1, 0, img, search_list, st.session_state.auto_edge_set)
                    main_view.write("## 解析実行🔍")
                elif st.session_state.auto_edge_set:
                    st.sidebar.write("解析ログ👇")
                    st.sidebar.write("自動検出位置で設定しました")
                    st.sidebar.write(f"自動検出位置: {search_list[0][0:2]}")
                    sim_pix.set_init_val(st.session_state.rail, trolley1, 0, img, search_list, st.session_state.auto_edge_set)
                    main_view.write("## 解析実行📈")
                else:
                    st.sidebar.success("💡画像左端のトロリ線位置を指定")

            elif file_idx == len(image_list) - 1:
                # 画像ファイルを読み込む
                sim_pix.load_picture(trolley1, file)
                sim_pix.load_picture(trolley2, file)
                sim_pix.load_picture(trolley3, file)
                img = trolley1["picture"]["im_org"]
                fig = sim_pix.plot_fig(img)
            else:
                # 画像ファイルを読み込む
                sim_pix.load_picture(trolley1, file)
                sim_pix.load_picture(trolley2, file)
                sim_pix.load_picture(trolley3, file)

            # 画像左端でのトロリ線の初期位置を指定したら実行
            if st.session_state.center_set or st.session_state.auto_edge_set:
                # 同一のカメラで連続して解析したい！
                st.sidebar.text(
                    f"{file_idx+1}/{len(image_list)}枚目を解析中, (デバッグ用)file_idx:{file_idx} ※0～"
                )
                st.sidebar.text(
                    str(datetime.datetime.now()) + f" Processing :{file}"
                )  # 後で削除する

                # if file_idx != st.session_state.initial_idx:
                # 画像ファイル読み込み
                # st.write(f'Next image loaded(file_idx:{file_idx})')

                # 画像の平均画素を算出（背景画素と同等とみなす）
                sim_pix.mean_brightness(trolley1, img)
                
                # pixel_bar = st.progress(0)
                with st.spinner(f'{file_idx + 1}枚目の画像を解析中'):
                    for ix in range(1000):
                        sim_pix.search_trolley(st.session_state.rail, trolley1, file_idx, ix)

                        sim_pix.search_second_trolley(st.session_state.rail, trolley1, trolley2, file_idx, ix)
                        sim_pix.search_second_trolley(st.session_state.rail, trolley1, trolley3, file_idx, ix)

                        sim_pix.search_trolley(st.session_state.rail, trolley2, file_idx, ix)
                        sim_pix.search_trolley(st.session_state.rail, trolley3, file_idx, ix)

                        # 出力ファイルへの書き込み
                        sim_pix.update_result_dic(st.session_state.rail, trolley1, trolley2, trolley3, file, outpath, file_idx, ix)
                    sim_pix.change_trolley(trolley1, trolley2, trolley3)

                    result_img_path = sim_pix.write_picture(trolley1, trolley2, trolley3,)

                    dt02 = datetime.datetime.now()
                    prc_time = dt02 - dt01
                    st.sidebar.text(str(datetime.datetime.now()) + f" Process end :{prc_time}")
                    st.session_state.analysis_message = "トロリ線の摺動面を検出した画像です"

                # トロリ線が検出できなかった場合
                if (
                    not trolley1["isInFrame"]
                    and not trolley2["isInFrame"]
                    and not trolley3["isInFrame"]
                ):
                    st.session_state.error_flag = True
                    if file_idx != len(image_list) - 1:
                        main_view.error(f"** トロリ線が検出できません(画像インデックスは{file_idx+1}です) **")
                        main_view.error(f"** 次の画像(画像インデックス{file_idx+2})からやり直してください。 **")
                        my_bar.progress(1 - (len(image_list) - file_idx) / img_count)
                        # continue
                        break
                    else:
                        st.error(
                            f"** トロリ線が検出できません(画像インデックスは{file_idx+1}です) 最後の画像のため解析を終了します。"
                        )
                        my_bar.progress(1 - (len(image_list) - file_idx) / img_count)
                        break
                        
            # カメラビューを設定する
            cam_img = vis.ohc_image_load(
                "images/" + st.session_state.dir_area + "/" + st.session_state.camera_num_mem + "/" + image_list[file_idx], 
                main_view
            )
            
            if st.session_state.center_set or st.session_state.auto_edge_set:
                column_view(main_view, camera_view, file_idx, cam_img, result_img_path, '')
            elif st.session_state.trolley_analysis and (
                file_idx == st.session_state.initial_idx
                or file_idx == len(image_list) - 1
            ):
                column_view(main_view, camera_view, file_idx, cam_img, '', fig)
            else:
                column_view(main_view, camera_view, file_idx, cam_img, '', '')
            
            # While文最後のインクリメント、解析開始前はwhileループさせない
            if st.session_state.center_set or st.session_state.auto_edge_set:
                file_idx += 1
                my_bar.progress(1 - (len(image_list) - file_idx) / img_count)
            else:
                my_bar.progress(1 - (len(image_list) - file_idx) / img_count)
                break

    # 線区が設定されていればメインページを表示する
    if st.session_state.rail_set:
        # メインページに表示する
        if st.session_state.center_set or st.session_state.auto_edge_set:
            # While文の最後になったら表示用のカメラ画像を更新する
            if file_idx >= len(image_list) - 1:
                main_view.success("## 最後の画像まで解析完了しました💡")
                main_view.write("最後の画像を読み込みなおしました")
                file_idx = len(image_list) - 1
                cam_img = vis.ohc_image_load(
                    "images/" + st.session_state.dir_area + "/" + st.session_state.camera_num_mem + "/" + image_list[file_idx],
                    main_view
                )
            elif st.session_state.error_flag:
                camera_view.error("## 解析エラーのため中断しました⚠️")
                camera_view.write("中断したときの画像を読み込みなおしました")
                cam_img = vis.ohc_image_load(
                    "images/" + st.session_state.dir_area + "/" + st.session_state.camera_num_mem + "/" + image_list[file_idx],
                    main_view
                )

        # カメラビューを表示する
        if st.session_state.center_set or st.session_state.auto_edge_set:
            column_view(main_view, camera_view, file_idx, cam_img, result_img_path, '')
        elif st.session_state.trolley_analysis and (
            file_idx == st.session_state.initial_idx
            or file_idx == len(image_list) - 1
        ):
            column_view(main_view, camera_view, file_idx, cam_img, '', fig)
        else:
            column_view(main_view, camera_view, file_idx, cam_img, '', '')

        st.sidebar.info("デバッグ用👇")
        st.sidebar.selectbox("取得されたファイルリスト", image_list)
        st.sidebar.write(f"結果出力ファイル:{st.session_state.csv_path}")
        st.sidebar.write(f'結果画像フォルダ:{st.session_state.rail["outpath"]}')

    # st.stop()
    return

# ---------------------------------------
# Streamlit操作
# ---------------------------------------

def rail_set_form(config, main_view):
    '''
    線区をフォームで指定し、その後に線区フォルダ内にメタデータ(csv)を生成する
    '''
    with main_view.container():
        with st.form('解析する線区を指定する', clear_on_submit=False):
            rail_list = helpers.get_dir_list('images/')
            dir_area = st.selectbox('線区フォルダ名を選んで決定してください', rail_list)
            rail_set = st.form_submit_button('線区フォルダを決定')
    if rail_set:
        st.session_state.rail_set_onetime = True
    elif not st.session_state.rail_set:
        # 線区が指定されていなければストップ
        st.sidebar.success("💡線区フォルダを選択")
        # st.stop()
    # ボタンをクリックしたときの動作
    if st.session_state.rail_set_onetime:
        # 線区フォルダ決定後に実行
        st.session_state.rail_set = True
        st.session_state.dir_area = dir_area
        # 線区を指定したらメタデータを作成
        st.session_state.csv_path = sim_pix.print_files("images/", st.session_state.dir_area, config.camera_types)
        # 辞書(rail)の作成
        st.session_state.rail = sim_pix.get_rail(
            st.session_state.csv_path, st.session_state.dir_area, config.camera_types
        )
        # ボタンクリックのフラグを元に戻す
        st.session_state.rail_set_onetime = False
    return


# カメラ画像をセット
def camera_set_form(config, main_view):
    '''
    サイドバーの入力フォーム
    カメラ番号を切替える
    '''
    # カメラを選択する
    camera_names = config.camera_names
    camera_name_list = [camera_names[camera_name] for camera_name in camera_names]
    camera_name = st.sidebar.selectbox("解析対象のカメラを選択してください", camera_name_list)
    camera_num = config.camera_types[camera_name_list.index(camera_name)]   # 内部ではHD11,12,21,22,31,32で処理する
    
    # main_view.write(f'camera_num:{camera_num}, st.session_state.camera_num_mem:{st.session_state.camera_num_mem}')

    # カメラごとの画像ファイルのリストを取得
    image_list = helpers.get_file_list("images/" + st.session_state.dir_area + "/" + camera_num + "/")
    if not image_list:
        main_view.error("解析対象の画像がありません。別の線区・カメラを選択してください。")
        st.stop()
    st.session_state.camera_num_mem = camera_num

    # idx選択ウィジェット
    idx = st.sidebar.number_input(
        f"画像インデックスを選択(1～{len(image_list)}で指定)",
        1, len(image_list), 1
    )
    cam_img = vis.ohc_image_load("images/" + st.session_state.dir_area + "/" + camera_num + "/" + image_list[idx - 1], main_view)

    # ボタンによって解析フラグを切替える
    if st.sidebar.button("この画像から解析を開始する"):
        trolley_analysis_start()
        st.session_state.initial_idx = idx - 1
    if st.sidebar.button("解析を中断する"):
        trolley_analysis_init()
        st.session_state.initial_idx = None
        st.session_state.center_set = False
        st.session_state.auto_edge_set = False
    if not st.session_state.trolley_analysis:
        st.sidebar.success("💡画像を選んで開始ボタンを押す")
    else:
        st.sidebar.error("⚠️別の画像を選ぶときは中断ボタン")
    return image_list, idx - 1, cam_img

# 解析モードのオン/オフ
def trolley_analysis_init():
    st.session_state.trolley_analysis = False
def trolley_analysis_start():
    st.session_state.trolley_analysis = True

# メインページにカラム表示する
def column_view(main_view, camera_view, file_idx, cam_img, result_img_path, fig):
    col1, col2 = camera_view.columns(2)
    with col1:
        st.header("📸カメラ画像")
        st.write(f"カメラ:{helpers.camera_num_to_name(st.session_state.camera_num_mem, config)} {file_idx + 1}番目の画像です")
        st.image(cam_img)
    with col2:
        st.header("🖥️解析結果")
        st.write(f"{st.session_state.analysis_message}")
        if result_img_path != '' and fig == '':
            result_img = vis.ohc_image_load(result_img_path, main_view)
            st.image(result_img)
        elif fig != '':
            st.pyplot(fig)
    return
    
    
if __name__ == "__main__":
    config = appProperties('config.yml')
    ohc_wear_analysis(config)
