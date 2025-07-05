import os
import logging
from os.path import join, dirname
from dotenv import load_dotenv

# 環境変数の設定
load_dotenv(verbose=True)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="[%X]",
    filename="./main.log",
    encoding="utf-8"
)

logger = logging.getLogger(__name__)

# 環境変数
TOKEN = os.environ.get("BOT_TOKEN")
APPLICATION_ID = os.environ.get("APPLICATION_ID")
BASE_URL = os.environ.get('baseURL')

# 辞書ファイル
DIC_FILE = 'bep-eng.dic'

# グローバル変数（初期化はmain.pyで行う）
play_queue = None  # 読み上げ途中に来たリクエストはここにため込んでおく
channel = []  # 読み上げ対象のチャンネルのIDを格納しておく
voice_mode = {}
voice_speed = {}
reminde_json = {}
reserved_guild = {} 