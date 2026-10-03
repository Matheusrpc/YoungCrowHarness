"""Offline declarations for mission agents. No credential or provider access."""
import copy
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re

from capabilities import canonical, parse_json, read_inputs

ROLES = ('pm', 'tech_lead', 'developer', 'qa')
OPTIONAL_ROLES = ('integration_specialist',)
CONFIG_PATH = 'youngcrow/agents.json'
LIMITS = dict(max_active_pbis=3, max_parallel_agents=3, max_correction_cycles=3,
              mission_active_seconds=None, agent_seconds=None, max_agent_runs=None,
              max_deploy_attempts=None, api_budget_usd=None)
AGENT = dict(client=None, connection='authenticated', model=None,
             effort=dict(level=None, native_value=None), credential_env=None, capabilities=[])


def require(condition):
    if not condition:
        raise ValueError('invalid_config')


def fields(value, allowed):
    require(isinstance(value, dict) and set(value) <= set(allowed))


def string(value):
    return isinstance(value, str) and 0 < len(value) <= 256 and all(ord(c) >= 32 for c in value)


def normalize_config(raw: dict) -> dict:
    fields(raw, ('schema_version', 'agents', 'limits', 'deploy_mode'))
    require(type(raw.get('schema_version')) is int and raw['schema_version'] == 1)
    agents = raw.get('agents')
    fields(agents, ROLES + OPTIONAL_ROLES)
    require(set(ROLES) <= set(agents))
    result = dict(schema_version=1, agents={}, limits=copy.deepcopy(LIMITS),
                  deploy_mode=raw.get('deploy_mode', 'manual'))
    require(result['deploy_mode'] in ('manual', 'automatic'))
    for role, data in agents.items():
        fields(data, AGENT)
        agent = copy.deepcopy(AGENT)
        agent.update(copy.deepcopy(data))
        require(agent['client'] in (None, 'codex', 'claude'))
        require(agent['connection'] in ('authenticated', 'api'))
        require(agent['model'] is None or string(agent['model']))
        fields(agent['effort'], ('level', 'native_value'))
        effort = dict(level=None, native_value=None)
        effort.update(agent['effort'])
        require(effort['level'] in (None, 'low', 'medium', 'high', 'native'))
        require(string(effort['native_value']) if effort['level'] == 'native' else effort['native_value'] is None)
        agent['effort'] = effort
        env = agent['credential_env']
        require(env is None or (isinstance(env, str) and len(env) <= 256 and re.fullmatch(r'[A-Z][A-Z0-9_]*', env)))
        require(agent['connection'] == 'api' or env is None)
        caps = agent['capabilities']
        require(isinstance(caps, list) and all(string(c) for c in caps))
        require(len(caps) == len(set(caps)))
        result['agents'][role] = agent
    limits = raw.get('limits', {})
    fields(limits, LIMITS)
    result['limits'].update(copy.deepcopy(limits))
    for name, value in result['limits'].items():
        if name == 'api_budget_usd':
            if value is not None:
                require(isinstance(value, str) and len(value) <= 64 and re.fullmatch(r'\d+(?:\.\d+)?', value))
                try:
                    require(Decimal(value).is_finite() and Decimal(value) > 0)
                except InvalidOperation:
                    raise ValueError('invalid_config') from None
        else:
            require((value is None and LIMITS[name] is None) or (type(value) is int and value > 0))
    require(result['limits']['max_correction_cycles'] == 3)
    return result


def load_config(root: Path) -> dict:
    try:
        return normalize_config(parse_json(read_inputs(root, [CONFIG_PATH])[CONFIG_PATH]))
    except (ValueError, OSError, UnicodeError, TypeError, KeyError):
        raise ValueError('invalid_config') from None


def effective_config(defaults: dict, overrides: dict) -> dict:
    result = normalize_config(defaults)
    fields(overrides, ('agents', 'limits', 'deploy_mode'))
    if 'agents' in overrides:
        fields(overrides['agents'], result['agents'])
        for role, patch in overrides['agents'].items():
            fields(patch, AGENT)
            for key, value in patch.items():
                if key == 'effort':
                    fields(value, ('level', 'native_value'))
                    result['agents'][role][key].update(copy.deepcopy(value))
                else:
                    result['agents'][role][key] = copy.deepcopy(value)
    if 'limits' in overrides:
        fields(overrides['limits'], LIMITS)
        result['limits'].update(copy.deepcopy(overrides['limits']))
    if 'deploy_mode' in overrides:
        result['deploy_mode'] = overrides['deploy_mode']
    return normalize_config(result)


def config_digest(config: dict) -> str:
    return hashlib.sha256(canonical(normalize_config(config))).hexdigest()


def config_gaps(config: dict) -> list[str]:
    config = normalize_config(config)
    gaps = []
    for role, agent in config['agents'].items():
        for key in ('client', 'model'):
            if agent[key] is None:
                gaps.append(f'agents.{role}.{key}')
        if agent['effort']['level'] is None:
            gaps.append(f'agents.{role}.effort.level')
        if agent['connection'] == 'api' and agent['credential_env'] is None:
            gaps.append(f'agents.{role}.credential_env')
    for key, value in config['limits'].items():
        if value is None and (key != 'api_budget_usd' or any(a['connection'] == 'api' for a in config['agents'].values())):
            gaps.append('limits.' + key)
    return gaps
