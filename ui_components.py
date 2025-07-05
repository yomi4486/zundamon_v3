import discord
import datetime
import json
from config import reminde_json, logger

class MyView(discord.ui.View):
    def __init__(self, url: str = "https://xenfo.org", label: str = "xenfo.org"):
        super().__init__()
        # URLを含むボタンを作成
        self.add_item(discord.ui.Button(label=f"{label}", url=f"{url}"))

class RemindeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="リマインダーの設定をしてほしいのだ", timeout=None, custom_id="reminde")
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
            await interaction.response.send_message("過去の時間を指定することはできないのだ。", ephemeral=True)
            return
        await interaction.response.send_message(f"{day_time[0]}/{day_time[1]}/{day_time[2]} {time[0]}:{time[1]}に\n「{self.content.value}」\nと通知するのだ。")
        
        new_dict = {
            "channel_id": f"{interaction.channel_id}",
            "content": f"{self.content.value}",
            "interaction_user_id": f"{interaction.user.id}"
        }
        now_time_recode = f"{int(day_time[0])}/{int(day_time[1])}/{int(day_time[2])}/{(int(time[0])*60)+(int(time[1]))}"
        reminde_json.update({now_time_recode: []})
        reminde_json[f"{now_time_recode}"].append(new_dict)
        return

class IssueModal(discord.ui.Modal):
    def __init__(self, select_type: int):
        super().__init__(title=f"{['起こっている問題','要望'][select_type]}を詳しく教えてほしいのだ", timeout=None, custom_id="issue")
        self.content = discord.ui.TextInput(
            label="内容",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000,
            row=2,
            custom_id="content"
        )
        self.select_type = select_type
        self.add_item(self.content)
    
    async def on_submit(self, interaction: discord.Interaction):
        with open(f"./issues/{['bug','documents'][self.select_type]}.txt", "a", encoding="utf-8") as f:
            f.write(f"\n{interaction.user.name}\n{self.content.value}")
        embed = discord.Embed(title="問題の報告が完了したのだ。", description="")
        embed.add_field(name=f"カテゴリ：{['バグ','要望'][self.select_type]}", value="")
        embed.add_field(name='内容', inline=False, value=self.content.value)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return 