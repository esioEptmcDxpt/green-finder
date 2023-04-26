import random
import numpy as np
import cv2
from PIL import Image
from .config import appProperties
from .trolley import trolley


class pixel(trolley):
    """トロリ情報を継承し、類似ピクセルの計算用の初期化とアップデートを実施
    Args:
        trolley (class): トロリ線のパラメータ
        appProperties (class) : 計算条件の設定用ファイル
    Parameters:

    Methods:
        __init__: 各種パラメータの初期化
    """
    pixel_config = appProperties('config.yml')
    
    
    # def __init__(self, file):
    #     super().__init__(trolley_id, y_init_u, y_init_l)
        
    
    def load_picture(self, file):
        self.picture['file'] = file
        self.picture['im_org'] = np.array(Image.open(file))
        self.brightness = []    # 摺面の輝度
        self.picture['im_trolley'] = np.zeros_like(self.picture['im_org']).astype(int)
        
        # 画面全体の平均輝度（背景輝度と同等とみなす）を算出
        img = self.picture['im_org']
        im_r = img[:, :, 0].flatten()
        im_random = []
        for i in range(1000): #全画素の平均は処理時間かかるのでランダム1000画素の輝度平均
            x = random.randint(0, 2047999)
            im_random.append(im_r[x])
        self.avg_brightness = round(np.mean(im_random))
        
        # シグモイド関数を使って理想形のエッジ配列を作成
        sigmoid_max = max(im_r).astype(int)              # 輝度Max値　＝　画像全体の輝度Max値
        sigmoid_min = int(self.avg_brightness)     # 輝度Min値  ＝　背景輝度(画像全体の平均輝度）
        x = np.arange(-7, 8, 1)
        self.sigmoid_edge_u = (sigmoid_max - sigmoid_min) / (1 + np.exp(-x/0.5) ) + sigmoid_min
        self.sigmoid_edge_l = (-sigmoid_max + sigmoid_min) / (1 + np.exp(-x/0.5) ) + sigmoid_max
        return
    
    def reset_trolley(self):
        """
        トロリ線消失リセット
        """
        self.edge_std_list_u = []
        self.edge_std_list_l = []
        self.edge_std_u = None
        self.edge_std_l = None
        self.err_skip = [0, 0, 0, 0]
        self.err_diff = [0, 0, 0, 0]
        self.err_edge = [0, 0, 0, 0]
        self.err_width = [0, 0, 0, 0]
        self.err_nan = [0, 0]
        self.w_ear = 0
        self.as_aj = 0
        self.isInFrame = False
        return
    
    
    def set_init_val(self, rail, ix, xin, search_list, auto_edge):
        img = self.picture['im_org']
        if auto_edge:
            self.upper_boundary1[ix] = search_list[0][0]
            self.lower_boundary1[ix] = search_list[0][1]
            self.last_state = search_list[0][0:2]
            self.slope_dir = search_list[0][2]
        elif xin != None:
            # 画像1の中心点設定と輝度の立上り／立下りサーチ範囲の設定
            width = 34
            start = int(xin)  - width // 2
            end = int(xin)  + width // 2
            # 画像1のトロリ線境界位置の初期値
            im_slice = np.copy(img[:, 0, 0])
            # 傾きから初期値算出
            slope = np.gradient(im_slice[start:end].astype(np.int16))
            slope_max = start + np.argmax(slope)
            slope_min = start + np.argmin(slope)
            upper = min([slope_max, slope_min])
            lower = max([slope_max, slope_min])
            self.upper_boundary1[ix] = upper
            self.lower_boundary1[ix] = lower
            self.last_state = [upper, lower]
            # 初期値から輝度の向きを確認
            self.slope_dir = 1 if slope_max < slope_min else -1
        else:
            print('トロリ線の初期値が正しく設定できませんでした。')
            print('やり直しえてください')
            # st.warning('トロリ線の初期値が正しく設定できませんでした。やり直してください。')
        
        return
    
    
    def search_trolley_init(self, ix):
        # 横1ピクセル、縦全ピクセル切り出し
        img = self.picture['im_org']
        im_slice_org = np.copy(img[:, ix, 0])
        im_slice = np.copy(img[:, ix, 0])
        
        # サーチ範囲
        st = 7
        ed = 2040
        
        # 切り出した縦ピクセルのノイズを除去
        im_slice[st:ed] = [round(np.mean(im_slice_org[i-1:i+2])) for i in range(st, ed)]
        
        # 理想的なエッジ配列に近い場所をサーチ
        slope_val_u, slope_val_l, slope_idx_u, slope_idx_l  = [], [], [], []
        for i in range(st, ed):
            diff1 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.sigmoid_edge_u.astype(int)))
            slope_val_u.append(diff1)
            slope_idx_u.append(i)
            diff2 = np.sum(abs(im_slice[i-7:i+8].astype(int) - self.sigmoid_edge_l.astype(int)))
            slope_val_l.append(diff2)
            slope_idx_l.append(i)
        slope_val_u = np.array(slope_val_u)
        slope_val_l = np.array(slope_val_l)
        slope_sort_u = np.argsort(slope_val_u)
        slope_sort_l = np.argsort(slope_val_l)

        list_idx,list_val = [],[]
        for idx_u, val_u in enumerate(slope_val_u):
            for idx_l, val_l in enumerate(slope_val_l):
                if (
                    idx_u < idx_l and                         # ピクセル位置は upper < lowerであること
                    0 <= (idx_u - idx_u) <= 35 and            # 摺面幅が明らかにあり得ない場合を除外
                    (val_u + val_l) <= 400                    # 誤差が大きい場合は除外
                ):
                    list_idx.append([idx_u+st, idx_l+st, 1])  # 摺面が立ち上があり→立下りの場合
                    list_val.append(val_u + val_l)
                elif (
                    idx_l < idx_u and                          # ピクセル位置は lower < upperであること
                    0 <= (idx_u - idx_l) <= 35 and             # 摺面幅が明らかにあり得ない場合を除外
                    (val_u + val_l) <= 400                     # 誤差が大きい場合は除外
                ):
                    list_idx.append([idx_l+st, idx_u+st, -1])  # 摺面が立ち下があり→立上りの場合
                    list_val.append(val_u + val_l)

        search_list = []
        for i in np.argsort(list_val):
            search_list.append(list_idx[i])

        # （補正）検出した点を傾きの中心にする
        for i, edge in enumerate(search_list):
            if edge[2] == 1:
                center_u = (max(im_slice[edge[0]-2:edge[0]+8]).astype(np.int16) + min(im_slice[edge[0]-7:edge[0]+3]).astype(np.int16)) / 2
                idx_uu = np.argmin(im_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
                idx_ul = np.argmax(im_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
                center_l = (max(im_slice[edge[1]-7:edge[1]+3]).astype(np.int16) + min(im_slice[edge[1]-2:edge[1]+8]).astype(np.int16)) / 2
                idx_lu = np.argmax(im_slice[edge[1]-7:edge[1]+3]) + (edge[1]-7)
                idx_ll = np.argmin(im_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
            elif edge[2] == -1:
                center_u = (max(im_slice[edge[0]-7:edge[0]+3]).astype(np.int16) + min(im_slice[edge[0]-2:edge[0]+8]).astype(np.int16)) / 2
                idx_uu = np.argmax(im_slice[edge[0]-7:edge[0]+3]) + (edge[0]-7)
                idx_ul = np.argmin(im_slice[edge[0]-2:edge[0]+8]) + (edge[0]-2)
                center_l = (max(im_slice[edge[1]-2:edge[1]+8]).astype(np.int16) + min(im_slice[edge[1]-7:edge[1]+3]).astype(np.int16)) / 2
                idx_lu = np.argmin(im_slice[edge[1]-7:edge[1]+2]) + (edge[1]-7)
                idx_ll = np.argmax(im_slice[edge[1]-2:edge[1]+8]) + (edge[1]-2)
            diff1 = abs(im_slice[idx_uu:idx_ul+1] - center_u)
            idx_u_new = np.argmin(diff1) + idx_uu
            diff2 = abs(im_slice[idx_lu:idx_ll+1] - center_l) 
            idx_l_new = np.argmin(diff2) + idx_lu
            search_list[i][0:2] = [idx_u_new, idx_l_new]
        return search_list
    
    
    def mean_brightness(self):
        img = self.picture['im_org']
        im_r = img[:, :, 0].flatten()
        im_random = []
        for i in range(1000): #全画素の平均は処理時間かかるのでランダム1000画素の平均
            x = random.randint(0, 2047999)
            im_random.append(im_r[x])
        self.avg_brightness = round(np.mean(im_random))
        return
    
    
if __name__ == '__main__':
    print('set similar_pixel class')
    