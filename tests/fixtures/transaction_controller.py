"""Run the production transaction/controller under its real outer supervisor."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mission_transaction as tx
from mission_execution import Registry
from isolated_controller import Launcher
from transaction_storage import registry_storage

request = json.load(sys.stdin)
with registry_storage(request['registry']):
    registry = Registry(request['registry'])
    record = tx.load(registry, request['operation_id'])
    root = Path(request['root'])
    calls = 0


    def factory(phase):
        directory = root/'.runtime'/('transaction-'+phase)
        directory.mkdir(parents=True, exist_ok=True)
        mode = 'unattributed_block' if phase == 'B' else 'success'
        if request.get('mode') == 'lost_response' and phase == 'A':
            mode = 'bad_echo'
        return Launcher(mode, directory)


    def observe():
        global calls
        calls += 1
        value = copy.deepcopy(record['plan']['baseline'])
        value['observations']['candidate_inspect']['state'] = 'running'
        value['observations']['sandbox_inventory']['sandboxes'][0]['status'] = 'running'
        if request.get('mode') == 'drift' and calls > 1:
            value['observations']['setting_proxy_sandbox']['value'] = 'external'
        return value


    result = tx.run_reserved(root, registry, request['operation_id'], factory, observe)
    print(json.dumps(result), flush=True)
