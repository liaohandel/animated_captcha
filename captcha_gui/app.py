# app.py
from flask import Flask, render_template, request, jsonify
import subprocess
import os
import sys
import random
import string
import mysql.connector
import glob # 導入 glob 模組
import time
import re # 導入正則表達式模組

# 初始化 Flask 應用程式
app = Flask(__name__)

# 定義 passwd_tab 列表 (保持不變)
# 格式: "array_mode,password_template,interference_number,font_mode,background_mode,flicker_mode"
# 注意: password_template 現在用於定義隨機生成密碼的長度
passwd_tab = [
    "3,ABCD,0,0,1,0,0",    #1 (此處ABCD的長度4將用於生成4位隨機密碼)
    "4,ABCD,0,0,1,0,0",    #2
    "5,ABCD,0,0,1,0,0",    #3

    "3,ABCD,2,0,1,1,0",    #4
    "4,ABCD,2,0,1,1,0",    #5
    "5,ABCD,2,0,1,1,0",    #6

    "3,ABCD,2,2,1,1,0",    #7
    "4,ABCD,2,2,1,1,0",    #8
    "5,ABCD,2,2,1,1,0",    #9

    "3,ABCD,2,2,1,1,1",    #10 (此處ABCDE的長度5將用於生成5位隨機密碼)
    "4,ABCD,2,2,1,1,1",    #11 (此處ABCDEF的長度6將用於生成6位隨機密碼)
    "5,ABCD,2,2,1,1,1",    #12
    
    "4,ABCDE,2,2,1,1,1",    #13 (此處ABCDE的長度5將用於生成5位隨機密碼)
    "5,ABCDE,2,2,1,1,1",    #14 (此處ABCDEF的長度6將用於生成6位隨機密碼)
    "5,ABCDEF,2,2,1,1,1",   #15
]

# 輔助函數：生成指定長度的隨機字串 (修正為只生成大寫字母)
def generate_random_string(length):
    """生成包含大寫字母的隨機字串，以符合 active_keyx105web.py 的密碼驗證"""
    characters = string.ascii_uppercase # 只使用大寫字母
    return ''.join(random.choice(characters) for i in range(length))

# 輔助函數：GIF 檔案清理邏輯 (提取出來以便重用)
def cleanup_passwd_lib(max_files=300):
    """檢查並清理 passwd_lib 目錄中的 GIF 檔案"""
    passwd_lib_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'static',
        'passwd_lib'
    )
    os.makedirs(passwd_lib_path, exist_ok=True) # 確保目錄存在

    gif_files = glob.glob(os.path.join(passwd_lib_path, '*.gif'))
    file_count = len(gif_files)

    print(f"passwd_lib 目錄中當前有 {file_count} 個 GIF 檔案。", file=sys.stderr)

    if file_count > max_files:
        print(f"偵測到 {file_count} 個 GIF 檔案，超過 {max_files} 個限制。正在清理目錄...", file=sys.stderr)
        # 為了安全，只刪除最舊的檔案，直到達到限制 (這裡簡化為全部刪除)
        for f in gif_files:
            try:
                os.remove(f)
                # print(f"已刪除檔案: {f}", file=sys.stderr) # 避免日誌過多
            except OSError as e:
                print(f"刪除檔案 {f} 失敗: {e}", file=sys.stderr)
        print("passwd_lib 目錄清理完成。", file=sys.stderr)
    return passwd_lib_path

# 輔助函數：從腳本輸出中提取 GIF 檔案路徑
def extract_gif_path(script_output):
    """
    從 active_keyx105web.py 的輸出中安全地提取 GIF 檔案的相對路徑。
    目標路徑格式為: passwd_lib/*.gif
    """
    # 使用正則表達式查找包含 "passwd_lib/" 且以 ".gif" 結尾的路徑
    # 這裡假設檔名不包含空格或其他特殊字符
    match = re.search(r'(passwd_lib/[^\s/]+\.gif)', script_output)
    
    if match:
        gif_relative_path = match.group(1).strip()
        print(f"從輸出中提取到的 GIF 路徑: {gif_relative_path}", file=sys.stderr)
        return gif_relative_path
    else:
        # 如果無法找到標準格式的路徑，則返回空字串或拋出錯誤
        print(f"警告: 無法從腳本輸出中提取 GIF 路徑。原始輸出:\n{script_output}", file=sys.stderr)
        return ""


