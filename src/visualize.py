import os
import shelve
import copy
import matplotlib
import numpy as np
import pandas as pd
import gc
from bokeh.plotting import figure, gridplot, show, save
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, FuncTickFormatter
from bokeh.models import NumeralTickFormatter
from bokeh.palettes import d3
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import src.helpers as helpers
import io
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots


# @st.cache(hash_funcs={matplotlib.figure.Figure: lambda _: None})
# def plot_fig(image_path, vert_pos, hori_pos):
def plot_fig(im_base, vert_pos, hori_pos):
    """ メモリ付き画像を生成する
    Args:
        image_path(str): 元の画像パス
    Return:
        fig: pyplot形式の画像データ
    """
    # im_base = Image.open(image_path)
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


# @st.cache    # デバッグ用後でコメントアウトを元に戻す
def ohc_image_load(image_path):
    """ 解析対象の画像を表示する
    Args:
        image_path(str): 元画像のパス
    Return: PIL形式の画像データ
    """
    return Image.open(image_path) if os.path.isfile(image_path) else []


# @st.cache
def out_image_load(rail_fpath, dir_area, camera_num, image_name, img, config, outpath):
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

    # カラーパレットを定義
    if background_brightness >= 128:
        # 明るい画像用の8色
        colors = [
            (0, 0, 255),        # 赤
            (0, 255, 0),        # 緑
            (255, 0, 0),        # 青
            (0, 255, 255),      # 黄
            (255, 0, 255),      # マゼンタ
            (255, 255, 0),      # シアン
            (128, 0, 128),      # 紫
            (0, 128, 128)       # ティール
        ]
    else:
        # 暗い画像用の8色
        colors = [
            (0, 255, 0),        # ライムグリーン
            (255, 0, 0),        # 赤
            (255, 0, 255),      # マゼンタ
            (255, 165, 0),      # オレンジ
            (0, 255, 255),      # シアン
            (255, 255, 0),      # 黄
            (255, 192, 203),    # ピンク
            (173, 216, 230)     # ライトブルー
        ]

    # csvファイルを開いてデータフレームにセットする
    # df_csv = helpers.result_csv_load(config, rail_fpath).copy()
    # csvファイルのリストを作成
    list_csv = helpers.list_csvs(outpath)
    # 目的のcsvファイルが存在するか確認
    csv_path = outpath + "/rail_" + image_name.split('.')[0] + ".csv"
    if csv_path in list_csv:
        # csvファイルをデータフレームにセット
        df_csv = pd.read_csv(csv_path)

        # 解析結果をチェックする
        # フィルタリング用の画像名の検索条件を作成する
        condition = (
            (df_csv['measurement_area'] == dir_area) &
            (df_csv['camera_num'] == camera_num) &
            (df_csv['image_name'] == image_name)# &
            # (df_csv['trolley_id'] == trolley_id)
        )
        df_csv_filtered = df_csv.loc[condition, :].copy()
        if not len(df_csv_filtered):
            # 解析結果が無ければ関数を抜ける
            return [], colors

        # データを描画
        # x_values = [int(str(num)[-3:]) for num in df_csv_filtered['ix']]
        # st.write(x_values)
        for idx, trolley_id in enumerate(config.trolley_ids):
            # trolley_idの数だけ繰り返す
            if trolley_id in set(list(df_csv_filtered['trolley_id'])):
                # trolley_idが存在する場合だけ実行
                x_values = [int(str(i)[-3:]) for i in df_csv_filtered[(df_csv_filtered['trolley_id'] == trolley_id)]['ix']]
                upper_edge = [int(i) for i in df_csv_filtered[(df_csv_filtered['trolley_id'] == trolley_id)]['estimated_upper_edge']]
                lower_edge = [int(i) for i in df_csv_filtered[(df_csv_filtered['trolley_id'] == trolley_id)]['estimated_lower_edge']]
                for x, y1, y2 in zip(x_values, upper_edge, lower_edge):
                    # estimated_upper_edgeとestimated_lower_edgeが0でない場合のみ色を変更
                    if y1 != 0:
                        # color_upper = [0, 255, 0] if background_brightness < 128 else [255, 0, 0]  # 緑または赤
                        # img_array[y1, x] = color_upper
                        img_array[y1, x] = colors[idx]
                    if y2 != 0:
                        # color_lower = [0, 255, 0] if background_brightness < 128 else [255, 0, 0]  # 緑または赤
                        # img_array[y2, x] = color_lower
                        img_array[y2, x] = colors[idx]
    else:
        # 目的のcsvファイルが存在しなければ関数を抜ける
        return [], colors

    return Image.fromarray(img_array), colors


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


