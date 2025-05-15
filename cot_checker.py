import json

# Load files
with open('dataset/possible_uris/saya_pusing.json', 'r', encoding='utf-8') as f:
    saya_pusing = json.load(f)

with open('dataset/possible_uris/qald_9_plus_train_wikidata_converted_labels_possible_uris_modified.json', 'r', encoding='utf-8') as f:
    qald_9 = json.load(f)

# 1. Ensure all questions in saya_pusing are unique
saya_pusing_questions = [item['question'] for item in saya_pusing]
unique_saya_pusing_questions = set(saya_pusing_questions)

if len(saya_pusing_questions) == len(unique_saya_pusing_questions):
    print("All questions in saya_pusing.json are unique.")
else:
    print("Duplicate questions found in saya_pusing.json!")
    # Print duplicates
    from collections import Counter
    counts = Counter(saya_pusing_questions)
    duplicates = [q for q, c in counts.items() if c > 1]
    print("Duplicates:", duplicates)

# 2. Check all qald_9 questions are in saya_pusing
qald_9_questions = [item['question'] for item in qald_9]

missing = [q for q in qald_9_questions if q not in unique_saya_pusing_questions]

if not missing:
    print("All questions in qald_9_plus_train are present in saya_pusing.json.")
else:
    print("These questions from qald_9_plus_train are missing in saya_pusing.json:")
    for q in missing:
        print("-", q)