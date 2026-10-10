"""Exercise installed mission commands in new/existing disposable trial consumers."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

from smoke_adoption import ROOT, smoke, run, write
from mission_fixtures import MissionCase
from test_mission_config import configured
import document_store


def check(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mission_smoke(root, client, extra_check=None):
    outcomes, retained = [], {}

    def prepare_existing(project, case, env):
        for args in (('init', '--mode', 'existing', '--run', 'before-harness'),
                     ('feature', '--slug', 'legacy', '--run', 'before-harness')):
            run([sys.executable, '-B', str(ROOT / 'scripts/personalize.py'), *args], env=env, cwd=project)
        write(project / 'youngcrow/agents.json', json.dumps(configured()).encode())
        for name in ('vault/project.json', 'vault/product/profile.md',
                     'vault/features/legacy/index.md', 'youngcrow/agents.json'):
            retained[name] = digest(project / name)

    def exercise(project, case, env):
        mode = 'new' if case == 'absent' else 'existing'
        if mode == 'new':
            run([shutil.which('git'), 'init', '-q'], env=env, cwd=project)
        else:
            for name, value in retained.items():
                check(digest(project / name) == value, 'adoption_changed_existing_file')
            check((project / 'CLAUDE.md').read_bytes() == b'Original instructions\n', 'instructions_changed')
            check((project / '.codex/config.toml').read_bytes() == b'# Original config\n', 'native_config_changed')
        run([sys.executable, '-B', 'scripts/personalize.py', 'init', '--mode', mode,
             '--run', 'mission-smoke'], env=env, cwd=project)
        # Migration preserves the old index. The authorized adaptation links newly installed sections.
        reconcile = """import sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from document_store import append_link
for name in ('capabilities', 'integrations'):
    append_link(Path.cwd(), 'vault/index.md', f'[{name}]({name}/index.md)')
