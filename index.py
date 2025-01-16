import os,discord,json,requests,io,re,asyncio,datetime,sys,logging
from discord import app_commands
from os.path import join, dirname
from dotenv import load_dotenv
from urlextract import URLExtract
play_queue = asyncio.Queue() #読み上げ途中に来たリクエストはここにため込んでおく
channel = [] # 読み上げ対象のチャンネルのIDを格納しておく
voice_mode = {}
voice_speed = {}
reminde_json = {}
extractor = URLExtract() # URL読み上げると長いから抜き出すためのやつ

# 環境変数の設定
load_dotenv(verbose=True)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="[%X]",
    filename="./main.log",
    encoding="utf-8"
)

logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
APPLICATION_ID = os.environ.get("APPLICATION_ID") # 起動自体には必要ないが、メンションで反応させる際に必要

# Discord.pyからクライアントインスタンスを作成するよおおおおおおおおおおお
client = discord.Client(intents = discord.Intents.all())
intents = discord.Intents.default()
intents.message_content = True
tree = app_commands.CommandTree(client)

dic_file = 'bep-eng.dic'
kana_dict = {}
with open(dic_file, mode='r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if i >= 6:
            line_list = line.replace('\n', '').split(' ')
            kana_dict[line_list[0]] = line_list[1]

class MyView(discord.ui.View):
    def __init__(self,url:str="https://xenfo.org",label:str="xenfo.org"):
        super().__init__()
        # URLを含むボタンを作成
        self.add_item(discord.ui.Button(label=f"{label}", url=f"{url}"))

class RemindeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="リマインダーの設定をしてほしいのだ",timeout=None,custom_id="reminde")
        dt_now = datetime.datetime.now()
        self.day = discord.ui.TextInput(
            label="日付",
            style=discord.TextStyle.short,
            placeholder="YYYY/MM/DD",
            default=dt_now.strftime("%Y/%m/%d"),
            max_length=10,
            min_length=10,
            row=0,
            custom_id="day"
        )
        self.add_item(self.day)
        self.time = discord.ui.TextInput(
            label="時間",
            style=discord.TextStyle.short,
            placeholder="HH:MM",
            required=True,
            max_length=5,
            min_length=5,
            row=1,
            custom_id="time"
        )
        self.add_item(self.time)
        self.content = discord.ui.TextInput(
            label="内容",
            style=discord.TextStyle.paragraph,
            placeholder="ここに書いたテキストがリマインドされるのだ",
            required=True,
            max_length=150,
            row=2,
            custom_id="content"
        )
        self.add_item(self.content)

    
    async def on_submit(self, interaction: discord.Interaction):
        day_time = self.day.value.split("/")
        time = self.time.value.split(":")
        t = datetime.datetime.now()
        if len(day_time) != 3 or len(time) != 2:
            await interaction.response.send_message("時間のフィールドが不正なのだ。")
            return
        date_format = "%Y/%m/%d/%H:%M"
        date_obj = datetime.datetime.strptime(f"{day_time[0]}/{day_time[1]}/{day_time[2]}/{time[0]}:{time[1]}", date_format)
        if date_obj < t:
            await interaction.response.send_message("過去の時間を指定することはできないのだ。",ephemeral=True)
            return
        await interaction.response.send_message(f"{day_time[0]}/{day_time[1]}/{day_time[2]} {time[0]}:{time[1]}に\n「{self.content.value}」\nと通知するのだ。")
        global reminde_json
        new_dict = {
            "channel_id":f"{interaction.channel_id}",
            "content":f"{self.content.value}",
            "interaction_user_id":f"{interaction.user.id}"
        }
        now_time_recode = f"{int(day_time[0])}/{int(day_time[1])}/{int(day_time[2])}/{(int(time[0])*60)+(int(time[1]))}"
        reminde_json.update({now_time_recode:[]})
        reminde_json[f"{now_time_recode}"].append(new_dict)
        return
    
