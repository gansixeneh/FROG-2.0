import json
from collections import Counter

# Load files
with open('dataset/possible_uris/train_cot.json', 'r', encoding='utf-8') as f:
    train_cot = json.load(f)

with open('dataset/possible_uris/qald_9_plus_train_wikidata_converted_labels_noises_possible_uris_modified.json', 'r', encoding='utf-8') as f:
    qald_9 = json.load(f)

# 1. Ensure all questions in train_cot are unique
train_cot_questions = [item['question'] for item in train_cot]
unique_train_cot_questions = set(train_cot_questions)

if len(train_cot_questions) == len(unique_train_cot_questions):
    print("All questions in train_cot.json are unique.")
else:
    print("Duplicate questions found in train_cot.json!")
    counts = Counter(train_cot_questions)
    duplicates = [q for q, c in counts.items() if c > 1]
    print("Duplicates:", duplicates)

# 2. Check all qald_9 questions are in train_cot
qald_9_questions = [item['question'] for item in qald_9]
missing = [q for q in qald_9_questions if q not in unique_train_cot_questions]

if not missing:
    print("All questions in qald_9_plus_train are present in train_cot.json.")
else:
    print("These questions from qald_9_plus_train are missing in train_cot.json:")
    for q in missing:
        print("-", q)

# 3. Update train_cot with all attributes from qald_9
# Build a mapping from question to train_cot entry
train_cot_map = {item['question']: item for item in train_cot}

updated = False
for qald_item in qald_9:
    q = qald_item['question']
    if q in train_cot_map:
        for k, v in qald_item.items():
            train_cot_map[q][k] = v
            updated = True

if updated:
    # Save the updated train_cot.json
    with open('dataset/possible_uris/train_cot.json', 'w', encoding='utf-8') as f:
        json.dump(list(train_cot_map.values()), f, ensure_ascii=False, indent=2)
    print("train_cot.json updated with all attributes from qald_9_plus_train.")
else:
    print("No updates needed; all attributes already present.")