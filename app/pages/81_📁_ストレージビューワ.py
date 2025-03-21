import streamlit as st
import os
import datetime
import pandas as pd
import shutil
from pathlib import Path
from src.config import appProperties
import src.auth_aws as auth


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


def is_binary_file(file_path, sample_size=1024):
    """ファイルがバイナリかテキストかを判定する

    Args:
        file_path (str): ファイルパス
        sample_size (int): 判定に使用するバイト数

    Returns:
        bool: バイナリファイルの場合True
    """
    # よく知られているテキストファイルの拡張子リスト
    text_extensions = [
        '.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.csv', 
        '.yml', '.yaml', '.ini', '.cfg', '.conf', '.sh', '.bat', '.ps1', 
        '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php',
        '.ts', '.jsx', '.tsx', '.vue', '.gradle', '.properties', '.toml',
        '.gitignore', '.dockerignore', '.env'
    ]
    
    # 拡張子がないがテキストファイルとして扱うファイル名
    text_filenames = ['Dockerfile', 'Makefile', 'README', 'LICENSE', 'Jenkinsfile']
    
    # 拡張子またはファイル名でテキストファイルかチェック
    file_ext = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path)
    
    if file_ext in text_extensions or file_name in text_filenames:
        return False
    
    # 拡張子での判定ができない場合はコンテンツを確認
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
            # NULL文字があるか確認
            if b'\x00' in sample:
                return True
                
            # テキストとして解釈できるか試みる
            try:
                sample.decode('utf-8')
                return False
            except UnicodeDecodeError:
                # 別のエンコーディングを試す
                try:
                    sample.decode('shift-jis')
                    return False
                except UnicodeDecodeError:
                    try:
                        sample.decode('euc-jp')
                        return False
                    except UnicodeDecodeError:
                        return True
    except Exception:
        return True  # エラーが発生した場合はバイナリ扱い


def get_language_from_extension(file_path):
    """ファイルの拡張子から言語を推測する

    Args:
        file_path (str): ファイルパス

    Returns:
        str: 言語識別子 (Streamlitが認識できる形式)
    """
    # 拡張子と言語のマッピング
    extension_to_language = {
        '.py': 'python',
        '.js': 'javascript',
        '.html': 'html',
        '.css': 'css',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.json': 'json',
        '.xml': 'xml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.ini': 'ini',
        '.conf': 'ini',
        '.toml': 'toml',
        '.dockerfile': 'dockerfile',
    }
    
    # ファイル名ベースの特殊ケース
    filename_to_language = {
        'Dockerfile': 'dockerfile',
        'Makefile': 'makefile',
        'docker-compose.yml': 'yaml',
        'docker-compose.yaml': 'yaml',
    }
    
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # まずファイル名で特殊ケースをチェック
    if file_name in filename_to_language:
        return filename_to_language[file_name]
    
    # 次に拡張子をチェック
    if file_ext in extension_to_language:
        return extension_to_language[file_ext]
    
    # 該当しない場合はNoneを返す
    return None


def is_code_file(file_path):
    """コードファイルかどうかを判定する

    Args:
        file_path (str): ファイルパス

    Returns:
        bool: コードファイルの場合True
    """
    return get_language_from_extension(file_path) is not None


def delete_item(path):
    """ファイルまたはディレクトリを削除する

    Args:
        path (str): 削除対象のパス

    Returns:
        bool: 削除成功時True
    """
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True
    except Exception as e:
        st.error(f"削除に失敗しました: {str(e)}")
        return False


