"""认证相关测试"""
import pytest
from app import config


class TestLogin:
    """登录功能测试"""
    
    def test_login_page_renders(self, client):
        """测试登录页面可以正常渲染"""
        response = client.get('/login')
        assert response.status_code == 200
        assert '密码' in response.data.decode('utf-8') or 'password' in response.data.decode('utf-8').lower()
    
    def test_login_with_correct_password(self, client):
        """测试正确密码登录成功"""
        response = client.post('/login', data={'password': config['auth']['password']}, follow_redirects=True)
        assert response.status_code == 200
        # 登录成功后应该重定向到首页
        assert '创建' in response.data.decode('utf-8') or '内容' in response.data.decode('utf-8')
    
    def test_login_with_wrong_password(self, client):
        """测试错误密码登录失败"""
        response = client.post('/login', data={'password': 'wrongpassword'})
        assert response.status_code == 200
        assert '错误' in response.data.decode('utf-8') or 'error' in response.data.decode('utf-8').lower()
    
    def test_login_required_redirect(self, client):
        """测试未登录访问保护路由重定向到登录页"""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location


class TestLogout:
    """登出功能测试"""
    
    def test_logout(self, logged_in_client):
        """测试登出功能"""
        # 确认已登录
        response = logged_in_client.get('/')
        assert response.status_code == 200
        
        # 登出
        response = logged_in_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        # 确认已登出
        response = logged_in_client.get('/')
        assert response.status_code == 302
