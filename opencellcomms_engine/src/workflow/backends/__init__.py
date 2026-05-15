"""Alternative workflow execution backends.

The default Python-direct executor (``WorkflowExecutor.execute_*``) handles
the ``biophysics`` kernel. Other kernels — notably ``physicell`` — bypass
the Python stage loop and run an external native binary instead. Each
backend module exposes a ``run(workflow, context) -> dict`` entry point
that the executor's ``execute_main`` hands off to when its kernel matches.
"""