def ohc_img_concat(base_images, idx, concat_nums, font_size):
    """
    Args:
        base_images(list): imgs/xxx/HDxxディレクトリ内の画像ファイルパス
        idx(int): 1枚目の画像インデックス
        concat_nums(int): 横方向に結合する枚数
        font_size(int): 追記する文字のサイズ
    Return:
        result_img(PIL Image): 結合後の画像オブジェクト
    """
    # 番号を追記
    font = ImageFont.truetype('fonts/DejaVuSans-Bold.ttf', size=font_size)

    for count, image_path in enumerate(base_images[idx:(idx + concat_nums)]):
        if not count:
            result_img = Image.open(image_path)
            draw = ImageDraw.Draw(result_img)
            draw.text((10, 10), str(idx + count + 1), fill='red', font=font)
        else:
            next_img = Image.open(image_path)
            # 画像を結合
            temp_img = Image.new('RGB', (result_img.width + next_img.width, result_img.height))
            temp_img.paste(im=result_img, box=(0, 0))
            temp_img.paste(im=next_img, box=(result_img.width, 0))

            # 番号を追記
            draw = ImageDraw.Draw(temp_img)
            draw.text((result_img.width + 10, 10), str(idx + count + 1), fill='red', font=font)

            # 不要な画像と画像オブジェクトを削除
            del result_img
            del next_img
            # del draw
            gc.collect()

            # 結果を保存
            result_img = temp_img
    return result_img


def out_image_concat(rail_fpath, dir_area, camera_num, base_images, idx, concat_nums, font_size, config, status_view, progress_bar, outpath):
    """
    """
    # 番号を追記
    font = ImageFont.truetype('fonts/DejaVuSans-Bold.ttf', size=font_size)

    for count, image_path in enumerate(base_images[idx:(idx + concat_nums)]):
        image_name = image_path.split('/')[-1]
        if not count:
            # st.write(f"{count}> {image_name}")
            result_img = Image.open(image_path)
            # 結果を追記する
            result_img, colors = out_image_load(rail_fpath, dir_area, camera_num, image_name, result_img, config, outpath)
            if not result_img:
                # 結果画像が無い場合（[]の場合）は空の画像を作成する
                # 結果が無い場合は、素の画像を読み込みなおす
                # result_img = Image.new('RGB', (config.img_width, config.img_height))
                result_img = Image.open(image_path)
            # 画像インデックスを追記する
            draw = ImageDraw.Draw(result_img)
            draw.text((10, 10), str(idx + count + 1), fill='red', font=font)

        else:
            next_img = Image.open(image_path)
            # 結果を追記する
            next_img, colors = out_image_load(rail_fpath, dir_area, camera_num, image_name, next_img, config, outpath)
            if not next_img:
                # 結果画像が無い場合（[]の場合）は空の画像を作成する
                # 結果が無い場合は、素の画像を読み込みなおす
                # next_img = Image.new('RGB', (config.img_width, config.img_height))
                next_img = Image.open(image_path)
            # 画像インデックスを追記する
            draw = ImageDraw.Draw(next_img)
            draw.text((10, 10), str(idx + count + 1), fill='red', font=font)
            # 画像を結合
            temp_img = Image.new('RGB', (result_img.width + next_img.width, result_img.height))
            temp_img.paste(im=result_img, box=(0, 0))
            temp_img.paste(im=next_img, box=(result_img.width, 0))

            # 不要な画像と画像オブジェクトを削除
            # del result_img
            # del next_img
            # del draw
            gc.collect()

            # 結果を保存
            result_img = temp_img.copy()
        # プログレスバーを更新
        status_view.write(f"解析結果画像を表示します({count+1}/{concat_nums})")
        progress_bar.progress((count + 1) / concat_nums)
    return result_img




