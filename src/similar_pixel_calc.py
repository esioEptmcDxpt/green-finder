import datetime
import streamlit as st
import shelve
import copy
from .config import appProperties
from .similar_pixel import pixel

def track_pixel(rail_fpath, camera_num, base_images, idx, xin, test_num, log_view):
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
        
        image_name = image_path.split('/')[-1]
        
        # pixelクラスが無い場合、インスタンスを生成
        # pixel_instance_1 = pixel(1, y_init_l, y_init_u)
        # pixel_instance_2 = pixel(2, y_init_l, y_init_u)
        # pixel_instance_3 = pixel(3, y_init_l, y_init_u)
        
        # 画像ファイルごとにshleveファイルを準備する
        with shelve.open(rail_fpath, writeback=True) as rail:
            trolley_dict = copy.deepcopy(rail[camera_num][image_path])
            for trolley_id in config.trolley_ids:
                if trolley_id not in trolley_dict.keys():
                    trolley_dict = {trolley_id: {}}
        
        # 結果保存要素を初期化する
        pixel_instance_1.reload_image_init()
        pixel_instance_2.reload_image_init()
        pixel_instance_3.reload_image_init()
        
        try:
            log_view.write(f'{file_idx}枚目の画像を処理中です。画像名は{image_name}')
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
            
        except Exception as e:
            # 途中で妙な値を拾った場合
            log_view.error(f"{file_idx}枚目の画像で処理が途中で終了しました。結果を確認して、やりなおしてください。")
            st.stop()
            
        finally:
            # 結果を辞書に書き込む
            # config.result_keysで指定した要素だけ辞書に書き込む
            trolley_dict = {
                trolley_id: {key: value for key, value in vars(instance).items() if key in config.result_keys}
                for trolley_id, instance in zip(config.trolley_ids, [
                    pixel_instance_1,
                    pixel_instance_2,
                    pixel_instance_3
                ])
            }

            # 結果をshelveに書き込む
            # print("shelve saving")
            with shelve.open(rail_fpath, writeback=True) as rail:
                rail_dict = copy.deepcopy(rail[camera_num][image_path])
                rail_dict = trolley_dict
                rail[camera_num][image_path] = rail_dict
           
        dt02 = datetime.datetime.now()
        prc_time = dt02 - dt01
        log_view.write(str(datetime.datetime.now()) + f' Process end :{prc_time}')
        
        # 指定画像数に達したら解析を終了する
        if file_idx >= test_num + idx -1:
            break
    
    # 解析終了後の処理
    log_view.success("ピクセルトレース完了＜トロリ線の検出処理が完了しました＞")