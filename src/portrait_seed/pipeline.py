import json
import time
from .errors import CloudError, PipelineError


def run_job(store, ident, generator, *, sleep=time.sleep):
    row = store.get(ident)
    if row['status'] == 'completed':
        return store.export(ident)
    # Verify reference BEFORE consuming an attempt or calling the provider.
    reference = store.reference(row['parent'])
    from .prompts import validate_description
    traits = json.loads(row['traits'])
    description = validate_description(json.loads(row['description']), traits)
    while True:
        store.begin_attempt(ident)
        try:
            image = generator.generate(description, traits, reference)
        except CloudError as error:
            attempts = store.get(ident)['attempts']
            retry = error.retryable and attempts < 3
            store.fail(ident, str(error), 'retryable' if retry else 'failed')
            if not retry:
                raise
            sleep(min(2 ** attempts, 8))
            continue
        # Local persistence failures NEVER trigger another paid request here.
        return store.complete(ident, image)

