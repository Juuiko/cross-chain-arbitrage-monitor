from flask import Flask, render_template, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)


@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/opportunities')
def get_opportunities():
    """API endpoint to get recent opportunities"""
    try:
        df = pd.read_csv('/app/data/opportunities.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Get last hour of opportunities
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_df = df[df['timestamp'] > one_hour_ago]

        opportunities = recent_df.to_dict('records')

        return jsonify({
            'success': True,
            'count': len(opportunities),
            'opportunities': opportunities
        })
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'message': 'No data available yet'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/stats')
def get_stats():
    """API endpoint for summary stats"""
    try:
        df = pd.read_csv('/app/data/opportunities.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Calculate stats
        stats = {
            'total_opportunities': len(df),
            'avg_spread': df['spread_pct'].mean(),
            'max_spread': df['spread_pct'].max(),
            'top_symbols': df['symbol'].value_counts().head(5).to_dict(),
            'last_update': df['timestamp'].max().isoformat() if len(df) > 0 else None
        }

        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)