import streamlit as st
from .kalman import kalman


def track_kalman(rail, camera_num, base_images, idx, trolley_id, x_init, y_init_u, y_init_l):
    """カルマンフィルタ計算用のラッパー
    Args:
        rail (object): shelveファイル
        camera_num (int): カメラのNo
        base_images (str): 画像ファイル
        idx (int): X座標の現在値
        trolley_id (str): 選択しているトロリID
        x_init (int): X座標の初期値
        y_init_u (int): 上部Y座標の初期指定値
        y_init_l (int): 下部Y座標の初期指定値
    """
    for image_path in base_images[idx:]:
        try:
            # shelveのrailからtrolley_idを取得
            trolley_id = rail[camera_num][image_path].get(trolley_id)    # rail.getが無い？ trolley_idがNoneになっている

            # Kalmanクラスが無い場合、インスタンスを生成
            kalman_instance = kalman(trolley_id, y_init_l, y_init_u)
            kalman_instance.infer_trolley_edge(image_path, x_init)

            # x = 0
            # y_u = kalman_instance.estimated_upper_edge[-1]
            # y_l = kalman_instance.estimated_upper_edge[-1]
            # st.text(trolley)

        except Exception as e:
            # 途中で妙な値を拾った場合
            st.error("処理が途中で終了しました。")

        finally:
            # 最後まで完了した値をインスタンス変数から辞書に変換し、shelveに出力
            rail[camera_num][image_path] = vars(kalman_instance)
            st.stop()

    rail.close()
