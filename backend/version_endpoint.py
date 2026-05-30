# 版本号API端点

from flask import jsonify
from main import app

@app.route('/api/version', methods=['GET'])
def get_version():
    return jsonify({
        'version': '1.0.0',
        'status': 'ok'
    })
