#!/usr/bin/env python3
# proxy_manager.py
import os
import re
import json
import base64
import subprocess
import requests
import concurrent.futures
import time
import socket
from datetime import datetime
from pathlib import Path

class ProxyManager:
    def __init__(self):
        self.sources = [
            'https://raw.githubusercontent.com/AvenCores/goida-vpn-configs/refs/heads/main/githubmirror/26.txt',
            'https://raw.githubusercontent.com/ShatakVPN/ConfigForge-V2Ray/refs/heads/main/configs/vless.txt',
            'https://raw.githubusercontent.com/Hidashimora/free-vpn-anti-rkn/main/configs/26.1.txt',
            'https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt'
        ]
        self.proxies = []
        self.working_servers = []
        self.output_path = Path('Githubmirror/Sub/BlankedVPN/sub.txt')
        
    def fetch_all_sources(self):
        """Загрузка конфигураций из всех источников"""
        print("📥 Fetching configs from sources...")
        
        for idx, source in enumerate(self.sources, 1):
            try:
                print(f"Fetching source {idx}/{len(self.sources)}")
                response = requests.get(source, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    self.parse_configs(response.text, source)
                    print(f"✅ Source {idx} loaded")
                else:
                    print(f"❌ Source {idx} status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Source {idx} error: {str(e)}")
                
    def parse_configs(self, content, source):
        """Парсинг конфигураций"""
        # Пробуем base64
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            lines = decoded.split('\n')
        except:
            lines = content.split('\n')
            
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if 'vless://' in line:
                # Найти все vless ссылки в строке
                urls = re.findall(r'vless://[^\s<>]+', line)
                for url in urls:
                    proxy = self.parse_vless(url)
                    if proxy:
                        proxy['source'] = source
                        self.proxies.append(proxy)
                        
    def parse_vless(self, url):
        """Парсинг VLESS"""
        try:
            clean_url = url.replace('vless://', '').strip()
            if '@' not in clean_url:
                return None
                
            uuid = clean_url.split('@')[0]
            after_at = clean_url.split('@')[1]
            
            if '?' not in after_at:
                return None
                
            ip_port = after_at.split('?')[0]
            if ':' not in ip_port:
                return None
                
            ip, port = ip_port.rsplit(':', 1)
            
            # Валидация
            if not self.is_valid_ip(ip):
                return None
                
            try:
                port = int(port)
                if port < 1 or port > 65535:
                    return None
            except:
                return None
                
            # Параметры и имя
            query_part = after_at.split('?')[1]
            name = ""
            if '#' in query_part:
                query_string, name = query_part.split('#', 1)
            else:
                query_string = query_part
                
            params = {}
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
                    
            return {
                'type': 'vless',
                'uuid': uuid,
                'ip': ip,
                'port': port,
                'params': params,
                'name': name,
                'url': url,
                'security': params.get('security', ''),
                'sni': params.get('sni', ''),
                'fp': params.get('fp', ''),
                'pbk': params.get('pbk', ''),
                'sid': params.get('sid', ''),
                'flow': params.get('flow', ''),
                'network': params.get('type', 'tcp'),
                'path': params.get('path', ''),
                'host': params.get('host', ''),
                'alpn': params.get('alpn', '')
            }
        except Exception as e:
            return None
            
    def is_valid_ip(self, ip):
        """Проверка IP"""
        try:
            socket.inet_pton(socket.AF_INET, ip)
            return True
        except:
            try:
                socket.inet_pton(socket.AF_INET6, ip)
                return True
            except:
                return False
                
    def get_country_from_ip(self, ip):
        """Определение страны по IP"""
        try:
            # Используем ip-api.com для определения страны
            response = requests.get(f'http://ip-api.com/json/{ip}?fields=country,countryCode', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country_code = data.get('countryCode', 'UN')
                    country_name = data.get('country', 'Unknown')
                    flag = self.get_country_flag(country_code)
                    return {
                        'code': country_code,
                        'name': country_name,
                        'flag': flag
                    }
        except:
            pass
            
        return {
            'code': 'UN',
            'name': 'Unknown',
            'flag': '🏳️'
        }
        
    def get_country_flag(self, country_code):
        """Получение флага"""
        if not country_code or len(country_code) != 2:
            return '🏳️'
        return chr(127397 + ord(country_code[0])) + chr(127397 + ord(country_code[1]))
        
    def test_proxy(self, proxy):
        """Тестирование прокси на доступность сервисов"""
        try:
            # Создаем временный конфиг для xray
            config = self.create_xray_config(proxy)
            
            # Сохраняем конфиг
            temp_config = f'/tmp/xray_test_{proxy["ip"]}_{proxy["port"]}.json'
            with open(temp_config, 'w') as f:
                json.dump(config, f)
                
            # Запускаем xray
            xray_proc = subprocess.Popen(
                ['xray', 'run', '-config', temp_config],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(2)  # Ждем запуска
            
            # Тестируем сервисы
            services = {
                'YouTube': 'https://www.youtube.com',
                'Telegram': 'https://t.me',
                'Instagram': 'https://www.instagram.com'
            }
            
            success_count = 0
            for service, url in services.items():
                try:
                    result = subprocess.run(
                        ['curl', '--socks5', '127.0.0.1:10808', '--max-time', '5', '-I', url],
                        capture_output=True,
                        timeout=7
                    )
                    if result.returncode == 0:
                        success_count += 1
                except:
                    pass
                    
            # Останавливаем xray
            xray_proc.terminate()
            xray_proc.wait(timeout=5)
            
            # Удаляем временный файл
            if os.path.exists(temp_config):
                os.remove(temp_config)
                
            # Считаем прокси рабочим если доступны минимум 2 из 3 сервисов
            return success_count >= 2
            
        except Exception as e:
            return False
            
    def create_xray_config(self, proxy):
        """Создание конфигурации xray"""
        stream_settings = {
            "network": proxy.get('network', 'tcp'),
            "security": proxy.get('security', 'none')
        }
        
        # Добавляем настройки для reality
        if proxy.get('security') == 'reality':
            stream_settings["realitySettings"] = {
                "serverName": proxy.get('sni', ''),
                "fingerprint": proxy.get('fp', 'chrome'),
                "publicKey": proxy.get('pbk', ''),
                "shortId": proxy.get('sid', '')
            }
        # Добавляем настройки для tls
        elif proxy.get('security') == 'tls':
            stream_settings["tlsSettings"] = {
                "serverName": proxy.get('sni', ''),
                "allowInsecure": True
            }
        # Добавляем настройки для ws
        if proxy.get('network') == 'ws':
            stream_settings["wsSettings"] = {
                "path": proxy.get('path', '/'),
                "headers": {
                    "Host": proxy.get('host', '')
                }
            }
            
        config = {
            "log": {"loglevel": "none"},
            "inbounds": [{
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True}
            }],
            "outbounds": [{
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": proxy['ip'],
                        "port": proxy['port'],
                        "users": [{
                            "id": proxy['uuid'],
                            "encryption": "none",
                            "flow": proxy.get('flow', '')
                        }]
                    }]
                },
                "streamSettings": stream_settings
            }]
        }
        return config
        
    def check_all_proxies(self):
        """Проверка всех прокси"""
        print(f"🔍 Checking {len(self.proxies)} proxies...")
        
        # Удаляем дубликаты
        unique_proxies = {}
        for proxy in self.proxies:
            key = f"{proxy['ip']}:{proxy['port']}"
            if key not in unique_proxies:
                unique_proxies[key] = proxy
                
        self.proxies = list(unique_proxies.values())
        print(f"Unique proxies: {len(self.proxies)}")
        
        # Проверяем параллельно
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {
                executor.submit(self.test_proxy, proxy): proxy 
                for proxy in self.proxies[:50]  # Проверяем только первые 50 для скорости
            }
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    if future.result():
                        # Получаем информацию о стране
                        country_info = self.get_country_from_ip(proxy['ip'])
                        proxy.update(country_info)
                        self.working_servers.append(proxy)
                        print(f"✅ {proxy['ip']} - {country_info['flag']} {country_info['name']}")
                except:
                    pass
                    
        # Сортируем по стране
        self.working_servers.sort(key=lambda x: x.get('name', ''))
        
        # Оставляем топ 15
        self.working_servers = self.working_servers[:15]
        
        print(f"✅ Working servers: {len(self.working_servers)}")
        
    def generate_subscription(self):
        """Генерация подписки"""
        content = []
        
        for server in self.working_servers:
            # Формируем тег
            tag = f"{server.get('flag', '🏳️')} {server.get('name', 'Unknown')} | {server['ip']}"
            
            # Формируем URL
            params = []
            if server.get('security'):
                params.append(f"security={server['security']}")
            if server.get('sni'):
                params.append(f"sni={server['sni']}")
            if server.get('fp'):
                params.append(f"fp={server['fp']}")
            if server.get('pbk'):
                params.append(f"pbk={server['pbk']}")
            if server.get('sid'):
                params.append(f"sid={server['sid']}")
            if server.get('network'):
                params.append(f"type={server['network']}")
            if server.get('flow'):
                params.append(f"flow={server['flow']}")
                
            param_str = '&'.join(params)
            url = f"vless://{server['uuid']}@{server['ip']}:{server['port']}?{param_str}#{tag}"
            content.append(url)
            
        # Конвертируем в base64
        subscription = base64.b64encode('\n'.join(content).encode('utf-8')).decode('utf-8')
        return subscription
        
    def save_subscription(self):
        """Сохранение подписки"""
        # Создаем директории
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Генерируем контент
        subscription = self.generate_subscription()
        
        # Сохраняем
        with open(self.output_path, 'w') as f:
            f.write(subscription)
            
        # Также сохраняем декодированную версию
        decoded_path = self.output_path.with_suffix('.decoded.txt')
        with open(decoded_path, 'w') as f:
            decoded = base64.b64decode(subscription).decode('utf-8')
            f.write(decoded)
            
        # Сохраняем информацию о серверах
        info_path = self.output_path.parent / 'servers_info.json'
        with open(info_path, 'w') as f:
            json.dump({
                'last_update': datetime.now().isoformat(),
                'total_servers': len(self.working_servers),
                'servers': self.working_servers
            }, f, indent=2)
            
        print(f"💾 Saved to {self.output_path}")
        print(f"📊 Total servers: {len(self.working_servers)}")
        
    def run(self):
        """Запуск полного цикла"""
        print("🚀 Starting proxy update...")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Загружаем конфигурации
        self.fetch_all_sources()
        
        # 2. Проверяем прокси
        self.check_all_proxies()
        
        # 3. Сохраняем результат
        self.save_subscription()
        
        print("✅ Update completed!")

if __name__ == '__main__':
    manager = ProxyManager()
    manager.run()