# --- 網頁路由 (保持不變) ---
@app.route('/')
def index():
    """
    根路徑，用於顯示網頁 GUI 介面。
    它會渲染 templates/index.html 檔案。
    """
    return render_template('index.html')

@app.route('/setgui')
def set_gui():
    """
    新的 GUI 路由，用於顯示 setweb.html 介面，以手動設定參數生成 GIF。
    """
    # 假設 setweb.html 位於 templates 資料夾中
    return render_template('setweb.html')

# --- API 路由 ---

# 原始的 /getpasswd API (更新了輸出處理邏輯)
@app.route('/getpasswd', methods=['GET'])
def get_password_api():
    """
    GET 請求 API 接口：/getpasswd
    接收 'no' 參數，根據 'no' 值從 passwd_tab 查詢參數，
    隨機生成密碼，並呼叫外部 Python 腳本 active_keyx105web.py 來生成 GIF。
    """
    no_param = request.args.get('no')

    if no_param is None:
        return jsonify({"status": "error", "message": "缺少 'no' 參數"}), 400

    try:
        no_index = int(no_param)
        if not (0 <= no_index < len(passwd_tab)):
            return jsonify({"status": "error", "message": f"'no' 值超出範圍。有效範圍: 0 到 {len(passwd_tab) - 1}"}), 400

        # 根據 no 值從 passwd_tab 獲取參數字串
        params_str = passwd_tab[no_index]
        params = params_str.split(',')

        if len(params) != 7:
            return jsonify({"status": "error", "message": "passwd_tab 中參數字串格式不正確 (需要7個欄位)"}), 500

        array_mode = params[0]
        password_template = params[1]
        interference_number = params[2]
        font_mode = params[3]
        background_mode = params[4]
        flicker_mode = params[5]
        showtype = params[6]

        # 根據 password_template 的長度生成隨機密碼 (現在只生成大寫字母)
        password_length = len(password_template)
        generated_password = generate_random_string(password_length)

        print(f"接收到 /getpasswd 請求 (no={no_index}):")
        print(f"  隨機生成的密碼 (長度={password_length}): {generated_password}")

        # --- 檢查並清理 passwd_lib 目錄 ---
        cleanup_passwd_lib()
        # --- 清理邏輯結束 ---

        # 構建呼叫 active_keyx105web.py 的命令
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static',
            'active_keyx105web.py'
        )
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"active_keyx105web.py 腳本未在預期路徑找到: {script_path}")

        command = [
            sys.executable, # 使用當前 Python 解釋器
            script_path,
            array_mode,         
            generated_password,
            interference_number,
            font_mode,          
            background_mode,    
            flicker_mode,
            showtype    
        ]

        # 執行外部腳本並捕獲其輸出
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        # --- 修正: 安全地提取 GIF 檔案路徑 ---
        gif_relative_path = extract_gif_path(result.stdout)
        
        if not gif_relative_path:
             raise Exception("GIF 腳本執行成功，但無法從輸出中提取 GIF 路徑。")

        gif_url = f"/static/{gif_relative_path}" # 構建完整的 URL
        print(f"生成的 GIF URL: {gif_url}")

    except ValueError:
        return jsonify({"status": "error", "message": "'no' 參數必須是整數"}), 400
    except subprocess.CalledProcessError as e:
        print(f"呼叫 active_keyx105web.py 失敗，錯誤碼: {e.returncode}")
        error_message = f"GIF 生成失敗: {e.stderr.strip() if e.stderr else '未知錯誤'}"
        return jsonify({"status": "error", "message": error_message}), 500
    except FileNotFoundError as e:
        print(f"錯誤: {e}")
        return jsonify({"status": "error", "message": f"伺服器配置錯誤: {e}"}), 500
    except Exception as e:
        print(f"發生未知錯誤: {e}")
        return jsonify({"status": "error", "message": "伺服器內部錯誤"}), 500

    return jsonify({
        "status": "success",
        "message": "GIF 已生成",
        "gif_url": gif_url,
        "passwd": generated_password
    })