class IssueModal(discord.ui.Modal):
    def __init__(self,select_type:int):
        super().__init__(title=f"{['起こっている問題','要望'][select_type]}を詳しく教えてほしいのだ",timeout=None,custom_id="issue")
        self.content = discord.ui.TextInput(
            label="内容",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000,
            row=2,
            custom_id="content"
        )
        self.select_type=select_type
        self.add_item(self.content)
    
    async def on_submit(self, interaction: discord.Interaction):
        with open(f"./issues/{['bug','documents'][self.select_type]}.txt","a",encoding="utf-8") as f:
            f.write(f"\n{interaction.user.name}\n{self.content.value}")
        embed = discord.Embed(title="問題の報告が完了したのだ。",description="")
        embed.add_field(name=f"カテゴリ：{['バグ','要望'][self.select_type]}",value="")
        embed.add_field(name='内容', inline=False ,value=self.content.value)
        await interaction.response.send_message(embed=embed,ephemeral=True)
        return

async def play_next():
    if not play_queue.empty():
        guild:discord.Guild
        source:bytes
        guild,source = await play_queue.get()
        if guild.voice_client is not None:
            try:
                guild.voice_client.play(discord.FFmpegPCMAudio(source=io.BytesIO(source),pipe=True), after=lambda e: asyncio.run_coroutine_threadsafe(play_next(), client.loop))
            except Exception as e:
                logger.error(f"play_next error: {e}")
                await play_next() # 再生に失敗しても再度関数を呼び出す（キューが詰まらないようにする）
                

def guild_dict_translate(base_text:str,id:str):
    """
    base_text: ベーステキスト
    id: guild_id(discord)
    """
    base_text = base_text.lower()
    with open("./guild_dict.json",encoding="utf-8",mode="r") as f:
        guild_dict = dict(json.load(f))
    if f"{id}" in guild_dict:
        for d in guild_dict[f"{id}"]:
            base_text = base_text.replace(d,guild_dict[f"{id}"][f"{d}"])
    return base_text

def eng_to_kana(base_text:str):
    pattern = r'[a-zA-Z]+'
    base_text = base_text.upper()
    matches = re.findall(pattern, base_text,re.DOTALL)
    for m in matches:
        if f"{m}" in kana_dict:
            base_text = base_text.replace(f"{m}",f"{kana_dict[m]}",1)
    return base_text.lower()

