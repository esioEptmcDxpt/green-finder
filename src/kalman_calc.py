import streamlit as st
import shelve
import json
import copy
import numpy as np
from src.config import appProperties
import src.helpers as helpers
from src.kalman import kalman


def track_kalman(rail_fpath, camera_num, base_images, df_csv, idx, test_num, trolley_id, x_init, y_init_u, y_init_l, status_view, progress_bar):
    """カルマンフィルタ計算用のラッパー
    Args:
        rail (object): shelveファイル
        camera_num (int): カメラのNo
        base_images (str): 画像ファイル
        idx (int): 処理したい対象の画像ファイルの開始位置
        test_num (int): 処理したい対象の画像ファイルの枚数
        trolley_id (str): 選択しているトロリID
        x_init (int): X座標の初期値
        y_init_u (int): 上部Y座標の初期指定値（最初期画像における手動入力）
        y_init_l (int): 下部Y座標の初期指定値（最初期画像における手動入力）
        y_l (int): 後続画像用の上部Y座標の初期指定値（前画像の最終推定値流用）
        y_u (int): 後続画像用の下部Y座標の初期指定値（前画像の最終推定値流用）
    """
    config = appProperties('config.yml')
    y_l = y_init_l
    y_u = y_init_u

    window = 100    # 標準偏差計算におけるウィンドウサイズ、いずれユーザ入力にする
    min_periods = helpers.window2min_periods(window)    # 標準偏差計算における最小計算範囲

    # 前回までの結果ファイルを読み込む
    df_csv = helpers.result_csv_load(config, rail_fpath).copy()

    count = 0
    for image_path in base_images[idx:(idx + test_num)]:
        # 解析条件を記録
        image_name = image_path.split('/')[-1]
        dir_area, camera_num = image_path.split("/")[1:3]    # image_pathから線区情報を読取る

        # df_csvで、指定された条件に一致する行を特定する用の条件
        condition = (
            (df_csv['measurement_area'] == dir_area) &
            (df_csv['camera_num'] == camera_num) &
            (df_csv['image_name'] == image_name) &
            (df_csv['trolley_id'] == trolley_id)
        )

        # CSV化によりtrolley_dictを使用しなくなったため、コードを修正
        # 元のコードはコメントアウト
        # with shelve.open(rail_fpath, writeback=True) as rail:
        #     trolley_dict = copy.deepcopy(rail[camera_num][image_path])
        #     if trolley_id not in trolley_dict.keys():
        #         trolley_dict = {trolley_id: {}}

        # ループの最初は入力した初期値を使い、それ以降は処理時の最後の値を使用するように変更
        count += 1
        # 進捗＆プログレスバーを更新
        status_view.write(f"解析の進捗：{idx + count}/{len(base_images)}")
        progress_bar.progress((idx + count -1) / len(base_images))
        if count == 1:
            st.text(f"{idx + count}枚目の画像を処理中です。画像名は{image_name}")
            try:
                kalman_instance = kalman(trolley_id, y_l, y_u, x_init)
                kalman_instance.infer_trolley_edge(image_path)
            except Exception as e:
                st.error(e)
                st.error("予期せぬ理由で処理が途中終了しました。管理者に問い合わせてください")
                break
            finally:
                if x_init > 0:
                    kalman_dict = {trolley_id: 
                                    {key: value for key, value in vars(kalman_instance).items() if key in config.result_keys}
                                   }
                    # 途中開始する場合、値を埋めるために処理を追加
                    # if len(trolley_dict[trolley_id]) == 0:
                    df_csv_trimmed = df_csv.loc[condition, :].copy()
                    # if len(df_csv_trimmed) == 0:
                    #     for key in kalman_dict[trolley_id].keys():
                    #         if key in ['estimated_upper_edge', 'estimated_lower_edge']:
                    #             kalman_dict[trolley_id][key] = [np.int16(0) for i in range(x_init)] + kalman_dict[trolley_id][key]
                    #         elif key in ['mask_edgelog_1', 'mask_edgelog_2']:
                    #             kalman_dict[trolley_id][key] = [np.int8(0) for i in range(x_init)] + kalman_dict[trolley_id][key]
                    #         elif key in ['trolley_end_reason']:
                    #             continue
                    #         else:
                    #             kalman_dict[trolley_id][key] = [np.float16(0) for i in range(x_init)] + kalman_dict[trolley_id][key]
                    # else:
                    #     for key in kalman_dict[trolley_id].keys():
                    #         if key in ['trolley_end_reason']:
                    #             continue
                    #         else:
                    #             # kalman_dict[trolley_id][key] = trolley_dict[trolley_id][key][0:x_init] + kalman_dict[trolley_id][key]
                    #             kalman_dict[trolley_id][key] = list(df_csv_trimmed[key][0:x_init]) + kalman_dict[trolley_id][key]
                    for key in kalman_dict[trolley_id].keys():
                        if key in ['trolley_end_reason']:
                            continue
                        else:
                            kalman_dict[trolley_id][key] = list(df_csv_trimmed[key][0:x_init]) + kalman_dict[trolley_id][key]
                else:
                    kalman_dict = {trolley_id: 
                                    {key: value for key, value in vars(kalman_instance).items() if key in config.result_keys}
                                   }

                # Shelveの場合
                # with shelve.open(rail_fpath, writeback=True) as rail:
                #     rail_dict = copy.deepcopy(rail[camera_num][image_path])
                #     rail_dict.update(kalman_dict)
                #     rail[camera_num][image_path] = rail_dict
                # CSVの場合
                # インスタンスをデータフレームとして読み込む
                # CSVと同じ列になるように画像/カメラの条件なども追記する
                
                # -----------------------------------------------
                # 高崎検証のためコメントアウト
                # 車モニ マスターデータが必須
                # -----------------------------------------------
                # df = helpers.result_dict_to_csv(config, kalman_dict, idx, count, dir_area, camera_num, image_name, trolley_id, config.ix_list).copy()
                # 画像ファイルとキロ程を紐づけるためのJSONファイルを辞書として読み込む
                with open(f"{config.tdm_dir}/{dir_area}.json", 'r') as file:
                    kiro_dict = json.load(file)
                df = helpers.experimental_result_dict_to_csv(config, kalman_dict, kiro_dict, idx, count, dir_area, camera_num, image_name, trolley_id, config.ix_list).copy()
                # 一致する行の値を新しいデータフレームの値で更新する
                df_csv = helpers.dfcsv_update(config, df_csv, df).copy()

        else:
            st.text(f"{idx + count}枚目の画像を処理中です。画像名は{image_name}")
            y_l = int(kalman_instance.last_state[0])
            y_u = int(kalman_instance.last_state[1])

            try:
                kalman_instance = kalman(trolley_id, y_l, y_u, 0)
                kalman_instance.infer_trolley_edge(image_path)
            except Exception as e:
                st.error(e)
                st.error("予期せぬ理由で処理が途中終了しました。管理者に問い合わせてください")
                break
            finally:
                kalman_dict = {trolley_id: 
                                {key: value for key, value in vars(kalman_instance).items() if key in config.result_keys}
                              }
                # Shelveの場合
                # with shelve.open(rail_fpath, writeback=True) as rail:
                #     rail_dict = copy.deepcopy(rail[camera_num][image_path])
                #     rail_dict.update(kalman_dict)
                #     rail[camera_num][image_path] = rail_dict
                # CSVの場合
                # インスタンスをデータフレームとして読み込む
                # CSVと同じ列になるように画像/カメラの条件なども追記する

                # -----------------------------------------------
                # 高崎検証のためコメントアウト
                # 車モニ マスターデータが必須
                # -----------------------------------------------
                # df = helpers.result_dict_to_csv(config, kalman_dict, idx, count, dir_area, camera_num, image_name, trolley_id, config.ix_list).copy()
                # 画像ファイルとキロ程を紐づけるためのJSONファイルを辞書として読み込む
                with open(f"{config.tdm_dir}/{dir_area}.json", 'r') as file:
                    kiro_dict = json.load(file)
                df = helpers.experimental_result_dict_to_csv(config, kalman_dict, kiro_dict, idx, count, dir_area, camera_num, image_name, trolley_id, config.ix_list).copy()
                # 一致する行の値を新しいデータフレームの値で更新する
                df_csv = helpers.dfcsv_update(config, df_csv, df).copy()

        # estimated_upper_edgeがNaNでない行だけ選択してestimated_widthの標準偏差を計算
        df_csv = helpers.dfcsv_std_calc(
            df_csv=df_csv,
            col_name='estimated_width',
            col_name_std='estimated_width_std',
            window=window,
            min_periods=min_periods,
            col_name_ref='estimated_upper_edge'
        ).copy()

        # CSVファイルを保存する
        df_csv.to_csv(rail_fpath, index = False)

        if len(kalman_instance.trolley_end_reason) > 0:
            if kalman_instance.error_flg == 1:
                st.error(kalman_instance.trolley_end_reason[0])
                st.markdown(f"{trolley_id}にて再試行の閾値を超えました。\n \
                            最後に推定した際のx座標は {kalman_instance.ix} , \n \
                            y座標上部は {int(kalman_instance.last_state[0])} , \n \
                            y座標下部は {int(kalman_instance.last_state[1])} \n \
                            画像がピンボケしているなど、推定しにくい条件である可能性があります。再実行しても修正されない場合、他のカメラ番号で実行してください。") 
            elif kalman_instance.error_flg == 2:
                st.error(kalman_instance.trolley_end_reason[0])
                st.markdown(f"{trolley_id}にて計算中に推定線幅が閾値を超えました。\n \
                            最後に推定した際のx座標は {kalman_instance.ix} , \n \
                            y座標上部は {int(kalman_instance.last_state[0])} , \n \
                            y座標下部は {int(kalman_instance.last_state[1])} \n \
                            入力幅が大きすぎないか、確認して再実行、もしくは異常が疑われますのでご確認下さい。")
            elif kalman_instance.error_flg == 3:
                st.error(kalman_instance.trolley_end_reason[0])
                st.markdown(f"{trolley_id}にて計算中に画面の上端、もしくは下端に到達しました。\n \
                            最後に推定した際のx座標は {kalman_instance.ix} , \n \
                            y座標上部は {int(kalman_instance.last_state[0])} , \n \
                            y座標下部は {int(kalman_instance.last_state[1])} \n \
                            入力した初期値が上端・下端になっていないか、確認してください。")
            break
