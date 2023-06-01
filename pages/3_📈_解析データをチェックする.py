import streamlit as st
import src.helpers as helpers
import src.visualize as vis
from src.config import appProperties


def check_graph(config):
    """ グラフ表示ページ
    Args:
        config: ymlファイルを読み込んだ設定値
    """
    # マルチページの設定
    st.set_page_config(page_title="解析データチェッカー")
    st.sidebar.header("解析データチェッカー")

    # メインページのコンテナを配置する
    main_view = st.container()
    graph_view = st.empty()

    # フォルダ直下の画像保管用ディレクトリのリスト
    images_path = helpers.list_imagespath(config.image_dir)

    # 画像保管線区の選択
    dir_area = st.sidebar.selectbox("線区のフォルダ名を選択してください", images_path)
    if dir_area is None:
        st.error("No frames fit the criteria. Please select different label or number.")

    rail_name, st_name, updown_name, measurement_date, measurement_time = helpers.rail_message(dir_area, config)
    with main_view.container():
        st.write(f"現在の線区：{rail_name} {st_name}({updown_name})")
        st.write(f"　　測定日：{measurement_date} ＜{measurement_time}＞")
        st.success("##### 👈別の線区を表示する場合は、再度「線区フォルダを決定」してください")

    # 解析対象のカメラ番号を選択する
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    zip(config.camera_names, config.camera_types)
                    )[0]
    camera_num = config.camera_name_to_type[camera_name]

    # 解析対象の画像フォルダを指定
    target_dir = config.image_dir + "/" + dir_area + "/" + camera_num

    # outputディレクトリの設定
    outpath = config.output_dir + "/" + dir_area + "/" + camera_num

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # 結果保存用のshelveファイル(rail)の保存パスを指定
    rail_fpath = outpath + "/rail.shelve"

    # スライダーでグラフ化する範囲を指定（サイドバーに表示）
    form_graph = main_view.form(key="graph_init")
    img_num = form_graph.select_slider("グラフ化する画像を指定",
                                       options=list(range(len(base_images))),
                                       value=(0, 50))
    graph_height = form_graph.text_input("グラフの表示高さを指定する(単位:px)", "200")
    submit = form_graph.form_submit_button("グラフを作成する")
    if submit:
        with st.spinner("グラフ作成中"):
            # グラフデータを作成する
            grid = vis.plot_fig_bokeh(
                config,
                base_images,
                rail_fpath,
                camera_num,
                img_num,
                graph_height
            )
            # グラフを表示
            graph_view.bokeh_chart(grid, use_container_width=True)
    return


if __name__ == "__main__":
    config = appProperties('config.yml')
    check_graph(config)