def seikei(text:str):
    text = text.lower()
    url = extractor.find_urls(text)
    for i in url:
        text = text.replace(f"{i}","URL ")
    text = text.replace("\n"," ").replace("`","").replace("_"," ").replace("-"," ").replace("("," ").replace(")"," ").replace("{"," ").replace("}"," ").replace("["," ").replace("]"," ").replace('"'," ").replace("/","")
    text = eng_to_kana(text) # 英語をカタカナ英語に変換
    with open('./word_dict.json', 'r',encoding="utf-8") as file:
        word_dict = dict(json.load(file))
    for d in word_dict:
        text = text.replace(d,word_dict[d])
    mention = re.findall(r'<@(.*?)>',f"{text}",re.DOTALL)
    for m in mention:
        text = text.replace(f"<@{m}>","メンション ")
    channels = re.findall(r'<#(.*?)>',f"{text}",re.DOTALL)
    for c in channels:
        text = text.replace(f"<#{c}>","チャンネル ")
    emoji_list = re.findall(r"<:(.*?)>",text,re.DOTALL)
    for e in emoji_list:
        text = text.replace(f"<:{e}>","")
    ignore_list = re.findall(r"\|\|(.*?)\|\|",text,re.DOTALL)
    for e in ignore_list:
        text = text.replace(f"||{e}||","(秘密のメッセージ)")
    code_list = re.findall(r"```(.*?)```",text,re.DOTALL)
    for e in code_list:
        text = text.replace(f"```py{e}```","Pythonコードスニペット").replace(f"```js{e}```","JSコードスニペット").replace(f"```rs{e}```","ラストコードスニペット").replace(f"```sh{e}```","シェルコードスニペット").replace(f"```{e}```","コードスニペット")
    if "wwwww" in text or "ｗｗｗｗｗ" in text:
        text = text.replace("ｗ","").replace("w","")
    # encode_dict = {
    #     "wa":"わ","wo":"を","nn":"ん",
    #     "jo":"じょ","ja":"じゃ","ju":"じゅ","je":"じぇ","tsu":"つ",
    #     "nya":"にゃ","nyu":"にゅ","nyo":"にょ",
    #     "rya":"りゃ","ryu":"りゅ","ryo":"りょ",
    #     "sya":"しゃ","sha":"しゃ","syu":"しゅ","shu":"しゅ","syo":"しょ","sho":"しょ",
    #     "la":"ぁ","xa":"ぁ","li":"ぃ","xi":"ぃ","lu":"ぅ","xu":"ぅ","le":"ぇ","xe":"ぇ","lo":"ぉ","xo":"ぉ",
    #     "ka":"か","ki":"き","ku":"く","ke":"け","ko":"こ","ga":"が","gi":"ぎ","gu":"ぐ","ge":"げ","go":"ご",
    #     "sa":"さ","si":"し","su":"す","se":"せ","so":"そ","za":"ざ","zi":"じ","ji":"じ","zu":"ず","ze":"ぜ","zo":"ぞ",
    #     "ta":"た","ti":"ち","tu":"つ","te":"て","to":"と","da":"だ","di":"ぢ","du":"づ","de":"で","do":"ど",
    #     "na":"な","ni":"に","nu":"ぬ","ne":"ね","no":"の","ba":"ば","bi":"び","bu":"ぶ","be":"べ","bo":"ぼ","pa":"ぱ","pi":"ぴ","pu":"ぷ","pe":"ぺ","po":"ぽ",
    #     "ma":"ま","mi":"み","mu":"む","me":"め","mo":"も",
    #     "ya":"や","yu":"ゆ","yo":"よ",
    #     "ha":"は","hi":"ひ","hu":"ふ","he":"へ","ho":"ほ",
    #     "a":"あ","i":"い","u":"う","e":"え","o":"お",
    #     "n":"ん","-":"ー"
    # }
    # for i in encode_dict:
    #     text = text.replace(i,encode_dict[i])
    return text

async def yomiage(text:str,mode:int=1,speed:float=1.0):
    if len(text) == 0:return 0
    print(f"[ {text} ] ==> VOICEVOX API")
    query = {
        "speaker": mode,
        "text": text
    }
    try:
        # 音声合成を実行
        synthesis = requests.post(
            f"{os.environ.get('baseURL')}/audio_query",
            headers={"Content-Type": "application/json"},
            params=query
        )
        synthesis.raise_for_status()
        json_data = synthesis.json()
        json_data["speedScale"] = speed
        response = requests.post(
            f"{os.environ.get('baseURL')}/synthesis",
            params=query,
            json=json_data,
            timeout=(1, 15.0)
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"合成音声に失敗: {e}")
        return 1

@client.event
async def on_ready():
    logger.info(f'{client.user}がログインしました')
    await client.change_presence(activity = discord.CustomActivity(name=str('👉 /help'), type=1))
    await tree.sync()#スラッシュコマンドを同期
    if not len(sys.argv) == 1:
        if sys.argv[1] == "update":
            if os.path.exists("update.txt"):
                with open("update.txt","r",encoding="utf-8") as f:
                    update_text = f.read()
                if not len(update_text) == 0:
                    guild = client.guilds
                    for g in guild:
                        try:
                            await g.system_channel.send(update_text)
                        except Exception as e:
                            logger.warning(f"{g.name}への通知に失敗しました。: {e}")
            else:
                logger.info("update.txtが見つかりません。")

    while True:
        global reminde_json
        dt_now = datetime.datetime.now()
        if f"{dt_now.year}/{dt_now.month}/{dt_now.day}/{(dt_now.hour*60)+(dt_now.minute)}" in reminde_json:
            reminde_ready = reminde_json[f"{dt_now.year}/{dt_now.month}/{dt_now.day}/{(dt_now.hour*60)+(dt_now.minute)}"]
            for i in reminde_ready:
                # "channel_id":f"{interaction.channel_id}",
                # "content":f"{self.content.value}",
                # "interaction_user_id":f"{interaction.user.id}"
                channel = client.get_channel(int(i["channel_id"]))
                await channel.send(content=f"<@{i['interaction_user_id']}> {i['content']}")
                if not channel.guild.voice_client is None:
                    if f"{channel.guild.id}" in voice_mode:
                        mode = voice_mode[f"{channel.guild.id}"]
                    else:
                        mode = 1
                    if f"{channel.guild.id}" in voice_speed:
                        speed = voice_speed[f"{channel.guild.id}"]
                    else:
                        speed = 1.0
                    global play_queue
                    source = await yomiage(text=seikei(i["content"]),mode=mode,speed=speed)
                    await play_queue.put((channel.guild,source))
                    if not channel.guild.voice_client.is_playing():
                        await play_next()
            reminde_json.pop(f"{dt_now.year}/{dt_now.month}/{dt_now.day}/{(dt_now.hour*60)+(dt_now.minute)}")
        await asyncio.sleep(5)

