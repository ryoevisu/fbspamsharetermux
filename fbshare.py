import os
import json
import re
import asyncio
import aiohttp
import time
import logging
from typing import Dict, Optional

class FacebookAutoShare:
    def __init__(self):
        self.sessions_dir = "fb_sessions"
        self.total: Dict[str, Dict] = {}
        self.fb_url_pattern = re.compile(r'^https:\/\/(?:www\.)?facebook\.com\/(?:(?:\w+\/)*\d+\/posts\/\d+\/?\??(?:app=fbl)?|share\/(?:p\/)?[a-zA-Z0-9]+\/?)')
        
        # Create sessions directory
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.load_sessions()
        
        # Configure logging
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def load_sessions(self):
        try:
            for file in os.listdir(self.sessions_dir):
                with open(os.path.join(self.sessions_dir, file), 'r') as f:
                    session_data = json.load(f)
                    self.total[session_data['id']] = session_data
        except Exception as e:
            self.logger.error(f"Error loading sessions: {str(e)}")

    async def get_post_id(self, url: str, session: aiohttp.ClientSession) -> Optional[str]:
        try:
            async with session.post(
                'https://id.traodoisub.com/api.php', 
                data={'link': url},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                data = await response.json()
                return data.get('id')
        except Exception as e:
            self.logger.error(f"Error getting post ID: {str(e)}")
            return None

    async def get_access_token(self, cookie: str, session: aiohttp.ClientSession) -> Optional[str]:
        try:
            headers = {
                'authority': 'business.facebook.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'cookie': cookie,
                'referer': 'https://www.facebook.com/'
            }
            
            async with session.get('https://business.facebook.com/content_management', headers=headers) as response:
                text = await response.text()
                token_match = re.search(r'"accessToken":\s*"([^"]+)"', text)
                
                return token_match.group(1) if token_match else None
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None

    def convert_cookie(self, cookie_str: str) -> str:
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

    async def share_post(self, cookies: str, url: str, amount: int, interval: int):
        async with aiohttp.ClientSession() as session:
            post_id = await self.get_post_id(url, session)
            if not post_id:
                self.logger.error("Unable to get post ID: invalid URL, or post is private or friends-only.")
                return

            access_token = await self.get_access_token(cookies, session)
            if not access_token:
                self.logger.error("Failed to get access token")
                return

            session_id = post_id if post_id not in self.total else post_id + '_1'
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
                    async with session.post(
                        f"https://graph.facebook.com/me/feed?link=https://m.facebook.com/{post_id}&published=0&access_token={access_token}",
                        headers=headers
                    ) as response:
                        if response.status == 200:
                            shared_count += 1
                            self.total[session_id]['count'] = shared_count
                            
                            with open(session_file, 'w') as f:
                                json.dump(self.total[session_id], f)
                            
                            self.logger.info(f"Shared {shared_count}/{amount}")
                    
                    await asyncio.sleep(interval)
                except Exception as e:
                    self.logger.error(f"Error sharing post: {str(e)}")
                    break

            os.remove(session_file)
            del self.total[session_id]

async def main():
    fb_share = FacebookAutoShare()
    
    print("=== Facebook Auto Share Tool by Yuri Evisu ===")
    print("Enhanced with aiohttp for improved performance")
    cookie = input("Enter Facebook cookies (JSON format): ")
    url = input("Enter Facebook post URL: ")
    amount = int(input("Enter number of shares: "))
    interval = int(input("Enter interval between shares (seconds): "))

    try:
        if not fb_share.fb_url_pattern.match(url):
            print("Invalid Facebook URL")
            return

        cookies = fb_share.convert_cookie(cookie)
        
        await fb_share.share_post(cookies, url, amount, interval)
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
