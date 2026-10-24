            ), 400

        ensure_database()

        conditions = []
        params = []

        if mode:
            conditions.append('mode = %s')
            params.append(mode)

        if symbol:
            conditions.append('symbol = %s')
            params.append(symbol)

        where_clause = (
            'WHERE ' + ' AND '.join(conditions)
            if conditions
            else ''
        )

        sql = f"""
            SELECT
                id, symbol, mode, direction,
                score, exchange, reference_time,
                detected_at, entry_price,
                stop_price, tp1_price, tp2_price,
                risk_reward, status
            FROM badang_signals
            {where_clause}
            ORDER BY detected_at DESC, id DESC
            LIMIT %s
        """

        params.append(limit)

        conn = db_connect()

        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        finally:
            conn.close()

        results = []

        for row in rows:
            results.append({
                'id': row[0],
                'symbol': row[1],
                'mode': row[2],
                'direction': row[3],
                'score': row[4],
                'exchange': row[5],
                'reference_time': row[6],
                'detected_at': row[7].isoformat(),
                'entry_price': row[8],
                'stop_price': row[9],
                'tp1_price': row[10],
                'tp2_price': row[11],
                'risk_reward': row[12],
                'status': row[13]
            })

        return jsonify(
            status='ok',
            total_returned=len(results),
            results=results
        )

    except Exception:
        logger.exception('Signal history query failed')
        return jsonify(
            status='error',
            error=(
                '추천 이력을 조회할 수 없습니다. '
                'PostgreSQL 연결 설정을 확인하세요.'
            )
        ), 503


@app.route('/api/v14-db-status')
def v14_db_status():
    if not database_url():
        return jsonify(
            status='not_configured',
            database='postgresql',
            connected=False,
            message='DATABASE_URL 설정 필요'
        )

    try:
        ensure_database()
        conn = db_connect()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT COUNT(*) FROM badang_signals'
                )
                count = cur.fetchone()[0]
        finally:
            conn.close()

        return jsonify(
            status='ok',
            database='postgresql',
            connected=True,
            total_signals=count,
            version='1.4'
        )

    except Exception:
        logger.exception('Database status check failed')
        return jsonify(
            status='error',
            database='postgresql',
            connected=False,
            message='데이터베이스 연결 실패'
        ), 503


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
