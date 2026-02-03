"""pytest 配置和 fixtures"""
import os
import sys
import tempfile
import pytest

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app, init_db, config

@pytest.fixture
def app():
    """创建测试应用实例"""
    # 使用临时数据库
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    # 临时修改数据库路径
    original_db_path = config['database']['path']
    config['database']['path'] = db_path
    
    # 初始化数据库
    init_db()
    
    yield flask_app
    
    # 清理
    config['database']['path'] = original_db_path
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()

@pytest.fixture
def logged_in_client(app):
    """创建已登录的测试客户端"""
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
        yield client
