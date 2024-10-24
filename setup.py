import json,os
if not os.path.exists('./guild_dict.json'):
    with open('./guild_dict.json', 'w',encoding="utf-8") as file:
        file.write(json.dumps({}, indent=4,ensure_ascii = False))

if not os.path.exists('./word_dict.json'):
    with open('./word_dict.json', 'w',encoding="utf-8") as file:
        file.write(json.dumps({"github":"ギットハブ"}, indent=4,ensure_ascii = False))

if not os.path.exists('./ignore.json'):
    with open('./ignore.json', 'w',encoding="utf-8") as file:
        file.write(json.dumps({}, indent=4,ensure_ascii = False))