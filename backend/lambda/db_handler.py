import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def lambda_handler(event, context):
    # 環境変数からDB接続情報を取得
    DB_HOST = os.environ['DB_HOST']
    DB_NAME = os.environ['DB_NAME']
    DB_USER = os.environ['DB_USER']
    DB_PASSWORD = os.environ['DB_PASSWORD']
    
    try:
        # リクエストボディからパラメータを取得
        body = json.loads(event['body'])
        lat = float(body['latitude'])
        lng = float(body['longitude'])
        
        # DB接続
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode='require'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 最寄りの世界遺産を5件検索
            query = """
            SELECT id, name, country, year_inscribed, description,
                   ST_X(location) as longitude, ST_Y(location) as latitude,
                   ST_Distance(location, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as distance
            FROM world_heritage_sites
            ORDER BY location <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            LIMIT 5
            """
            
            cur.execute(query, (lng, lat, lng, lat))
            results = cur.fetchall()
            
            if results:
                # 距離をキロメートルに変換
                for result in results:
                    result['distance'] = round(result['distance'] * 111.32, 2)
                
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps(results, ensure_ascii=False)
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'error': '世界遺産が見つかりませんでした'})
                }
                
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(e)})
        }
    finally:
        if 'conn' in locals():
            conn.close() 