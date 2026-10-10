"""Persistent one-PBI rehearsal. No native dispatch or real delivery acceptance."""
import hashlib
import json
import uuid

from capabilities import canonical, text
from mission_backlog import identity, require
import mission_runs
import mission_store as store

QUEUE_VERSION = 1
ACTIVE = ('dev_pending', 'qa_pending')
SCHEMA = (
    'CREATE TABLE queue_sessions (id TEXT PRIMARY KEY, mission_id TEXT NOT NULL REFERENCES records(id), mission_revision INTEGER NOT NULL, revision INTEGER NOT NULL, state TEXT NOT NULL, snapshot TEXT NOT NULL, UNIQUE(mission_id,mission_revision))',
    "CREATE UNIQUE INDEX queue_one_active ON queue_sessions ((1)) WHERE state IN ('dev_pending','qa_pending')",
    'CREATE TABLE queue_events (seq INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT UNIQUE NOT NULL, request_hash TEXT NOT NULL, session_id TEXT NOT NULL REFERENCES queue_sessions(id), revision INTEGER NOT NULL, receipt TEXT NOT NULL)',
)


def migrate(conn):
    mission_runs.migrate(conn)
    if conn.execute('SELECT schema_version FROM metadata').fetchone()[0] == 2:
        for statement in SCHEMA:
            conn.execute(statement)
        conn.execute('UPDATE metadata SET schema_version=3')


def available(conn):
    return conn is not None and conn.execute('SELECT schema_version FROM metadata').fetchone()[0] == 3


def sessions(root, mission_id):
    with store.reader(root) as conn:
        return read_sessions(conn, mission_id)


def read_sessions(conn, mission_id):
    if not available(conn):
        return []
    result = []
    for row in conn.execute('SELECT snapshot FROM queue_sessions WHERE mission_id=? ORDER BY rowid', (mission_id,)):
        session = json.loads(row[0])
        session['events'] = [json.loads(event[0]) for event in conn.execute(
            'SELECT receipt FROM queue_events WHERE session_id=? ORDER BY seq', (session['id'],))]
        result.append(session)
    return result


def view(result, status):
    for session in result:
        reason = ('cancel_stale_rehearsal' if session['mission_revision'] != status['revision'] else
                  status['next_action'] if not status['check_available'] else None)
        if session['state'] not in ACTIVE:
            reason = None
        session['blocked_reason'] = reason
        session['next_action'] = ((reason or 'step_rehearsal') if session['state'] in ACTIVE else
                                 'rehearsal_complete' if session['state'] == 'fixture_completed' else 'rehearsal_cancelled')
    return result


def fixture_result(session):
    """Closed pure adapter: hashes frozen input; never invokes an agent or tool."""
    role = session['next_role']
    if role == 'qa':
        developer = session['results'][0]
        observed = developer['output_sha256']
        payload = {key: value for key, value in developer.items() if key != 'output_sha256'}
        require(observed == hashlib.sha256(canonical(payload)).hexdigest(), 'invalid_fixture_result')
    previous = session['results'][-1]['output_sha256'] if session['results'] else None
    payload = dict(fixture_id='queue-v1', scope='deterministic_rehearsal', role=role,
                   candidate_id=session['candidate_id'], pbi_id=session['pbi_id'],
                   pbi_revision=session['pbi_revision'], input_sha256=session['input_sha256'],
                   previous_output_sha256=previous)
    return dict(payload, output_sha256=hashlib.sha256(canonical(payload)).hexdigest())