@client.event
async def on_message(message:discord.Message):
    if message.guild:
        logger.info(f"[{message.guild.name}/{message.channel.name}] {message.author.display_name} ({message.author.name}) : {message.content}")
    if message.author.bot:return
    if message.content.replace(" ","") == f"<@{APPLICATION_ID}>":
        await message.reply("<:zunda:1277689238632267848> 使い方を知りたい場合は`/help`を実行してほしいのだ！")
        return
    
    text = guild_dict_translate(base_text=f"{message.content}",id=f"{message.guild.id}")
    if len(text) > 500:
        return
    with open("./ignore.json",encoding="utf-8",mode="r") as f:
        ignore = dict(json.load(f))
    if f"{message.guild.id}" in ignore:
        for i in ignore[f"{message.guild.id}"]:
            if i in text:
                return
    global channel,play_queue,voice_mode,voice_speed
    if message.guild.voice_client is None:return
    if f"{message.guild.id}" in voice_mode:
        mode = voice_mode[f"{message.guild.id}"]
    else:
        mode = 1
    if f"{message.guild.id}" in voice_speed:
        speed = voice_speed[f"{message.guild.id}"]
    else:
        speed = 1.0
    if f"{message.channel.id}" in channel:
        source = await yomiage(text=seikei(text),mode=mode,speed=speed)
        if source == 0:
            return
        elif source == 1:
            await message.reply(":octagonal_sign: 音声合成に失敗したのだ <:zunda:1277689238632267848>",silent=True,delete_after=5)
            return
        await play_queue.put((message.guild,source))
        if not message.guild.voice_client.is_playing():
            await play_next()

@client.event
async def on_voice_state_update(member:discord.Member, before:discord.VoiceClient, after:discord.VoiceClient): # 入退室読み上げ
    if member.bot:return
    if before.channel != after.channel:
        global voice_mode,voice_speed
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
            source = await yomiage(text=seikei(f"{guild_dict_translate(base_text=f'{member.display_name}',id=f'{member.guild.id}')}が参加したのだ！"),mode=mode,speed=speed)
        elif after.channel is None:
            source = await yomiage(text=seikei(f"{guild_dict_translate(base_text=f'{member.display_name}',id=f'{member.guild.id}')}が退出したのだ！"),mode=mode,speed=speed)
        else: # ほかのVCに移動したとき
            source = 0
        if source == 0 or source == 1:return
        global play_queue
        await play_queue.put((member.guild,source))
        if not member.guild.voice_client is None:
            if not member.guild.voice_client.is_playing():
                await play_next()

