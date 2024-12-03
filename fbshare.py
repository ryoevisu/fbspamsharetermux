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
from rich.prompt import Prompt
from rich.table import Table
from pyfiglet import Figlet
import random
import json
import getpass
import platform

class FacebookShareTool:
    def __init__(self):
        self.console = Console()
        self.session = requests.Session()
        self.success_counter = 0
        self.failed_counter = 0
        self.lock = threading.Lock()
        self.user_agents = self.load_user_agents()
        self.proxies = self.load_proxies()
        self.version = "2.2.0"
        
    def load_user_agents(self):
        return [
            'Mozilla/5.0 (Linux; Android 12; SM-S906N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 11; SM-G996U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Mobile Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1'
        ]

    def load_proxies(self):
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []

    def check_for_updates(self):
        try:
            response = requests.get("https://api.github.com/repos/yurievisu/fbspamsharetermux/releases/latest")
            latest_version = response.json()["tag_name"]
            if latest_version > self.version:
                self.console.print(f"[yellow]New version {latest_version} available! Current version: {self.version}")
        except:
            pass

    def print_system_info(self):
        table = Table(title="System Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("OS", platform.system())
        table.add_row("Python Version", platform.python_version())
        table.add_row("Tool Version", self.version)
        table.add_row("Proxies Loaded", str(len(self.proxies)))
        
        self.console.print(table)

    def print_banner(self):
        f = Figlet(font='slant')
        banner = f.renderText('FB Auto Share')
        self.console.print(Panel(
            Text(banner, style="bold cyan") + "\n" +
            Text("Created by Yuri Evisu", style="bold yellow") + "\n" +
            Text(f"Version {self.version}", style="bold green") + "\n" +
            Text("Telegram: @yurievisu", style="bold blue"),
            border_style="cyan"
        ))

    def print_menu(self):
        menu = Table(show_header=True, header_style="bold magenta")
        menu.add_column("Option", style="cyan")
        menu.add_column("Description", style="green")
        
        menu.add_row("1", "Start Auto Share")
        menu.add_row("2", "Load Session")
        menu.add_row("3", "System Info")
        menu.add_row("4", "Check Updates")
        menu.add_row("5", "Exit")
        
        self.console.print(menu)

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

    def get_cookie(self, email, password):
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

    def get_token(self, cookie):
        try:
            headers = {
                'Cookie': cookie,
                'User-Agent': random.choice(self.user_agents)
            }
            response = self.session.get(
                'https://business.facebook.com/business_locations',
                headers=headers,
                proxies=self.get_random_proxy()
            )
            token = re.search(r'EAAG\w+', response.text)
            return token.group(0) if token else None
        except Exception as e:
            self.console.print(f"[bold red]Error getting token: {str(e)}")
            return None

    def share_post(self, token_data, post_id, delay):
        cookie, token = token_data.split('|')
        headers = {
            'Cookie': cookie,
            'User-Agent': random.choice(self.user_agents)
        }
        
        try:
            time.sleep(delay)
            response = self.session.post(
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

    def start_sharing(self):
        try:
            session_data = self.load_session()
            if session_data:
                use_session = Prompt.ask("[bold yellow]Found existing session. Use it?", choices=["y", "n"], default="y")
                if use_session == "y":
                    cookie, token = session_data['cookie'], session_data['token']
                else:
                    session_data = None
            
            if not session_data:
                email = Prompt.ask("[bold blue]Enter your Facebook email")
                password = getpass.getpass("Enter your Facebook password: ")
                
                cookie = self.get_cookie(email, password)
                if not cookie:
                    self.console.print("[bold red]Login failed!")
                    return
                
                self.console.print("[bold green]Login successful!")
                token = self.get_token(cookie)
                if not token:
                    self.console.print("[bold red]Failed to get access token!")
                    return
                
                self.save_session(cookie, token)
            
            shares = int(Prompt.ask("[bold blue]Number of shares", default="10"))
            delay = float(Prompt.ask("[bold blue]Delay between shares (seconds)", default="2.0"))
            post_url = Prompt.ask("[bold blue]Post URL")
            
            post_id = re.search(r"pfbid(\w+)", post_url)
            if not post_id:
                self.console.print("[bold red]Invalid post URL!")
                return
            
            self.console.print("[bold yellow]Starting share process...")
            
            token_data = f"{cookie}|{token}"
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(self.share_post, token_data, post_id.group(0), delay)
                    for _ in range(shares)
                ]
                
                for future in futures:
                    future.result()
            
            self.console.print(Panel(
                Text.assemble(
                    ("Share process completed!\n", "bold green"),
                    (f"Successful shares: {self.success_counter}\n", "bold blue"),
                    (f"Failed shares: {self.failed_counter}", "bold red")
                )
            ))
            
        except Exception as e:
            self.console.print(f"[bold red]An error occurred: {str(e)}")

    def main(self):
        while True:
            try:
                os.system('clear' if 'linux' in sys.platform.lower() else 'cls')
                self.print_banner()
                self.print_menu()
                
                choice = Prompt.ask("[bold cyan]Select option", choices=["1", "2", "3", "4", "5"])
                
                if choice == "1":
                    self.start_sharing()
                elif choice == "2":
                    session_data = self.load_session()
                    if session_data:
                        self.console.print(Panel(
                            Text.assemble(
                                ("Session Information\n", "bold green"),
                                (f"Timestamp: {session_data['timestamp']}\n", "bold yellow")
                            )
                        ))
                    else:
                        self.console.print("[bold red]No saved session found!")
                elif choice == "3":
                    self.print_system_info()
                elif choice == "4":
                    self.check_for_updates()
                elif choice == "5":
                    self.console.print("[bold green]Thanks for using FB Auto Share!")
                    break
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                self.console.print("\n[bold yellow]Exiting...")
                break
            except Exception as e:
                self.console.print(f"[bold red]An error occurred: {str(e)}")
                input("\nPress Enter to continue...")

if __name__ == "__main__":
    tool = FacebookShareTool()
    tool.main()
