import os
import re

for root, _, files in os.walk('backend/app/services'):
    for f in files:
        if not f.endswith('.py'): continue
        p = os.path.join(root, f)
        text = open(p, 'r', encoding='utf-8').read()
        
        text2 = re.sub(
            r'int\(\s*highest\["id"\]\[(\d+):\]\s*\)', 
            'int(highest["id"].split("_")[1]) if len(highest["id"].split("_")) > 1 and highest["id"].split("_")[1].isdigit() else 0', 
            text
        )
        text3 = re.sub(
            r'int\(\s*highest_exp\["id"\]\[(\d+):\]\s*\)', 
            'int(highest_exp["id"].split("_")[1]) if len(highest_exp["id"].split("_")) > 1 and highest_exp["id"].split("_")[1].isdigit() else 0', 
            text2
        )
        text4 = re.sub(
            r'int\(\s*highest_evt\["id"\]\[(\d+):\]\s*\)', 
            'int(highest_evt["id"].split("_")[1]) if len(highest_evt["id"].split("_")) > 1 and highest_evt["id"].split("_")[1].isdigit() else 0', 
            text3
        )
        
        if text != text4:
            open(p, 'w', encoding='utf-8').write(text4)
            print(f'Fixed {p}')
