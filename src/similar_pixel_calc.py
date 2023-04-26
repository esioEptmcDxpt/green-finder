import streamlit as st
from .similar_pixel import pixel

def track_pixel(rail, camera_num, base_images, idx, xin):
    """類似ピクセル計算用のラッパー
    
    Args:
        rail (object): shelveファイル
        camera_num (int): カメラのNo
        base_images (str): 画像ファイル
        idx (int): X座標の現在値
        xin (int): 摺動面中心の位置指定値
    """
    for image_path in base_images[idx:]:
        try:
            pixel_instance = pixel(rail, trolley_id)
            pixel_instance.infer_trolley_edge(image_path)
            
        except Exception as e:
            # 途中で妙な値を拾った場合
            st.error("処理が途中で終了しました。")
            
        finally:
            # 最後まで完了した値をインスタンス変数から辞書に変換し、shelveに出力
            rail[camera_num][image_path] = vars(pixel_instance)
            st.stop()
    
    rail.close()    # 不要？