def storage_viewer(config):
    """(開発用) コンテナ上のファイルを表示する

    Args:
        config (object): 設定ファイル
    """
    st.set_page_config(page_title="ストレージビューワ", page_icon="📁", layout="wide")

    # 認証マネージャーの初期化
    auth_manager = auth.AuthenticationManager()
    # 認証処理とUI表示
    is_authenticated = auth_manager.authenticate_page(title="トロリ線摩耗判定支援システム")
    # 認証済みの場合のみコンテンツを表示
    if not is_authenticated:
        return
    
    # 認証情報からユーザー名を取得
    username = auth_manager.authenticator.get_username()
    
    # 開発者チェック
    if username != 'esiodxpt':
        st.error("このページは開発者向けのため利用できません")
        st.info("利用を希望する場合は、管理者までお問い合わせください")
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
        if st.button("⇧ 親ディレクトリへ", key="parent_dir_button1"):
            st.session_state.current_path = str(Path(st.session_state.current_path).parent)
            st.rerun()

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
            col1, col2 = st.columns([1, 5])
            if col1.button("移動", key="move_button"):
                selected_path = os.path.join(st.session_state.current_path, selected_dir)
                st.session_state.current_path = selected_path
                st.rerun()
            if col2.button("⇧ 親ディレクトリへ", key="parent_dir_button2"):
                st.session_state.current_path = str(Path(st.session_state.current_path).parent)
                st.rerun()
        else:
            st.info("このディレクトリには下位フォルダがありません")

        # ファイル/ディレクトリ削除機能
        st.write("### ファイル/ディレクトリの削除")
        all_items = [i for i in items]
        if all_items:
            item_names = [i["名前"] for i in all_items]
            selected_item = st.selectbox("削除するアイテムを選択", item_names, key="delete_selector")
            
            if selected_item:
                selected_path = os.path.join(st.session_state.current_path, selected_item)
                selected_type = "ディレクトリ" if os.path.isdir(selected_path) else "ファイル"
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"選択中: {selected_item}")
                    st.write(f"タイプ: {selected_type}")
                
                # 削除確認UI
                delete_confirmation = st.checkbox("削除を確認する", key="delete_confirm")
                if delete_confirmation:
                    st.warning(f"⚠️ **注意**: {selected_item} ({selected_type}) を完全に削除します。この操作は元に戻せません！")
                    if selected_type == "ディレクトリ":
                        dir_size = get_directory_size(selected_path)
                        st.info(f"ディレクトリサイズ: {format_size(dir_size)}")
                        
                    if st.button("🗑️ 削除を実行", key="execute_delete"):
                        if delete_item(selected_path):
                            st.success(f"{selected_item} を削除しました")
                            # 削除が成功したら、ページを再読み込み
                            st.rerun()
        else:
            st.info("このディレクトリには削除可能なアイテムがありません")

        # ファイル内容表示機能
        st.write("### ファイルの内容を表示")
        file_items = [i for i in items if i["タイプ"] == "ファイル"]
        if file_items:
            file_names = [i["名前"] for i in file_items]
            selected_file = st.selectbox("ファイルを選択", file_names, key="file_selector")
            
            if selected_file:
                selected_path = os.path.join(st.session_state.current_path, selected_file)
                file_size = os.path.getsize(selected_path)
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"ファイルサイズ: {format_size(file_size)}")
                
                # 大きなファイルの場合は警告と部分表示オプション
                max_display_size = 1024 * 1024  # 1MB
                display_limit = st.slider("表示する最大バイト数", 1024, 1024*1024, min(100*1024, file_size))
                
                if is_binary_file(selected_path):
                    st.warning("バイナリファイルのため内容を表示できません")
                    if st.button("それでも表示する（16進数表示）"):
                        try:
                            with open(selected_path, 'rb') as f:
                                content = f.read(display_limit)
                                hex_content = content.hex(' ')
                                st.code(hex_content)
                        except Exception as e:
                            st.error(f"ファイルの読み込みに失敗しました: {str(e)}")
                else:
                    try:
                        with open(selected_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read(display_limit if file_size > max_display_size else file_size)
                            
                            # ファイルサイズの警告
                            if file_size > max_display_size:
                                st.warning(f"大きなファイルです。先頭の{format_size(display_limit)}のみ表示します。")
                            
                            # コードファイルの場合はシンタックスハイライトを適用
                            language = get_language_from_extension(selected_path)
                            if language:
                                st.code(content, language=language)
                            else:
                                st.text_area("ファイル内容", content, height=400)
                                
                    except Exception as e:
                        st.error(f"ファイルの読み込みに失敗しました: {str(e)}")
        else:
            st.info("このディレクトリには表示可能なファイルがありません")

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



if __name__ == "__main__":
    config = appProperties('config.yml')
    storage_viewer(config)

