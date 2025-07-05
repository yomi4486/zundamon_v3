import json
import re
from urlextract import URLExtract
from config import DIC_FILE, logger

extractor = URLExtract()  # URL読み上げると長いから抜き出すためのやつ

# カタカナ辞書の読み込み
kana_dict = {}
with open(DIC_FILE, mode='r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if i >= 6:
            line_list = line.replace('\n', '').split(' ')
            kana_dict[line_list[0]] = line_list[1]

def guild_dict_translate(base_text: str, id: str):
    """
    base_text: ベーステキスト
    id: guild_id(discord)
    """
    base_text = base_text.lower()
    with open("./guild_dict.json", encoding="utf-8", mode="r") as f:
        guild_dict = dict(json.load(f))
    if f"{id}" in guild_dict:
        for d in guild_dict[f"{id}"]:
            base_text = base_text.replace(d, guild_dict[f"{id}"][f"{d}"])
    return base_text

def eng_to_kana(base_text: str):
    """英語をカタカナに変換"""
    pattern = r'[a-zA-Z]+'
    base_text = base_text.upper()
    matches = re.findall(pattern, base_text, re.DOTALL)
    for m in matches:
        if f"{m}" in kana_dict:
            base_text = base_text.replace(f"{m}", f"{kana_dict[m]}", 1)
    return base_text.lower()

def seikei(text: str):
    """テキストを整形して読み上げ用に変換"""
    text = text.lower()
    url = extractor.find_urls(text)
    for i in url:
        text = text.replace(f"{i}", "URL ")
    
    text = text.replace("\n", " ").replace("_", " ").replace("-", " ").replace("(", " ").replace(")", " ").replace("{", " ").replace("}", " ").replace("[", " ").replace("]", " ").replace('"', " ").replace("/", "")
    text = eng_to_kana(text)  # 英語をカタカナ英語に変換
    
    with open('./word_dict.json', 'r', encoding="utf-8") as file:
        word_dict = dict(json.load(file))
    for d in word_dict:
        text = text.replace(d, word_dict[d])
    
    mention = re.findall(r'<@(.*?)>', f"{text}", re.DOTALL)
    for m in mention:
        text = text.replace(f"<@{m}>", "メンション ")
    
    channels = re.findall(r'<#(.*?)>', f"{text}", re.DOTALL)
    for c in channels:
        text = text.replace(f"<#{c}>", "チャンネル ")
    
    emoji_list = re.findall(r"<:(.*?)>", text, re.DOTALL)
    for e in emoji_list:
        text = text.replace(f"<:{e}>", "")
    
    ignore_list = re.findall(r"\|\|(.*?)\|\|", text, re.DOTALL)
    for e in ignore_list:
        text = text.replace(f"||{e}||", "(秘密のメッセージ)")
    
    code_list = re.findall(r"```(.*?)```", text, re.DOTALL)
    for e in code_list:
        text = text.replace(f"```py{e}```", "Pythonコードスニペット").replace(f"```js{e}```", "JSコードスニペット").replace(f"```rs{e}```", "ラストコードスニペット").replace(f"```sh{e}```", "シェルコードスニペット").replace(f"```{e}```", "コードスニペット")
    
    if "wwwww" in text or "ｗｗｗｗｗ" in text:
        text = text.replace("ｗ", "").replace("w", "")
    
    return text 