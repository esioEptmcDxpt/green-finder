import json
import os
import boto3
import urllib.request
import urllib.parse
import base64
import hmac
import hashlib
import logging
import secrets  # ランダムなstateを生成するために追加

# ロギングの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数から認証情報を取得
REGION = os.environ.get('REGION')
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI')
COGNITO_DOMAIN = os.environ.get('COGNITO_DOMAIN')

# Cognitoクライアント
cognito_idp = boto3.client('cognito-idp', region_name=REGION)

def calculate_secret_hash(username):
    """クライアントシークレットハッシュを計算する"""
    message = username + CLIENT_ID
    dig = hmac.new(
        key=CLIENT_SECRET.encode('utf-8'),
        msg=message.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()

def lambda_handler(event, context):
    """Lambda関数のエントリーポイント"""
    logger.info(f"受信イベント: {json.dumps(event)}")
    
    try:
        # リクエストパスを取得（複数の形式に対応）
        resource = event.get('resource')
        path = event.get('path', '')
        
        # デバッグ用にパス情報をログに出力
        logger.info(f"処理パス: resource={resource}, path={path}")
        
        # リソースまたはパスに基づいて処理を分岐
        if resource == '/auth/login' or path.endswith('/login') or path.endswith('/auth/login'):
            return handle_login(event)
        elif resource == '/auth/callback' or path.endswith('/callback') or path.endswith('/auth/callback'):
            return handle_callback(event)
        elif resource == '/auth/token' or path.endswith('/token') or path.endswith('/auth/token'):
            return handle_token_exchange(event)
        elif resource == '/auth/validate' or path.endswith('/validate') or path.endswith('/auth/validate'):
            return validate_token(event)
        elif resource == '/auth/logout' or path.endswith('/logout') or path.endswith('/auth/logout'):
            return handle_logout(event)
        elif resource == '/auth/authenticate' or path.endswith('/authenticate') or path.endswith('/auth/authenticate'):
            return handle_authenticate(event)
        elif path == '/':  # ルートパスのハンドリングを追加
            return handle_login(event)
        else:
            # デバッグ情報を追加
            logger.error(f"無効なリクエストパス: resource={resource}, path={path}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
                },
                'body': json.dumps({'error': '無効なリクエストパス', 'resource': resource, 'path': path})
            }
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': f'処理中にエラーが発生しました: {str(e)}'})
        }

def handle_login(event):
    """ログインリクエストを処理する"""
    # Cognitoのホスト名
    cognito_domain = f"https://{COGNITO_DOMAIN}"
    
    # セキュアなランダムstate値を生成
    state = secrets.token_hex(16)
    logger.info(f"生成したstate値: {state}")
    
    # 認証URLを構築
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': 'email openid phone',
        'redirect_uri': REDIRECT_URI,
        'state': state
    }
    
    # Cognitoのログイン画面へのURLを生成
    login_url = f"{cognito_domain}/login?{urllib.parse.urlencode(params)}"
    
    # デバッグ用にURLをログに出力
    logger.info(f"生成したログインURL: {login_url}")
    logger.info(f"使用リダイレクトURI: {REDIRECT_URI}")
    
    return {
        'statusCode': 302,  # リダイレクト
        'headers': {
            'Location': login_url,
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({'message': 'リダイレクト中...', 'url': login_url})
    }

def handle_callback(event):
    """Cognitoからのコールバックを処理する"""
    # クエリパラメータから認証コードを取得
    query_params = event.get('queryStringParameters', {})
    code = query_params.get('code')
    state = query_params.get('state')
    
    # デバッグ用にパラメータをログに出力
    logger.info(f"コールバックパラメータ: code={code}, state={state}")
    
    if not code:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': '認証コードがありません'})
        }
    
    # リダイレクトURIを生成（フロントエンドに認証コードを渡す）
    app_domain = REDIRECT_URI
    redirect_to_app = f"{app_domain}?code={code}"
    
    logger.info(f"アプリにリダイレクト: {redirect_to_app}")
    
    return {
        'statusCode': 302,  # リダイレクト
        'headers': {
            'Location': redirect_to_app,
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'message': 'アプリにリダイレクト中...'})
    }

