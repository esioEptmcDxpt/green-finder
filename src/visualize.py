import matplotlib
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

# @st.cache(hash_funcs={streamlit.delta_generator.DeltaGenerator: my_hash_func})
def ohc_image_load(path, main_view):
    try:
        img = Image.open(path)
        st.session_state.result_img_get = True
    except Exception as e:
        img = None
        st.session_state.analysis_messag = "解析対象の画像がありません。"
        st.session_state.result_img_get = False
    return img


# @st.cache()    # ←エラーのため実装できず…
def dir_area_view_JP(config, dir_area, main_view):
    # メインページに設定した線区等の情報を表示する
    rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
    with main_view.container():
        st.write(f"現在の線区：{rail_name} {st_name}({updown_name})")
        st.write(f"　　測定日：{measurement_date} ＜{measurement_time}＞")
        st.success("##### 👈別の線区を表示する場合は、再度「線区フォルダを決定」してください") 


# メインページにカラム表示する　※修正中
def column_view(main_view, camera_view, file_idx, cam_img, result_img_path, fig):
    col1, col2 = camera_view.columns(2)
    with col1:
        st.header("📸カメラ画像")
        st.write(f"カメラ:{helpers.camera_num_to_name(st.session_state.camera_num_mem, config)} {file_idx + 1}番目の画像です")
        st.image(cam_img)
    with col2:
        st.header("🖥️解析結果")
        st.write(f"{st.session_state.analysis_message}")
        if result_img_path != '' and fig == '':
            result_img = vis.ohc_image_load(result_img_path, main_view)
            st.image(result_img)
        elif fig != '':
            st.pyplot(fig)
    return
