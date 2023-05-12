import streamlit as st
from .kalman import kalman


def track_kalman(rail, camera_num, base_images, idx, trolley_id, x_init, y_init_u, y_init_l):
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

        # ループの最初は入力した初期値を使い、それ以降は処理時の最後の値を使用するように変更
        count += 1
        if count == 1:
            print(y_l, y_u)
            try:
                st.text(image_path)
                kalman_instance = kalman(trolley_id, y_l, y_u)
                kalman_instance.infer_trolley_edge(image_path)
                rail[camera_num][image_path]= vars(kalman_instance)

            except:
                st.error("処理が途中で終了しました。")

            finally:
                rail[camera_num][image_path] = vars(kalman_instance)

        else:
            y_l = int(kalman_instance.last_state[0])
            y_u = int(kalman_instance.last_state[1])
            print(y_l, y_u)

            try:
                st.text(image_path)
                kalman_instance = kalman(trolley_id, y_l, y_u)
                kalman_instance.infer_trolley_edge(image_path)
                rail[camera_num][image_path]= vars(kalman_instance)

            except:
                print('error')

            finally:
                rail[camera_num][image_path] = vars(kalman_instance)

    rail.close()