# --- 新增的 /setpasswd API 路由 (更新了輸出處理邏輯) ---
@app.route('/setpasswd', methods=['GET'])
def set_password_api():
    """
    新的 GET 請求 API 接口：/setpasswd
    接收 kk0..kk6 參數，手動設置 GIF 生成參數，並呼叫外部 Python 腳本。
    - kk0: array_mode
    - kk1: generated_password
    - kk2: interference_number
    - kk3: font_mode
    - kk4: background_mode
    - kk5: flicker_mode
    - kk6: showtype
    """
    # 獲取所有需要的參數
    params = {}
    param_keys = ['kk0', 'kk1', 'kk2', 'kk3', 'kk4', 'kk5',  'kk6']
    for key in param_keys:
        params[key] = request.args.get(key)
        if params[key] is None:
            return jsonify({"status": "error", "message": f"缺少必要參數: '{key}'"}), 400

    # 參數映射到腳本變數
    array_mode = params['kk0']
    generated_password = params['kk1']
    interference_number = params['kk2']
    font_mode = params['kk3']
    background_mode = params['kk4']
    flicker_mode = params['kk5']
    showtype = params['kk6']

    # 驗證密碼長度 (確保不是空字串)
    if not generated_password:
        return jsonify({"status": "error", "message": "密碼 (kk1) 不能為空"}), 400

    print(f"接收到 /setpasswd 請求:")
    print(f"  RC模式 (kk0): {array_mode}")
    print(f"  密碼 (kk1): {generated_password}")
    print(f"  干擾數 (kk2): {interference_number}")
    print(f"  字體模式 (kk3): {font_mode}")
    print(f"  背景模式 (kk4): {background_mode}")
    print(f"  閃動模式 (kk5): {flicker_mode}")
    print(f"  顯示模式 (kk6): {showtype}")

    try:
        # --- 檢查並清理 passwd_lib 目錄 ---
        cleanup_passwd_lib()
        # --- 清理邏輯結束 ---

        # 構建呼叫 active_keyx105web.py 的命令
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'static',
            'active_keyx105web.py'
        )
        
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"active_keyx105web.py 腳本未在預期路徑找到: {script_path}")

        command = [
            sys.executable,
            script_path,
            array_mode,
            generated_password,
            interference_number,
            font_mode,
            background_mode,
            flicker_mode,
            showtype
        ]

        # 執行外部腳本並捕獲其輸出
        # 設置 timeout 以防腳本執行時間過長
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30) 
        
        # --- 修正: 安全地提取 GIF 檔案路徑 ---
        gif_relative_path = extract_gif_path(result.stdout)
        
        if not gif_relative_path:
             # 如果 stdout 為空或無法提取路徑，拋出錯誤
             raise Exception("GIF 腳本執行成功，但無法從輸出中提取 GIF 路徑。")

        gif_url = f"/static/{gif_relative_path}" # 構建完整的 URL
        print(f"生成的 GIF URL: {gif_url}")

        return jsonify({
            "status": "success",
            "message": "GIF 已根據手動參數生成",
            "gif_url": gif_url,
            "passwd": generated_password
        })

    except subprocess.CalledProcessError as e:
        print(f"呼叫 active_keyx105web.py 失敗，錯誤碼: {e.returncode}", file=sys.stderr)
        print(f"標準輸出: {e.stdout}", file=sys.stderr)
        print(f"標準錯誤: {e.stderr}", file=sys.stderr)
        return jsonify({
            "status": "error",
            "message": f"GIF 生成失敗: {e.stderr.strip() if e.stderr else '未知錯誤'}"
        }), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            "status": "error",
            "message": "GIF 生成超時 (>30 秒)"
        }), 500
    except FileNotFoundError as e:
        print(f"錯誤: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": f"伺服器配置錯誤: {e}"}), 500
    except Exception as e:
        print(f"發生未知錯誤: {e}", file=sys.stderr)
        return jsonify({"status": "error", "message": "伺服器內部錯誤", "details": str(e)}), 500