def plot_fig_bokeh(config, rail_fpath, graph_height, graph_width, graph_thinout, ix_set_flag, ix_view_range, scatter_size):
    """
    Args:
        config: 設定ファイル
        rail_fpath(str): shelveファイルのパス
        graph_height(int): グラフ1枚当たりの高さ
        graph_width(int): グラフ1枚当たりの幅
        graph_thinout(int): データフレームを間引く間隔
        ix_set_flag(bool): 横軸の表示範囲を指定するフラグ
        ix_view_range(tuple): 横軸の表示範囲
        scatter_size(int): 散布図のプロットサイズ
    """
    y_max = 2048

    # CSVファイルの保存パスを指定
    # csv_fpath = rail_fpath.replace(".shelve", ".csv")
    # st.write(f"csv_fpath: {csv_fpath}")

    # CSVファイルからデータフレームを作成する
    df_csv = pd.read_csv(rail_fpath, engine='c', dtype=config.csv_dtype)    # 列の型を指定

    # CSVファイルの読込でメモリが不足する場合は以下のコードを使用する
    # df_csv = pd.DataFrame(columns=config.columns_list)    # 空のデータフレームを作成
    # reader = pd.read_csv(rail_fpath, engine='c', dtype=config.csv_dtype, chunksize=10000)
    # for r in reader:
    #     df_csv = pd.concat([df_csv, r], ignore_index=True)

    # データを間引く
    # そのままだとメモリ不足等で表示不可…
    # df_csv = df_csv[::graph_thinout]    # 単純に間引くと最大値を取り逃す可能性があるため修正
    if graph_thinout != 1:
        labels = (df_csv.index // graph_thinout)
        df_grp = df_csv.groupby(labels).max()    # 間引き間隔での最大値を求める
        df_csv = df_grp.reset_index(drop=True).copy()

    # ユーザ用にimage_indexを調整する
    df_csv['image_idx'] = df_csv['image_idx'] + 1

    # ユーザ入力に基づいて表示範囲を限定する
    if ix_set_flag:
        df_csv = df_csv.query(f'{ix_view_range[0]} <= image_idx <= {ix_view_range[1]}', engine='python').copy()

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
            # p.line(
            p.scatter(
                x_values,
                line_data,
                legend_label=f"{label_name}_{trolley_id}",
                # line_color=colors[i % len(colors)],  # もし色の数が足りない場合は循環するように
                fill_color=colors[i % len(colors)],  # もし色の数が足りない場合は循環するように
                marker="dot",
                size=scatter_size,
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


def split_data(x, y, max_gap):
    split_x, split_y = [], []
    current_x, current_y = [], []
    
    x_values = x.values if hasattr(x, 'values') else np.array(x)
    y_values = y.values if hasattr(y, 'values') else np.array(y)
    
    for i in range(len(x_values)):
        if i > 0 and abs(x_values[i] - x_values[i-1]) > max_gap:
            split_x.append(current_x)
            split_y.append(current_y)
            current_x, current_y = [], []
        
        current_x.append(x_values[i])
        current_y.append(y_values[i])
    
    split_x.append(current_x)
    split_y.append(current_y)
    
    return split_x, split_y


def filter_invalid_floats(value):
    if isinstance(value, (float, np.float64)):
        if np.isnan(value) or np.isinf(value):
            return None
    return value


def experimental_plot_fig_bokeh(config, outpath, graph_height, graph_width, graph_thinout, ix_set_flag, ix_view_range, scatter_size):
    """ 高崎検証用 画像キロ程を利用するため、車モニ マスターデータが必須
    Args:
        config: 設定ファイル
        rail_fpath(str): shelveファイルのパス
        graph_height(int): グラフ1枚当たりの高さ
        graph_width(int): グラフ1枚当たりの幅
        graph_thinout(int): データフレームを間引く間隔
        ix_set_flag(bool): 横軸の表示範囲を指定するフラグ
        ix_view_range(tuple): 横軸の表示範囲
        scatter_size(int): 散布図のプロットサイズ
    """
    y_max = 2048

    # CSVファイルの保存パスを指定
    # csv_fpath = rail_fpath.replace(".shelve", ".csv")
    # st.write(f"csv_fpath: {csv_fpath}")

    # CSVファイルからデータフレームを作成する
    # df_csv = pd.read_csv(rail_fpath, engine='c', dtype=config.csv_dtype)    # 列の型を指定
    df_csv = helpers.rail_csv_concat(outpath)
    df_csv = df_csv.sort_values(by='kiro_tei')

    # CSVファイルの読込でメモリが不足する場合は以下のコードを使用する
    # df_csv = pd.DataFrame(columns=config.columns_list)    # 空のデータフレームを作成
    # reader = pd.read_csv(rail_fpath, engine='c', dtype=config.csv_dtype, chunksize=10000)
    # for r in reader:
    #     df_csv = pd.concat([df_csv, r], ignore_index=True)

    # データを間引く
    # そのままだとメモリ不足等で表示不可…
    # df_csv = df_csv[::graph_thinout]    # 単純に間引くと最大値を取り逃す可能性があるため修正
    if graph_thinout != 1:
        labels = (df_csv.index // graph_thinout)
        df_grp = df_csv.groupby(labels).max().copy()    # 間引き間隔での最大値を求める
        df_csv = df_grp.reset_index(drop=True).copy()

    # ユーザ用にimage_indexを調整する
    df_csv['image_idx'] = df_csv['image_idx'] + 1

    # ユーザ入力に基づいて表示範囲を限定する
    if ix_set_flag:
        df_csv = df_csv.query(f'{ix_view_range[0]} <= image_idx <= {ix_view_range[1]}', engine='python').copy()

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
        ('kiro_tei', '@kiro_tei'),
        ('upper_edge', '@estimated_upper_edge'),
        ('lower_edge', '@estimated_lower_edge'),
    ]
    TOOLTIPS_WIDTH=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('kiro_tei', '@kiro_tei'),
        ('estimated_width', '@estimated_width'),
    ]
    TOOLTIPS_WIDTH_STD=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('kiro_tei', '@kiro_tei'),
        ('estimated_width_std', '@estimated_width_std'),
    ]
    TOOLTIPS_BRIGHTNESS=[
        ('image_index', '@image_idx'),
        ('image_name', '@image_name'),
        ('kiro_tei', '@kiro_tei'),
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
    x_values = "kiro_tei"
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

        for i, (p, line_data, label_name) in enumerate(edges + widths + width_stds + centers):
            x = trolley_df[x_values]
            y = trolley_df[line_data]
            
            split_x, split_y = split_data(x, y, max_gap=0.1)  # max_gap: 連続データの閾値
            
            for j in range(len(split_x)):
                indices = x.index[x.isin(split_x[j])]
                source_data = {
                    'x': [filter_invalid_floats(val) for val in split_x[j]],
                    'y': [filter_invalid_floats(val) for val in split_y[j]],
                    'image_idx': trolley_df.loc[indices, 'image_idx'].tolist(),
                    'image_name': trolley_df.loc[indices, 'image_name'].tolist(),
                    'kiro_tei': [filter_invalid_floats(val) for val in trolley_df.loc[indices, 'kiro_tei'].tolist()],
                    'estimated_upper_edge': [filter_invalid_floats(val) for val in trolley_df.loc[indices, 'estimated_upper_edge'].tolist()],
                    'estimated_lower_edge': [filter_invalid_floats(val) for val in trolley_df.loc[indices, 'estimated_lower_edge'].tolist()],
                    'estimated_width': [filter_invalid_floats(val) for val in trolley_df.loc[indices, 'estimated_width'].tolist()],
                    'estimated_width_std': [filter_invalid_floats(val) for val in trolley_df.loc[indices, 'estimated_width_std'].tolist()],
                    'brightness_center': [filter_invalid_floats(val) for val in trolley_df.loc[indices, 'brightness_center'].tolist()],
                }
                source_data = {k: [v for v in vs if v is not None] for k, vs in source_data.items()}
                source = ColumnDataSource(data=source_data)
                p.line(
                    'x', 'y',
                    legend_label=f"{label_name}_{trolley_id}",
                    line_color=colors[i % len(colors)],
                    line_width=scatter_size/10,
                    source=source
                )

    # 軸・凡例の条件を指定する
    # 軸表示用のフォーマット関数
    formatter_x = FuncTickFormatter(code="""
        return tick.toLocaleString() + "km";
    """)
    formatter_y = FuncTickFormatter(code="""
        return tick.toLocaleString() + "px";
    """)
    for p in [sublist[0] for sublist in plots]:
        # p.legend.location = "top_left"    # グラフ内に表示
        p.add_layout(p.legend[0], "right")    # グラフの外に表示
        p.legend.click_policy = "hide"    # 凡例でグラフを非表示
        # p.legend.click_policy = "mute"    # 凡例でグラフをミュート
        p.xaxis.axis_label = "location"
        # p.xaxis.formatter = NumeralTickFormatter(format="0,0")
        p.xaxis.formatter = formatter_x
        p.yaxis.formatter = formatter_y
    
    save(grid, filename='graph_recent.html')

    return grid


def experimental_plot_fig_plotly(config, outpath, graph_height, graph_width, graph_thinout, ix_set_flag, ix_view_range, scatter_size):
    y_max = 2048

    # CSVファイルからデータフレームを作成する
    df_csv = helpers.rail_csv_concat(outpath)
    df_csv = df_csv.sort_values(by='kiro_tei')

    # データを間引く
    if graph_thinout != 1:
        labels = (df_csv.index // graph_thinout)
        df_grp = df_csv.groupby(labels).max().copy()
        df_csv = df_grp.reset_index(drop=True).copy()

    # ユーザ用にimage_indexを調整する
    df_csv['image_idx'] = df_csv['image_idx'] + 1

    # ユーザ入力に基づいて表示範囲を限定する
    if ix_set_flag:
        df_csv = df_csv.query(f'{ix_view_range[0]} <= image_idx <= {ix_view_range[1]}', engine='python').copy()

    # サブプロットを作成
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=("Upper and Lower Edge", "Width", "Width Standard Deviation", "Brightness Center"))

    # trolley_idのユニークな値を取得
    unique_trolleys = df_csv['trolley_id'].unique()

    # カラーパレットを設定
    colors = plotly.colors.qualitative.D3

    # ホバーテンプレートを定義
    hover_template_upper_edge = """
    Image Index: %{customdata[0]}
    Pole Num: %{customdata[1]}
    Location: %{x:.2f} km
    Upper Edge: %{y:.2f} px
    Lower Edge: %{customdata[2]:.2f} px
    <extra></extra>
    """

    hover_template_lower_edge = """
    Image Index: %{customdata[0]}
    Pole Num: %{customdata[1]}
    Location: %{x:.2f} km
    Upper Edge: %{customdata[2]:.2f} px
    Lower Edge: %{y:.2f} px
    <extra></extra>
    """
    
    hover_template_width = """
    Image Index: %{customdata[0]}
    Pole Num: %{customdata[1]}
    Location: %{x:.2f} km
    Estimated Width: %{y:.2f} px
    <extra></extra>
    """

    hover_template_width_std = """
    Image Index: %{customdata[0]}
    Pole Num: %{customdata[1]}
    Location: %{x:.2f} km
    Width Std Dev: %{y:.2f} px
    <extra></extra>
    """

    hover_template_brightness = """
    Image Index: %{customdata[0]}
    Pole Num: %{customdata[1]}
    Location: %{x:.2f} km
    Brightness Center: %{y:.2f}
    <extra></extra>
    """

    for count, trolley_id in enumerate(unique_trolleys):
        trolley_df = df_csv[df_csv['trolley_id'] == trolley_id]
        
        color_step = len(unique_trolleys) * count

        # Upper and Lower Edge
        fig.add_trace(go.Scatter(
            x=trolley_df['kiro_tei'], 
            y=trolley_df['estimated_upper_edge'],
            mode='lines', 
            name=f'upper_edge_{trolley_id}',
            line=dict(color=colors[0 + color_step]),
            customdata=np.column_stack((trolley_df['image_idx'], trolley_df['pole_num'], trolley_df['estimated_lower_edge'])),
            hovertemplate=hover_template_upper_edge
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=trolley_df['kiro_tei'], 
            y=trolley_df['estimated_lower_edge'],
            mode='lines', 
            name=f'upper_edge_{trolley_id}',
            line=dict(color=colors[1 + color_step]),
            customdata=np.column_stack((trolley_df['image_idx'], trolley_df['pole_num'], trolley_df['estimated_upper_edge'])),
            hovertemplate=hover_template_lower_edge
        ), row=1, col=1)

        # Width
        fig.add_trace(go.Scatter(
            x=trolley_df['kiro_tei'], 
            y=trolley_df['estimated_width'],
            mode='lines', 
            name=f'estimated_width_{trolley_id}',
            line=dict(color=colors[2 + color_step]),
            customdata=np.column_stack((trolley_df['image_idx'], trolley_df['pole_num'])),
            hovertemplate=hover_template_width
        ), row=2, col=1)

        # Width Standard Deviation
        fig.add_trace(go.Scatter(
            x=trolley_df['kiro_tei'], 
            y=trolley_df['estimated_width_std'],
            mode='lines', 
            name=f'estimated_width_std_{trolley_id}',
            line=dict(color=colors[3 + color_step]),
            customdata=np.column_stack((trolley_df['image_idx'], trolley_df['pole_num'])),
            hovertemplate=hover_template_width_std
        ), row=3, col=1)

        # Brightness Center
        fig.add_trace(go.Scatter(
            x=trolley_df['kiro_tei'], 
            y=trolley_df['brightness_center'],
            mode='lines', 
            name=f'brightness_center_{trolley_id}',
            line=dict(color=colors[4 + color_step]),
            customdata=np.column_stack((trolley_df['image_idx'], trolley_df['pole_num'])),
            hovertemplate=hover_template_brightness
        ), row=4, col=1)

    # レイアウトを更新
    fig.update_layout(height=graph_height*4,
                      width=graph_width,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      dragmode='zoom',
                      xaxis=dict(rangeslider=dict(visible=False)),
                     )

    fig.update_xaxes(title_text="location (km)", tickformat=".0f")
    fig.update_yaxes(title_text="px", tickformat=".0f")

    # 最初のサブプロットのy軸を反転
    fig.update_yaxes(range=[y_max, 0], row=1, col=1)

    config = {
        'scrollZoom': True,
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape']
    }

    return fig, config


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
    # csv_fpath = rail_fpath.replace(".shelve", ".csv")    # CSVファイルの保存パスを指定
    title_text = f'Analysis data on Camera:{camera_num}'    # タイトル共通ヘッダ

    # CSVを読み込む
    df = pd.read_csv(rail_fpath)
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
        df_temp = df.query(f'trolley_id == "{trolleyid}"', engine='python').copy()
        x = df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}', engine='python'
        )['ix']
        ax1.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}', engine='python'
        )['estimated_upper_edge'], label=trolleyid)
        ax1.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}', engine='python'
        )['estimated_lower_edge'], label=trolleyid)
        ax2.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}', engine='python'
        )['estimated_width'], label=trolleyid)
        ax3.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}', engine='python'
        )['estimated_width_std'], label=trolleyid)
        ax4.plot(x, df_temp.query(
            f'{ix_view_range[0]} <= ix <= {ix_view_range[1]}', engine='python'
        )['brightness_std'], label=trolleyid)

    # 凡例を有効化する
    ax1.legend()
    ax2.legend()
    ax3.legend()
    ax4.legend()

    return fig, (ax1, ax2, ax3, ax4)


