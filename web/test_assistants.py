import time, json, uuid, urllib.request, urllib.error
from server import get_token, WORKSPACE_ID

token = get_token()
agent_id = 'e8fc166b-360e-4b0a-922b-05ca8bba3ff4'
base = f'https://msitapi.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/dataagents/{agent_id}/aiassistant/openai'
api_v = 'api-version=2024-05-01-preview'

def api(method, path, body=None):
    url = f'{base}/{path}?{api_v}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'ActivityId': str(uuid.uuid4()),
    }, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

# 1. Create assistant
print('1. Creating assistant...')
asst = api('POST', 'assistants', {'model': 'not used'})
asst_id = asst['id']
print(f'   Assistant: {asst_id}')

# 2. Create thread
print('2. Creating thread...')
thread = api('POST', 'threads', {})
thread_id = thread['id']
print(f'   Thread: {thread_id}')

# 3. Add message
print('3. Adding message...')
msg = api('POST', f'threads/{thread_id}/messages', {
    'role': 'user',
    'content': 'What are the top 3 stores by total revenue?'
})
print('   Message added')

# 4. Create run
print('4. Starting run...')
run = api('POST', f'threads/{thread_id}/runs', {'assistant_id': asst_id})
run_id = run['id']
print(f'   Run: {run_id}, status: {run["status"]}')

# 5. Poll until done
print('5. Polling...')
for i in range(30):
    time.sleep(3)
    run = api('GET', f'threads/{thread_id}/runs/{run_id}')
    status = run['status']
    print(f'   [{i*3}s] status: {status}')
    if status not in ('queued', 'in_progress'):
        break

# 6. Get messages
print('6. Getting response...')
msgs = api('GET', f'threads/{thread_id}/messages')
for m in msgs.get('data', []):
    role = m.get('role', '?')
    content = m.get('content', [])
    if content:
        c = content[0]
        if isinstance(c, dict) and 'text' in c:
            txt = c['text']
            if isinstance(txt, dict):
                txt = txt.get('value', str(txt))
            print(f'   [{role}]: {txt[:800]}')
        else:
            print(f'   [{role}]: {str(c)[:500]}')

print('\nDONE!')