# --- /savedata API (寫入 MySQL，含 modeltype 欄位) ---
@app.route('/savedata', methods=['GET', 'POST'])
def save_data_api():
    """
    API：/savedata (支援 GET 與 POST)
    將前端送來的測試結果寫入 MySQL userlog 表。
    參數：
      - age       : 操作者編碼 (1=user, 2=hermes)
      - no        : 題目索引 (對應 passwd_tab no)
      - passflag  : 通過旗標 (1=PASS, 0=FAIL)
      - timecount : 答題秒數
      - model     : 模型名稱 (對應 DB modeltype 欄位，可為空字串)
    """
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        age = payload.get('age')
        no = payload.get('no')
        passflag = payload.get('passflag')
        timecount = payload.get('timecount')
        model = payload.get('model', '') or ''
    else:
        age = request.args.get('age')
        no = request.args.get('no')
        passflag = request.args.get('passflag')
        timecount = request.args.get('timecount')
        model = request.args.get('model', '') or ''

    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', '192.168.5.11'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'handel'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'passwddb'),
    }

    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        sql = """
        INSERT INTO userlog (`date`, age, lev, runt_sec, passflag, modeltype)
        VALUES (NOW(), %s, %s, %s, %s, %s);
        """
        data_to_insert = (
            int(age) if age is not None else None,
            int(no) if no is not None else None,
            int(timecount) if timecount is not None else None,
            int(passflag) if passflag is not None else None,
            (model[:64] if model else None),
        )
        cursor.execute(sql, data_to_insert)
        conn.commit()

        executed_sql = (
            f"INSERT INTO userlog (`date`, age, lev, runt_sec, passflag, modeltype) "
            f"VALUES (NOW(), {data_to_insert[0]}, {data_to_insert[1]}, "
            f"{data_to_insert[2]}, {data_to_insert[3]}, '{data_to_insert[4]}');"
        )

        print(f"[savedata] SQL: {executed_sql}")

        return jsonify({
            "status": "success",
            "message": "資料已寫入 MySQL userlog",
            "sql": executed_sql,
            "data": {
                "age": age,
                "no": no,
                "passflag": passflag,
                "timecount": timecount,
                "modeltype": model,
            },
        })

    except mysql.connector.Error as err:
        print(f"資料庫操作錯誤: {err}", file=sys.stderr)
        return jsonify({"status": "error", "message": "資料庫儲存失敗", "details": str(err)}), 500
    except ValueError as err:
        print(f"參數類型轉換錯誤: {err}", file=sys.stderr)
        return jsonify({"status": "error", "message": "參數類型錯誤", "details": str(err)}), 400
    except Exception as err:
        print(f"發生未知錯誤: {err}", file=sys.stderr)
        return jsonify({"status": "error", "message": "伺服器內部錯誤", "details": str(err)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn and conn.is_connected():
            try: conn.close()
            except Exception: pass


# ===== DataSet 測試流程 =====
_DATASET_CACHE = None

def load_dataset():
    """讀取並解析 static/demo/dataset.json（JS 物件格式 dataset={...}），回傳 dict[path] -> list["index,filename,passwd"]"""
    global _DATASET_CACHE
    if _DATASET_CACHE is not None:
        return _DATASET_CACHE
    import json as _json
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "demo", "dataset.json")
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    # 去掉開頭 dataset= 與結尾，移除 JSON 不允許的尾端逗號
    raw = raw.strip()
    if raw.startswith("dataset"):
        raw = raw[raw.index("=") + 1:].strip()
    raw = re.sub(r",\s*([\]}])", r"\1", raw)  # 移除 trailing comma
    _DATASET_CACHE = _json.loads(raw)
    return _DATASET_CACHE


@app.route('/dataset')
def dataset_gui():
    """資料集測試 GUI 頁面"""
    return render_template('dataset_gui.html')


@app.route('/getdataset', methods=['GET'])
def get_dataset_api():
    """依 dataset path 與 lev(1..100) 回傳對應資料項 {gif_url, passwd}"""
    path = request.args.get('path')
    lev = request.args.get('lev')
    if not path or lev is None:
        return jsonify({"status": "error", "message": "缺少 path 或 lev 參數"}), 400
    try:
        lev_i = int(lev)
    except ValueError:
        return jsonify({"status": "error", "message": "lev 必須為整數"}), 400
    try:
        ds = load_dataset()
    except Exception as e:
        return jsonify({"status": "error", "message": f"dataset.json 載入失敗: {e}"}), 500
    items = ds.get(path)
    if items is None:
        return jsonify({"status": "error", "message": f"找不到 dataset path: {path}"}), 404
    if not (1 <= lev_i <= len(items)):
        return jsonify({"status": "error", "message": f"lev 超出範圍 (1..{len(items)})"}), 400
    # 每筆格式: "index,gif-filename,anspasswd"
    parts = [p.strip() for p in items[lev_i - 1].split(",")]
    if len(parts) < 3:
        return jsonify({"status": "error", "message": "資料項格式不正確"}), 500
    index, gif_filename, anspasswd = parts[0], parts[1], parts[2]
    gif_url = f"/static/demo/{path}/{gif_filename}"
    return jsonify({
        "status": "success",
        "message": " index,data path, load ok ",
        "index": index,
        "datasetpath": path,
        "gif_url": gif_url,
        "passwd": anspasswd
    })


@app.route('/savedataset', methods=['GET', 'POST'])
def save_dataset_api():
    """將資料集測試結果寫入 MySQL datasetlog 表（含 datasetpath 欄位）"""
    if request.method == 'POST':
        payload = request.get_json(silent=True) or {}
        age = payload.get('age')
        no = payload.get('no')
        passflag = payload.get('passflag')
        timecount = payload.get('timecount')
        model = payload.get('model', '') or ''
        datasetpath = payload.get('datasetpath', '') or ''
    else:
        age = request.args.get('age')
        no = request.args.get('no')
        passflag = request.args.get('passflag')
        timecount = request.args.get('timecount')
        model = request.args.get('model', '') or ''
        datasetpath = request.args.get('datasetpath', '') or ''
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', '192.168.5.11'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'user': os.environ.get('DB_USER', 'handel'),
        'password': os.environ.get('DB_PASSWORD', ''),
        'database': os.environ.get('DB_NAME', 'passwddb'),
    }
    conn = None; cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        sql = ("INSERT INTO datasetlog (`date`, age, lev, runt_sec, passflag, modeltype, datasetpath) "
               "VALUES (NOW(), %s, %s, %s, %s, %s, %s);")
        cursor.execute(sql, (
            int(age) if age else None,
            int(no) if no else None,
            int(timecount) if timecount else None,
            int(passflag) if passflag is not None else None,
            (model[:64] if model else None),
            (datasetpath[:64] if datasetpath else None),
        ))
        conn.commit()
        print(f"接收到 /savedataset: age={age}, no={no}, passflag={passflag}, "
              f"timecount={timecount}, modeltype={model!r}, datasetpath={datasetpath!r}")
        return jsonify({"status": "success", "message": "資料已寫入 datasetlog",
                        "data": {"age": age, "no": no, "passflag": passflag,
                                 "timecount": timecount, "modeltype": model, "datasetpath": datasetpath}})
    except mysql.connector.Error as err:
        print(f"資料庫操作錯誤: {err}", file=sys.stderr)
        return jsonify({"status": "error", "message": "資料庫儲存失敗", "details": str(err)}), 500
    except Exception as err:
        print(f"發生未知錯誤: {err}", file=sys.stderr)
        return jsonify({"status": "error", "message": "伺服器內部錯誤", "details": str(err)}), 500
    finally:
        if cursor:
            try: cursor.close()
            except Exception: pass
        if conn and conn.is_connected():
            try: conn.close()
            except Exception: pass


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
