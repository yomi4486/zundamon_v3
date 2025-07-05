import discord
import json
import asyncio
from discord import app_commands
from config import channel, reserved_guild, voice_mode, voice_speed, logger
from text_processor import guild_dict_translate
from voice_synthesis import yomiage, play_next
from ui_components import MyView, RemindeModal, IssueModal
import gomi_omikuzi

def setup_commands(tree, client):
    """コマンドを設定する"""
    
    @tree.command(name="join", description="VCに参加するのだ")
    async def join_command(interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("<:zunda:1277689238632267848> 先にVCに参加してほしいのだ", silent=True)
            return
        elif interaction.guild.voice_client is None:
            await interaction.user.voice.channel.connect(self_deaf=True)  # ボイスチャンネルに接続する
            await interaction.response.send_message("<:zunda:1277689238632267848> 参加したのだ！", silent=True)
            channel.append(f"{interaction.channel_id}")
            reserved_guild[f"{interaction.guild.id}"] = [f"{interaction.channel_id}"]
            if interaction.channel_id != interaction.user.voice.channel.id:
                channel.append(f"{interaction.user.voice.channel.id}")
                reserved_guild[f"{interaction.guild.id}"].append(f"{interaction.user.voice.channel.id}")
        elif interaction.guild.voice_client:
            await interaction.response.send_message("<:zunda:1277689238632267848> 既に参加してるのだ！", silent=True)
            return
        else:
            await interaction.response.send_message("<:zunda:1277689238632267848> VCに参加できないのだ", silent=True)
            return

    @tree.command(name="bye", description="VCから退出するのだ")
    async def bye_command(interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("既に抜けてるのだ", silent=True)
        elif interaction.guild.voice_client:
            if f"{interaction.guild_id}" in reserved_guild:
                for i in reserved_guild[f"{interaction.guild.id}"]:
                    channel.remove(i)
                await interaction.guild.voice_client.disconnect()
                await interaction.response.send_message("<:zunda:1277689238632267848> 退出するのだ", silent=True)
            else:
                await interaction.response.send_message("<:zunda:1277689238632267848> このコマンドは`/join`を使ったチャンネルで実行してほしいのだ！", silent=True)
    
    @tree.command(name="force-leave", description="強制的にVCから退出するのだ（/byeが動作しなくなったときにのみ使用してください）")
    async def force_leave_command(interaction: discord.Interaction):
        if interaction.guild.voice_client is None:
            await interaction.response.send_message("既に抜けてるのだ", silent=True)
        elif interaction.guild.voice_client:
            try:
                try:
                    channel.remove(f"{interaction.channel_id}")
                    channel.remove(f"{interaction.user.voice.channel.id}")
                    reserved_guild[f"{interaction.guild.id}"] = []
                except:
                    pass
                await interaction.guild.voice_client.disconnect()
                await interaction.response.send_message("<:zunda:1277689238632267848> 退出するのだ", silent=True)
            except:
                await interaction.response.send_message(":warning: 退出処理に失敗しました。管理者に連絡してください。", silent=True)

    @tree.command(name="dict", description="特定の単語の文字列を矯正できます。")
    async def dict_command(interaction: discord.Interaction, 書き: str, 読み: str):
        if interaction.user.name == 'makao1521':
            await interaction.response.send_message(gomi_omikuzi.gen())
            return
        書き = 書き.lower()
        読み = 読み.lower()
        if 書き == 読み:
            await interaction.response.send_message(content="<:zunda:1277689238632267848> 読みと書きは同じ文字列にできないのだ", delete_after=5, silent=True)
            return
        with open("./guild_dict.json", encoding="utf-8", mode="r") as f:
            guild_dict = dict(json.load(f))
        if not f'{interaction.guild_id}' in guild_dict:
            guild_dict.update({f'{interaction.guild_id}': {}})
        if f"{書き}" in guild_dict[f'{interaction.guild_id}']:
            action = "上書き"
        else:
            action = "設定"
        guild_dict[f'{interaction.guild_id}'].update({書き: 読み})
        updated_json = json.dumps(guild_dict, indent=4, ensure_ascii=False)
        with open('./guild_dict.json', 'w', encoding="utf-8") as file:
            file.write(updated_json)
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{書き}」の読み方を「{読み}」に{action}したのだ！")

    @tree.command(name="delete_dict", description="dictコマンドで登録した言葉を辞書から削除できるのだ")
    async def delete_dict(interaction: discord.Interaction, 書き: str):
        if interaction.user.name == 'makao1521':
            await interaction.response.send_message('ごめんなに？よく聞こえんかったわｗ')
            return
        書き = 書き.lower()
        with open("./guild_dict.json", encoding="utf-8", mode="r") as f:
            guild_dict = dict(json.load(f))
        if not f'{interaction.guild_id}' in guild_dict:
            await interaction.response.send_message("<:zunda:1277689238632267848> このサーバーではまだ辞書を作成してないのだ", ephemeral=True, delete_after=5)
            return
        if f"{書き}" in guild_dict[f'{interaction.guild_id}']:
            guild_dict[f'{interaction.guild_id}'].pop(f"{書き}")
            updated_json = json.dumps(guild_dict, indent=4, ensure_ascii=False)
            with open('./guild_dict.json', 'w', encoding="utf-8") as file:
                file.write(updated_json)
            await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{書き}」を辞書から削除したのだ")
        else:
            await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{書き}」は辞書に存在しないのだ", ephemeral=True, delete_after=5)

    @tree.command(name="ignore", description="特定の文字列が含まれていた場合に読み上げをスキップするのだ。もう一度同じ文字を指定すると削除できるのだ")
    async def ignore(interaction: discord.Interaction, 文字: str):
        if interaction.user.name == 'makao1521':
            await interaction.response.send_message('今忙しいから後にしてクレメンスｗｗｗｗｗｗｗｗｗ')
            return
        文字 = 文字.lower()
        with open("./ignore.json", encoding="utf-8", mode="r") as f:
            ignore = dict(json.load(f))
        if not f'{interaction.guild_id}' in ignore:
            ignore.update({f'{interaction.guild_id}': []})
        if not f"{文字}" in ignore[f'{interaction.guild_id}']:
            ignore[f'{interaction.guild_id}'].append(f"{文字}")
            updated_json = json.dumps(ignore, indent=4, ensure_ascii=False)
            with open('./ignore.json', 'w', encoding="utf-8") as file:
                file.write(updated_json)
            await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{文字}」をスキップ対象に設定したのだ")
        else:
            ignore[f'{interaction.guild_id}'].remove(f"{文字}")
            updated_json = json.dumps(ignore, indent=4, ensure_ascii=False)
            with open('./ignore.json', 'w', encoding="utf-8") as file:
                file.write(updated_json)
            await interaction.response.send_message(content=f"<:zunda:1277689238632267848> 「{文字}」をスキップ対象から削除したのだ")

    @tree.command(name="show_ignore", description="スキップ対象の文字列をすべて表示するのだ")
    async def show_ignore(interaction: discord.Interaction):
        with open("./ignore.json", encoding="utf-8", mode="r") as f:
            ignore = dict(json.load(f))
        if (not f'{interaction.guild_id}' in ignore):
            await interaction.response.send_message(content=f"<:zunda:1277689238632267848> このサーバーではスキップ対象の文字が設定されていないのだ。", ephemeral=True)
            return
        if len(ignore[f'{interaction.guild_id}']) == 0:
            await interaction.response.send_message(content=f"<:zunda:1277689238632267848> このサーバーではスキップ対象の文字が1つも設定されていないのだ。", ephemeral=True)
            return
        ignore_list = ""
        for l in ignore[f'{interaction.guild_id}']:
            ignore_list += f"{l}\n"
        await interaction.response.send_message(content=f"<:zunda:1277689238632267848> スキップ対象一覧なのだ\n```\n{ignore_list}```")

    @tree.command(name="preview_dict", description="あなたのサーバーにおける辞書を表示します")
    async def preview_dict(interaction: discord.Interaction):
        with open("./guild_dict.json", encoding="utf-8", mode="r") as f:
            guild_dict = dict(json.load(f))
        if not f'{interaction.guild_id}' in guild_dict:
            await interaction.response.send_message("<:zunda:1277689238632267848> このサーバーではまだ辞書を作成してないのだ", ephemeral=True, delete_after=5)
            return
        if len(guild_dict[f'{interaction.guild_id}']) == 0:
            await interaction.response.send_message(content="<:zunda:1277689238632267848> 登録されている単語が一つもないのだ。", ephemeral=True, delete_after=5)
            return
        res = ""
        for i in dict(guild_dict[f'{interaction.guild_id}']):
            res += f"{i}：{guild_dict[f'{interaction.guild_id}'][i]}\n"
        await interaction.response.send_message(f"### 書き：読み\n```{res}```", ephemeral=True)

    @tree.command(name="clear", description="キューを空にします。")
    async def clear_command(interaction: discord.Interaction):
        import config
        while not config.play_queue.empty():
            config.play_queue.get()
        await interaction.response.send_message("キューを空にしました。")

    @tree.command(name="help", description="Botの説明をするのだ")
    async def help_command(interaction: discord.Interaction):
        embed = discord.Embed(title="使用方法", description="")
        embed.add_field(name='概要', inline=False, value='`/join`を実行したテキストチャンネルのメッセージを参加したVCで読み上げるのだ！')
        embed.add_field(name='コマンド - 基本', inline=False, value='')
        embed.add_field(name='`/join`', value='コマンドを実行したテキストチャンネルのメッセージを参加先のVCで読み上げるのだ！')
        embed.add_field(name='`/bye`', value='VCから退出するのだ！')
        embed.add_field(name='`/mode`', value='喋り方を変更できるのだ！')
        embed.add_field(name='`/speed`', value='喋る速度を変更できるのだ！')
        embed.add_field(name='`/help`', value='このパネルを表示できるのだ！')
        embed.add_field(name='コマンド - 辞書', inline=False, value='')
        embed.add_field(name='`/dict`', value='サーバー固有の読ませ方をしたい言葉を登録できるのだ。')
        embed.add_field(name='`/delete_dict`', value='登録した言葉を辞書から削除できるのだ。')
        embed.add_field(name='`/preview_dict`', value='作成した辞書を表示できるのだ。')
        embed.add_field(name='`/reminder`', value='特定の時間になったら指定されたメッセージを通知するのだ。')
        embed.add_field(name='`/force-leave`', value='BotがVCから退出できなくなったときに使用してほしいのだ。それでも解決しなければ、管理者に連絡してほしいのだ。')
        embed.add_field(name='`/clear`', value='キューの中身を全て空にします')
        view = MyView(url="https://voicevox.hiroshiba.jp/term/", label="利用規約")
        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)

    @tree.command(name="mode", description="喋り方を変えられるのだ")
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
        voice_mode.update({f"{interaction.guild.id}": mode})
        await interaction.response.send_message(f"<:zunda:1277689238632267848> 喋り方を「{モード.name}」に設定したのだ！")

    @tree.command(name="speed", description="喋る速度を変えられるのだ")
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
        voice_speed.update({f"{interaction.guild.id}": mode})
        await interaction.response.send_message(f"<:zunda:1277689238632267848> 喋る速度を「{スピード.name}」に設定したのだ！")

    @tree.command(name="reminder", description="特定の時間になったら任意の言葉を喋るのだ")
    async def reminder_command(interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(content="このコマンドはサーバー限定です。", ephemeral=True)
            return
        await interaction.response.send_modal(RemindeModal())

    @tree.command(name="issue", description="Botに問題が発生したときにエラーの詳細を報告できるのだ。")
    @app_commands.describe(カテゴリ="次から選択してほしいのだ")
    @app_commands.choices(カテゴリ=[
        discord.app_commands.Choice(name="バグ", value=0),
        discord.app_commands.Choice(name="要望", value=1),
    ])
    async def issue_command(interaction: discord.Interaction, カテゴリ: discord.app_commands.Choice[int]):
        await interaction.response.send_modal(IssueModal(select_type=カテゴリ.value)) 