@tree.command(name="join",description="VCに参加するのだ")
async def join_command(interaction: discord.Interaction):
    global channel
    if interaction.user.voice is None:
        await interaction.response.send_message("<:zunda:1277689238632267848> 先にVCに参加してほしいのだ",silent=True)
        return
    elif interaction.guild.voice_client is None:
        await interaction.user.voice.channel.connect(self_deaf=True) # ボイスチャンネルに接続する
        await interaction.response.send_message("<:zunda:1277689238632267848> 参加したのだ！",silent=True)
        channel.append(f"{interaction.channel_id}")
        if interaction.channel_id != interaction.user.voice.channel.id:
            channel.append(f"{interaction.user.voice.channel.id}")
    elif interaction.guild.voice_client:
        await interaction.response.send_message("<:zunda:1277689238632267848> 既に参加してるのだ！",silent=True)
        return
    else:
        await interaction.response.send_message("<:zunda:1277689238632267848> VCに参加できないのだ",silent=True)
        return

@tree.command(name="bye",description="VCから退出するのだ")
async def bye_command(interaction: discord.Interaction):
    global channel
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("既に抜けてるのだ",silent=True)
    elif interaction.guild.voice_client:
        if f"{interaction.channel_id}" in channel:
            channel.remove(f"{interaction.channel_id}")
            try:
                channel.remove(f"{interaction.user.voice.channel.id}")
            except:
                pass
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("<:zunda:1277689238632267848> 退出するのだ",silent=True)
        else:
            await interaction.response.send_message("<:zunda:1277689238632267848> このコマンドは`/join`を使ったチャンネルで実行してほしいのだ！",silent=True)
    
@tree.command(name="force-leave",description="強制的にVCから退出するのだ（/byeが動作しなくなったときにのみ使用してください）")
async def force_leave_command(interaction: discord.Interaction):
    global channel
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("既に抜けてるのだ",silent=True)
    elif interaction.guild.voice_client:

        try:
            try:
                channel.remove(f"{interaction.channel_id}")
                channel.remove(f"{interaction.user.voice.channel.id}")
            except:
                pass
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("<:zunda:1277689238632267848> 退出するのだ",silent=True)
        except:
            await interaction.response.send_message(":warning: 退出処理に失敗しました。管理者に連絡してください。",silent=True)

@tree.command(name="dict",description="特定の単語の文字列を矯正できます。")
async def dict_command(interaction: discord.Interaction,書き:str,読み:str):
    if interaction.user.name == 'makao1521':
        import gomi_omikuzi
        await interaction.response.send_message(gomi_omikuzi.gen())
        return
    書き = 書き.lower()
    読み = 読み.lower()
    if 書き==読み:
        await interaction.response.send_message(content="<:zunda:1277689238632267848> 読みと書きは同じ文字列にできないのだ",delete_after=5,silent=True)
        return
    with open("./guild_dict.json",encoding="utf-8",mode="r") as f:
        guild_dict = dict(json.load(f))
    if not f'{interaction.guild_id}' in guild_dict:
        guild_dict.update({f'{interaction.guild_id}':{}})
    if f"{書き}" in guild_dict[f'{interaction.guild_id}']:
        action = "上書き"
    else:
        action = "設定"
    guild_dict[f'{interaction.guild_id}'].update({書き:読み})
    updated_json = json.dumps(guild_dict, indent=4,ensure_ascii = False)
    with open('./guild_dict.json', 'w',encoding="utf-8") as file:
        file.write(updated_json)
    await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{書き}」の読み方を「{読み}」に{action}したのだ！")

@tree.command(name="delete_dict",description="dictコマンドで登録した言葉を辞書から削除できるのだ")
async def delete_dict(interaction: discord.Interaction,書き:str):
    if interaction.user.name == 'makao1521':
        await interaction.response.send_message('ごめんなに？よく聞こえんかったわｗ')
        return
    書き = 書き.lower()
    with open("./guild_dict.json",encoding="utf-8",mode="r") as f:
        guild_dict = dict(json.load(f))
    if not f'{interaction.guild_id}' in guild_dict:
        await interaction.response.send_message("<:zunda:1277689238632267848> このサーバーではまだ辞書を作成してないのだ",ephemeral=True,delete_after=5)
        return
    if f"{書き}" in guild_dict[f'{interaction.guild_id}']:
        guild_dict[f'{interaction.guild_id}'].pop(f"{書き}")
        updated_json = json.dumps(guild_dict, indent=4,ensure_ascii = False)
        with open('./guild_dict.json', 'w',encoding="utf-8") as file:
            file.write(updated_json)
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{書き}」を辞書から削除したのだ")
    else:
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{書き}」は辞書に存在しないのだ",ephemeral=True,delete_after=5)

