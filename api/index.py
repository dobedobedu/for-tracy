"""
Vercel serverless function - direct Neon PostgreSQL connection.
No external imports at top level to avoid build-time failures.
"""
import os
import json

def handler(event, context):
    """AWS Lambda handler for Vercel"""
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    try:
        # Lazy import to avoid build-time failures
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        DATABASE_URL = os.environ.get('DATABASE_URL', '')
        if not DATABASE_URL:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'DATABASE_URL not set'})
            }
        
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        if path in ('/uploads', '/api/uploads'):
            cur.execute('SELECT * FROM uploads ORDER BY id DESC')
            uploads = [dict(row) for row in cur.fetchall()]
            conn.close()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'uploads': uploads}, default=str)
            }
        
        elif path in ('/communities', '/api/communities'):
            cur.execute("""
                SELECT community, COUNT(*) as count 
                FROM permits 
                WHERE community != '' 
                GROUP BY community 
                ORDER BY count DESC
            """)
            communities = [dict(row) for row in cur.fetchall()]
            conn.close()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'communities': communities}, default=str)
            }
        
        elif path in ('/kanban', '/api/kanban'):
            cur.execute('SELECT * FROM permits ORDER BY record_number')
            permits = [dict(row) for row in cur.fetchall()]
            
            columns = {}
            for p in permits:
                milestone = p['current_milestone']
                if milestone not in columns:
                    columns[milestone] = {'milestone': milestone, 'permits': []}
                columns[milestone]['permits'].append(p)
            
            conn.close()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'columns': list(columns.values())}, default=str)
            }
        
        elif path in ('/calendar', '/api/calendar'):
            cur.execute("""
                SELECT report_date, COUNT(*) as uploads 
                FROM uploads 
                GROUP BY report_date 
                ORDER BY report_date
            """)
            activity = [dict(row) for row in cur.fetchall()]
            conn.close()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'activity': activity}, default=str)
            }
        
        else:
            conn.close()
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Not found', 'path': path})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
