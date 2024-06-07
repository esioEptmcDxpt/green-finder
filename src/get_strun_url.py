import boto3
import json


def get_sagemaker_resouce_name():
    """
        このノートブックを起動している SageMaker のリソース名を取得する
        ノートブックインスタンス起動時に metadataをjsonファイルに記録している
        参考：https://docs.aws.amazon.com/ja_jp/sagemaker/latest/dg/nbi-metadata.html
        その後、Streamlitが起動するURL(8501のみ)を表示する
    Return:
        RESOURCE_NAME(str): ノートブックインスタンスの名前
    """
    # ノートブックインスタンス名を取得する
    sg_json_path = "/opt/ml/metadata/resource-metadata.json"
    with open(sg_json_path, 'r') as file:
        sg_meta = json.load(file)
    RESOURCE_NAME = sg_meta['ResourceName']
    return RESOURCE_NAME


def get_st_running_url():
    """ 実行環境のインスタンス名を取得し、Streamlitが起動するURLを表示する
    """
    # ノートブックインスタンス名を取得
    RESOURCE_NAME = get_sagemaker_resouce_name()

    # ノートブックインスタンスの情報を取得
    client = boto3.client('sagemaker')
    response = client.describe_notebook_instance(NotebookInstanceName=RESOURCE_NAME)
    current_url = response['Url']

    # Streamlit が起動するURLを作成する
    ST_RUNNING_URL = f'https://{current_url}/proxy/8501/'
    
    print(f'アプリが起動するURLです👇')
    print('次のセルを実行したら、アクセスしてください。')
    print(f'{ST_RUNNING_URL}')
    print(' ')
    print('※標準ではURLの末尾が`8501`でアプリが起動しますが、')
    print('  複数回起動するとURL末尾が`8502`等で起動する場合があります。')
    print('  その場合は、👆にアクセスした後、`8501` を `8502` に修正してください。')
    return # ST_RUNNING_URL


if __name__ == '__main__':
    ST_RUNNING_URL = get_st_running_url()
