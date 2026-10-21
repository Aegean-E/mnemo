# mnemo

## ⚡ 30-Second Cold-Start Quick Reference

- **Runtime Prerequisites**: <FILL: each runtime this project needs and its minimum version>
- **Canonical Regression Shield Gate**:
  ```bash
  python -m unittest discover
  ```

### 🛠️ AIKit Commands (run from the AIKit folder)
| Role | Command |
|---|---|
| Status, task and gates | `python aikit.py status mnemo` |
| Phase 4: every gate | `python aikit.py check mnemo` |
| Repair memory and map, then check | `python aikit.py fix mnemo` |
| Resume an interrupted task | `python aikit.py resume mnemo` |

## 📦 What's Inside

```text
mnemo/
├── .gitignore                <- transient AIKit state excluded
├── README.md
└── .aikit/                   <- this project's memory: record, ledger, decisions
```
