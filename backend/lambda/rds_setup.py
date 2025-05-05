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
        # autocommitをTrueに設定して接続
        admin_conn = psycopg2.connect(
            host=DB_HOST,
            database=os.environ['MASTER_DB_NAME'],
            user=os.environ['MASTER_DB_USER'],
            password=os.environ['MASTER_DB_PASSWORD'],
            sslmode='require'
        )
        admin_conn.autocommit = True
        
        with admin_conn.cursor() as admin_cur:
            # ステップ1: PostGIS拡張機能を管理するユーザー（ロール）を作成
            admin_cur.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gis_admin') THEN
                        CREATE ROLE gis_admin LOGIN PASSWORD %s;
                        GRANT rds_superuser TO gis_admin;
                    END IF;
                END $$;
            """, (DB_PASSWORD,))
            
            # データベースが存在するかチェック
            admin_cur.execute("SELECT 1 FROM pg_database WHERE datname = 'lab_gis'")
            exists = admin_cur.fetchone()
            if not exists:
                admin_cur.execute("CREATE DATABASE lab_gis")
            
            admin_cur.execute("GRANT ALL PRIVILEGES ON DATABASE lab_gis TO gis_admin")
        
        # gis_adminユーザーで接続（PostGISのセットアップ）
        gis_conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode='require'
        )
        
        with gis_conn.cursor() as gis_cur:
            # ステップ2: PostGIS拡張機能のインストール
            gis_cur.execute("""
                CREATE EXTENSION IF NOT EXISTS postgis;
                CREATE EXTENSION IF NOT EXISTS postgis_raster;
                CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
                CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
                CREATE EXTENSION IF NOT EXISTS postgis_topology;
                CREATE EXTENSION IF NOT EXISTS address_standardizer_data_us;
            """)
            
            # ステップ3: 拡張機能スキーマの所有権を移管
            gis_cur.execute("""
                ALTER SCHEMA tiger OWNER TO gis_admin;
                ALTER SCHEMA tiger_data OWNER TO gis_admin;
                ALTER SCHEMA topology OWNER TO gis_admin;
            """)
            
            # ステップ4: PostGISテーブルの所有権を移管
            gis_cur.execute("""
                CREATE OR REPLACE FUNCTION exec(text) returns text language plpgsql volatile AS $f$ 
                BEGIN 
                    EXECUTE $1; 
                    RETURN $1; 
                END; 
                $f$;
                
                SELECT exec('ALTER TABLE ' || quote_ident(s.nspname) || '.' || quote_ident(s.relname) || ' OWNER TO gis_admin;')
                FROM (
                    SELECT nspname, relname
                    FROM pg_class c JOIN pg_namespace n ON (c.relnamespace = n.oid) 
                    WHERE nspname in ('tiger','topology') AND
                    relkind IN ('r','S','v') ORDER BY relkind = 'S'
                ) s;
            """)
            
            # ステップ5: 世界遺産テーブルの作成とデータ挿入
            gis_cur.execute("""
                CREATE TABLE IF NOT EXISTS world_heritage_sites (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    country VARCHAR(100) NOT NULL,
                    year_inscribed INTEGER,
                    location GEOMETRY(Point, 4326) NOT NULL,
                    description TEXT,
                    CONSTRAINT unique_name_country UNIQUE (name, country)
                );
                
                CREATE INDEX IF NOT EXISTS world_heritage_sites_location_idx 
                ON world_heritage_sites USING GIST (location);
            """)
            
            # データが既に存在するか確認
            gis_cur.execute("SELECT COUNT(*) FROM world_heritage_sites")
            count = gis_cur.fetchone()[0]

            # データが存在しない場合のみ挿入する
            if count == 0:
                gis_cur.execute("""
                    INSERT INTO world_heritage_sites (name, country, year_inscribed, location, description) VALUES
                        ('姫路城', '日本', 1993, ST_SetSRID(ST_MakePoint(134.6938, 34.8396), 4326), '白鷺城とも呼ばれる日本を代表する城郭建築'),
                        ('法隆寺地域の仏教建造物', '日本', 1993, ST_SetSRID(ST_MakePoint(135.7341, 34.6148), 4326), '世界最古の木造建築群'),
                        ('屋久島', '日本', 1993, ST_SetSRID(ST_MakePoint(130.5283, 30.3333), 4326), '樹齢数千年の屋久杉が生息する自然遺産'),
                        ('白神山地', '日本', 1993, ST_SetSRID(ST_MakePoint(140.2000, 40.5000), 4326), 'ブナの原生林が広がる自然遺産'),
                        ('古都京都の文化財', '日本', 1994, ST_SetSRID(ST_MakePoint(135.7681, 35.0116), 4326), '京都の寺院・神社・城郭などの文化財群'),
                        ('白川郷・五箇山の合掌造り集落', '日本', 1995, ST_SetSRID(ST_MakePoint(136.9075, 36.2556), 4326), '伝統的な合掌造りの集落'),
                        ('原爆ドーム', '日本', 1996, ST_SetSRID(ST_MakePoint(132.4536, 34.3955), 4326), '広島の原爆被害を伝える負の世界遺産'),
                        ('厳島神社', '日本', 1996, ST_SetSRID(ST_MakePoint(132.3219, 34.2958), 4326), '海に浮かぶ朱塗りの大鳥居で有名な神社'),
                        ('古都奈良の文化財', '日本', 1998, ST_SetSRID(ST_MakePoint(135.8450, 34.6851), 4326), '奈良の寺院・神社などの文化財群'),
                        ('日光の社寺', '日本', 1999, ST_SetSRID(ST_MakePoint(139.6000, 36.7500), 4326), '日光東照宮を中心とする神社仏閣群'),
                        ('琉球王国のグスク及び関連遺産群', '日本', 2000, ST_SetSRID(ST_MakePoint(127.8000, 26.2000), 4326), '沖縄の城跡と関連遺跡群'),
                        ('紀伊山地の霊場と参詣道', '日本', 2004, ST_SetSRID(ST_MakePoint(135.9000, 34.0000), 4326), '熊野古道などの霊場と参詣道'),
                        ('知床', '日本', 2005, ST_SetSRID(ST_MakePoint(145.0000, 44.0000), 4326), '北海道の自然遺産、野生動物の宝庫'),
                        ('石見銀山遺跡とその文化的景観', '日本', 2007, ST_SetSRID(ST_MakePoint(132.4833, 35.1167), 4326), '銀山とその文化的景観'),
                        ('小笠原諸島', '日本', 2011, ST_SetSRID(ST_MakePoint(142.2000, 27.0000), 4326), '独自の生態系を持つ島々'),
                        ('平泉―仏国土（浄土）を表す建築・庭園及び考古学的遺跡群', '日本', 2011, ST_SetSRID(ST_MakePoint(141.1167, 38.9833), 4326), '浄土思想に基づく文化遺産'),
                        ('富士山―信仰の対象と芸術の源泉', '日本', 2013, ST_SetSRID(ST_MakePoint(138.7278, 35.3606), 4326), '日本の象徴的な山とその文化的景観'),
                        ('富岡製糸場と絹産業遺産群', '日本', 2014, ST_SetSRID(ST_MakePoint(138.8917, 36.2556), 4326), '近代製糸業の遺産'),
                        ('明治日本の産業革命遺産 製鉄・製鋼、造船、石炭産業', '日本', 2015, ST_SetSRID(ST_MakePoint(130.4000, 33.5000), 4326), '日本の近代化を支えた産業遺産群'),
                        ('ル・コルビュジエの建築作品―近代建築運動への顕著な貢献', '日本', 2016, ST_SetSRID(ST_MakePoint(139.6000, 35.7000), 4326), '国立西洋美術館を含む近代建築群'),
                        ('「神宿る島」宗像・沖ノ島と関連遺産群', '日本', 2017, ST_SetSRID(ST_MakePoint(130.1000, 33.9000), 4326), '古代の信仰と交易の遺産'),
                        ('長崎と天草地方の潜伏キリシタン関連遺産', '日本', 2018, ST_SetSRID(ST_MakePoint(129.8833, 32.7500), 4326), 'キリスト教迫害と信仰の歴史を伝える遺産'),
                        ('百舌鳥・古市古墳群―古代日本の墳墓群', '日本', 2019, ST_SetSRID(ST_MakePoint(135.4833, 34.5667), 4326), '古代日本の巨大古墳群'),
                        ('北海道・北東北の縄文遺跡群', '日本', 2021, ST_SetSRID(ST_MakePoint(141.0000, 41.0000), 4326), '縄文時代の生活と文化を伝える遺跡群'),
                        ('奄美大島、徳之島、沖縄島北部及び西表島', '日本', 2021, ST_SetSRID(ST_MakePoint(129.3000, 28.3000), 4326), '亜熱帯の生態系と固有種の宝庫')
                """)
            
            gis_conn.commit()
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST,OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                },
                'body': json.dumps({'message': 'RDSの初期セットアップが完了しました'})
            }
                
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': json.dumps({'error': str(e)})
        }
    finally:
        if 'admin_conn' in locals():
            admin_conn.close()
        if 'gis_conn' in locals():
            gis_conn.close()
