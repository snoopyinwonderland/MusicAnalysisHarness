"""Stdlib-only, owned-process timing and evidence-preserving execution.

This module must load before any music21/analysis imports. Parent execution
summary never overwrites raw worker JSON or turns a late result into a timely
benchmark success. Timeout cleanup targets only this launch's live process.
"""
import argparse
import faulthandler
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from time import perf_counter_ns
import traceback
import uuid

VERSION = 'owned-harmony-execution-0.1.0'


def atomic_json(path, value):
    path = Path(path)
    pending = path.with_name(path.name + '.pending')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(pending, path)


def read_events(path, nonce):
    if not path.exists():
        return [], ['no_bootstrap_events']
    raw = path.read_bytes()
    rows, issues = [], []
    if raw and not raw.endswith(b'\n'):
        issues.append('incomplete_last_event_preserved')
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        if not line.endswith(b'\n'):
            continue
        try:
            row = json.loads(line)
        except (ValueError, UnicodeError):
            issues.append(f'invalid_event_line_{number}')
            continue
        if not isinstance(row, dict) or row.get('nonce') != nonce or row.get('sequence') != len(rows):
            issues.append(f'foreign_or_out_of_order_event_{number}')
            continue
        if (type(row.get('clock_ns')) is not int or type(row.get('pid')) is not int or
                row['pid'] <= 0 or not isinstance(row.get('event'), str) or
                (rows and (row['clock_ns'] < rows[-1]['clock_ns'] or row['pid'] != rows[0]['pid']))):
            issues.append(f'invalid_clock_or_identity_event_{number}')
            continue
        rows.append(row)
    if rows and rows[0]['event'] != 'bootstrap_enter':
        issues.append('missing_initial_bootstrap_enter')
    return rows, issues


def event_times(rows, launched, exited):
    by = {r['event']: r['clock_ns'] for r in rows}
    seconds = lambda start, end: (end-start)/1_000_000_000 if start is not None and end is not None and end >= start else None
    return dict(process_wall_seconds=seconds(launched, exited),
        bootstrap_startup_seconds=seconds(launched, by.get('bootstrap_enter')),
        module_load_seconds=seconds(by.get('module_load_begin'), by.get('module_loaded')),
        platform_query_seconds=seconds(by.get('platform_query_begin'), by.get('platform_query_returned')),
        worker_call_seconds=seconds(by.get('worker_begin'), by.get('worker_returned')),
        post_worker_process_seconds=seconds(by.get('worker_returned'), exited),
        clocks='perf_counter_ns_common_host', missing_end_is_unknown_not_zero=True)


def stop_owned_process(proc, stdout, stderr):
    """Bounded cleanup of a LIVE process we launched; never enumerate by name."""
    if proc.poll() is not None:
        return dict(method='already_exited', stopped=True)
    if os.name == 'nt':
        # Windows venv launchers may have a real Python child. This owned live
        # PID cannot have been reused. /T kills its tree, NOT other Python jobs.
        executable = Path(os.environ.get('SystemRoot', r'C:\Windows'))/'System32/taskkill.exe'
        try:
            result = subprocess.run([str(executable), '/PID', str(proc.pid), '/T', '/F'],
                stdout=stdout, stderr=stderr, timeout=5, check=False)
            method = dict(method='taskkill_owned_live_pid_tree', command_returncode=result.returncode)
        except (OSError, subprocess.TimeoutExpired) as exc:
            method = dict(method='owned_tree_cleanup_failed', error=type(exc).__name__)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # private start_new_session below
            method = dict(method='owned_new_session_kill')
        except OSError as exc:
            method = dict(method='owned_tree_cleanup_failed', error=type(exc).__name__)
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError as exc:
            method['fallback_kill_error'] = type(exc).__name__
    try:
        proc.wait(timeout=5)
        method['stopped'] = True
    except subprocess.TimeoutExpired:
        method['stopped'] = False
    method['tree_cleanup_confirmed'] = method['method'] == 'owned_new_session_kill' or method.get('command_returncode') == 0
    return method


