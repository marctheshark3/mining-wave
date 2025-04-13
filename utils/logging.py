# utils/logging.py
import logging
import telegram
import asyncio
from functools import partial
from typing import Optional, Dict
from config import settings
import json
from datetime import datetime, timedelta
from redis import asyncio as aioredis
import hashlib

class TelegramHandler(logging.Handler):
    def __init__(self, token: str, chat_id: str, level: int = logging.ERROR):
        super().__init__(level)
        self.bot = telegram.Bot(token=token)
        self.chat_id = chat_id
        self._queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._redis: Optional[aioredis.Redis] = None
        self._notification_window = settings.NOTIFICATION_WINDOW
        self._max_similar_notifications = settings.MAX_SIMILAR_NOTIFICATIONS
        
    async def setup_redis(self):
        """Initialize Redis connection"""
        if not self._redis:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf8",
                decode_responses=True
            )
    
    def _get_error_key(self, record: logging.LogRecord) -> str:
        """Generate a unique key for similar errors"""
        # Create a hash of the error message and type
        error_content = f"{record.levelname}:{record.module}:{record.funcName}:{record.msg}"
        return f"telegram:error:{hashlib.md5(error_content.encode()).hexdigest()}"
    
    async def _should_send_notification(self, record: logging.LogRecord) -> bool:
        """Check if we should send this notification based on rate limiting"""
        await self.setup_redis()
        error_key = self._get_error_key(record)
        
        # Get current notification count for this error
        notification_data = await self._redis.get(error_key)
        current_time = datetime.now().timestamp()
        
        if notification_data:
            data = json.loads(notification_data)
            count = data['count']
            first_seen = data['first_seen']
            last_seen = data['last_seen']
            
            # If we're still within the notification window
            if current_time - first_seen < self._notification_window:
                # Update the count and last seen time
                count += 1
                await self._redis.set(
                    error_key,
                    json.dumps({
                        'count': count,
                        'first_seen': first_seen,
                        'last_seen': current_time
                    }),
                    ex=self._notification_window
                )
                
                # Only send if we haven't exceeded the limit
                if count <= self._max_similar_notifications:
                    return True
                elif count == self._max_similar_notifications + 1:
                    # Send one final message about rate limiting
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=f"🔇 *Rate Limited*\nSimilar errors are being suppressed for {self._notification_window//60} minutes.\nSeen {count} times in the last {int(current_time - first_seen)} seconds.",
                        parse_mode='Markdown'
                    )
                return False
            else:
                # Window expired, start fresh
                await self._redis.set(
                    error_key,
                    json.dumps({
                        'count': 1,
                        'first_seen': current_time,
                        'last_seen': current_time
                    }),
                    ex=self._notification_window
                )
                return True
        else:
            # First occurrence of this error
            await self._redis.set(
                error_key,
                json.dumps({
                    'count': 1,
                    'first_seen': current_time,
                    'last_seen': current_time
                }),
                ex=self._notification_window
            )
            return True
    
    async def _sender(self):
        while True:
            try:
                record = await self._queue.get()
                
                # Check rate limiting before sending
                if await self._should_send_notification(record):
                    message = self.format(record)
                    # Truncate message if too long
                    if len(message) > 4000:
                        message = message[:3997] + "..."
                    
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=f"🚨 *ALERT*\n```\n{message}\n```",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                print(f"Error sending Telegram message: {e}")
            finally:
                self._queue.task_done()
    
    def emit(self, record):
        try:
            asyncio.create_task(self._queue.put(record))
        except Exception:
            self.handleError(record)
    
    def start(self):
        """Start the background sender task"""
        if not self._task:
            self._task = asyncio.create_task(self._sender())
    
    async def stop(self):
        """Stop the background sender task and cleanup Redis"""
        if self._task:
            self._task.cancel()
            self._task = None
        if self._redis:
            await self._redis.close()
            self._redis = None

# Create logger
logger = logging.getLogger("mining-wave")
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Telegram handler (only for ERROR and CRITICAL)
if hasattr(settings, 'TELEGRAM_BOT_TOKEN') and hasattr(settings, 'TELEGRAM_CHAT_ID'):
    telegram_handler = TelegramHandler(
        token=settings.TELEGRAM_BOT_TOKEN,
        chat_id=settings.TELEGRAM_CHAT_ID,
        level=logging.ERROR
    )
    telegram_handler.setFormatter(formatter)
    logger.addHandler(telegram_handler)
    
    # Start the telegram handler
    def start_telegram_handler():
        telegram_handler.start()
    
    async def stop_telegram_handler():
        await telegram_handler.stop()
else:
    start_telegram_handler = lambda: None
    stop_telegram_handler = lambda: None