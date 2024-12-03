import sys
import re
import os
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup as bs
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from pyfiglet import Figlet
import random
import json

class FacebookShareTool:
    def __init__(self):
        self.console = Console()
        self.session = requests.Session()
        self.success_counter = 0
        self.failed_counter = 0
        self.lock = threading.Lock()
        self.user_agents = self.load_user_agents()
        self.proxies = self.load_proxies()
        
    def load_user_agents(self):
        user_agents = [
            'Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/80.0.3987.119 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 10; SM-G996U Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 10; SM-G980F Build/QP1A.190711.020; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/78.0.3904.96 Mobile Safari/537.36'
        ]
        return user_agents

    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []

    def print_banner(self):
        f = Figlet(font='slant')
        banner = f.renderText('FB Auto Share')
        self.console.print(Panel(
            Text(banner, style="bold cyan") + "\n" +
            Text("Created by Yuri Evisu", style="bold yellow") + "\n" +
            Text("Version 2.1.0", style="bold green"),
            border_style="cyan"
        ))

    def get_random_proxy(self):
        return {'http': random.choice(self.proxies)} if self.proxies else None

    def save_session(self, cookie, token):
        session_data = {
            'cookie': cookie,
            'token': token,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open('.session', 'w') as f:
            json.dump(session_data, f)

    def load_session(self):
        try:
            with open('.session', 'r') as f:
                return json.load(f)
        except:
            return None

    async def get_cookie(self, email, password):
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("[cyan]Logging in...", total=100)
            
            try:
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                }
                
                progress.update(task, advance=30)
                self.session.headers.update(headers)
                
                response = self.session.get('https://m.facebook.com', proxies=self.get_random_proxy())
                progress.update(task, advance=20)
                
                soup = bs(response.text, 'html.parser')
                data = {
                    'email': email,
                    'pass': password,
                    'login': 'Log In'
                }
                
                for input_tag in soup.find_all('input', {'type': ['hidden', 'submit']}):
                    if input_tag.get('value') and input_tag.get('name'):
                        data[input_tag['name']] = input_tag['value']
                
                progress.update(task, advance=25)
                response = self.session.post(
                    'https://m.facebook.com/login',
                    data=data,
                    allow_redirects=True,
                    proxies=self.get_random_proxy()
                )
                
                progress.update(task, advance=25)
                cookie = "; ".join([f"{k}={v}" for k, v in self.session.cookies.items()])
                
                return cookie if 'c_user' in cookie else None
                
            except Exception as e:
                self.console.print(f"[bold red]Error during login: {str(e)}")
                return None

    async def share_post(self, token_data, post_id, delay):
        cookie, token = token_data.split('|')
        headers = {
            'Cookie': cookie,
            'User-Agent': random.choice(self.user_agents)
        }
        
        try:
            await asyncio.sleep(delay)
            response = await self.session.post(
                'https://graph.facebook.com/me/feed',
                params={
                    'link': f'https://m.facebook.com/{post_id}',
                    'published': '0',
                    'access_token': token
                },
                headers=headers,
                proxies=self.get_random_proxy()
            )
            
            result = response.json()
            
            with self.lock:
                if 'id' in result:
                    self.success_counter += 1
                    self.console.print(f"[{datetime.now().strftime('%H:%M:%S')}] [bold green]Share successful ({self.success_counter})")
                else:
                    self.failed_counter += 1
                    self.console.print(f"[{datetime.now().strftime('%H:%M:%S')}] [bold red]Share failed ({self.failed_counter})")
                    
        except Exception as e:
            with self.lock:
                self.failed_counter += 1
                self.console.print(f"[bold red]Error sharing: {str(e)}")

    async def main(self):
        try:
            os.system('clear' if 'linux' in sys.platform.lower() else 'cls')
            self.print_banner()
            
            session_data = self.load_session()
            if session_data:
                use_session = self.console.input("[bold yellow]Found existing session. Use it? (y/n): ").lower() == 'y'
                if use_session:
                    cookie, token = session_data['cookie'], session_data['token']
                else:
                    session_data = None
            
            if not session_data:
                email = self.console.input("[bold blue]Enter your Gmail: ")
                password = self.console.input("[bold blue]Enter your password: ", password=True)
                
                cookie = await self.get_cookie(email, password)
                if not cookie:
                    self.console.print("[bold red]Login failed!")
                    return
                
                self.console.print("[bold green]Login successful!")
                token = await self.get_token(cookie)
                if not token:
                    self.console.print("[bold red]Failed to get access token!")
                    return
                
                self.save_session(cookie, token)
            
            shares = int(self.console.input("[bold blue]Number of shares: "))
            delay = float(self.console.input("[bold blue]Delay between shares (seconds): "))
            post_url = self.console.input("[bold blue]Post URL: ")
            
            post_id = re.search(r"pfbid(\w+)", post_url)
            if not post_id:
                self.console.print("[bold red]Invalid post URL!")
                return
            
            self.console.print("[bold yellow]Starting share process...")
            
            tasks = []
            token_data = f"{cookie}|{token}"
            
            async with asyncio.TaskGroup() as tg:
                for _ in range(shares):
                    tasks.append(tg.create_task(
                        self.share_post(token_data, post_id.group(0), delay)
                    ))
            
            self.console.print(Panel(
                Text.assemble(
                    ("Share process completed!\n", "bold green"),
                    (f"Successful shares: {self.success_counter}\n", "bold blue"),
                    (f"Failed shares: {self.failed_counter}", "bold red")
                )
            ))
            
        except Exception as e:
            self.console.print(f"[bold red]An error occurred: {str(e)}")

if __name__ == "__main__":
    import asyncio
    tool = FacebookShareTool()
    asyncio.run(tool.main())