def run_owned(argv, output, *, seconds, env=None, nonce=None):
    """The caller supplies the same fresh folder and nonce to the bootstrap."""
    if seconds <= 0:
        raise ValueError('nonpositive_process_deadline')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    nonce = nonce or uuid.uuid4().hex
    started = perf_counter_ns()
    launch = dict(version=VERSION, nonce=nonce, argv=[str(x) for x in argv],
        deadline_seconds=seconds, launched_clock_ns=started,
        raw_worker_result='worker.json', separate_execution_summary=True)
    atomic_json(output/'launch.json', launch)
    timed_out = False
    cleanup = None
    proc = None
    launch_error = None
    with (output/'stdout.txt').open('wb') as stdout, (output/'trace.txt').open('wb') as stderr:
        try:
            proc = subprocess.Popen([str(x) for x in argv], env=env,
                stdout=stdout, stderr=stderr, start_new_session=os.name != 'nt')
        except OSError as exc:
            launch_error = dict(type=type(exc).__name__, message=str(exc))
        if proc is not None:
            launch['launcher_pid'] = proc.pid
            atomic_json(output/'launch.json', launch)
        try:
            if proc is not None:
                remaining = seconds - (perf_counter_ns()-started)/1_000_000_000
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(argv, seconds)
                proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup = stop_owned_process(proc, stdout, stderr)
        except BaseException:
            if proc is not None:
                stop_owned_process(proc, stdout, stderr)
            raise
    exited = perf_counter_ns()
    events, issues = read_events(output/'events.jsonl', nonce)
    raw = output/'worker.json'
    worker = None
    raw_error = None
    if raw.exists():
        try:
            worker = json.loads(raw.read_text(encoding='utf-8'))
            if not isinstance(worker, dict):
                worker = None
                raw_error = 'non_object_worker_result'
        except (ValueError, UnicodeError) as exc:
            raw_error = type(exc).__name__
    returncode = proc.returncode if proc is not None else None
    if launch_error is not None:
        status = 'process_launch_error'
    elif timed_out:
        status = 'whole_process_timeout'
    elif returncode != 0:
        status = 'process_error'
    elif issues:
        status = 'execution_protocol_error'
    elif worker is not None:
        status = worker.get('status', 'unrecognized_worker_result')
    elif any(r['event'] == 'probe_returned' for r in events):
        status = 'probe_complete'
    else:
        status = 'missing_worker_result'
    eligible = (not timed_out and returncode == 0 and not issues and worker is not None and
        worker.get('status') == 'complete' and any(r['event'] == 'worker_returned' for r in events))
    summary = dict(version=VERSION, status=status, nonce=nonce, launcher_pid=proc.pid if proc is not None else None,
        worker_pid=events[0].get('pid') if events else None, process_returncode=returncode, launch_error=launch_error,
        timed_out=timed_out, cleanup=cleanup, prediction_eligible=eligible,
        worker_result_present=raw.exists(), worker_status=worker.get('status') if worker else None,
        raw_result_parse_error=raw_error, raw_result_sha256=hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None,
        event_issues=issues, timings=event_times(events,started,exited),
        eligibility_scope='execution_only_not_music_accuracy_or_contract_validation')
    atomic_json(output/'execution.json', summary)
    return summary


def child(output, nonce, action, source=None, *, windows_label=False):
    sequence = 0
    def emit(event, **facts):
        nonlocal sequence
        row = dict(nonce=nonce, sequence=sequence, event=event, clock_ns=perf_counter_ns(),
            pid=os.getpid(), parent_pid=os.getppid(), **facts)
        with (output/'events.jsonl').open('a', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
            handle.flush()
        sequence += 1

    emit('bootstrap_enter', action=action, executable=sys.executable,
        base_executable=sys._base_executable, python_version=sys.version,
        sys_prefix=sys.prefix, os_name=os.name, sys_platform=sys.platform)
    faulthandler.enable()
    faulthandler.dump_traceback_later(5, repeat=True)
    try:
        if action == 'noop':
            emit('probe_returned', no_music_analysis=True)
            return
        emit('module_load_begin', windows_label_requested=windows_label)
        if action == 'platform_system':
            import platform
            emit('module_loaded')
            emit('platform_query_begin')
            value = platform.system()
            emit('platform_query_returned', system=value)
            emit('probe_returned', no_music_analysis=True)
            return
        if action not in ('engine_import', 'intervals', 'compiled'):
            raise ValueError('unrecognized_execution_action')
        from .harmony_windows_import import isolated_windows_label
        module_name = ('harmony_whole_score_intervals' if action != 'compiled'
                       else 'harmony_phase_checkpoint')
        with isolated_windows_label(windows_label) as guard:
            module = importlib.import_module('musicanote_harness.'+module_name)
        emit('module_loaded', windows_label=guard)
        if action == 'engine_import':
            from music21 import common
            emit('probe_returned', music21_os_label=common.getPlatform(),
                no_music_analysis=True, windows_label=guard)
            return
        if source is None:
            raise ValueError('analysis_source_missing')
        emit('worker_begin', source_file=str(source))
        if action == 'compiled':
            module.worker(source, output/'worker.json', implementation='compiled')
        else:
            module.worker(source, output/'worker.json')
        emit('worker_returned')
    except BaseException as exc:
        emit('bootstrap_error', error=type(exc).__name__)
        traceback.print_exc()
        raise
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--child', type=Path, required=True)
    ap.add_argument('--nonce', required=True)
    ap.add_argument('--action', choices=('noop','platform_system','engine_import','intervals','compiled'), required=True)
    ap.add_argument('--source', type=Path)
    ap.add_argument('--windows-label', action='store_true')
    args=ap.parse_args()
    child(args.child.resolve(),args.nonce,args.action,args.source,windows_label=args.windows_label)
