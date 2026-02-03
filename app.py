#!/usr/bin/env python3
"""
Content Share WebUI - 内容分享工具
一个自托管的内容分享 WebUI，支持创建文本内容、生成分享链接、配置热加载和历史管理
"""

import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps

import yaml
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, Response

# =============================================================================
# 配置加载
# =============================================================================

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

def load_config():
    """加载配置文件"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_config(new_config):
    """保存配置文件"""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        yaml.dump(new_config, f, default_flow_style=False, allow_unicode=True)

config = load_config()

def reload_config():
    """热加载配置"""
    global config
    config = load_config()
    app.secret_key = config['server']['secret_key']

# =============================================================================
# Flask 应用初始化
# =============================================================================

app = Flask(__name__)
app.secret_key = config['server']['secret_key']

# =============================================================================
# 数据库操作
# =============================================================================

def get_db_path():
    """获取数据库路径"""
    db_path = config['database']['path']
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
    return db_path

def get_db_connection():
    """获取数据库连接"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS contents (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            title TEXT,
            render_mode TEXT DEFAULT 'raw'
        )
    ''')
    # 迁移：添加 render_mode 列（如果不存在）
    try:
        c.execute('ALTER TABLE contents ADD COLUMN render_mode TEXT DEFAULT "raw"')
    except sqlite3.OperationalError:
        pass  # 列已存在
    conn.commit()
    conn.close()

def generate_short_id():
    """生成 8 位随机短 ID"""
    return secrets.token_urlsafe(6)  # 生成 8 个 URL 安全字符

def is_expired(expires_at):
    """检查是否过期"""
    if expires_at is None:
        return False
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    return datetime.now() > expires_at

def save_content(content, title, expire_hours, custom_id=None, render_mode='raw'):
    """保存内容到数据库"""
    short_id = custom_id if custom_id else generate_short_id()
    expires_at = None
    if expire_hours and expire_hours > 0:
        expires_at = datetime.now() + timedelta(hours=expire_hours)
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # 检查自定义 ID 是否已存在
    if custom_id:
        c.execute('SELECT id FROM contents WHERE id = ?', (custom_id,))
        if c.fetchone():
            conn.close()
            return None  # ID 已存在
    
    c.execute(
        'INSERT INTO contents (id, content, title, expires_at, render_mode) VALUES (?, ?, ?, ?, ?)',
        (short_id, content, title, expires_at, render_mode)
    )
    conn.commit()
    conn.close()
    return short_id

def get_content(short_id):
    """获取内容（检查过期）"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM contents WHERE id = ?', (short_id,))
    row = c.fetchone()
    conn.close()
    
    if row is None:
        return None
    
    content_dict = dict(row)
    if is_expired(content_dict.get('expires_at')):
        # 过期则删除并返回 None
        delete_content(short_id)
        return None
    
    return content_dict

def delete_content(short_id):
    """删除内容"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM contents WHERE id = ?', (short_id,))
    conn.commit()
    conn.close()

def list_contents():
    """列出所有内容"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM contents ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    # 过滤掉过期内容
    result = []
    for row in rows:
        content_dict = dict(row)
        if not is_expired(content_dict.get('expires_at')):
            result.append(content_dict)
    
    return result

# =============================================================================
# 认证装饰器
# =============================================================================

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# 路由
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == config['auth']['password']:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error='密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """登出"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """管理主页"""
    contents = list_contents()
    return render_template('index.html', 
                         contents=contents, 
                         config=config,
                         default_expire_hours=config['content']['default_expire_hours'])

@app.route('/create', methods=['POST'])
@login_required
def create():
    """创建内容"""
    content = request.form.get('content', '')
    title = request.form.get('title', '')
    custom_id = request.form.get('custom_id', '').strip()
    render_mode = request.form.get('render_mode', 'raw')
    expire_hours = request.form.get('expire_hours', config['content']['default_expire_hours'])
    
    try:
        expire_hours = int(expire_hours)
    except (ValueError, TypeError):
        expire_hours = config['content']['default_expire_hours']
    
    # 检查内容大小
    max_size = config['content']['max_content_size']
    if len(content.encode('utf-8')) > max_size:
        return jsonify({'error': f'内容超过最大限制 ({max_size} bytes)'}), 400
    
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    
    # 验证自定义 ID
    if custom_id:
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', custom_id):
            return jsonify({'error': '自定义链接只能包含字母、数字、下划线和连字符'}), 400
        if len(custom_id) < 2 or len(custom_id) > 50:
            return jsonify({'error': '自定义链接长度需要在 2-50 个字符之间'}), 400
    
    # 验证 render_mode
    if render_mode not in ('raw', 'html'):
        render_mode = 'raw'
    
    short_id = save_content(content, title, expire_hours, custom_id or None, render_mode)
    
    if short_id is None:
        return jsonify({'error': f'自定义链接 "{custom_id}" 已被使用'}), 400
    
    share_url = url_for('view', short_id=short_id, _external=True)
    
    return jsonify({
        'success': True,
        'short_id': short_id,
        'share_url': share_url
    })

@app.route('/s/<short_id>')
def view(short_id):
    """公开访问内容"""
    content = get_content(short_id)
    if content is None:
        abort(404)
    
    render_mode = content.get('render_mode', 'raw')
    if render_mode == 'html':
        return render_template('view.html', content=content)
    else:
        return Response(content['content'], mimetype='text/plain; charset=utf-8')

@app.route('/delete/<short_id>', methods=['POST'])
@login_required
def delete(short_id):
    """删除内容"""
    delete_content(short_id)
    return jsonify({'success': True})

@app.route('/config', methods=['GET', 'POST'])
@login_required
def config_page():
    """配置管理"""
    if request.method == 'GET':
        # 返回当前配置（隐藏敏感信息用于显示）
        safe_config = {
            'server': {
                'host': config['server']['host'],
                'port': config['server']['port'],
                'debug': config['server']['debug']
            },
            'auth': {
                'password': config['auth']['password']
            },
            'content': config['content'].copy(),
            'database': config['database'].copy()
        }
        return jsonify(safe_config)
    
    # POST: 更新配置
    try:
        new_values = request.get_json()
        if not new_values:
            return jsonify({'error': '无效的 JSON 数据'}), 400
        
        # 验证配置
        updated_config = config.copy()
        
        # 深度合并配置
        for section, values in new_values.items():
            if section not in updated_config:
                continue
            if isinstance(values, dict):
                for key, value in values.items():
                    if key in updated_config[section]:
                        # 验证类型
                        original_type = type(updated_config[section][key])
                        if original_type == int:
                            try:
                                value = int(value)
                            except (ValueError, TypeError):
                                return jsonify({'error': f'{section}.{key} 必须是整数'}), 400
                        elif original_type == bool:
                            if isinstance(value, str):
                                value = value.lower() in ('true', '1', 'yes')
                            else:
                                value = bool(value)
                        updated_config[section][key] = value
        
        # 保存配置
        save_config(updated_config)
        reload_config()
        
        # 检查是否需要重启
        restart_needed = False
        if new_values.get('server', {}).get('port') or new_values.get('server', {}).get('host'):
            restart_needed = True
        
        return jsonify({
            'success': True,
            'message': '配置已更新' + (' (端口/主机更改需要重启服务)' if restart_needed else '')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# =============================================================================
# 入口
# =============================================================================

# 确保数据库初始化
init_db()

if __name__ == '__main__':
    app.run(
        host=config['server']['host'],
        port=config['server']['port'],
        debug=config['server']['debug']
    )
