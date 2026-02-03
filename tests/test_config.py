"""配置管理相关测试"""
import json
import pytest
import os
import yaml
from app import config, CONFIG_PATH


class TestConfigGet:
    """获取配置测试"""
    
    def test_get_config(self, logged_in_client):
        """测试获取当前配置"""
        response = logged_in_client.get('/config')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'server' in data
        assert 'auth' in data
        assert 'content' in data
    
    def test_get_config_without_login(self, client):
        """测试未登录无法获取配置"""
        response = client.get('/config')
        assert response.status_code == 302


class TestConfigUpdate:
    """更新配置测试"""
    
    def test_update_password(self, logged_in_client):
        """测试更新密码"""
        original_password = config['auth']['password']
        
        try:
            response = logged_in_client.post('/config',
                data=json.dumps({'auth': {'password': 'newpassword123'}}),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # 验证密码已更新
            assert config['auth']['password'] == 'newpassword123'
        finally:
            # 恢复原密码
            config['auth']['password'] = original_password
            with open(CONFIG_PATH, 'r') as f:
                file_config = yaml.safe_load(f)
            file_config['auth']['password'] = original_password
            with open(CONFIG_PATH, 'w') as f:
                yaml.dump(file_config, f)
    
    def test_update_default_expire(self, logged_in_client):
        """测试更新默认过期时间"""
        response = logged_in_client.post('/config',
            data=json.dumps({'content': {'default_expire_hours': 48}}),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # 验证配置文件已更新
        with open(CONFIG_PATH, 'r') as f:
            file_config = yaml.safe_load(f)
        assert file_config['content']['default_expire_hours'] == 48
        
        # 恢复原配置
        file_config['content']['default_expire_hours'] = 24
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(file_config, f)
    
    def test_update_invalid_port(self, logged_in_client):
        """测试无效端口值被拒绝"""
        response = logged_in_client.post('/config',
            data=json.dumps({'server': {'port': 'invalid'}}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_update_config_without_login(self, client):
        """测试未登录无法更新配置"""
        response = client.post('/config',
            data=json.dumps({'auth': {'password': 'hacked'}}),
            content_type='application/json'
        )
        assert response.status_code == 302
