import os
import json

d = 'mongodb_seed'
for fn in os.listdir(d):
    if not fn.endswith('.json'): continue
    p = os.path.join(d, fn)
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    changed = False
    if type(data) is list:
        for obj in data:
            if '_id' in obj and 'id' not in obj:
                obj['id'] = obj['_id']
                changed = True
            if 'node_type' in obj:
                obj['type'] = obj.pop('node_type')
                changed = True
    if changed:
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
print("Done repairing JSONs.")
