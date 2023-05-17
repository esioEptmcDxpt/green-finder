import matplotlib
import numpy as np
from bokeh.plotting import figure, show
import streamlit as st
from PIL import Image
import src.helpers as helpers


# @st.cache(hash_funcs={matplotlib.figure.Figure: lambda _: None})
def plot_fig(base_images, idx):
    im_base = Image.open(base_images[idx])
    dpi = 200
    margin = 0.05
    xpixels, ypixels = 1000, 2200
    mag = 2

    figsize = mag * (1 + margin) * ypixels / dpi, mag * (1 + margin) * xpixels / dpi

    fig = matplotlib.pyplot.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([margin, margin, 1 - 2 * margin, 1 - 2 * margin])
    ax.set_yticks(range(0, 2200, 50))
    ax.minorticks_on()
    ax.imshow(im_base, interpolation="none")
    return fig

    
@st.cache
def plot_fig_bokeh(base_images, idx):
    ### 画像の左端での輝度グラフ

    # PILイメージとして読み込む
    pil_im = Image.open(base_images[idx])
    # RGBからRGBAに変換
    pil_im_rgba = pil_im.convert('RGBA')
    # PILイメージからndarrayに変換
    im_rgba = np.asarray(pil_im_rgba)

    # (高さ, 幅, [R,G,B,A]）の配列から（高さ, 幅, RGBA）の配列に変換
    im_uint32 = im_rgba.view(np.uint32).reshape(im_rgba.shape[:2])

    # 画像の高さと幅を取得
    h, w = im_rgba.shape[:2]

    # 画像情報を上下反転
    im = np.flip(im_uint32, 0)

    size = 300
    # 画像サイズと同じキャンバスを作成
    p = figure(
            width = size,
            height = int(size*h/w),
            x_range = (0, w),
            y_range = (h, 0),
            toolbar_location = 'above',
            y_minor_ticks = 25,
        )
    # 画像をサイズ通りに描画
    p.image_rgba(image=[im], x=0, y=h, dw=w, dh=h)
    
    return p
    
@st.cache
def ohc_image_load(base_images, idx):
    try:
        im_base = Image.open(base_images[idx])
    except Exception as e:
        im_base = []
    return im_base

@st.cache
def out_image_load(rail, camera_num, base_images, idx):
    image_path = base_images[idx]
    # オリジナル画像
    im = Image.open(rail[camera_num][image_path])
    
    # 解析結果の情報
    for trolley_id in config.trolley_ids:
        im_result = im + rail[camera_num][image_path][trolley_id]['']
    
    # try:
    #     out_img = rail[camera_num][image_path]['out_image']
    # except Exception as e:
    #     out_img = []
    return out_img

def rail_info_view(dir_area, config, main_view):
    rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
    with main_view.container():
        st.write(f"現在の線区：{rail_name} {st_name}({updown_name})")
        st.write(f"　　測定日：{measurement_date} ＜{measurement_time}＞")
        st.success("##### 👈別の線区を表示する場合は、再度「線区フォルダを決定」してください") 
    return

