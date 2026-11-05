"""Small terminal entry points, no user interface or background service."""
import argparse
import json
import sys
from .errors import PipelineError
from .prompts import DEFAULT_TRAITS, KEYS


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local camera analysis to a saved fictional portrait.')
    parser.add_argument('--data', default='private-data', help='Private output directory, never commit it')
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('describe', 'generate'):
        sub = commands.add_parser(command)
        sub.add_argument('--camera', type=int, default=0)
        sub.add_argument('--traits', default=','.join(DEFAULT_TRAITS))
        sub.add_argument('--consent', action='store_true', help='Confirm participants agreed to capture and processing')
        if command == 'generate':
            sub.add_argument('--allow-paid', action='store_true', help='Allow at most three chargeable attempts')
    sub = commands.add_parser('resume')
    sub.add_argument('job')
    sub.add_argument('--allow-paid', action='store_true')
    sub = commands.add_parser('export')
    sub.add_argument('job')
    commands.add_parser('list')
    commands.add_parser('doctor')
    args = parser.parse_args(argv)
    store = generator = None
    try:
        if args.command == 'doctor':
            import httpx
            with httpx.Client(trust_env=False, follow_redirects=False, timeout=3) as client:
                healthy = client.get('http://127.0.0.1:8795/health').status_code == 200
            print('Local service ready.' if healthy else 'Local service not ready.')
            return 0 if healthy else 1
        if args.command in ('generate','resume'):
            if not args.allow_paid:
                raise PipelineError('paid_permission_required')
            from .cloud import ImageGenerator
            generator = ImageGenerator()  # Check credentials before opening the camera.
        if args.command in ('describe','generate'):
            if not args.consent:
                raise PipelineError('participant_consent_required')
            keys = args.traits.split(',')
            if not keys or len(keys) != len(set(keys)) or not set(keys) <= KEYS:
                raise PipelineError('invalid_traits')
            traits = [{'key':key} for key in keys]
        from .store import Store
        store = Store(args.data)
        if args.command in ('describe','generate'):
            from .capture import capture_description
            captured_at, description = capture_description(args.camera, traits)
            ident = store.create(captured_at, description, traits)
            print('Job:', ident, flush=True)
            if args.command == 'describe':
                return 0
        elif args.command == 'resume':
            ident = args.job
        elif args.command == 'list':
            rows = store.db.execute('SELECT id,status,attempts,error FROM jobs ORDER BY captured_at').fetchall()
            print(json.dumps([dict(row) for row in rows], indent=2))
            return 0
        elif args.command == 'export':
            print(store.export(args.job))
            return 0
        from .pipeline import run_job
        print(run_job(store, ident, generator))
        return 0
    except KeyboardInterrupt:
        print('Interrupted. A submitted cloud request may still be charged.', file=sys.stderr)
        return 130
    except PipelineError as error:
        print('Stopped:', str(error), file=sys.stderr)
        return 1
    except Exception:
        # Upstream errors can contain payloads, paths or secrets. Do not echo them.
        print('Stopped: local_or_dependency_error. See docs/TROUBLESHOOTING.md.', file=sys.stderr)
        return 1
    finally:
        if generator is not None:
            generator.close()
        if store is not None:
            store.close()