def apply(root, action, identifier, expected_revision, operation_id, actor_id):
    import missions
    require(action in ('start', 'step', 'cancel'), 'invalid_arguments')
    require(text(identifier, 200) and identifier.strip(), 'invalid_identity')
    identity(operation_id)
    require(text(actor_id, 200) and actor_id.strip(), 'invalid_actor')
    require(type(expected_revision) is int and expected_revision > 0, 'invalid_revision')
    digest = hashlib.sha256(canonical(dict(action=action, identifier=identifier,
        expected_revision=expected_revision, actor_id=actor_id))).hexdigest()
    with store.transaction(root) as conn:
        if available(conn):
            row = conn.execute('SELECT request_hash,receipt FROM queue_events WHERE operation_id=?', (operation_id,)).fetchone()
            if row:
                require(row[0] == digest, 'operation_conflict')
                return json.loads(row[1])
        if action == 'start':
            status = missions.mission_status(root, identifier)
            require('id' in status, 'unknown_mission')
            require(status['revision'] == expected_revision, 'revision_conflict')
            if available(conn):
                require(not conn.execute('SELECT 1 FROM queue_sessions WHERE mission_id=? AND mission_revision=?',
                                         (status['id'], expected_revision)).fetchone(), 'queue_already_started')
                require(not conn.execute('SELECT 1 FROM queue_sessions WHERE state IN (?,?)', ACTIVE).fetchone(), 'queue_busy')
            require(status['check_available'], 'mission_not_ready')
            items = status['queue_preview']['items']
            require(len(items) == 1 and not items[0]['dependencies'], 'unsupported_queue_scope')
            session_id = str(uuid.uuid4())
            session = dict(schema_version=1, id=session_id, mission_id=status['id'],
                mission_revision=expected_revision, pbi_id=items[0]['id'], pbi_revision=items[0]['revision'],
                pbi_code=items[0]['code'], scope='deterministic_rehearsal', state='dev_pending', revision=1,
                next_role='developer', candidate_id=str(uuid.uuid5(uuid.UUID(session_id), 'developer')),
                input_sha256=hashlib.sha256(canonical(status['snapshot'])).hexdigest(), results=[],
                created_at=missions.utc_now(), runtime_available=False, runnable=False)
            migrate(conn)
            conn.execute('INSERT INTO queue_sessions VALUES(?,?,?,?,?,?)',
                         (session_id, status['id'], expected_revision, 1, session['state'], canonical(session).decode()))
        else:
            identity(identifier)
            require(available(conn), 'unknown_queue_session')
            row = conn.execute('SELECT snapshot FROM queue_sessions WHERE id=?', (identifier,)).fetchone()
            require(row is not None, 'unknown_queue_session')
            session = json.loads(row[0])
            require(session['revision'] == expected_revision, 'revision_conflict')
            require(session['state'] in ACTIVE, 'invalid_transition')
            if action == 'cancel':
                session.update(state='cancelled', next_role=None, candidate_id=None)
            else:
                status = missions.mission_status(root, session['mission_id'])
                require(status.get('revision') == session['mission_revision'], 'revision_conflict')
                require(status['check_available'], 'mission_not_ready')
                session['results'].append(fixture_result(session))
                developer = session['state'] == 'dev_pending'
                session.update(state='qa_pending' if developer else 'fixture_completed',
                               next_role='qa' if developer else None,
                               candidate_id=str(uuid.uuid5(uuid.UUID(session['id']), 'qa')) if developer else None)
            session['revision'] += 1
        session['updated_at'] = missions.utc_now()
        conn.execute('UPDATE queue_sessions SET revision=?,state=?,snapshot=? WHERE id=?',
                     (session['revision'], session['state'], canonical(session).decode(), session['id']))
        receipt = dict(schema_version=1, operation_id=operation_id, action=action, actor_id=actor_id, session=session)
        cursor = conn.execute('INSERT INTO queue_events(operation_id,request_hash,session_id,revision,receipt) VALUES(?,?,?,?,?)',
                             (operation_id, digest, session['id'], session['revision'], canonical(receipt).decode()))
        receipt['sequence'] = cursor.lastrowid
        conn.execute('UPDATE queue_events SET receipt=? WHERE seq=?', (canonical(receipt).decode(), cursor.lastrowid))
        return receipt
