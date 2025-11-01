import discord
import asyncio
import datetime
import sys
import os
import json
from discord import app_commands
from config import TOKEN, APPLICATION_ID, logger, channel, voice_mode, voice_speed, reminde_json, reserved_guild
from text_processor import guild_dict_translate, seikei
from voice_synthesis import yomiage, play_next
from commands import setup_commands

# Discord.pyからクライアントインスタンスを作成
client = discord.Client(intents=discord.Intents.all())
intents = discord.Intents.default()
intents.message_content = True
tree = app_commands.CommandTree(client)

# コマンドを設定
setup_commands(tree, client)

@client.event
async def on_disconnect():
    """接続が切れた時の処理"""
    import config
    while not config.play_queue.empty():
        config.play_queue.get()
    for i in channel:
        try:
            channel_obj = client.get_channel(int(i))
            if channel_obj and hasattr(channel_obj, 'guild') and channel_obj.guild and channel_obj.guild.voice_client:
                await channel_obj.guild.voice_client.disconnect()
        except:
            pass
    channel.clear()
    print("インターネットの接続が切れました。状態を初期化します")

@client.event
async def on_ready():
    """Botが準備完了した時の処理"""
    logger.info(f'{client.user}がログインしました')
    await client.change_presence(activity=discord.CustomActivity(name=str('👉 /help'), type=1))
    await tree.sync()  # スラッシュコマンドを同期
    
    # アップデート通知の処理
    if not len(sys.argv) == 1:
        if sys.argv[1] == "update":
            if os.path.exists("update.txt"):
                with open("update.txt", "r", encoding="utf-8") as f:
                    update_text = f.read()
                if not len(update_text) == 0:
                    guild = client.guilds
                    for g in guild:
                        try:
                            if g.system_channel:
                                await g.system_channel.send(update_text)
                        except Exception as e:
                            logger.warning(f"{g.name}への通知に失敗しました。: {e}")
            else:
                logger.info("update.txtが見つかりません。")

    # リマインダー処理のメインループ
    while True:
        dt_now = datetime.datetime.now()
        if f"{dt_now.year}/{dt_now.month}/{dt_now.day}/{(dt_now.hour*60)+(dt_now.minute)}" in reminde_json:
            reminde_ready = reminde_json[f"{dt_now.year}/{dt_now.month}/{dt_now.day}/{(dt_now.hour*60)+(dt_now.minute)}"]
            for i in reminde_ready:
                try:
                    channel_obj = client.get_channel(int(i["channel_id"]))
                    if channel_obj and hasattr(channel_obj, 'send'):
                        await channel_obj.send(content=f"<@{i['interaction_user_id']}> {i['content']}")
                        
                        # 音声読み上げ処理
                        if hasattr(channel_obj, 'guild') and channel_obj.guild and channel_obj.guild.voice_client:
                            if f"{channel_obj.guild.id}" in voice_mode:
                                mode = voice_mode[f"{channel_obj.guild.id}"]
                            else:
                                mode = 1
                            if f"{channel_obj.guild.id}" in voice_speed:
                                speed = voice_speed[f"{channel_obj.guild.id}"]
                            else:
                                speed = 1.0
                            
                            source = await yomiage(text=seikei(i["content"]), mode=mode, speed=speed)
                            import config
                            await config.play_queue.put((channel_obj.guild, source))
                            if not channel_obj.guild.voice_client.is_playing():
                                await play_next(client, config.play_queue)
                except Exception as e:
                    logger.error(f"リマインダー処理でエラー: {e}")
                    
            reminde_json.pop(f"{dt_now.year}/{dt_now.month}/{dt_now.day}/{(dt_now.hour*60)+(dt_now.minute)}")
        await asyncio.sleep(5)

@client.event
async def on_message(message: discord.Message):
    """メッセージ受信時の処理"""
    if message.guild:
        logger.info(f"[{message.guild.name}/{message.channel.name}] {message.author.display_name} ({message.author.name}) : {message.content}")
    if message.author.bot:
        return
    if message.content.replace(" ", "") == f"<@{APPLICATION_ID}>":
        await message.reply("<:zunda:1277689238632267848> 使い方を知りたい場合は`/help`を実行してほしいのだ！")
        return
    
    # メッセージの処理
    if not message.guild:
        return
        
    text = guild_dict_translate(base_text=f"{message.content}", id=f"{message.guild.id}")
    if len(text) > 500:
        return
    
    # 無視リストのチェック
    with open("./ignore.json", encoding="utf-8", mode="r") as f:
        ignore = dict(json.load(f))
    if f"{message.guild.id}" in ignore:
        for i in ignore[f"{message.guild.id}"]:
            if i in text:
                return
    
    # 音声読み上げ処理
    if not message.guild.voice_client:
        return
        
    if f"{message.guild.id}" in voice_mode:
        mode = voice_mode[f"{message.guild.id}"]
    else:
        mode = 1
    if f"{message.guild.id}" in voice_speed:
        speed = voice_speed[f"{message.guild.id}"]
    else:
        speed = 1.0
    
    if f"{message.channel.id}" in channel:
        source = await yomiage(text=seikei(text), mode=mode, speed=speed)
        if source == 0:
            return
        elif source == 1:
            await message.reply(":octagonal_sign: 音声合成に失敗したのだ <:zunda:1277689238632267848>", silent=True, delete_after=5)
            return
        import config
        await config.play_queue.put((message.guild, source))
        try:
            if not message.guild.voice_client.is_playing():
                await play_next(client, config.play_queue)
        except Exception as e:
            print(e)
            await play_next(client, config.play_queue)

@client.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """ボイスチャンネルの状態変更時の処理（入退室読み上げ）"""
    if member.id == client.user.id and after.channel is None and f"{member.guild.id}" in reserved_guild:
        for i in reserved_guild[f"{member.guild.id}"]:
            try:
                channel.remove(f"{i}")
            except:
                pass
    if not f"{member.guild.id}" in reserved_guild:
        return  # 予約済みでないチャンネルでのアクションは無視

    if member.bot:
        return
    if before.channel != after.channel:
        # modeの定義
        if f"{member.guild.id}" in voice_mode:
            mode = voice_mode[f"{member.guild.id}"]
        else:
            mode = 1
        # speedの定義
        if f"{member.guild.id}" in voice_speed:
            speed = voice_speed[f"{member.guild.id}"]
        else:
            speed = 1.0
        
        if before.channel is None:
            source = await yomiage(text=seikei(f"{guild_dict_translate(base_text=f'{member.display_name}', id=f'{member.guild.id}')}が参加したのだ！"), mode=mode, speed=speed)
        elif after.channel is None:
            source = await yomiage(text=seikei(f"{guild_dict_translate(base_text=f'{member.display_name}', id=f'{member.guild.id}')}が退出したのだ！"), mode=mode, speed=speed)
        else:  # ほかのVCに移動したとき
            source = 0
        
        if source == 0 or source == 1:
            return
        
        import config
        await config.play_queue.put((member.guild, source))
        if member.guild.voice_client is not None:
            if not member.guild.voice_client.is_playing():
                await play_next(client, config.play_queue)

# アプリケーションの実行
if __name__ == "__main__":
    if TOKEN is None:
        logger.error("BOT_TOKENが設定されていません")
        sys.exit(1)
    
    # グローバル変数の初期化
    import asyncio
    from config import play_queue, channel, voice_mode, voice_speed, reminde_json, reserved_guild
    import config
    config.play_queue = asyncio.Queue()
    
    client.run(TOKEN) 