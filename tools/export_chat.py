"""Export this chat's visible user/assistant messages verbatim, in source order.

No system/developer messages, reasoning, or private application metadata are exported.
Re-run after a turn ends to include the newly persisted final answer.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os

parser = argparse.ArgumentParser()
parser.add_argument('--thread-id', default=os.environ.get('CODEX_THREAD_ID', '01a1da0d-fee1-7220-a535-12eed796f3db'))
args = parser.parse_args()
source_dir = Path.home()/'.codex/sessions'
matches = list(source_dir.rglob('*'+args.thread_id+'*.jsonl'))
if len(matches) != 1:
    raise SystemExit(f'Expected exactly one current-chat log, found {len(matches)}')
source = matches[0]
messages = []
for raw in source.read_text(encoding='utf-8').splitlines():
    event = json.loads(raw)
    p = event.get('payload', {})
    if event.get('type') == 'response_item' and p.get('type') == 'function_call' and 'request_user_input' in p.get('name', ''):
        messages.append({'role': 'assistant', 'text': '【用户可见的提问工具；以下为原始提问参数】\n\n' + p.get('arguments', ''),
                         'timestamp': event.get('timestamp'), 'phase': 'visible_question'})
        continue
    if event.get('type') != 'response_item' or p.get('type') != 'message':
        continue
    role = p.get('role')
    if role not in {'user', 'assistant'}:
        continue
    parts = [c.get('text', '') for c in p.get('content', []) if c.get('type') in {'input_text', 'output_text'}]
    body = '\n'.join(parts)
    if not body or body.lstrip().startswith('<environment_context>'):
        continue
    messages.append({'role': role, 'text': body, 'timestamp': event.get('timestamp'), 'phase': p.get('phase')})

out = Path(__file__).resolve().parent.parent/'collaboration'
out.mkdir(exist_ok=True)
stamp = datetime.now(timezone.utc).isoformat()
chunks = ['# AI 协作聊天记录（持续更新）',
          f'聊天标识：{args.thread_id}\n\n导出时间（UTC）：{stamp}',
          '范围：截至本次导出时，应用日志已落盘的用户与助手可见文字消息，按原始顺序保留；不改写、不补写。工具执行日志不包含在本文件中，实验脚本与产物另存。运行中的最后一条回复可能尚未落盘，请在本轮结束后重新运行导出脚本。此文件不是已经完结的作业全流程记录。']
for i, message in enumerate(messages, 1):
    title = '用户' if message['role'] == 'user' else 'AI 助手'
    chunks.extend([f"## {i}. {title}（{message['timestamp']}）", message['text']])
(out/'chat.md').write_text('\n\n'.join(chunks)+'\n', encoding='utf-8')
manifest = {'thread_id': args.thread_id, 'exported_at_utc': stamp, 'message_count': len(messages),
            'messages_sha256': hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
            'publication_status': 'export snapshot; publication is checked separately in the repository',
            'completion_status': 'snapshot of an ongoing conversation'}
(out/'export_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(manifest, ensure_ascii=False, indent=2))
