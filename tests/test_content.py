"""内容管理相关测试"""
import json
import pytest
from datetime import datetime, timedelta
from app import save_content, get_content, delete_content, list_contents, get_db_connection


class TestContentCreation:
    """内容创建测试"""
    
    def test_create_content_success(self, logged_in_client):
        """测试成功创建内容"""
        response = logged_in_client.post('/create', data={
            'content': 'Hello World',
            'title': 'Test Title',
            'expire_hours': '24'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'short_id' in data
        assert 'share_url' in data
    
    def test_create_content_empty(self, logged_in_client):
        """测试创建空内容失败"""
        response = logged_in_client.post('/create', data={
            'content': '',
            'title': 'Test'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_content_without_login(self, client):
        """测试未登录无法创建内容"""
        response = client.post('/create', data={
            'content': 'Test',
            'title': 'Test'
        })
        
        assert response.status_code == 302  # 重定向到登录页


class TestContentView:
    """内容查看测试"""
    
    def test_view_content(self, client, logged_in_client):
        """测试查看内容"""
        # 先创建内容
        response = logged_in_client.post('/create', data={
            'content': 'View Test Content',
            'title': 'View Test',
            'expire_hours': '24'
        })
        data = json.loads(response.data)
        short_id = data['short_id']
        
        # 查看内容（无需登录）
        response = client.get(f'/s/{short_id}')
        assert response.status_code == 200
        assert 'View Test Content' in response.data.decode('utf-8')
    
    def test_view_nonexistent_content(self, client):
        """测试查看不存在的内容返回 404"""
        response = client.get('/s/nonexistent123')
        assert response.status_code == 404
    
    def test_view_expired_content(self, app, client):
        """测试查看过期内容返回 404"""
        # 直接插入一条过期记录
        conn = get_db_connection()
        c = conn.cursor()
        expired_time = datetime.now() - timedelta(hours=1)
        c.execute(
            'INSERT INTO contents (id, content, title, expires_at) VALUES (?, ?, ?, ?)',
            ('expired123', 'Expired content', 'Expired', expired_time.isoformat())
        )
        conn.commit()
        conn.close()
        
        # 访问过期内容
        response = client.get('/s/expired123')
        assert response.status_code == 404


class TestContentDelete:
    """内容删除测试"""
    
    def test_delete_content(self, logged_in_client):
        """测试删除内容"""
        # 先创建
        response = logged_in_client.post('/create', data={
            'content': 'Delete Test',
            'title': 'Delete',
            'expire_hours': '24'
        })
        data = json.loads(response.data)
        short_id = data['short_id']
        
        # 删除
        response = logged_in_client.post(f'/delete/{short_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # 确认已删除
        assert get_content(short_id) is None
    
    def test_delete_without_login(self, client):
        """测试未登录无法删除"""
        response = client.post('/delete/someid')
        assert response.status_code == 302


class TestContentList:
    """内容列表测试"""
    
    def test_list_contents(self, app, logged_in_client):
        """测试列出内容"""
        # 创建几条内容
        logged_in_client.post('/create', data={'content': 'Content 1', 'title': 'Title 1', 'expire_hours': '24'})
        logged_in_client.post('/create', data={'content': 'Content 2', 'title': 'Title 2', 'expire_hours': '24'})
        
        # 访问首页应该能看到列表
        response = logged_in_client.get('/')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'Title 1' in html
        assert 'Title 2' in html