def draw_marker(candidate_init, num, img, col, x_init):
    with col:
        img_array = np.array(img)

        # 画像にマーカー描画
        upper_edge = candidate_init[num][0]
        lower_edge = candidate_init[num][1]
        for i in range(20):
            ixu = upper_edge - i if (upper_edge - i) >= 0 else 0 
            ixl = lower_edge + i if (upper_edge + i) <= 1999 else 1999 
            if x_init <= 500:                                       # x_initに対応
                iy = round(i / 1.5)
            elif x_init > 500:                                      # x_initに対応
                iy = round(i / 1.5) * -1                            # x_initに対応

            # img_array[ixu, 0:3] = [255, 0, 0]
            # img_array[ixu, iy:iy+3] = [255, 0, 0]
            img_array[ixu, x_init:x_init+3] = [255, 0, 0]           # x_initに対応
            img_array[ixu, x_init+iy:x_init+iy+3] = [255, 0, 0]     # x_initに対応

            # img_array[ixl, 0:3] = [255, 0, 0]
            # img_array[ixl, iy:iy+3] = [255, 0, 0]
            img_array[ixl, x_init:x_init+3] = [255, 0, 0]           # x_initに対応
            img_array[ixl, x_init+iy:x_init+iy+3] = [255, 0, 0]     # x_initに対応

        cam_img_mk = Image.fromarray(img_array)
        st.write("📸カメラ画像（自動エッジ検出）")
        st.write(f"{num + 1}番目の候補をマーカーで表示（idx={x_init}）")
        st.image(cam_img_mk)
    return


def download_image(img, image_name):                                                       # 2024.5.21 -->
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    byte_im = buf.getvalue()
    # ダウンロードボタンを設置する
    st.download_button(
        label="画像をダウンロード",
        data=byte_im,
        file_name=image_name,
        mime="image/png"
    )                                                                                      # --> 2024.5.21
    