@tree.command(name="ignore",description="特定の文字列が含まれていた場合に読み上げをスキップするのだ。もう一度同じ文字を指定すると削除できるのだ")
async def ignore(interaction: discord.Interaction,文字:str):
    if interaction.user.name == 'makao1521':
        await interaction.response.send_message('今忙しいから後にしてクレメンスｗｗｗｗｗｗｗｗｗ')
        return
    文字 = 文字.lower()
    with open("./ignore.json",encoding="utf-8",mode="r") as f:
        ignore = dict(json.load(f))
    if not f'{interaction.guild_id}' in ignore:
        ignore.update({f'{interaction.guild_id}':[]})
    if not f"{文字}" in ignore[f'{interaction.guild_id}']:
        ignore[f'{interaction.guild_id}'].append(f"{文字}")
        updated_json = json.dumps(ignore, indent=4,ensure_ascii = False)
        with open('./ignore.json', 'w',encoding="utf-8") as file:
            file.write(updated_json)
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{文字}」をスキップ対象に設定したのだ")
    else:
        ignore[f'{interaction.guild_id}'].remove(f"{文字}")
        updated_json = json.dumps(ignore, indent=4,ensure_ascii = False)
        with open('./ignore.json', 'w',encoding="utf-8") as file:
            file.write(updated_json)
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{文字}」をスキップ対象から削除したのだ")

@tree.command(name="show_ignore",description="スキップ対象の文字列をすべて表示するのだ")
async def show_ignore(interaction: discord.Interaction):
    with open("./ignore.json",encoding="utf-8",mode="r") as f:
        ignore = dict(json.load(f))
    if (not f'{interaction.guild_id}' in ignore):
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> このサーバーではスキップ対象の文字が設定されていないのだ。",ephemeral=True)
        return
    if len(ignore[f'{interaction.guild_id}']) == 0:
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> このサーバーではスキップ対象の文字が1つも設定されていないのだ。",ephemeral=True)
        return
    ignore_list = ""
    for l in ignore[f'{interaction.guild_id}']:
        ignore_list += f"{l}\n"
    await interaction.response.send_message(content=f"<:zunda:1277689238632267848> スキップ対象一覧なのだ\n```\n{ignore_list}```")

@tree.command(name="preview_dict",description="あなたのサーバーにおける辞書を表示します")
async def preview_dict(interaction: discord.Interaction):
    with open("./guild_dict.json",encoding="utf-8",mode="r") as f:
        guild_dict = dict(json.load(f))
    if not f'{interaction.guild_id}' in guild_dict:
        await interaction.response.send_message("<:zunda:1277689238632267848> このサーバーではまだ辞書を作成してないのだ",ephemeral=True,delete_after=5)
        return
    if len(guild_dict[f'{interaction.guild_id}']) == 0:
        await interaction.response.send_message(content="<:zunda:1277689238632267848> 登録されている単語が一つもないのだ。",ephemeral=True,delete_after=5)
        return
    res = ""
    for i in dict(guild_dict[f'{interaction.guild_id}']):
        res += f"{i}：{guild_dict[f'{interaction.guild_id}'][i]}\n"
    await interaction.response.send_message(f"### 書き：読み\n```{res}```",ephemeral=True)

