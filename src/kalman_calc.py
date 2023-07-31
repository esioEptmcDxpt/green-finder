import streamlit as st
import shelve
import copy
from src.config import appProperties
from src.kalman import kalman


def track_kalman(rail_fpath, camera_num, base_images, idx, trolley_id, x_init, y_init_u, y_init_l):
    """カルマンフィルタ計算用のラッパー

    Args:
        rail (object): shelveファイル
        camera_num (int): カメラのNo
        base_images (str): 画像ファイル
        idx (int): 処理したい対象の画像ファイルの開始位置
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

    count = 0
    for image_path in base_images[idx:]:
        image_name = image_path.split('/')[-1]

        with shelve.open(rail_fpath, writeback=True) as rail:
            trolley_dict = copy.deepcopy(rail[camera_num][image_path])
            if trolley_id not in trolley_dict.keys():
                trolley_dict = {trolley_id: {}}

        # ループの最初は入力した初期値を使い、それ以降は処理時の最後の値を使用するように変更
        count += 1
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
                    if len(trolley_dict[trolley_id]) == 0:
                        for key in kalman_dict[trolley_id].keys():
                            if key in ['estimated_upper_edge', 'estimated_lower_edge']:
                                kalman_dict[trolley_id][key] = [np.int16(0) for i in range(x_init)] + kalman_dict[trolley_id][key]
                            elif key in ['mask_edgelog_1', 'mask_edgelog_2']:
                                kalman_dict[trolley_id][key] = [np.int8(0) for i in range(x_init)] + kalman_dict[trolley_id][key]
                            elif key in ['trolley_end_reason']:
                                continue
                            else:
                                kalman_dict[trolley_id][key] = [np.float16(0) for i in range(x_init)] + kalman_dict[trolley_id][key]
                    else:
                        for key in kalman_dict[trolley_id].keys():
                            if key in ['trolley_end_reason']:
                                continue
                            else:
                                kalman_dict[trolley_id][key] = trolley_dict[trolley_id][key][0:x_init] + kalman_dict[trolley_id][key]

                else:
                    kalman_dict = {trolley_id:
                                   {key: value for key, value in vars(kalman_instance).items() if key in config.result_keys}
                                   }

                with shelve.open(rail_fpath, writeback=True) as rail:
                    rail_dict = copy.deepcopy(rail[camera_num][image_path])
                    rail_dict.update(kalman_dict)
                    rail[camera_num][image_path] = rail_dict

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
                with shelve.open(rail_fpath, writeback=True) as rail:
                    rail_dict = copy.deepcopy(rail[camera_num][image_path])
                    rail_dict.update(kalman_dict)
                    rail[camera_num][image_path] = rail_dict

        if len(kalman_instance.trolley_end_reason) > 0:
            if kalman_instance.error_flg == 1:
                st.error(kalman_instance.trolley_end_reason[0])
                st.markdown(f"{trolley_id}にて再試行の閾値を超えました。\n \
                            最後に推定した際のx座標は{kalman_instance.ix}, \n \
                            y座標上部は{int(kalman_instance.last_state[0])}, \n \
                            y座標下部は{int(kalman_instance.last_state[1])} \n \
                            画像がピンボケしているなど、推定しにくい条件である可能性があります。再実行しても修正されない場合、他のカメラ番号で実行してください。") 
            elif kalman_instance.error_flg == 2:
                st.error(kalman_instance.trolley_end_reason[0])
                st.markdown(f"{trolley_id}にて計算中に推定線幅が閾値を超えました。\n \
                            最後に推定した際のx座標は{kalman_instance.ix}, \n \
                            y座標上部は{int(kalman_instance.last_state[0])}, \n \
                            y座標下部は{int(kalman_instance.last_state[1])} \n \
                            入力幅が大きすぎないか、確認して再実行、もしくは異常が疑われますのでご確認下さい。")
            elif kalman_instance.error_flg == 3:
                st.error(kalman_instance.trolley_end_reason[0])
                st.markdown(f"{trolley_id}にて計算中に画面の上端、もしくは下端に到達しました。\n \
                            最後に推定した際のx座標は{kalman_instance.ix}, \n \
                            y座標上部は{int(kalman_instance.last_state[0])}, \n \
                            y座標下部は{int(kalman_instance.last_state[1])} \n \
                            入力した初期値が上端・下端になっていないか、確認してください。")
            break
