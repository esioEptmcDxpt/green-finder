import shelve
import copy
import matplotlib
import numpy as np
from bokeh.plotting import figure, gridplot
from bokeh.models import ColumnDataSource, HoverTool
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


# @st.cache()
def plot_fig_bokeh(config, base_images, rail_fpath, camera_num, img_num, graph_height):

    with shelve.open(rail_fpath) as rail:
        trolley_dict = copy.deepcopy(rail[camera_num])

    # グラフ用のデータソースを作成
    # source_upper = ColumnDataSource(data=dict(x=[], y=[]))
    # source_lower = ColumnDataSource(data=dict(x=[], y=[]))
    # source_width = ColumnDataSource(data=dict(x=[], y=[]))
    # source_center = ColumnDataSource(data=dict(x=[], y=[]))

    # グラフを作成
    p_edge = figure(title="Upper and Lower Edge", sizing_mode="stretch_width", height=int(graph_height))
    p_width = figure(title="Width", sizing_mode="stretch_width", x_range=p_edge.x_range, height=int(graph_height))
    p_center = figure(title="Brightness Center", sizing_mode="stretch_width", x_range=p_edge.x_range, height=int(graph_height))

    # グラフを表示する領域を作成
    grid = gridplot([[p_edge], [p_width], [p_center]], toolbar_location="above")

    # データを追加していくループ
    for idx in range(img_num[0], img_num[1] + 1):
        image_path = base_images[idx]
        x_values = np.array([n + 1000 * idx for n in trolley_dict[image_path][config.trolley_ids[0]]["ix"]])

        # データを更新
        upper_edge = trolley_dict[image_path][config.trolley_ids[0]].get("estimated_upper_edge", [])
        lower_edge = trolley_dict[image_path][config.trolley_ids[0]].get("estimated_lower_edge", [])
        estimated_width = trolley_dict[image_path][config.trolley_ids[0]].get("estimated_width", [])
        brightness_center = trolley_dict[image_path][config.trolley_ids[0]].get("brightness_center", [])

        if not upper_edge or not lower_edge or not estimated_width or not brightness_center:
            continue

        # 1つ目のグラフ（Upper and Lower Edge）
        p_edge.line(x_values, upper_edge, line_color="blue")
        p_edge.line(x_values, lower_edge, line_color="red")

        # 2つ目のグラフ（Brightness Std）
        p_width.line(x_values, estimated_width, line_color="green")

        # 3つ目のグラフ（Brightness Center）
        p_center.line(x_values, brightness_center, line_color="orange")

    return grid


@st.cache
def ohc_image_load(base_images, idx):
    try:
        im_base = Image.open(base_images[idx])
    except Exception as e:
        im_base = []
    return im_base


@st.cache
def out_image_load(rail_fpath, camera_num, base_images, idx, config):
    with shelve.open(rail_fpath) as rail:
        trolley_dict = copy.deepcopy(rail[camera_num])

    image_path = base_images[idx]
    img = Image.open(image_path)

    # 画像をnumpy配列に変換
    img_array = np.array(img)

    # ランダムに1000画素を選択し、その平均輝度を背景の輝度とする
    random_pixels = img_array[
        np.random.randint(0, img_array.shape[0], 1000),
        np.random.randint(0, img_array.shape[1], 1000)
    ]
    background_brightness = random_pixels.mean()

    # データを描画
    # trolley_idのひとつめのixを使用する
    x_values = trolley_dict[image_path][config.trolley_ids[0]]["ix"]
    for trolley_id in config.trolley_ids:
        upper_edge = trolley_dict[image_path][trolley_id]["estimated_upper_edge"]
        lower_edge = trolley_dict[image_path][trolley_id]["estimated_lower_edge"]
        for x, y1, y2 in zip(x_values, upper_edge, lower_edge):
            # estimated_upper_edgeとestimated_lower_edgeが0でない場合のみ色を変更
            if y1 != 0:
                color_upper = [0, 255, 0] if background_brightness < 128 else [255, 0, 0]  # 緑または赤
                img_array[y1, x] = color_upper
            if y2 != 0:
                color_lower = [0, 255, 0] if background_brightness < 128 else [255, 0, 0]  # 緑または赤
                img_array[y2, x] = color_lower

    # 変更後の画像を返す
    out_img = Image.fromarray(img_array)

    return out_img


def rail_info_view(dir_area, config, main_view):
    rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
    with main_view.container():
        st.write(f"現在の線区：{rail_name} {st_name}({updown_name})")
        st.write(f"　　測定日：{measurement_date} ＜{measurement_time}＞")
        st.success("##### 👈別の線区を表示する場合は、再度「線区フォルダを決定」してください")
    return
