import requests
import json
import time
import os
import re
from concurrent.futures import ThreadPoolExecutor

class FacebookAutoShare:
    def __init__(self):
        self.sessions_dir = "fb_sessions"
        self.total = {}
        self.fb_url_pattern = re.compile(r'^https:\/\/(?:www\.)?facebook\.com\/(?:(?:\w+\/)*\d+\/posts\/\d+\/?\??(?:app=fbl)?|share\/(?:p\/)?[a-zA-Z0-9]+\/?)')
        
        # Create sessions directory
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.load_sessions()

    def load_sessions(self):
        try:
            for file in os.listdir(self.sessions_dir):
                with open(os.path.join(self.sessions_dir, file), 'r') as f:
                    session_data = json.load(f)
                    self.total[session_data['id']] = session_data
        except Exception as e:
            print(f"Error loading sessions: {str(e)}")

    async def get_post_id(self, url):
        try:
            response = requests.post(
                'https://id.traodoisub.com/api.php',
                data={'link': url},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            return response.json().get('id')
        except:
            return None

    async def get_access_token(self, cookie):
        try:
            headers = {
                'authority': 'business.facebook.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'cookie': cookie,
                'referer': 'https://www.facebook.com/'
            }
            
            response = requests.get('https://business.facebook.com/content_management', headers=headers)
            token_match = re.search(r'"accessToken":\s*"([^"]+)"', response.text)
            
            return token_match.group(1) if token_match else None
        except:
            return None

    def convert_cookie(self, cookie_str):
        try:
            cookies = json.loads(cookie_str)
            sb_cookie = next((c for c in cookies if c['key'] == 'sb'), None)
            
            if not sb_cookie:
                raise ValueError('Invalid appstate: missing sb cookie.')
                
            formatted_cookies = f"sb={sb_cookie['value']}; " + '; '.join(
                f"{c['key']}={c['value']}" for c in cookies[1:]
            )
            return formatted_cookies
        except Exception as e:
            raise ValueError(f'Error processing appstate: {str(e)}')

    async def share_post(self, cookies, url, amount, interval):
        post_id = await self.get_post_id(url)
        if not post_id:
            raise ValueError("Unable to get post ID: invalid URL, or post is private or friends-only.")

        access_token = await self.get_access_token(cookies)
        if not access_token:
            raise ValueError("Failed to get access token")

        session_id = post_id if post_id not in self.total else post_id + 1
        session_data = {'url': url, 'id': post_id, 'count': 0, 'target': amount}
        
        session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
        with open(session_file, 'w') as f:
            json.dump(session_data, f)
        
        self.total[session_id] = session_data

        headers = {
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate',
            'connection': 'keep-alive',
            'cookie': cookies,
            'host': 'graph.facebook.com'
        }

        shared_count = 0

        while shared_count < amount:
            try:
                response = requests.post(
                    f"https://graph.facebook.com/me/feed?link=https://m.facebook.com/{post_id}&published=0&access_token={access_token}",
                    headers=headers
                )

                if response.status_code == 200:
                    shared_count += 1
                    self.total[session_id]['count'] = shared_count
                    
                    with open(session_file, 'w') as f:
                        json.dump(self.total[session_id], f)
                    
                    print(f"Shared {shared_count}/{amount}")
                
                time.sleep(interval)
            except Exception as e:
                print(f"Error sharing post: {str(e)}")
                break

        os.remove(session_file)
        del self.total[session_id]

def main():
    fb_share = FacebookAutoShare()
    
    print("=== Facebook Auto Share Tool by Yuri Evisu ===")
    cookie = input("Enter Facebook cookies (JSON format): ")
    url = input("Enter Facebook post URL: ")
    amount = int(input("Enter number of shares: "))
    interval = int(input("Enter interval between shares (seconds): "))

    try:
        if not fb_share.fb_url_pattern.match(url):
            print("Invalid Facebook URL")
            return

        cookies = fb_share.convert_cookie(cookie)
        
        import asyncio
        asyncio.run(fb_share.share_post(cookies, url, amount, interval))
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
