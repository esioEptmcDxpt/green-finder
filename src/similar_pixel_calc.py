import datetime
import streamlit as st
import copy
from .config import appProperties
from .similar_pixel import pixel

def track_pixel(rail, camera_num, base_images, idx, xin, test_num):
    """ピクセルエッジ検出計算用のラッパー
    
    Args:
        rail (object): shelveファイル
        camera_num (str): カメラのNo
        base_images (str): 画像ファイルリスト
        idx (int): 画像のインデックス
        xin (int): 摺動面中心の位置指定値
    """
    config = appProperties('config.yml')
    auto_edge = False
    y_init_l, y_init_u = 0, 0    # カルマンフィルタと整合させるためダミーで作成
    # pixelクラスが無い場合、インスタンスを生成
    pixel_instance_1 = pixel(1, y_init_l, y_init_u)
    pixel_instance_2 = pixel(2, y_init_l, y_init_u)
    pixel_instance_3 = pixel(3, y_init_l, y_init_u)
    
    for file_idx, image_path in enumerate(base_images[idx:], idx):
        dt01 = datetime.datetime.now()
        
        # pixelクラスが無い場合、インスタンスを生成
        # pixel_instance_1 = pixel(1, y_init_l, y_init_u)
        # pixel_instance_2 = pixel(2, y_init_l, y_init_u)
        # pixel_instance_3 = pixel(3, y_init_l, y_init_u)
        
        # 結果保存要素を初期化する
        pixel_instance_1.reload_image_init()
        pixel_instance_2.reload_image_init()
        pixel_instance_3.reload_image_init()
        
        try:
            st.write(f'{file_idx}>>> {image_path}')
            # 画像を読み込む
            pixel_instance_1.load_picture(image_path)
            pixel_instance_2.load_picture(image_path)
            pixel_instance_3.load_picture(image_path)
            
            # 初期位置の設定 一番最初の画像でだけ実行する
            if file_idx == idx:
                pixel_instance_1.search_trolley_init(0)    # 左端で検索するため0
                if not pixel_instance_1.search_trolley_init:
                    auto_edge = True
                # st.write(f'search_list:{pixel_instance_1.search_list}')
                pixel_instance_1.set_init_val(idx, xin, auto_edge)
            # st.write(f'last_state:{pixel_instance_1.last_state}')
            
            # x座標(ix)ごとにトロリ線検出
            pixel_instance_1.infer_trolley_edge(image_path, pixel_instance_2, pixel_instance_3)
            
            # 検出結果を画像に重ねて描画した配列を作る
            # im = pixel_instance_1.write_picture(pixel_instance_2, pixel_instance_3)
            
        except Exception as e:
            # 途中で妙な値を拾った場合
            st.error(f"処理が途中で終了しました。インデックスは{file_idx}です。")
            
        finally:
            # 最後まで完了した値をインスタンス変数から辞書に変換し、shelveに出力
            # st.write(f"update results")
            # st.write(f'camera_num:{camera_num}')
            # st.write(f'image_path:{image_path}')
            # st.write(f'estimated_upper_edge:{pixel_instance_1.estimated_upper_edge[:5]}')
            # st.write(f'estimated_lower_edge:{pixel_instance_1.estimated_lower_edge[:5]}')
            rail[camera_num][image_path] = {
                trolley_id: copy.deepcopy(result)
                for trolley_id, result in zip(config.trolley_ids, [
                    vars(pixel_instance_1),
                    vars(pixel_instance_2),
                    vars(pixel_instance_3)
                ])
            }
            # st.write(f'rail[camera_num][image_path] 1枚目のデータ')
            # st.write(f'estimated_upper_edge:{rail[camera_num][base_images[0]]["trolley1"]["estimated_upper_edge"][:5]}')
            # st.write(f'estimated_lower_edge:{rail[camera_num][base_images[0]]["trolley1"]["estimated_lower_edge"][:5]}')
            # st.write(f'rail[camera_num][image_path] {file_idx+1}枚目のデータ')
            # st.write(f'estimated_upper_edge:{rail[camera_num][base_images[file_idx]]["trolley1"]["estimated_upper_edge"][:5]}')
            # st.write(f'estimated_lower_edge:{rail[camera_num][base_images[file_idx]]["trolley1"]["estimated_lower_edge"][:5]}')
            
        
        dt02 = datetime.datetime.now()
        prc_time = dt02 - dt01
        st.write(str(datetime.datetime.now()) + f' Process end :{prc_time}')
        
        # 指定画像数に達したら解析を終了する
        if file_idx >= test_num + idx -1:
            break
    
    # 解析終了後の処理
    st.success("ピクセルトレース完了＜トロリ線の検出処理が完了しました＞")
    st.write("rail.close start")
    rail.close()    # 不要？
    st.write("rail.close end")