"""
        run([sys.executable, '-B', '-c', reconcile], env=env, cwd=project)

        def cli(*args, expected=0):
            return json.loads(run([sys.executable, '-B', 'scripts/missions.py', '--json', *args],
                                  env=env, cwd=project, expected=expected))

        current = cli('config', 'show')
        candidate = 'vault/local/agents-draft.json'
        write(project / candidate, json.dumps(configured()).encode())
        validated = cli('config', 'validate', '--input', candidate)
        check(not validated['gaps'], 'incomplete_config')
        check(set(validated['compatibility'].values()) == {'not_verified'}, 'false_native_compatibility')
        cli('config', 'apply', '--input', candidate, '--expected-digest', current.get('digest', 'absent'))
        # Shared fixture helpers only author synthetic notes. Every state change uses installed code.
        fixture = MissionCase()
        fixture.root, fixture.store = project, document_store
        fixture.project_id = json.loads((project / 'vault/project.json').read_text())['project_id']
        paths = fixture.tree(features=2, pbis=2)
        from integrations import note
        plan_path = 'vault/local/technical-plan.md'
        plan_bytes = note(fixture.project_id, plan_path, 'decision', 'Synthetic technical plan', 'index.md',
                          '# Synthetic plan\n\n[Index](index.md)\n\nImplement within the existing criteria.\n',
                          '2026-10-10T00:00:00+00:00').encode()
        write(project / plan_path, plan_bytes)
        document_store.append_link(project, 'vault/local/index.md', '[Technical plan](technical-plan.md)')
        first_pbi_path = next(p for p in paths if '/pbis/' in p)
        fixture.contract(first_pbi_path, references=[dict(note_id=fixture.item_id(plan_path), path=plan_path)])
        if mode == 'existing':
            paths.append('vault/features/legacy/index.md')
        for path in paths:
            role = 'tech_lead' if '/pbis/' in path else 'pm'
            cli('backlog', 'import', '--note', path, '--expected-revision', '0',
                '--operation-id', str(uuid.uuid4()), '--actor-id', 'fixture', '--actor-role', role)
        features = [fixture.item_id(p) for p in paths if '/local/product/features/' in p]
        pbis = [fixture.item_id(p) for p in paths if '/pbis/' in p]
        mission_path = 'vault/local/mission-request.json'
        request = dict(title='Synthetic mission', feature_ids=features[:1], priority=pbis[:2],
                       overrides={}, scope_reference='Approved synthetic smoke only')
        actor = ('--actor-id', 'fixture', '--actor-role', 'pm')

        def prepare(operation):
            return cli('prepare', '--input', mission_path, '--operation-id', operation, *actor)

        write(project / mission_path, json.dumps(request).encode())
        first = prepare(str(uuid.uuid4()))
        frozen = cli('status', first['code'])
        check(frozen['state'] == 'prepared' and len(frozen['snapshot']['pbi_ids']) == 2, 'single_feature_failed')
        request.update(feature_ids=features, priority=pbis)
        write(project / mission_path, json.dumps(request).encode())
        operation = str(uuid.uuid4())
        second = prepare(operation)
        repeated = prepare(operation)
        check(second['event_id'] == repeated['event_id'] and second['sequence'] == repeated['sequence'], 'duplicate_event')
        many = cli('status', second['code'])
        check(many['state'] == 'prepared' and len(many['snapshot']['pbi_ids']) == 4, 'multi_feature_failed')
        check(many['snapshot']['config']['limits']['max_active_pbis'] == 3, 'wip_is_not_total')
        check([p['id'] for p in many['queue_preview']['items']] == pbis, 'preview_priority_incorrect')
        check(many['queue_preview']['scope'] == 'initial_backlog' and
              many['queue_preview']['first_candidate_id'] == pbis[0], 'initial_candidate_incorrect')
        check(len(many['events']) == 1, 'duplicate_mission_event')
        inventory_before = fixture.snapshot()
        inventory = cli('list')
        check([entry['id'] for entry in inventory['missions']] == [first['record_id'], second['record_id']],
              'mission_inventory_incorrect')
        discovered = inventory['missions'][1]
        check(cli('status', discovered['code'])['id'] == discovered['id'], 'mission_discovery_failed')
        check(fixture.snapshot() == inventory_before, 'mission_discovery_wrote_files')
        context = cli('context', second['code'], '--pbi', pbis[0], '--expected-revision', '1')
        check([item['kind'] for item in context['items']] == ['epic', 'feature', 'pbi'], 'context_ancestry_incorrect')
        check(context['pbi_id'] == pbis[0] and not context['runnable'], 'context_scope_incorrect')
        expected_sources = {r['snapshot']['note_path'] for r in context['items']} | {'vault/product/profile.md', plan_path}
        check({source['path'] for source in context['sources']} == expected_sources, 'context_leaked_other_items')
        for source in context['sources']:
            check(source['content'].encode('utf-8') == (project / source['path']).read_bytes() and
                  source['sha256'] == digest(project / source['path']), 'context_source_mismatch')
        check(cli('context', second['code'], '--pbi', pbis[0], '--expected-revision', '2', expected=1)
              ['error'] == 'revision_conflict', 'context_accepted_wrong_revision')
        check(fixture.snapshot() == inventory_before, 'context_wrote_files')
        proposal_path = 'vault/local/priority-proposal.json'
        proposal = dict(schema_version=1, project_id=fixture.project_id, mission_id=second['record_id'],
                        mission_revision=1, priority=list(reversed(pbis)), reason='Synthetic planning priority')
        write(project / proposal_path, json.dumps(proposal).encode())
        priority_args = ('reprioritize', '--input', proposal_path, '--operation-id', str(uuid.uuid4()), *actor)
        before_priority = fixture.snapshot()
        preview = cli(*priority_args, '--dry-run')
        check(preview['state'] == 'preview' and fixture.snapshot() == before_priority, 'priority_preview_wrote_files')
        priority_receipt = cli(*priority_args)
        check(priority_receipt['revision'] == 2 and cli(*priority_args) == priority_receipt, 'priority_replay_failed')
        reordered = cli('status', second['code'])
        changed = dict(reordered['snapshot'])
        check(changed.pop('last_planning_decision') == dict(action='reprioritize', reason=proposal['reason']) and
              changed.pop('priority') == proposal['priority'], 'priority_decision_incorrect')
        check(changed == {k: v for k, v in many['snapshot'].items() if k != 'priority'}, 'priority_changed_scope')
        check(len(reordered['events']) == 2 and not reordered['runnable'], 'priority_started_runtime')
        technical = dict(schema_version=1, project_id=fixture.project_id, mission_id=second['record_id'],
                         mission_revision=2, pbi_id=pbis[0], pbi_revision=1, reason='Synthetic plan selection',
                         plan_reference=dict(note_id=fixture.item_id(plan_path), path=plan_path, sha256=digest(project / plan_path)))
        technical_path = 'vault/local/technical-proposal.json'
        write(project / technical_path, json.dumps(technical).encode())
        technical_args = ('technical-plan', '--input', technical_path, '--operation-id', str(uuid.uuid4()),
                          '--actor-id', 'fixture-tl', '--actor-role', 'tech_lead')
        before_plan = fixture.snapshot()
        check(cli(*technical_args, '--dry-run')['state'] == 'preview' and fixture.snapshot() == before_plan,
              'technical_preview_wrote_files')
        technical_receipt = cli(*technical_args)
        check(technical_receipt['revision'] == 3 and cli(*technical_args) == technical_receipt, 'technical_replay_failed')
        selected = cli('context', second['code'], '--pbi', pbis[0], '--expected-revision', '3')
        check(selected['technical_decision']['plan_reference'] == technical['plan_reference'], 'technical_context_missing')
        check(cli('context', second['code'], '--pbi', pbis[1], '--expected-revision', '3')['technical_decision'] is None,
              'technical_context_wrong_pbi')
        after_plan = cli('status', second['code'])['snapshot']
        after_plan.pop('technical_decisions')
        check(after_plan == reordered['snapshot'] and (project / plan_path).read_bytes() == plan_bytes, 'technical_plan_changed_scope')
        defaults = cli('config', 'show')
        updated = defaults['config']
        updated['agents']['pm']['model'] = 'fixture-b'
        write(project / candidate, json.dumps(updated).encode())
        cli('config', 'apply', '--input', candidate, '--expected-digest', defaults['digest'])
        after = cli('status', first['code'])
        check(after['snapshot'] == frozen['snapshot'] and not after['stale_inputs'], 'defaults_rewrote_mission')
        request['title'] = 'Projection recovery'
        write(project / mission_path, json.dumps(request).encode())
        recovery_operation = str(uuid.uuid4())
        injection = '''import json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'scripts')
import missions
with patch('missions.project_receipt', side_effect=OSError('synthetic interruption')):
    result = missions.prepare_mission(Path.cwd(), json.loads(Path(sys.argv[1]).read_text()), sys.argv[2], dict(id='fixture', role='pm'))
print(json.dumps(result))
'''
        pending = json.loads(run([sys.executable, '-B', '-c', injection, mission_path, recovery_operation], env=env, cwd=project))
        check(pending['projection_state'] == 'pending', 'fault_not_observed')
        before_read = fixture.snapshot()
        pending_status = cli('status', pending['code'], expected=1)
        check(pending_status['projection_state'] == 'pending' and fixture.snapshot() == before_read, 'status_wrote_files')
        check(pending_status['queue_preview']['first_candidate_id'] is None, 'pending_projection_selected_candidate')
        recovered = prepare(recovery_operation)
        check(recovered['event_id'] == pending['event_id'] and recovered['projection_state'] == 'current', 'recovery_failed')
        repaired = cli('repair', recovered['code'])
        final = cli('status', recovered['code'])
        check(repaired['projection_state'] == 'current' and len(final['events']) == 1, 'repair_duplicated_event')
        for status in (frozen, many, final):
            check(not status['runtime_available'] and not status['runnable'], 'runtime_started')
        if mode == 'existing':
            for name in retained:
                if name != 'youngcrow/agents.json':
                    check(digest(project / name) == retained[name], 'legacy_content_changed')
        if extra_check:
            extra_check(project, case, env, first['record_id'])
        freezing = '''import json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, 'scripts')
import missions
root = Path.cwd()
profile = root / 'vault/product/profile.md'
original_bytes = profile.read_bytes()
original_freeze = missions.frozen_inputs
def changed(root, items):
    profile.write_bytes(original_bytes + b'\\nChanged during prepare\\n')
    return original_freeze(root, items)
try:
    with patch('missions.frozen_inputs', side_effect=changed):
        result = missions.prepare_mission(root, json.loads(Path(sys.argv[1]).read_text()),
                                          sys.argv[2], dict(id='fixture', role='pm'))
finally:
    profile.write_bytes(original_bytes)
print(json.dumps(result))
'''
        raced = json.loads(run([sys.executable, '-B', '-c', freezing, mission_path, str(uuid.uuid4())], env=env, cwd=project))
        before_read = fixture.snapshot()
        inconsistent = cli('status', raced['code'])
        check(inconsistent['state'] == 'draft' and not inconsistent['check_available'] and
              inconsistent['stale_inputs'] == ['vault/product/profile.md'] and
              'stale_input:vault/product/profile.md' in inconsistent['gaps'], 'mixed_input_mission_accepted')
        check(inconsistent['queue_preview']['first_candidate_id'] is None and fixture.snapshot() == before_read,
              'mixed_input_status_changed_state')
        cli('revise', raced['code'], '--input', mission_path, '--expected-revision', '1',
            '--operation-id', str(uuid.uuid4()), *actor)
        check(cli('status', raced['code'])['check_available'], 'explicit_consistent_revision_failed')
        vault = json.loads(run([sys.executable, '-B', 'scripts/vault.py', 'check', '--json'], env=env, cwd=project))
        check(vault['issues'] == [], 'vault_invalid')
        outcomes.append(dict(mode=mode, project_id=fixture.project_id, features=2, pbis=4,
                             mission_codes=[first['code'], second['code'], recovered['code']],
                             existing_hashes_preserved=mode == 'existing', legacy_hashes=retained if mode == 'existing' else {},
                             snapshots_frozen=True, replay_without_duplicate=True,
                             read_only_status=True, read_only_discovery=True, initial_queue_preview=True,
                             selected_pbi_context=True, context_without_writes=True,
                             restricted_pm_priority=True, priority_preview_without_writes=True,
                             selected_technical_plan=True, technical_preview_without_writes=True,
                             inconsistent_inputs_blocked=True, explicit_consistent_revision=True,
                             projection_recovered=True, vault_notes=vault['notes_checked'],
                             state='prepared', runtime_available=False))

    result = smoke(root, client, prepare_existing=prepare_existing, exercise=exercise, cases=('absent', 'dirty-git'))
    check(len({entry['project_id'] for entry in outcomes}) == 2, 'consumer_identity_collision')
    return dict(result, missions=outcomes, native_execution='not_run')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--client', choices=('claude', 'codex', 'both'), default='both')
    args = parser.parse_args()
    try:
        print(json.dumps(mission_smoke(args.root, args.client), ensure_ascii=True))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, KeyError):
        print(json.dumps(dict(state='failed', code='mission_foundation_smoke_failed')), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
