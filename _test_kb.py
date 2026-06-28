import sys
sys.path.insert(0, r'D:\CBD\TORChecklist')
from backend.services.knowledge_base import build_tor_knowledge_base

kb = build_tor_knowledge_base(force_rebuild=True)
total_patterns = sum(len(ex['rows']) for ex in kb['checklist_examples'])
print(f"Total pattern rows learned: {total_patterns}")
print(f"Categories: {len(kb['category_names'])}")
print(f"Doc types: {len(kb['document_types'])}")
for ex in kb['checklist_examples']:
    print(f"  {ex['source']}: {len(ex['rows'])} rows")
