import os
import shelve
import copy
import matplotlib
import numpy as np
import pandas as pd
from bokeh.plotting import figure, gridplot, show
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, FuncTickFormatter
from bokeh.models import NumeralTickFormatter
from bokeh.palettes import d3
import streamlit as st
from PIL import Image
import src.helpers as helpers


# @st.cache(hash_funcs={matplotlib.figure.Figure: lambda _: None})
def plot_fig(image_path, vert_pos, hori_pos):
    """ メモリ付き画像を生成する
    Args:
        image_path(str): 元の画像パス
    Return:
        fig: pyplot形式の画像データ
    """
    im_base = Image.open(image_path)
    dpi = 200
    margin = 0.05
    xpixels, ypixels = 1000, 2200
    mag = 2
    LINECOLOR = 'red'
    LINEWIDTH = 0.5

    figsize = mag * (1 + margin) * ypixels / dpi, mag * (1 + margin) * xpixels / dpi

    fig = matplotlib.pyplot.figure(figsize=figsize, dpi=dpi)
    ax = fig.add_axes([margin, margin, 1 - 2 * margin, 1 - 2 * margin])
    ax.set_yticks(range(0, 2200, 50))
    ax.minorticks_on()
    ax.imshow(im_base, interpolation="none")

    # 指定位置に線を描画する
    # 数値が0で無ければ描画する
    if hori_pos:
        ax.axvline(x=hori_pos, color='red', linewidth=LINEWIDTH)
    if vert_pos[0]:
        ax.axhline(y=vert_pos[0], color='red', linewidth=LINEWIDTH)
    if vert_pos[1]:
        ax.axhline(y=vert_pos[1], color='red', linewidth=LINEWIDTH)

    return fig


@st.cache
def ohc_image_load(image_path):
    """ 解析対象の画像を表示する
    Args:
        image_path(str): 元画像のパス
    Return: PIL形式の画像データ
    """
    return Image.open(image_path) if os.path.isfile(image_path) else []


# @st.cache
def out_image_load(rail_fpath, camera_num, image_path, img, config):
    """
    Args:
        rail_fpath(str): shelveファイルのパス
        camera_num(str): 選択されたカメラ番号(例)HD11
        image_path(str): 画像ファイルパス
        img (PIL Image): PIL画像オブジェクト(例)cam_img
        config(instance): 設定ファイル
    Return:
        out_img(PIL Image): 結果を重ね合わせた画像データ
    """
    # オリジナル画像データを取得する
    # img = Image.open(image_path)

    # 画像をnumpy配列に変換
    img_array = np.array(img)

    # ランダムに1000画素を選択し、その平均輝度を背景の輝度とする
    random_pixels = img_array[
        np.random.randint(0, img_array.shape[0], 1000),
        np.random.randint(0, img_array.shape[1], 1000)
    ]
    background_brightness = random_pixels.mean()

    # shelveファイルを開いて辞書にセットする
    with shelve.open(rail_fpath) as rail:
        trolley_dict = copy.deepcopy(rail[camera_num][image_path])

    # 解析結果をチェックする
    trolley_count = len(trolley_dict)
    if not trolley_count:
        # 解析結果が無ければ関数を抜ける
        return []

    # データを描画 
    x_values = list(range(config.max_len))
    for trolley_id in config.trolley_ids:
        # trolley_idの数だけ繰り返す
        if trolley_id in trolley_dict.keys():
            # trolley_idが存在する場合だけ実行
            upper_edge = trolley_dict[trolley_id]["estimated_upper_edge"]
            lower_edge = trolley_dict[trolley_id]["estimated_lower_edge"]
            for x, y1, y2 in zip(x_values, upper_edge, lower_edge):
                # estimated_upper_edgeとestimated_lower_edgeが0でない場合のみ色を変更
                if y1 != 0:
                    color_upper = [0, 255, 0] if background_brightness < 128 else [255, 0, 0]  # 緑または赤
                    img_array[y1, x] = color_upper
                if y2 != 0:
                    color_lower = [0, 255, 0] if background_brightness < 128 else [255, 0, 0]  # 緑または赤
                    img_array[y2, x] = color_lower

    return Image.fromarray(img_array)


