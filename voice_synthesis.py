import asyncio
import io
import requests
import discord
from config import BASE_URL, logger

async def yomiage(text: str, mode: int = 1, speed: float = 1.0):
    """VOICEVOXを使用して音声合成を行う"""
    if len(text) == 0:
        return 0
    
    print(f"[ {text} ] ==> VOICEVOX API")
    query = {
        "speaker": mode,
        "text": text
    }
    
    try:
        # 音声合成を実行
        synthesis = requests.post(
            f"{BASE_URL}/audio_query",
            headers={"Content-Type": "application/json"},
            params=query
        )
        synthesis.raise_for_status()
        json_data = synthesis.json()
        json_data["speedScale"] = speed
        
        response = requests.post(
            f"{BASE_URL}/synthesis",
            params=query,
            json=json_data,
            timeout=(1, 15.0)
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"合成音声に失敗: {e}")
        return 1

async def play_next(client, play_queue):
    """音声キューから次の音声を再生する"""
    if not play_queue.empty():
        guild, source = await play_queue.get()
        if guild.voice_client is not None:
            try:
                guild.voice_client.play(
                    discord.FFmpegPCMAudio(source=io.BytesIO(source), pipe=True), 
                    after=lambda e: asyncio.run_coroutine_threadsafe(play_next(client, play_queue), client.loop)
                )
            except Exception as e:
                logger.error(f"play_next error: {e}")
                await play_next(client, play_queue)  # 再生に失敗しても再度関数を呼び出す（キューが詰まらないようにする） 