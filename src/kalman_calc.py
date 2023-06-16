import streamlit as st
import shelve
import copy
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
            st.text(f"{count + 1}枚目の画像を処理中です。画像名は{image_name}")

            try:
                kalman_instance = kalman(trolley_id, y_l, y_u, x_init)
                kalman_instance.infer_trolley_edge(image_path)
            except Exception as e:
                st.error(e)
                st.error("予期せぬ理由で処理が途中終了しました。管理者に問い合わせてください")
                break
            finally:
                if x_init > 0:
                    kalman_dict = vars(kalman_instance)
                    update_params = ['estimated_upper_edge',
                                     'estimated_lower_edge',
                                     'estimated_width',
                                     'estimated_slope',
                                     'estimated_upper_edge_variance',
                                     'estimated_lower_edge_variance',
                                     'estimated_slope_variance',
                                     'blightness_center',
                                     'blightness_mean',
                                     'blightness_std',
                                     'measured_upper_edge',
                                     'measured_lower_edge']
                    for key in update_params:
                        if len(trolley_dict[trolley_id]) == 0:
                            # 初期値が0でない and image_pathのKeyが0の時、新規作成だと判断し、途中までの値は全てNaNで埋める
                            kalman_dict[key] = [float('nan') for i in range(x_init)] + kalman_dict[key]
                        else:
                            # 初期値が0でない and 途中までの値が存在していればその値を挿入
                            kalman_dict[key] = trolley_dict[trolley_id][key][0:x_init] + kalman_dict[key]
                    trolley_dict[trolley_id] = kalman_dict

                else:
                    trolley_dict[trolley_id] = vars(kalman_instance)

                del trolley_dict[trolley_id]['kf_multi']
                del trolley_dict[trolley_id]['trolley_id']
                    
                with shelve.open(rail_fpath, writeback=True) as rail:
                    rail_dict = copy.deepcopy(rail[camera_num][image_path])
                    rail_dict = trolley_dict
                    rail[camera_num][image_path] = rail_dict

        else:
            st.text(f"{count + 1}枚目の画像を処理中です。画像名は{image_name}")
            y_l = int(kalman_instance.last_state[0])
            y_u = int(kalman_instance.last_state[1])
            
            try:
                kalman_instance = kalman(trolley_id, y_l, y_u)
                kalman_instance.infer_trolley_edge(image_path)
            except Exception as e:
                st.error(e)
                st.error("予期せぬ理由で処理が途中終了しました。管理者に問い合わせてください")
                break
            finally:
                trolley_dict[trolley_id] = vars(kalman_instance)
                del trolley_dict[trolley_id]['kf_multi']
                del trolley_dict[trolley_id]['trolley_id']
                with shelve.open(rail_fpath, writeback=True) as rail:
                    rail_dict = copy.deepcopy(rail[camera_num][image_path])
                    rail_dict = trolley_dict
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
