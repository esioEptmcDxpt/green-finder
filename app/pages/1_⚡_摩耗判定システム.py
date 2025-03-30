import os
import shelve
import copy
import streamlit as st
import src.helpers as helpers
import src.visualize as vis
import src.auth_aws as auth
from src.kalman_calc import track_kalman
from src.similar_pixel_calc import track_pixel
from src.config import appProperties


@st.dialog("技セ・MCを選択")
def set_office(_config, office_default):
    office_names = helpers.get_office_names_jp(_config)
    office_default_jp = _config.office_names[office_default]["name"]
    office_names_default_index = office_names.index(office_default_jp)
    office_name_jp = st.selectbox("技セを選択", office_names, index=office_names_default_index)
    office_name = helpers.get_office_name(_config, office_name_jp)
    mc_name_jp = st.selectbox("MCを選択", helpers.get_mc_names_jp(_config, office_name_jp))
    mc_name = helpers.get_mc_name(_config, office_name_jp, mc_name_jp)
    if st.button("設定"):
        st.session_state.office = f"{office_name}/{mc_name}"
        st.rerun()


def ohc_wear_analysis(config):
    st.set_page_config(page_title="トロリ線摩耗検出システム", layout="centered")
    # st.logo("icons/cis_page-eye-catch.jpg", size="large")

    # 認証マネージャーの初期化
    auth_manager = auth.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return
        # pass    # ローカル環境でテストする場合に有効化する。デプロイ前には必ずコメントアウトすること

    # 認証情報からユーザー名を取得
    username = auth_manager.authenticator.get_username()

    st.sidebar.header("トロリ線摩耗検出システム")

    # メインページのコンテナを配置する
    main_view = st.container()
    camera_view = st.empty()
    log_view = st.container()

    # 箇所名を選択
    if 'office' not in st.session_state:
        st.session_state.office = None

    # 技セ・MCを選択
    if "office_dialog" not in st.session_state:
        if st.sidebar.button("技セ・MCを選択"):
            set_office(config, username)

    # 選択された技セ・MCを表示
    if not st.session_state.office:
        st.sidebar.error("技セ・MCを選択してください")
        st.stop()
    else:
        st.sidebar.write(f"選択箇所: {helpers.get_office_message(config, st.session_state.office)}")

    # 線区フォルダの選択
    images_path = helpers.list_imagespath_nonCache(f"{config.image_dir}/{st.session_state.office}")

    # 画像保管線区の選択
    main_view.markdown("# ___Step1___ 線区を選択")
    st.sidebar.markdown("# ___Step1___ 線区を選択")
    st.sidebar.write(f"解析対象の線区フォルダを指定👉️")

    # 検索ボックスによる対象フォルダの絞り込み
    dir_search = st.sidebar.toggle("検索ボックス表示", value=False)
    if dir_search:
        dir_area_key = main_view.text_input("線区 検索キーワード(英語で入力)").lower()
        images_path_filtered = [path for path in images_path if dir_area_key in path.lower()]
        if dir_area_key:
            if not images_path_filtered:
                main_view.error("対象データがありません。検索キーワードを変更してください。")
                st.stop()
        else:
            images_path_filtered = images_path
    else:
        images_path_filtered = images_path

    # セッションステートの初期化
    if 'previous_dir_area' not in st.session_state:
        st.session_state.previous_dir_area = None
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 1

    # 対象フォルダの選択
    dir_area = main_view.selectbox("線区のフォルダ名を選択してください", images_path_filtered)

    # 検測車の走行タイミングの選択
    # 画像ファイル名とキロ程をリンクするために 車モニ の GazoFileIndex を使用
    meas_quater = main_view.selectbox("走行タイミングを選択", config.quarter_measurements)

    # dir_areaが変更されたらcurrent_idxをリセット
    if st.session_state.previous_dir_area != dir_area:
        st.session_state.current_idx = 1
        st.session_state.previous_dir_area = dir_area

    if dir_area is None:
        st.error("線区のフォルダ・画像がありません。👈️ データ管理 を選択して データをダウンロードしてください。")
        st.stop()

    # 選択された線区情報を表示する
    vis.rail_info_view(dir_area, config, main_view)

    st.sidebar.markdown("# ___Step2___ 解析条件を設定")
    # 解析対象のカメラ番号を選択する
    camera_name_list = helpers.get_camera_list(config)
    camera_name = st.sidebar.selectbox(
                    "解析対象のカメラを選択してください",
                    camera_name_list
                    ).split(':')[0]
    st.sidebar.write(f"カメラ番号: {camera_name}")
    camera_num = config.camera_name_to_type[camera_name]

    # 解析対象の画像フォルダを指定
    target_dir = f"{config.image_dir}/{st.session_state.office}/{dir_area}/{camera_num}"

    # outputディレクトリを指定
    outpath = f"{config.output_dir}/{st.session_state.office}/{dir_area}/{camera_num}"

    # imagesフォルダ内の画像一覧取得
    base_images = helpers.list_images(target_dir)

    # ファイルインデックスを指定する
    if not base_images:
        st.sidebar.error("画像がありません")
        st.stop()
    else:
        idx = st.sidebar.number_input(f"インデックス(1～{len(base_images)}で指定)",
                                      min_value=1,
                                      max_value=len(base_images),
                                      value=st.session_state.current_idx) - 1
        # st.sidebar.write(f"ファイルパス:{base_images[idx]}")
        # 画像ファイル名を取得
        image_name = base_images[idx].split('/')[-1]

    # キロ程情報チェック
    img2kiro_tdm_prefix = f"{config.kiro_prefix}/{meas_quater}/csv/"
    csv_files = helpers.list_csv_files(config.bucket, img2kiro_tdm_prefix)
    if not csv_files:
        main_view.error("##### ⚠️ 選択された走行タイミングの画像->キロ程情報がデータベースにありません。管理者に問い合わせてください。")

    # 結果保存用のCSVファイル(rail)の保存パスを指定
    image_name_noExtension = os.path.splitext(os.path.basename(base_images[idx]))[0]
    rail_fpath = f"{outpath}/{config.csv_fname}_{image_name_noExtension}.csv"

    # 表示中の画像、カメラ番号を対象に、トロリーIDを指定して結果を削除する
    result_del = st.sidebar.toggle("表示中の結果を削除", value=False, key='result_del')
    if result_del:
        result_del_form = st.sidebar.form("(💣注意 結果削除)")
        del_trolley_id = result_del_form.selectbox("トロリ線のIDを入力してください", config.trolley_ids)
        result_del_form.warning("元に戻せません 本当に削除しますか？")
        result_del_submit = result_del_form.form_submit_button("💣 削除 💣")
        if result_del_submit:
            helpers.result_csv_drop(rail_fpath, dir_area, camera_num, image_name, del_trolley_id, config)
            main_view.error(f"💥 {idx+1}枚目 {del_trolley_id} の結果を削除しました 💥")

    # メインページにカメラ画像を表示する
    col1, col2 = camera_view.columns(2)

    with col1:
        st.write("📸カメラ画像")
        cam_img = vis.ohc_image_load(base_images[idx])
        st.write(f"カメラ:{camera_name} {idx + 1}番目の画像")
        vis.image_to_html(cam_img, width="100%")
        cam_img_name = f"downloaded_image_{idx}.png"
        vis.download_image(cam_img, cam_img_name)
    with col2:
        st.write("🖥️解析結果")
        st.write("解析結果を表示中")
        try:
            out_img, colors = vis.out_image_load(rail_fpath, dir_area, camera_num, image_name, cam_img, config, outpath)
        except Exception as e:
            out_img = []
            colors = []
            st.write(e)
        if not out_img:
            st.error("解析結果がありません")
        else:
            vis.image_to_html(out_img, width="100%")
            out_img_name = f"downloaded_image_{idx}_analized.png"
            vis.download_image(out_img, out_img_name)
    if out_img:
        with st.sidebar.expander("解析結果の凡例", expanded=True):
            trolley_ids_legend = "<span>トロリ線の描画色</span>"
            for trolley_id, color in zip(config.trolley_ids, colors):
                trolley_ids_legend += f'<br><span style="color:rgb{color};">{trolley_id}</span>'
            st.markdown(trolley_ids_legend, unsafe_allow_html=True)

    main_view.markdown("# ___Step3___ 解析を実行する")
    st.sidebar.markdown("# ___Step3___ 解析を実行する")
    # 暫定的にカルマンフィルタに限定

    trace_method = st.sidebar.radio(
        "システムを選択", 
        ("カルマンフィルタ", "ピクセルトレース")
    )
    # trace_method = "カルマンフィルタ"

    # キロ程情報の使用有無
    kiro_data = st.sidebar.toggle("キロ程情報を使用", value=True)

    # メモリ付き画像を表示
    support_line = st.sidebar.toggle("補助線を使用")
    if support_line:
        # 補助線を使用する場合
        form_support_line = st.sidebar.form(key="support_line_form")
        result_line_draw = form_support_line.toggle("結果を重ねて描画", value=True)
        form_support_line.write(" 0 にすると線を表示しません")
        hori_pos = form_support_line.number_input("補助線の横位置", 0, 999, 0)
        # 選択したシステムによって横線の本数を変更
        vert_pos = [0, 0]
        if trace_method == "ピクセルトレース":
            vert_pos[0] = form_support_line.number_input("補助線の縦位置", 0, 2047, 1000)
        if trace_method == "カルマンフィルタ":
            vert_pos[0] = form_support_line.number_input("補助線の縦位置(上側)", 0, 2047, 1000)
            vert_pos[1] = form_support_line.number_input("補助線の縦位置(下側)", 0, 2047, 1500)
        spline_submit = form_support_line.form_submit_button("📈初期値入力用メモリ付画像を表示する")
        # グラフ付画像の描画を実行
        if spline_submit:
            if (not result_line_draw) | (not out_img):
                # 元のカメラ画像 または 結果が無い場合
                fig = vis.plot_fig(cam_img, vert_pos, hori_pos)
            else:
                fig = vis.plot_fig(out_img, vert_pos, hori_pos)
            with log_view:
                vis.plot_to_html(fig)
    else:
        form_graph_img = st.sidebar.form(key="graph_img_form")
        result_line_draw = form_graph_img.toggle("結果を重ねて描画", value=True)
        # 補助線を使用しない場合
        hori_pos = 0
        vert_pos = [0, 0]
        spline_submit = form_graph_img.form_submit_button("📈初期値入力用メモリ付画像を表示する")
        if spline_submit:
            if (not result_line_draw) | (not out_img):
                # 元のカメラ画像 または 結果が無い場合
                fig = vis.plot_fig(cam_img, vert_pos, hori_pos)
            else:
                fig = vis.plot_fig(out_img, vert_pos, hori_pos)
            with log_view:
                vis.plot_to_html(fig)

    # ピクセルトレースを実行
    if trace_method == "ピクセルトレース":
        form_px = st.sidebar.form(key="similar_pixel_init")
        xin = form_px.number_input("トロリ線の中心位置を入力(0～2048)", 0, 2048, 1024)
        test_num = form_px.number_input(f"解析する画像枚数を入力(1～{len(base_images)-idx})",
                                        1,
                                        len(base_images)-idx,
                                        len(base_images)-idx
                                       )
        submit = form_px.form_submit_button("ピクセルトレース実行")
        if submit:
            # outputディレクトリの準備
            os.makedirs(outpath, exist_ok=True)

            # shelveファイルの初期化
            with shelve.open(rail_fpath) as rail:
                # 線区名を記録する
                rail["name"] = dir_area
                # 解析結果が既にある場合は初期化しない
                helpers.rail_camera_initialize(rail, camera_num, base_images, config.trolley_ids)
            if st.button('計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                st.stop()
                st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

            with st.spinner("ピクセルトレース実行中"):
                track_pixel(
                    rail_fpath,
                    camera_num,
                    base_images,
                    idx,
                    xin,
                    test_num,
                    log_view,
                )

    # カルマンフィルタを実行
    elif trace_method == "カルマンフィルタ":
        # カルマンフィルタの初期値設定
        detect_edge = st.sidebar.toggle("自動で初期値を入力しますか？", value=True)
        # form_support_line = st.sidebar.form(key="detect_edge_form")    # 試作（初期エッジ自動検出）用フォーム
        # form_detect = st.sidebar.form(key="kalman_init_detect")
        form = st.sidebar.form(key="kalman_init")

        trolley_id = form.selectbox("トロリ線のIDを入力してください", config.trolley_ids)
        x_init = form.number_input("横方向の初期座標を入力してください", 0, 999)

        # 初期値自動入力フォーム
        # -----------------------------------------------
        if detect_edge:
            candidate_init = helpers.detect_init_edge(cam_img, x_init)    # x_initに対応
            candidate_len = len(candidate_init)
            if x_init:
                candidate_init = helpers.detect_init_edge(cam_img, x_init)    # x_initに対応
                candidate_len = len(candidate_init)

            if candidate_len > 0:
                num_init = form.number_input("初期値候補を選択してください", 1, candidate_len) - 1
            else:
                form.error("初期値候補がありません。設定を変えてください")
                num_init = 0  # デフォルト値を設定
            init_edge_submit = form.form_submit_button("📈自動で初期値を入力する")
            if init_edge_submit and candidate_len != 0:
                vis.draw_marker(candidate_init, num_init, cam_img, col1, x_init)    # x_initに対応
                print(f'else num:{num_init}')
            elif init_edge_submit and candidate_len == 0:
                st.write("初期値を検出できませんでした・・・")
        # -----------------------------------------------
        else:
            candidate_len = 0

        if candidate_len == 0:
            y_init_l = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください", 0, 1999)
            y_init_u = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください", 0, 1999)
        else:
            y_init_l = form.number_input("上記X座標でのエッジ位置（上端）の座標を入力してください",
                                         min_value=0, max_value=1999,
                                         value=candidate_init[num_init][0])
            y_init_u = form.number_input("上記X座標でのエッジ位置（下端）の座標を入力してください",
                                         min_value=0, max_value=1999,
                                         value=candidate_init[num_init][1])

        test_num = form.number_input(f"解析する画像枚数を入力してください(1～{len(base_images)-idx})",
                                     1, len(base_images)-idx,
                                     len(base_images)-idx)
        submit = form.form_submit_button("カルマンフィルタ実行")

        # デバッグ用
        # ----------------------------------------------------
        # st.sidebar.write(f"x_init  ={x_init}")
        # st.sidebar.write(f"y_init_l={y_init_l}")
        # st.sidebar.write(f"y_init_u={y_init_u}")
        # st.sidebar.write(f"candidate_init={candidate_init}")
        # ----------------------------------------------------

        if submit:
            # outputディレクトリの準備
            os.makedirs(outpath, exist_ok=True)

            # 画像キロ程情報の処理
            # とりあえず、一度でも画像キロ程jsonを作成していればスキップする
            # 画像キロ程jsonの削除は手動対応…
            if not os.path.exists(f"{config.tdm_dir}/{st.session_state.office}/{dir_area}.json"):
                with st.spinner("検測車マスタデータからキロ程情報をリンクしています（お待ちください）"):
                    helpers.get_img2kiro(config, dir_area, st.session_state.office, base_images, csv_files)

            # 選択画像における処理結果が既に存在しているかチェック
            # trolley_dict = helpers.load_shelves(rail_fpath, camera_num, base_images, idx)
            df_csv = helpers.result_csv_load(config, rail_fpath)
            # df_csvで、指定された条件に一致する行を特定する用の条件
            image_name = base_images[idx].split('/')[-1]
            condition = (
                (df_csv['measurement_area'] == dir_area) &
                (df_csv['camera_num'] == camera_num) &
                (df_csv['image_name'] == image_name) &
                (df_csv['trolley_id'] == trolley_id)
            )

            status_view = st.empty()
            status_view.write(f"{idx+1}/{len(base_images)}枚目の画像を解析します🔍")
            progress_bar = log_view.progress(0)
            # if trolley_id in trolley_dict.keys():
            if len(df_csv.loc[condition, :]) > 0:
                st.warning('既に同じ画像での結果が存在していますが、上書きして実行します')

                if st.button('計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                    st.stop()
                    st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

                with st.spinner("カルマンフィルタ実行中"):
                    count = track_kalman(
                            outpath,
                            camera_num,
                            st.session_state.office,
                            base_images,
                            df_csv,
                            idx,
                            test_num,
                            trolley_id,
                            x_init,
                            y_init_u,
                            y_init_l,
                            status_view,
                            progress_bar,
                            kiro_data
                        )
                    # 処理終了後にセッションステートを更新
                    st.session_state.current_idx = idx + count
                    camera_view.success("# 解析が終了しました")
                    log_view.button(f"🔎 {idx+count}番目の画像から再開する")
                    log_view.write("  👆️ ボタンを押して停止した位置から再開する")
            else:
                if st.button(f'計算停止ボタン ＜現在の計算が終わったら停止します＞'):
                    st.stop()
                    st.error('計算停止ボタンが押されたため、計算を停止しました。再開する際には左下の計算ボタンを再度押してください。')

                with st.spinner("カルマンフィルタ実行中"):
                    count = track_kalman(
                        outpath,
                        camera_num,
                        st.session_state.office,
                        base_images,
                        df_csv,
                        idx,
                        test_num,
                        trolley_id,
                        x_init,
                        y_init_u,
                        y_init_l,
                        status_view,
                        progress_bar,
                        kiro_data
                    )
                    # 処理終了後にセッションステートを更新
                    st.session_state.current_idx = idx + count
                    camera_view.success("# 解析が終了しました")
                    log_view.button(f"🔎 {idx+count}番目の画像から再開する")
                    log_view.write("  👆️ ボタンを押して停止した位置から再開する")

    # 解析結果があるかをサイドバーに表示する
    st.sidebar.markdown("# 参考 結果有無👇")
    exist_csv = helpers.search_csv(outpath)
    if not exist_csv:
        st.sidebar.error("CSVファイルがありません。別の線区・カメラを選択してください。")
    else:
        csv_downloader = st.sidebar.toggle("ダウンロード用CSVファイルを準備する✔")
        if csv_downloader:
            with st.spinner("一生懸命CSVを準備しています🐭"):
                df_csv = helpers.rail_csv_concat(outpath)
                csv_data = df_csv.to_csv(index=False).encode('utf-8-sig')
            try:
                with open(rail_fpath) as csv:
                    st.sidebar.download_button(
                        label="CSVファイルをダウンロード",
                        data=csv_data,
                        file_name=dir_area + "_" + camera_num + "_output.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.sidebar.error("解析後にCSVをダウンロードできます")
    idx_result_check = st.sidebar.toggle("解析済みインデックスを表示する", value=True)
    if idx_result_check:
        df = helpers.check_camera_dirs_addIdxLen(dir_area, st.session_state.office, config)
    else:
        df = helpers.check_camera_dirs(dir_area, st.session_state.office, config)
    st.sidebar.dataframe(df)
    csv_delete_btn = st.sidebar.button("結果CSVデータを削除する")
    if csv_delete_btn:
        if os.path.exists(outpath):
            # helpers.file_remove(rail_fpath)
            helpers.imgs_dir_remove(outpath)
            st.session_state.current_idx = 1
            main_view.error("CSVファイルを削除しました")
            main_view.button("はじめから解析する")
        else:
            main_view.error("削除するCSVファイルがありません")

    # st.write("画像ファイルリスト👇")
    # # image_list_for_view = []
    # for idx, image_path in enumerate(base_images):
    #     image_name = image_path.split('/')[-1]
    #     # image_list_for_view.append([idx + 1, image_name])
    #     st.text(f"{idx + 1},{image_name}")



if __name__ == "__main__":
    config = appProperties('config.yml')
    ohc_wear_analysis(config)