def rail_info_view(dir_area, config, main_view):
    """ 線区情報を日本語で表示する
    Args:
        dir_area(str): 線区フォルダのパス
        config(dict): 設定ファイル
        main_view: Streamlitのコンテナ
    """
    rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
    with main_view.container():
        st.write(f"現在の線区：{rail_name} {st_name}({updown_name})")
        st.write(f"　　測定日：{measurement_date} ＜{measurement_time}＞")
        st.success("##### 👈別の線区を表示する場合は、再度「線区フォルダを決定」してください")
    return


def plot_fig_bokeh(config, rail_fpath, graph_height, graph_width, graph_thinout, ix_set_flag, ix_view_range):
    """
    Args:
        config: 設定ファイル
        rail_fpath(str): shelveファイルのパス
        graph_height(int): グラフ1枚当たりの高さ
        graph_width(int): グラフ1枚当たりの幅
        graph_thinout(int): データフレームを間引く間隔
    """
    y_max = 2048

    # CSVファイルの保存パスを指定
    csv_fpath = rail_fpath.replace(".shelve", ".csv")
    # st.write(f"csv_fpath: {csv_fpath}")

    # CSVファイルからデータフレームを作成する
    # df_csv = pd.read_csv(csv_fpath, encoding='cp932')
    df_csv = pd.read_csv(csv_fpath, engine='c', dtype=config.csv_dtype)    # 列の型を指定

    # データを間引く
    # そのままだとメモリ不足等で表示不可…
    df_csv = df_csv[::graph_thinout]
    
    # ユーザ入力に基づいて表示範囲を限定する
    if ix_set_flag:
        df_csv = df_csv.query(f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}').copy()

    # CSVから作成したデータフレームをbokeh形式で読み込む
    source = ColumnDataSource(data=df_csv)

    # グラフの色情報を設定する
    # グラフの数に合わせて12色だけ取得する
    # edge(upper,lower),width,width_std,brightness=4 -> 3*5=15
    colors = d3["Category20"][20]

    # ツールチップを設定
    TOOLTIPS_EDGE=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('ix', '@ix'),
        ('upper_edge', '@estimated_upper_edge'),
        ('lower_edge', '@estimated_lower_edge'),
    ]
    TOOLTIPS_WIDTH=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('ix', '@ix'),
        ('estimated_width', '@estimated_width'),
    ]
    TOOLTIPS_WIDTH_STD=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('ix', '@ix'),
        ('estimated_width_std', '@estimated_width_std'),
    ]
    TOOLTIPS_BRIGHTNESS=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('ix', '@ix'),
        ('brightness_center', '@brightness_center'),
    ]

    # グラフを作成
    p_edge = figure(
        title="Upper and Lower Edge",
        sizing_mode="stretch_width",
        y_range=(y_max, 0),
        tooltips=TOOLTIPS_EDGE,
        height=int(graph_height),
        width=int(graph_width)
    )
    p_width = figure(
        title="Width",
        sizing_mode="stretch_width",
        tooltips=TOOLTIPS_WIDTH,
        x_range=p_edge.x_range,
        height=int(graph_height),
        width=int(graph_width)
    )
    p_width_std = figure(
        title="Width Standard Deviation",
        sizing_mode="stretch_width",
        tooltips=TOOLTIPS_WIDTH_STD,
        x_range=p_edge.x_range,
        height=int(graph_height),
        width=int(graph_width)
    )
    p_center = figure(
        title="Brightness Center",
        sizing_mode="stretch_width",
        tooltips=TOOLTIPS_BRIGHTNESS,
        x_range=p_edge.x_range,
        height=int(graph_height),
        width=int(graph_width)
    )
    plots = [[p_edge], [p_width], [p_width_std], [p_center]]

    # グラフを表示する領域を作成
    grid = gridplot(
        plots,
        toolbar_location="above"
    )

    # グラフにデータを追加
    # 列名と変数名を紐づける
    x_values = "ix"
    upper_edge = "estimated_upper_edge"
    lower_edge = "estimated_lower_edge"
    estimated_width = "estimated_width"
    estimated_width_std = "estimated_width_std"
    brightness_center = "brightness_center"

    # 各グラフに描画する要素を指定
    edges = [
        (p_edge, upper_edge, "upper_edge"),
        (p_edge, lower_edge, "lower_edge")
    ]
    widths = [
        (p_width, estimated_width, "estimated_width")
    ]
    width_stds = [
        (p_width_std, estimated_width_std, "estimated_width_std")
    ]
    centers = [
        (p_center, brightness_center, "brightness_center")
    ]
    
    # trolley_idのユニークな値を取得
    unique_trolleys = df_csv['trolley_id'].unique()
    
    for trolley_id in unique_trolleys:
        trolley_df = df_csv[df_csv['trolley_id'] == trolley_id]
        source = ColumnDataSource(data=trolley_df)

        for i, (p, line_data, label_name) in enumerate(edges + widths + width_stds + centers):
            p.line(
                x_values,
                line_data,
                legend_label=f"{label_name}_{trolley_id}",
                line_color=colors[i % len(colors)],  # もし色の数が足りない場合は循環するように
                source=source
            )

    # 軸・凡例の条件を指定する
    # 軸表示用のフォーマット関数
    formatter = FuncTickFormatter(code="""
        return tick.toLocaleString() + "px";
    """)
    for p in [sublist[0] for sublist in plots]:
        # p.legend.location = "top_left"    # グラフ内に表示
        p.add_layout(p.legend[0], "right")    # グラフの外に表示
        p.legend.click_policy = "hide"    # 凡例でグラフを非表示
        # p.legend.click_policy = "mute"    # 凡例でグラフをミュート
        p.xaxis.axis_label = "location"
        # p.xaxis.formatter = NumeralTickFormatter(format="0,0")
        p.xaxis.formatter = formatter
        p.yaxis.formatter = formatter

    return grid


