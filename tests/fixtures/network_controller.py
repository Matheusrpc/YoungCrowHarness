"""Production coordinator, pipes, ledger and sockets; only sbx/upstream are local."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests'))
from fixtures.isolated_controller import Launcher
from fixtures.transaction_storage import registry_storage
from test_mission_network import SettingsFixture
import mission_execution as execution
import mission_egress as egress
import mission_network as network
import mission_transaction as tx


class LocalGuard(egress.Guard):
    def command(self):
        return [sys.executable,'-I','-B',str(Path(__file__).with_name('egress_controller.py')),'--guard-local']


class LocalNetwork(network.Network):
    def start_guard(self, config, persist):
        return LocalGuard(config,persist,cwd=self.cwd)

    def after_phase(self, phase):
        try:
            super().after_phase(phase)
        except BaseException as error:
            self.failure = type(error).__name__+':'+str(error)
            raise


request = json.load(sys.stdin)
with registry_storage(request['registry']):
    registry = execution.Registry(request['registry'])
    record = tx.load(registry,request['operation_id'])
    backend = SettingsFixture(record['plan'],registry)
    coordinator = LocalNetwork(registry,request['operation_id'],backend,cwd=request['root'])
    def factory(phase):
        directory = Path(request['root'])/'.runtime'/('network-'+phase)
        directory.mkdir(parents=True,exist_ok=True)
        ready = network.entry(coordinator.record(),'guard_ready')
        (directory/'loopback-network.json').write_text(json.dumps(dict(port=ready['port'],phase=phase)))
        backend.active = True
        backend._state()
        if request.get('mode') == 'drift':
            backend.current['observations']['setting_proxy_sandbox']['value'] = 'external'
        return Launcher('unattributed_block' if phase == 'B' else 'success',directory)
    result = tx.run_reserved(Path(request['root']),registry,request['operation_id'],factory,backend.observe,network=coordinator)
    print(json.dumps(dict(result=result,current=backend.current,effects=backend.effects,
                         failure=getattr(coordinator,'failure',None))),flush=True)