def handle_token_exchange(event):
    """認証コードをトークンと交換する"""
    # リクエストボディからコードを取得
    body = json.loads(event.get('body', '{}'))
    code = body.get('code')
    
    logger.info(f"トークン交換リクエスト: code={code}")
    
    if not code:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': '認証コードがありません'})
        }
    
    try:
        # メタデータURLを構築
        metadata_url = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/openid-configuration'
        
        # メタデータを取得
        with urllib.request.urlopen(metadata_url) as response:
            metadata = json.loads(response.read().decode('utf-8'))
        
        token_url = metadata['token_endpoint']
        
        # トークンリクエストデータを準備
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,  # 環境変数と同じリダイレクトURIを使用
            'client_id': CLIENT_ID,
        }
        
        # クライアントシークレットがある場合は追加
        if CLIENT_SECRET:
            token_data['client_secret'] = CLIENT_SECRET
        
        # デバッグ用にトークンリクエストをログに出力
        logger.info(f"トークンエンドポイント: {token_url}")
        logger.info(f"トークンリクエストデータ: {token_data}")
        
        # トークンリクエストを送信
        data = urllib.parse.urlencode(token_data).encode('utf-8')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        req = urllib.request.Request(token_url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            token_response = json.loads(response.read().decode('utf-8'))
        
        logger.info("トークン交換成功")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps(token_response)
        }
    
    except Exception as e:
        logger.error(f"トークン交換エラー: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'トークン交換中にエラーが発生しました: {str(e)}'})
        }

def validate_token(event):
    """トークンの有効性を検証する"""
    # リクエストからトークンを取得
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return {
            'statusCode': 401,
            'body': json.dumps({'error': '有効な認証トークンがありません'})
        }
    
    access_token = auth_header.split(' ')[1]
    
    try:
        # Cognitoを使用してトークンを検証
        response = cognito_idp.get_user(
            AccessToken=access_token
        )
        
        # ユーザー情報を返す
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'valid': True,
                'user': {
                    'username': response.get('Username'),
                    'attributes': {attr['Name']: attr['Value'] for attr in response.get('UserAttributes', [])}
                }
            })
        }
    
    except cognito_idp.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': 'トークンが無効または期限切れです'})
        }
    except Exception as e:
        logger.error(f"トークン検証エラー: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'トークン検証中にエラーが発生しました: {str(e)}'})
        }

def handle_logout(event):
    """ログアウト処理を行う"""
    # リクエストからトークンを取得
    body = json.loads(event.get('body', '{}'))
    refresh_token = body.get('refresh_token')
    
    if not refresh_token:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'リフレッシュトークンが必要です'})
        }
    
    try:
        # CognitoからログアウトするためにリフレッシュトークンをRevokeする
        response = cognito_idp.revoke_token(
            ClientId=CLIENT_ID,
            ClientSecret=CLIENT_SECRET,
            Token=refresh_token
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': 'ログアウトに成功しました'})
        }
    
    except Exception as e:
        logger.error(f"ログアウトエラー: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'ログアウト処理中にエラーが発生しました: {str(e)}'})
        }

def handle_authenticate(event):
    """ユーザー名とパスワードで直接認証する"""
    try:
        # リクエストボディからユーザー名とパスワードを取得
        body = json.loads(event.get('body', '{}'))
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'ユーザー名とパスワードは必須です'})
            }
        
        # シークレットハッシュの計算（必要な場合）
        secret_hash = None
        if CLIENT_SECRET:
            secret_hash = calculate_secret_hash(username)
        
        # Cognitoで認証
        auth_params = {
            'USERNAME': username,
            'PASSWORD': password
        }
        
        if secret_hash:
            auth_params['SECRET_HASH'] = secret_hash
        
        response = cognito_idp.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters=auth_params
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(response)
        }
    
    except cognito_idp.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'body': json.dumps({'error': '認証に失敗しました。ユーザー名またはパスワードが正しくありません。'})
        }
    except cognito_idp.exceptions.UserNotFoundException:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'ユーザーが見つかりません'})
        }
    except Exception as e:
        logger.error(f"認証エラー: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'認証処理中にエラーが発生しました: {str(e)}'})
        } 