def plot_fig_plt(config, rail_fpath, camera_num, graph_height, graph_width, graph_thinout, ix_set_flag, ix_view_range):
    """
    Args:
        config: 設定ファイル
        rail_fpath(str): shelveファイルのパス
        graph_height(int): グラフ1枚当たりの高さ
        graph_width(int): グラフ1枚当たりの幅
        graph_thinout(int): データフレームを間引く間隔
        ix_set_flag(boolen): x軸方向の表示範囲を指定するフラグ
        ix_view_range(tuple): x軸方向の表示範囲
    """
    # 初期設定
    csv_fpath = rail_fpath.replace(".shelve", ".csv")    # CSVファイルの保存パスを指定
    title_text = f'Analysis data on Camera:{camera_num}'    # タイトル共通ヘッダ

    # CSVを読み込む
    df = pd.read_csv(csv_fpath)
    # 表示するixの範囲を指定しない場合は、ixの最小・最大を適用
    if not ix_set_flag:
        ix_view_range = (int(df['ix'].min()), int(df['ix'].max()))

    # グラフ描画エリアを設定
    fig, (ax1, ax2, ax3, ax4) = matplotlib.pyplot.subplots(4, 1, figsize=(graph_width, graph_height))
    matplotlib.pyplot.subplots_adjust(hspace=graph_height / 25)    # グラフ間の間隔を調整

    fig.suptitle(title_text)
    ax1.set_ylabel('estimated_edge')
    ax2.set_ylabel('width')
    ax3.set_ylabel('width_std')
    ax4.set_xlabel('ix')
    ax4.set_ylabel('brightness_std')

    # グラフの要素を追加, trolley_idごとに追加
    for trolleyid in df['trolley_id'].unique():
        df_temp = df.query(f'trolley_id == "{trolleyid}"').copy()
        x = df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}'
        )['ix']
        ax1.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}'
        )['estimated_upper_edge'], label=trolleyid)
        ax1.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}'
        )['estimated_lower_edge'], label=trolleyid)
        ax2.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}'
        )['estimated_width'], label=trolleyid)
        ax3.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}'
        )['estimated_width_std'], label=trolleyid)
        ax4.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}'
        )['brightness_std'], label=trolleyid)

    # 凡例を有効化する
    ax1.legend()
    ax2.legend()
    ax3.legend()
    ax4.legend()

    return fig, (ax1, ax2, ax3, ax4)