@tree.command(name="help",description="Botの説明をするのだ")
async def test_command(interaction: discord.Interaction):
    embed = discord.Embed(title="使用方法",description="")
    embed.add_field(name='概要', inline=False ,value='`/join`を実行したテキストチャンネルのメッセージを参加したVCで読み上げるのだ！')
    embed.add_field(name='コマンド - 基本', inline=False ,value='')
    embed.add_field(name='`/join`', value='コマンドを実行したテキストチャンネルのメッセージを参加先のVCで読み上げるのだ！')
    embed.add_field(name='`/bye`', value='VCから退出するのだ！')
    embed.add_field(name='`/mode`', value='喋り方を変更できるのだ！')
    embed.add_field(name='`/speed`', value='喋る速度を変更できるのだ！')
    embed.add_field(name='`/help`', value='このパネルを表示できるのだ！')
    embed.add_field(name='コマンド - 辞書', inline=False ,value='')
    embed.add_field(name='`/dict`', value='サーバー固有の読ませ方をしたい言葉を登録できるのだ。')
    embed.add_field(name='`/delete_dict`', value='登録した言葉を辞書から削除できるのだ。')
    embed.add_field(name='`/preview_dict`', value='作成した辞書を表示できるのだ。')
    embed.add_field(name='`/reminder`', value='特定の時間になったら指定されたメッセージを通知するのだ。')
    embed.add_field(name='`/force-leave`', value='BotがVCから退出できなくなったときに使用してほしいのだ。それでも解決しなければ、管理者に連絡してほしいのだ。')
    view = MyView(url="https://voicevox.hiroshiba.jp/term/",label="利用規約")
    await interaction.response.send_message(embed=embed,ephemeral=True,view=view)

@tree.command(name="mode",description="喋り方を変えられるのだ")
@app_commands.describe(モード="喋り方を選択してほしいのだ")
@app_commands.choices(モード=[
    discord.app_commands.Choice(name="ノーマル", value=3),
    discord.app_commands.Choice(name="あまあま", value=1),
    discord.app_commands.Choice(name="ツンツン", value=7),
    discord.app_commands.Choice(name="セクシー", value=5),
    discord.app_commands.Choice(name="ささやき", value=22),
    discord.app_commands.Choice(name="ヒソヒソ", value=38),
    discord.app_commands.Choice(name="ヘロヘロ", value=75),
    discord.app_commands.Choice(name="なみだめ", value=76),
])
async def mode(interaction: discord.Interaction, モード: discord.app_commands.Choice[int]):
    mode = int(モード.value)
    global voice_mode
    voice_mode.update({f"{interaction.guild.id}":mode})
    await interaction.response.send_message(f"<:zunda:1277689238632267848> 喋り方を「{モード.name}」に設定したのだ！")

@tree.command(name="speed",description="喋る速度を変えられるのだ")
@app_commands.describe(スピード="速度を選択してほしいのだ")
@app_commands.choices(スピード=[
    discord.app_commands.Choice(name="超ゆっくり(0.5倍)", value=0.5),
    discord.app_commands.Choice(name="ゆっくり(0.75倍)", value=0.75),
    discord.app_commands.Choice(name="普通(1.0倍)", value=1.0),
    discord.app_commands.Choice(name="早口(1.5倍)", value=1.5),
    discord.app_commands.Choice(name="超高速(2倍)", value=2.0),
])
async def speed(interaction: discord.Interaction, スピード: discord.app_commands.Choice[float]):
    mode = float(スピード.value)
    global voice_speed
    voice_speed.update({f"{interaction.guild.id}":mode})
    await interaction.response.send_message(f"<:zunda:1277689238632267848> 喋る速度を「{スピード.name}」に設定したのだ！")
# Reminder
@tree.command(name="reminder", description="特定の時間になったら任意の言葉を喋るのだ")
async def food_slash(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(content="このコマンドはサーバー限定です。",ephemeral=True)
        return
    await interaction.response.send_modal(RemindeModal())

@tree.command(name="issue", description="Botに問題が発生したときにエラーの詳細を報告できるのだ。")
@app_commands.describe(カテゴリ="速度を選択してほしいのだ")
@app_commands.choices(カテゴリ=[
    discord.app_commands.Choice(name="バグ", value=0),
    discord.app_commands.Choice(name="要望", value=1),
])
async def food_slash(interaction: discord.Interaction,カテゴリ: discord.app_commands.Choice[int]):
    await interaction.response.send_modal(IssueModal(select_type=カテゴリ.value))
client.run(TOKEN)