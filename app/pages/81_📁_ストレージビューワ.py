import streamlit as st
import os
import datetime
import pandas as pd
from pathlib import Path
from src.config import appProperties
import src.auth as auth


def get_directory_size(path):
    """ディレクトリのサイズを計算する

    Args:
        path (str): ディレクトリパス

    Returns:
        int: サイズ（バイト）
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if not os.path.islink(file_path):
                    total_size += os.path.getsize(file_path)
    except PermissionError:
        pass
    return total_size


def format_size(size_bytes):
    """バイト数を人間が読みやすい形式に変換する

    Args:
        size_bytes (int): サイズ（バイト）

    Returns:
        str: 読みやすい形式のサイズ
    """
    if size_bytes == 0:
        return "0B"
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f}{size_names[i]}"


def get_file_info(path):
    """ファイルの詳細情報を取得する

    Args:
        path (str): ファイルパス

    Returns:
        dict: ファイル情報
    """
    try:
        stat = os.stat(path)
        is_dir = os.path.isdir(path)
        
        if is_dir:
            size = get_directory_size(path)
        else:
            size = stat.st_size
            
        return {
            "名前": os.path.basename(path),
            "タイプ": "ディレクトリ" if is_dir else "ファイル",
            "サイズ": format_size(size),
            "更新日時": datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            "パーミッション": oct(stat.st_mode)[-3:],
            "パス": path
        }
    except Exception as e:
        return {
            "名前": os.path.basename(path),
            "タイプ": "エラー",
            "サイズ": "N/A",
            "更新日時": "N/A",
            "パーミッション": "N/A",
            "パス": path,
            "エラー": str(e)
        }


def storage_viewer(config):
    """(開発用) コンテナ上のファイルを表示する

    Args:
        config (object): 設定ファイル
    """
    st.set_page_config(page_title="ストレージビューワ", page_icon="📁",)
    # 認証チェック
    if not auth.check_authentication():
        return

    st.sidebar.title("何をしますか？")
    st.sidebar.success("👆アプリを選択してください")

    st.title("ストレージビューワ")
    st.write("コンテナ上のファイルを表示します")
    
    # セッション状態の初期化
    if "current_path" not in st.session_state:
        st.session_state.current_path = os.getcwd()

    # パス移動機能
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_path = st.text_input(
            "現在のディレクトリ", 
            value=st.session_state.current_path
        )
        if new_path != st.session_state.current_path and os.path.isdir(new_path):
            st.session_state.current_path = new_path
    
    with col2:
        if st.button("親ディレクトリへ"):
            st.session_state.current_path = str(Path(st.session_state.current_path).parent)
            st.experimental_rerun()

    # フィルタリングオプション
    with st.expander("フィルタリングオプション"):
        col1, col2 = st.columns(2)
        with col1:
            show_hidden = st.checkbox("隠しファイルを表示", value=False)
            file_filter = st.text_input("ファイル名フィルタ（部分一致）")
        with col2:
            file_types = st.multiselect(
                "ファイルタイプ",
                options=["ディレクトリ", "ファイル"],
                default=["ディレクトリ", "ファイル"]
            )

    # ディレクトリ内のファイルとフォルダを取得
    try:
        items = []
        for item in os.listdir(st.session_state.current_path):
            # 隠しファイルのフィルタリング
            if not show_hidden and item.startswith('.'):
                continue
                
            full_path = os.path.join(st.session_state.current_path, item)
            info = get_file_info(full_path)
            
            # ファイル名フィルタ
            if file_filter and file_filter.lower() not in info["名前"].lower():
                continue
                
            # ファイルタイプフィルタ
            if info["タイプ"] not in file_types:
                continue
                
            items.append(info)
        
        # データフレームに変換して表示
        if items:
            df = pd.DataFrame(items)
            st.dataframe(
                df,
                column_config={
                    "名前": st.column_config.TextColumn("名前"),
                    "タイプ": st.column_config.TextColumn("タイプ"),
                    "サイズ": st.column_config.TextColumn("サイズ"),
                    "更新日時": st.column_config.TextColumn("更新日時"),
                    "パーミッション": st.column_config.TextColumn("パーミッション"),
                    "パス": st.column_config.TextColumn("パス", width="large")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # 合計サイズの表示
            total_size = sum([get_directory_size(i["パス"]) if i["タイプ"] == "ディレクトリ" 
                              else os.path.getsize(i["パス"]) for i in items])
            st.info(f"合計サイズ: {format_size(total_size)}")
        else:
            st.warning("表示するファイルがありません")
            
        # ディレクトリのクリック操作
        st.write("### ディレクトリをクリックして移動")
        dir_items = [i for i in items if i["タイプ"] == "ディレクトリ"]
        if dir_items:
            dir_names = [i["名前"] for i in dir_items]
            selected_dir = st.selectbox("選択してください", dir_names)
            if st.button("移動"):
                selected_path = os.path.join(st.session_state.current_path, selected_dir)
                st.session_state.current_path = selected_path
                st.experimental_rerun()
        else:
            st.info("このディレクトリには下位フォルダがありません")

    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        
    # システム情報
    with st.expander("システム情報"):
        st.code(f"現在の作業ディレクトリ: {os.getcwd()}")
        st.code(f"Pythonパス: {os.environ.get('PYTHONPATH', '設定なし')}")
        
        # ディスク使用状況
        st.subheader("ディスク使用状況")
        try:
            disk_info = os.popen("df -h").read()
            st.code(disk_info)
        except:
            st.warning("ディスク情報の取得に失敗しました")
    
    # ログアウトボタン
    if st.sidebar.button("ログアウト"):
        auth.logout()


if __name__ == "__main__":
    config = appProperties('config.yml')
    storage_viewer(config)

