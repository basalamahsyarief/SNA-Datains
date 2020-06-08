from flask import Flask, abort, jsonify, request, render_template
import json
import os
import io
app = Flask(__name__, static_url_path='',
            static_folder='static',
            template_folder='templates')
# refers to application_top
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_STATIC = os.path.join(APP_ROOT, 'static')


@app.route('/', methods=['POST', 'GET'])
@app.route('/index', methods=['POST', 'GET'])
def prediksi():

    return render_template('index.html')


@app.route('/', methods=['POST', 'GET'])
@app.route('/tabs', methods=['POST', 'GET'])
def contoh():

    return render_template('admin/ui-tabs.html')
# prediksi()


if __name__ == '__main__':
    print("Loading PyTorch model and Flask starting server ...")
    print("Please wait until server has fully started")
    app.run(host='0.0.0.0', port=5000)
